"""Forward Check as a Telegram bot: forward it a message and it replies with the verdict.

    python -m bot.telegram_bot

Needs TELEGRAM_BOT_TOKEN in .env (create a bot with @BotFather in Telegram to get one).
Uses long polling, so it needs no public address.
"""
import html
import logging
import sys
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from app import config, i18n, service, tts
from app.ingest import IngestError
from app.llm import LLMError
from app.schemas import CheckResult, Verdict

log = logging.getLogger("forward_check.bot")

API = "https://api.telegram.org"
EMOJI = {
    Verdict.VERIFIED: "✅", Verdict.FALSE: "❌", Verdict.OUTDATED: "🕒",
    Verdict.PARTLY_SUPPORTED: "🟡", Verdict.UNVERIFIABLE: "❔",
}
MESSAGE_LIMIT = 4096
# Telegram allows about one edit a second per message; progress updates are spaced wider than that.
EDIT_EVERY_SECONDS = 2.5
SPOKEN_KEPT = 200  # replies whose Listen button still works
MAX_SOURCES = 4


def esc(text: str) -> str:
    return html.escape(text or "", quote=False)


def extract_input(message: dict) -> dict | None:
    """What to check in a Telegram message: {"text": ...} or {"file_id": ..., "filename": ...}."""
    if message.get("photo"):
        return {"file_id": message["photo"][-1]["file_id"], "filename": "photo.jpg"}  # last is the largest
    if message.get("voice"):
        return {"file_id": message["voice"]["file_id"], "filename": "voice.ogg"}
    if message.get("audio"):
        audio = message["audio"]
        return {"file_id": audio["file_id"], "filename": audio.get("file_name") or "audio.mp3"}
    if message.get("document"):
        document = message["document"]
        return {"file_id": document["file_id"], "filename": document.get("file_name") or "file"}
    text = (message.get("text") or message.get("caption") or "").strip()
    return {"text": text} if text else None


def format_reply(result: CheckResult) -> str:
    """The answer as Telegram HTML, shortened to fit one message."""
    code = result.reply_language_code
    if not result.claims:
        return esc(result.summary)

    lines = [f"{EMOJI[result.overall_verdict]} <b>{esc(result.overall_label)}</b>"]
    several = len(result.claims) > 1
    for number, item in enumerate(result.claims, start=1):
        lines.append("")
        if several:
            lines.append(f"<b>{number}. {EMOJI[item.verdict]} {esc(item.verdict_label)}</b>")
            lines.append(f"<i>“{esc(item.claim.original_span or item.claim.text)}”</i>")
        lines.append(esc(item.explanation))
        if item.what_is_wrong:
            lines.append(f"✗ <b>{esc(i18n.bot_text('wrong', code))}:</b> {esc(item.what_is_wrong)}")
        if item.correct_information:
            lines.append(f"✓ <b>{esc(i18n.bot_text('true', code))}:</b> {esc(item.correct_information)}")

    if result.risk_flags:
        lines += ["", f"⚠️ <b>{esc(i18n.bot_text('warning', code))}</b>"]
        lines += [f"• {esc(flag.message)}" for flag in result.risk_flags]

    sources: OrderedDict[str, str] = OrderedDict()
    for item in result.claims:
        for ev in item.evidence:
            if ev.tier != "other" and urlsplit(ev.url).scheme in ("http", "https"):
                sources.setdefault(ev.url, ev.source_name or ev.domain)
    source_lines = [f'• <a href="{html.escape(url)}">{esc(name)}</a>' for url, name in list(sources.items())[:MAX_SOURCES]]

    body = "\n".join(lines)
    tail = "\n".join(["", f"<b>{esc(i18n.bot_text('sources', code))}</b>", *source_lines]) if source_lines else ""
    room = MESSAGE_LIMIT - len(tail) - 1
    if len(body) > room:
        # Cut at a line break so no HTML tag is left open, and keep the sources.
        body = body[:room].rsplit("\n", 1)[0] + "\n…"
    return body + ("\n" + tail if tail else "")


def spoken_text(result: CheckResult) -> str:
    parts = [f"{result.overall_label}."]
    for item in result.claims:
        parts += [item.explanation, item.correct_information]
    text = ""
    for part in filter(None, parts):
        if len(text) + len(part) + 1 > tts.MAX_CHARS:
            break
        text += (" " if text else "") + part
    return text


