"""Paths shared by the video scripts."""
import os
import subprocess
from pathlib import Path

import imageio_ffmpeg

VIDEO = Path(__file__).resolve().parent
ROOT = VIDEO.parent
BUILD = VIDEO / "build"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
TG_PORT = 9333
BOT = "ForwarddCheck_bot"
WEB = "http://127.0.0.1:8011/"
# The Chrome profile that is logged in to Telegram Web. It holds a login, so it stays out of git (build/ is ignored).
PROFILE = os.getenv("TG_PROFILE", str(BUILD / "tg-profile"))


def ffmpeg(*args: str) -> str:
    """Runs ffmpeg and returns what it printed (it reports on stderr)."""
    done = subprocess.run([FFMPEG, "-hide_banner", "-y", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.returncode:
        raise RuntimeError(done.stderr[-2000:])
    return done.stderr


def duration(path: Path) -> float:
    """Length of an audio or video file in seconds."""
    import re
    done = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", done.stderr).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)
