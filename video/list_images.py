"""Lists the images on a web page (largest first is not known yet; prints url and alt text).

usage: list_images.py <url> [<url> ...]
"""
import re
import sys
from urllib.parse import urljoin

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0 Safari/537.36"}

for url in sys.argv[1:]:
    print("==", url)
    try:
        page = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
    except httpx.HTTPError as exc:
        print("  failed:", exc)
        continue
    print("  status", page.status_code, "| bytes", len(page.text))
    seen = set()
    for tag in re.findall(r"<img\b[^>]*>", page.text, flags=re.I):
        src = re.search(r"""(?:data-src|data-lazy-src|src)\s*=\s*["']([^"']+)["']""", tag, flags=re.I)
        alt = re.search(r"""alt\s*=\s*["']([^"']*)["']""", tag, flags=re.I)
        if not src:
            continue
        full = urljoin(str(page.url), src.group(1))
        if full in seen or full.startswith("data:") or re.search(r"logo|icon|avatar|sprite|\.svg", full, flags=re.I):
            continue
        seen.add(full)
        print("  ", full[:200], "|", (alt.group(1) if alt else "")[:90])
    for meta in re.findall(r"""<meta[^>]+property=["']og:image["'][^>]*>""", page.text, flags=re.I):
        print("  og:", meta[:220])