class Bot:
    def __init__(self, token: str) -> None:
        self.base = f"{API}/bot{token}"
        self.files = f"{API}/file/bot{token}"
        self.http = httpx.Client(timeout=70)
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.languages: dict[int, str] = {}  # chat id -> reply language chosen with /lang
        self.spoken: OrderedDict[str, tuple[str, str]] = OrderedDict()  # "chat:message" -> (text, language)
        self.lock = threading.Lock()

    def call(self, method: str, **params) -> dict:
        response = self.http.post(f"{self.base}/{method}", json=params)
        payload = response.json()
        if not payload.get("ok"):
            raise httpx.HTTPError(f"{method}: {payload.get('description')}")
        return payload["result"]

    def download(self, file_id: str) -> bytes:
        path = self.call("getFile", file_id=file_id)["file_path"]
        response = self.http.get(f"{self.files}/{path}")
        response.raise_for_status()
        return response.content

    def run(self) -> None:
        me = self.call("getMe")
        print(f"Forward Check bot is running as @{me['username']}. Press Ctrl+C to stop.")
        offset = 0
        while True:
            try:
                updates = self.call("getUpdates", offset=offset, timeout=50, allowed_updates=["message", "callback_query"])
            except httpx.HTTPError as exc:
                log.warning("polling failed: %s", exc)
                time.sleep(5)
                continue
            for update in updates:
                offset = update["update_id"] + 1
                if "message" in update:
                    self.pool.submit(self.safely, self.on_message, update["message"])
                elif "callback_query" in update:
                    self.pool.submit(self.safely, self.on_listen, update["callback_query"])

    def safely(self, handler, payload: dict) -> None:
        try:
            handler(payload)
        except Exception:  # one bad update must not take the bot down
            log.exception("update failed")

    def chat_language(self, chat_id: int) -> str:
        return self.languages.get(chat_id, "auto")

    def ui_language(self, chat_id: int, message: dict) -> str:
        """Language for the bot's own short messages before the message's language is known."""
        chosen = self.chat_language(chat_id)
        return chosen if chosen != "auto" else (message.get("from", {}).get("language_code") or "en")[:2]

    def on_message(self, message: dict) -> None:
        chat_id = message["chat"]["id"]
        ui = self.ui_language(chat_id, message)
        text = (message.get("text") or "").strip()
        if text.startswith(("/start", "/help")):
            self.call("sendMessage", chat_id=chat_id, text=i18n.bot_text("welcome", ui))
            return
        if text.startswith("/lang"):
            choice = i18n.reply_key(text.partition(" ")[2])
            if choice != "auto" and choice not in i18n.LANGUAGE_NAMES:
                self.call("sendMessage", chat_id=chat_id, text=i18n.bot_text("lang_help", ui))
                return
            self.languages[chat_id] = choice
            name = i18n.LANGUAGE_NAMES.get(choice, "Auto")
            self.call("sendMessage", chat_id=chat_id, text=i18n.bot_text("lang_set", choice, name=name))
            return

        given = extract_input(message)
        if not given:
            self.call("sendMessage", chat_id=chat_id, text=i18n.bot_text("unsupported", ui))
            return

        status = self.call("sendMessage", chat_id=chat_id, text=i18n.bot_text("start", ui),
                           reply_to_message_id=message["message_id"])
        last_edit = 0.0

        def progress(event: dict) -> None:
            nonlocal ui, last_edit
            if event["type"] == "claims":
                ui = event["reply_language_code"]
                line = i18n.bot_text("claims", ui, n=len(event["claims"]))
            elif event["type"] == "step":
                detail = event["detail"] if event["action"] == "search" else urlsplit(event["detail"]).hostname or ""
                line = i18n.bot_text(event["action"], ui, detail=detail)
            else:
                return
            if event["type"] == "step" and time.time() - last_edit < EDIT_EVERY_SECONDS:
                return
            last_edit = time.time()
            try:
                self.call("editMessageText", chat_id=chat_id, message_id=status["message_id"], text=line[:300])
            except httpx.HTTPError:
                pass  # a missed progress line does not matter; the answer still follows

        try:
            if "text" in given:
                result = service.run_check(text=given["text"], reply_language=self.chat_language(chat_id), on_event=progress)
            else:
                data = self.download(given["file_id"])
                result = service.run_check(file=(given["filename"], data), reply_language=self.chat_language(chat_id), on_event=progress)
        except IngestError as exc:
            self.call("editMessageText", chat_id=chat_id, message_id=status["message_id"], text=str(exc))
            return
        except (LLMError, httpx.HTTPError) as exc:
            log.warning("check failed: %s", exc)
            self.call("editMessageText", chat_id=chat_id, message_id=status["message_id"], text=i18n.bot_text("error", ui))
            return

        code = result.reply_language_code
        extra = {}
        if result.claims and code in tts.VOICES:
            key = f"{chat_id}:{status['message_id']}"
            with self.lock:
                self.spoken[key] = (spoken_text(result), code)
                while len(self.spoken) > SPOKEN_KEPT:
                    self.spoken.popitem(last=False)
            extra["reply_markup"] = {"inline_keyboard": [[{"text": i18n.bot_text("listen", code), "callback_data": "listen"}]]}
        self.call("editMessageText", chat_id=chat_id, message_id=status["message_id"], text=format_reply(result),
                  parse_mode="HTML", disable_web_page_preview=True, **extra)

    def on_listen(self, query: dict) -> None:
        self.call("answerCallbackQuery", callback_query_id=query["id"])
        message = query.get("message") or {}
        chat_id = message.get("chat", {}).get("id")
        with self.lock:
            entry = self.spoken.get(f"{chat_id}:{message.get('message_id')}")
        if not entry:
            return  # the bot restarted, or the reply is too old to read out
        text, code = entry
        try:
            audio = tts.synthesize(text, code)
        except tts.TTSError as exc:
            log.warning("speech failed: %s", exc)
            return
        response = self.http.post(
            f"{self.base}/sendAudio",
            data={"chat_id": chat_id, "reply_to_message_id": message["message_id"], "title": "Forward Check"},
            files={"audio": ("forward-check.mp3", audio, "audio/mpeg")},
        )
        response.raise_for_status()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # its request log would print the bot token
    if not config.TELEGRAM_BOT_TOKEN:
        sys.exit(f"TELEGRAM_BOT_TOKEN is not set. Create a bot with @BotFather and add the token to {Path('.env').resolve()}")
    try:
        Bot(config.TELEGRAM_BOT_TOKEN).run()
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
