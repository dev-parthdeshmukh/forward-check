"""Records the Telegram bot in Telegram Web (Chrome, phone-sized): a Hindi text forward, a voice message
spoken through a fake microphone, and the Listen button. Uses the Chrome profile that is logged in to Telegram.

usage: rec_tg.py [text] [voice] [listen]
"""
import asyncio
import sys

import httpx
from playwright.async_api import async_playwright

from common import BOT, BUILD, PROFILE, TG_PORT
from rec import Recorder

WIDTH, HEIGHT, SCALE = 400, 860, 2.5
SCHEME = ("🔥 बड़ी खुशखबरी 🔥 प्रधानमंत्री फ्री लैपटॉप योजना 2026 के तहत सरकार सभी छात्रों को मुफ्त लैपटॉप दे रही है। "
          "10वीं पास सभी छात्र आवेदन कर सकते हैं। अभी रजिस्टर करें: http://pm-laptop-yojana.xyz "
          "आखिरी तारीख कल है, जल्दी करें और सभी ग्रुप में भेजें 🙏")
VOICE_SECONDS = 17.4
INPUT = ".input-message-input:not(.input-field-input-fake)"
ANSWERS = ".bubble.is-in.with-reply-markup"

# Hides the chat's earlier messages (they stay in Telegram) so the recording starts on a clean chat.
HIDE_OLDER = """threshold => {
    const sweep = () => {
        for (const b of document.querySelectorAll('.bubble[data-mid]')) if (+b.dataset.mid <= threshold) b.style.display = 'none';
        for (const g of document.querySelectorAll('.bubbles-group'))
            if (![...g.querySelectorAll('.bubble')].some(b => b.style.display !== 'none')) g.style.display = 'none';
    };
    sweep();
    new MutationObserver(sweep).observe(document.querySelector('.bubbles'), {childList: true, subtree: true});
}"""
TAG_SCROLLER = """() => {
    const all = [...document.querySelectorAll('.bubble[data-mid]')];
    let s = all[all.length - 1];
    while (s && !s.classList.contains('scrollable-y')) s = s.parentElement;
    s.setAttribute('data-fc-scroll', '1');
}"""
BUBBLE_TOP = """sel => {
    const s = document.querySelector('[data-fc-scroll]');
    const all = document.querySelectorAll(sel);
    const b = all[all.length - 1];
    return s.scrollTop + b.getBoundingClientRect().top - s.getBoundingClientRect().top - 84;
}"""


async def count(page, selector: str) -> int:
    return await page.locator(selector).count()


async def wait_more(page, selector: str, before: int, timeout: float) -> bool:
    try:
        await page.wait_for_function("([s, n]) => document.querySelectorAll(s).length > n", arg=[selector, before], timeout=timeout * 1000)
        return True
    except Exception:
        return False


async def await_answer(page, rec: Recorder, name: str, replies: int, answers: int) -> bool:
    if await wait_more(page, ".bubble.is-in", replies, 60):
        rec.mark(f"{name}_status")
    done = await wait_more(page, ANSWERS, answers, 420)
    rec.mark(f"{name}_result" if done else f"{name}_TIMEOUT")
    if done:
        text = await page.locator(ANSWERS).last.inner_text()
        print("  answer:", text[:160].replace("\n", " | "), flush=True)
    return done


async def read_answer(page, rec: Recorder, name: str) -> None:
    """Shows the answer from its first line, then lets it run to the end."""
    await rec.hold(1.2)
    await rec.scroll("[data-fc-scroll]", await page.evaluate(BUBBLE_TOP, ANSWERS), 0.8)
    rec.mark(f"{name}_top")
    await rec.hold(2.4)
    await rec.scroll("[data-fc-scroll]", "end", 1.3)
    rec.mark(f"{name}_end")
    await rec.hold(2.0)


async def main() -> None:
    which = sys.argv[1:] or ["text", "voice", "listen"]
    try:  # the profile can only be open in one Chrome at a time
        async with async_playwright() as p:
            headed = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{TG_PORT}")
            await (await headed.new_browser_cdp_session()).send("Browser.close")
        await asyncio.sleep(4)
    except Exception:
        pass
    assert not _port_open(), "the recording Chrome window is still open"

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            PROFILE, channel="chrome", headless=True, viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=SCALE, permissions=["microphone"], locale="en-IN",
            args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                  f"--use-file-for-fake-audio-capture={BUILD / 'inputs' / 'mic.wav'}%noloop"])
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(f"https://web.telegram.org/k/#@{BOT}")
        await page.wait_for_selector(".bubble[data-mid]", timeout=60_000)
        await page.wait_for_timeout(3000)
        print("chat:", await page.locator(".chat-info .peer-title").first.inner_text())

        newest = await page.evaluate("() => Math.max(...[...document.querySelectorAll('.bubble[data-mid]')].map(b => +b.dataset.mid))")
        await page.evaluate(HIDE_OLDER, newest)
        await page.evaluate(TAG_SCROLLER)
        replies = await count(page, ".bubble.is-in")
        await page.locator(INPUT).click()
        await page.keyboard.insert_text("/start")
        await page.keyboard.press("Enter")
        await wait_more(page, ".bubble.is-in", replies, 30)
        await page.wait_for_timeout(2000)

        rec = Recorder(page, BUILD / "rec" / "telegram", WIDTH, HEIGHT, SCALE)
        await rec.start()
        await rec.hold(1.2)

        if "text" in which:
            replies, answers = await count(page, ".bubble.is-in"), await count(page, ANSWERS)
            await rec.click(page.locator(INPUT), kind="tap")
            await page.keyboard.insert_text(SCHEME)
            rec.mark("text_pasted")
            await rec.hold(1.0)
            await rec.click(page.locator(".btn-send"), kind="tap")
            rec.mark("text_sent")
            if await await_answer(page, rec, "text", replies, answers):
                await read_answer(page, rec, "text")

        if "voice" in which:
            replies, answers = await count(page, ".bubble.is-in"), await count(page, ANSWERS)
            await rec.click(page.locator(".btn-send"), kind="tap")
            rec.mark("voice_recording")
            await rec.hold(VOICE_SECONDS)
            await rec.click(page.locator(".btn-send"), kind="tap", pause=0.3)
            rec.mark("voice_sent")
            if await await_answer(page, rec, "voice", replies, answers):
                await read_answer(page, rec, "voice")

        if "listen" in which and await count(page, ANSWERS):
            replies = await count(page, ".bubble.is-in")
            await rec.click(page.locator(ANSWERS).last.locator(".reply-markup-button").first, kind="tap")
            rec.mark("listen_tapped")
            if await wait_more(page, ".bubble.is-in", replies, 60):
                rec.mark("listen_audio")
                await rec.hold(0.8)
                await rec.scroll("[data-fc-scroll]", "end", 0.7)
                await rec.hold(2.5)

        await rec.stop()
        await context.close()


def _port_open() -> bool:
    try:
        return httpx.get(f"http://127.0.0.1:{TG_PORT}/json/version", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


asyncio.run(main())
