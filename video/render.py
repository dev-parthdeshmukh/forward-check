"""Draws the film frame by frame in headless Chrome and encodes it.

    render.py stills 3.5 12 20.4      -> build/stills/t0003.50.jpg ...   (to look at single frames)
    render.py film [workers]          -> build/picture.mp4               (no sound; mix.py adds it)

Needs the project folder served on port 8020:  python -m http.server 8020  (run from the project root).
"""
import asyncio
import json
import subprocess
import sys
import time

from playwright.async_api import async_playwright

from common import BUILD, FFMPEG, VIDEO, ffmpeg

PAGE = "http://127.0.0.1:8020/video/composition.html?render"
TIMELINE = json.loads((VIDEO / "timeline.json").read_text(encoding="utf-8"))
FPS = TIMELINE["fps"]


async def open_page(browser):
    context = await browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    page = await context.new_page()
    page.on("pageerror", lambda e: print("  !! page error:", e, flush=True))
    page.on("console", lambda m: print("  !! console:", m.text, flush=True) if m.type == "error" else None)
    await page.goto(PAGE)
    await page.wait_for_function("window.ready === true", timeout=180_000)
    return page


async def shot(page, t: float) -> bytes:
    await page.evaluate("t => renderAt(t)", t)
    return await page.screenshot(type="jpeg", quality=96)


async def stills(browser, times: list[float]) -> None:
    page = await open_page(browser)
    out = BUILD / "stills"
    out.mkdir(parents=True, exist_ok=True)
    for t in times:
        (out / f"t{t:07.2f}.jpg").write_bytes(await shot(page, t))
    print("stills:", ", ".join(f"t{t:07.2f}.jpg" for t in times))


async def part(page, index: int, first: int, last: int) -> str:
    """Renders frames first..last-1 to their own file; the parts are joined afterwards."""
    path = BUILD / "parts" / f"part{index:02d}.mp4"
    encoder = subprocess.Popen(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
         "-color_trc", "bt709", "-vf", "scale=out_color_matrix=bt709:out_range=tv", "-r", str(FPS), str(path)],
        stdin=subprocess.PIPE)
    for frame in range(first, last):
        encoder.stdin.write(await shot(page, frame / FPS))
        if index == 0 and (frame - first) % 60 == 0:
            print(f"  part 0: {frame - first}/{last - first}", flush=True)
    encoder.stdin.close()
    if await asyncio.to_thread(encoder.wait):
        raise RuntimeError(f"encoder failed on part {index}")
    return path.name


async def film(browser, workers: int) -> None:
    total = round(TIMELINE["duration"] * FPS)
    (BUILD / "parts").mkdir(parents=True, exist_ok=True)
    edges = [round(total * i / workers) for i in range(workers + 1)]
    began = time.time()
    pages = [await open_page(browser) for _ in range(workers)]  # one at a time: loading them together can stall
    names = await asyncio.gather(*(part(pages[i], i, edges[i], edges[i + 1]) for i in range(workers)))
    (BUILD / "parts" / "list.txt").write_text("".join(f"file '{n}'\n" for n in names), encoding="utf-8")
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(BUILD / "parts" / "list.txt"), "-c", "copy", str(BUILD / "picture.mp4"))
    print(f"film: {total} frames in {time.time() - began:.0f}s -> build/picture.mp4")


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", args=["--force-color-profile=srgb"])
        if sys.argv[1] == "stills":
            await stills(browser, [float(a) for a in sys.argv[2:]])
        else:
            await film(browser, int(sys.argv[2]) if len(sys.argv) > 2 else 4)
        await browser.close()


asyncio.run(main())
