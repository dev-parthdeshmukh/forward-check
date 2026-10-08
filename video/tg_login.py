"""Opens a Chrome window on Telegram Web using the recording profile, so you can log in once (QR code).
Close the window when done; rec_tg.py then uses the same profile without a window.
"""
import subprocess

from common import BOT, PROFILE

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

subprocess.Popen([CHROME, f"--user-data-dir={PROFILE}", "--no-first-run", "--no-default-browser-check",
                  f"https://web.telegram.org/k/#@{BOT}"], creationflags=subprocess.DETACHED_PROCESS)
print("Chrome opened. Log in to Telegram there, then close the window.")
