"""Screen recording as a numbered run of screenshots with a clock, plus the clicks made, so the
video can retime the footage and draw its own smooth cursor.

A recording folder holds 00000.jpg ... and manifest.json:
  {"width", "height", "scale", "frames": [{"t", "f"}], "events": [{"t", "x", "y", "kind"}], "marks": {name: t}}
Times are seconds from the start of the recording; x and y are CSS pixels in the page.
"""
import asyncio
import json
import time
from pathlib import Path


class Recorder:
    def __init__(self, page, out: Path, width: int, height: int, scale: float, quality: int = 90) -> None:
        self.page, self.out, self.quality = page, out, quality
        self.meta = {"width": width, "height": height, "scale": scale}
        self.frames, self.events, self.marks = [], [], {}
        self.shift = 0.0  # stepped sections take longer to shoot than they last on the clock
        self.running = False
        self.busy = asyncio.Lock()
        out.mkdir(parents=True, exist_ok=True)
        for old in out.glob("*.jpg"):
            old.unlink()

    def now(self) -> float:
        return time.perf_counter() - self.t0 - self.shift

    async def shoot(self, t: float) -> None:
        data = await self.page.screenshot(type="jpeg", quality=self.quality, caret="initial", animations="allow")
        name = f"{len(self.frames):05d}.jpg"
        (self.out / name).write_bytes(data)
        self.frames.append({"t": round(t, 3), "f": name})

    async def loop(self) -> None:
        while self.running:
            async with self.busy:
                await self.shoot(self.now())
            await asyncio.sleep(0.01)

    async def start(self) -> None:
        self.t0 = time.perf_counter()
        self.running = True
        self.task = asyncio.create_task(self.loop())

    def mark(self, name: str) -> None:
        self.marks[name] = round(self.now(), 3)
        print(f"  [{self.marks[name]:7.2f}s] {name}", flush=True)

    async def hold(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    async def click(self, locator, kind: str = "click", pause: float = 0.6) -> None:
        """Logs where the click lands, waits (the video moves its cursor there), then clicks."""
        box = await locator.bounding_box()
        self.events.append({"t": round(self.now() + pause, 3), "x": round(box["x"] + box["width"] / 2, 1),
                            "y": round(box["y"] + box["height"] / 2, 1), "kind": kind})
        await asyncio.sleep(pause)
        await locator.click()

    async def stepped(self, seconds: float, apply, fps: int = 30) -> None:
        """A smooth move shot frame by frame: apply(progress 0..1) is awaited before each frame."""
        async with self.busy:
            start = self.now()
            real = time.perf_counter()
            count = max(2, round(seconds * fps))
            for i in range(count):
                await apply(i / (count - 1))
                await self.shoot(start + i / fps)
            self.shift += (time.perf_counter() - real) - count / fps

    async def scroll(self, selector: str, to: float | str, seconds: float = 1.0) -> None:
        """Eased scroll of one element to a position in pixels, or "end"."""
        top, limit = await self.page.evaluate(
            "s => { const e = document.querySelector(s); return [e.scrollTop, e.scrollHeight - e.clientHeight]; }", selector)
        target = limit if to == "end" else max(0, min(float(to), limit))

        async def apply(p: float) -> None:
            eased = p * p * (3 - 2 * p)
            await self.page.evaluate("([s, y]) => { const e = document.querySelector(s); e.style.scrollBehavior = 'auto'; e.scrollTop = y; }",
                                     [selector, top + (target - top) * eased])
        self.events.append({"t": round(self.now(), 3), "kind": "scroll", "x": 0, "y": 0})
        await self.stepped(seconds, apply)

    async def stop(self) -> None:
        self.running = False
        await self.task
        self.meta.update(frames=self.frames, events=self.events, marks=self.marks, duration=round(self.now(), 3))
        (self.out / "manifest.json").write_text(json.dumps(self.meta), encoding="utf-8")
        print(f"  saved {len(self.frames)} frames, {self.meta['duration']}s -> {self.out}", flush=True)
