"""Remembers finished checks so a forward that comes in again is answered at once.

Matching is exact after light text normalisation; a reworded forward is a new check.
"""
import hashlib
import sqlite3
import time
import unicodedata
from contextlib import closing

from . import config
from .schemas import CheckResult

_SCHEMA = """CREATE TABLE IF NOT EXISTS checks (
    key TEXT PRIMARY KEY, result TEXT NOT NULL, created REAL NOT NULL, hits INTEGER NOT NULL DEFAULT 0
)"""


def _connect() -> sqlite3.Connection:
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.CACHE_DIR / "cache.db", timeout=10)
    conn.execute(_SCHEMA)
    return conn


def make_key(kind: str, content: bytes | str, reply_language: str | None) -> str:
    if isinstance(content, str):
        content = " ".join(unicodedata.normalize("NFKC", content).casefold().split()).encode("utf-8")
    reply = (reply_language or "auto").strip().lower()
    return f"{kind}:{reply}:{hashlib.sha256(content).hexdigest()}"


def get(key: str) -> CheckResult | None:
    """The stored result if it is still fresh, counted as one more time the message was asked about."""
    with closing(_connect()) as conn, conn:
        row = conn.execute("SELECT result, created, hits FROM checks WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        stored, created, hits = row
        if time.time() - created > config.CACHE_TTL_DAYS * 86400:
            conn.execute("DELETE FROM checks WHERE key = ?", (key,))
            return None
        conn.execute("UPDATE checks SET hits = hits + 1 WHERE key = ?", (key,))
    result = CheckResult.model_validate_json(stored)
    result.cached = True
    result.times_checked = hits + 2  # the original check, earlier repeats, and this one
    return result


def put(key: str, result: CheckResult) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT OR REPLACE INTO checks (key, result, created, hits) VALUES (?, ?, ?, 0)",
            (key, result.model_dump_json(), time.time()),
        )
