"""Claude through the Claude Code CLI in headless mode (runs on the logged-in subscription).

The default Claude Code system prompt and tool set cost ~37K tokens per call, so every call
replaces the system prompt and names only the tools it needs.
"""
import base64
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from .. import config
from .base import Attachment, LLMBackend, LLMError, OnStep, ResearchResult

_URL_RE = re.compile(r"https?://[^\s\"'\\<>\]\)]+")
_WEB_TOOLS = "WebSearch,WebFetch"


def _find_cli() -> str:
    if config.CLAUDE_CLI_PATH:
        return config.CLAUDE_CLI_PATH
    # Prefer a real .exe over the npm .cmd shim: arguments pass through without cmd.exe quoting.
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = glob.glob(os.path.join(local, "Microsoft", "WinGet", "Packages", "Anthropic.ClaudeCode*", "claude.exe"))
    candidates.append(str(Path.home() / ".local" / "bin" / "claude.exe"))
    for path in candidates:
        if os.path.isfile(path):
            return path
    found = shutil.which("claude.exe") or shutil.which("claude")
    if not found:
        raise LLMError("Claude Code CLI not found. Install it or set CLAUDE_CLI_PATH.")
    return found


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


class ClaudeCLIBackend(LLMBackend):
    name = "claude_cli"

    def __init__(self) -> None:
        super().__init__()
        self.exe = _find_cli()
        # An empty working directory keeps project settings and CLAUDE.md files out of the call.
        self.cwd = tempfile.mkdtemp(prefix="forward-check-")

    def _run(self, system: str, prompt: str, schema: dict, effort: str, tools: str, timeout: int,
             attachments: list[Attachment] | None = None, on_step: OnStep | None = None):
        stdin = prompt
        extra: list[str] = []
        if attachments:
            # Files travel as content blocks, which the CLI only accepts as stream-json input.
            blocks = [
                {
                    "type": "document" if a.mime == "application/pdf" else "image",
                    "source": {"type": "base64", "media_type": a.mime, "data": base64.b64encode(a.data).decode()},
                }
                for a in attachments
            ]
            blocks.append({"type": "text", "text": prompt})
            stdin = json.dumps({"type": "user", "message": {"role": "user", "content": blocks}}) + "\n"
            extra = ["--input-format", "stream-json"]
        cmd = [
            self.exe, "-p",
            "--model", config.CLAUDE_MODEL,
            "--effort", effort,
            "--system-prompt", system,
            "--tools", tools,
            "--json-schema", json.dumps(schema),
            "--output-format", "stream-json", "--verbose",
            "--setting-sources", "",
            "--strict-mcp-config",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--permission-mode", "dontAsk",
        ] + extra
        if tools:
            cmd += ["--allowedTools", tools]
        events, noise, returncode = self._stream(cmd, stdin, timeout, on_step)
        result = next((e for e in events if e.get("type") == "result"), None)
        if result is None:
            raise LLMError(f"Claude CLI gave no result (exit {returncode}): {' '.join(noise)[-400:]}")
        usage = result.get("usage") or {}
        self._count(
            usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0),
            usage.get("output_tokens", 0),
        )
        if result.get("is_error") or result.get("structured_output") is None:
            raise LLMError(f"Claude CLI call failed ({result.get('subtype')}): {str(result.get('result'))[:400]}")
        return result["structured_output"], events

    def _stream(self, cmd: list[str], stdin: str, timeout: int, on_step: OnStep | None):
        """Run the CLI, reading its event stream line by line so tool calls can be reported live."""
        try:
            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", cwd=self.cwd,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            raise LLMError(f"Could not start the Claude CLI: {exc}") from exc

        timed_out = threading.Event()

        def kill() -> None:
            timed_out.set()
            proc.kill()

        def feed() -> None:
            # Written from its own thread: a large attachment must not block reading the output.
            try:
                proc.stdin.write(stdin)
                proc.stdin.close()
            except OSError:
                pass

        timer = threading.Timer(timeout, kill)
        timer.start()
        threading.Thread(target=feed, daemon=True).start()
        events: list[dict] = []
        noise: list[str] = []  # anything that is not an event, kept for error messages
        try:
            for line in proc.stdout:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    if line.strip():
                        noise.append(line.strip())
                    continue
                if not isinstance(event, dict):
                    continue
                events.append(event)
                if on_step:
                    for step in _steps_in(event):
                        on_step(step)
            proc.wait()
        finally:
            timer.cancel()
        if timed_out.is_set():
            raise LLMError(f"Claude CLI timed out after {timeout}s")
        return events, noise, proc.returncode

    def structured(self, system: str, prompt: str, schema: dict, effort: str = "low",
                   attachments: list[Attachment] | None = None) -> dict:
        data, _ = self._run(system, prompt, schema, effort, tools="", timeout=180, attachments=attachments)
        return data

    def research(self, system: str, prompt: str, schema: dict, effort: str = "medium",
                 on_step: OnStep | None = None) -> ResearchResult:
        data, events = self._run(system, prompt, schema, effort, tools=_WEB_TOOLS, timeout=420, on_step=on_step)
        return ResearchResult(data=data, seen_urls=_seen_urls(events))


def _steps_in(event: dict) -> list[dict]:
    """The searches and page reads the model starts in one stream event."""
    if event.get("type") != "assistant":
        return []
    steps = []
    for block in event.get("message", {}).get("content", []):
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        tool_input = block.get("input") or {}
        if block.get("name") == "WebSearch" and tool_input.get("query"):
            steps.append({"action": "search", "detail": tool_input["query"]})
        elif block.get("name") == "WebFetch" and tool_input.get("url"):
            steps.append({"action": "fetch", "detail": tool_input["url"]})
    return steps


def _seen_urls(events: list[dict]) -> set[str]:
    """URLs the model really retrieved: search hits, plus fetched pages that did not error."""
    fetch_urls: dict[str, str] = {}
    seen: set[str] = set()
    for event in events:
        if event.get("type") not in ("assistant", "user"):
            continue
        for block in event.get("message", {}).get("content", []):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == "WebFetch":
                fetch_urls[block["id"]] = block.get("input", {}).get("url", "")
            elif block.get("type") == "tool_result":
                if block.get("is_error"):
                    fetch_urls.pop(block.get("tool_use_id"), None)
                    continue
                seen.update(u.rstrip(".,;") for u in _URL_RE.findall(_text_of(block.get("content"))))
    seen.update(u for u in fetch_urls.values() if u)
    return seen
