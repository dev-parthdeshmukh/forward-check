"""Makes a contact sheet of a recording at the given times, to see what the footage holds.

usage: peek.py <recording> <t1> <t2> ...    (or "marks" to use every mark)
"""
import json
import sys

from PIL import Image, ImageDraw

from common import BUILD

name = sys.argv[1]
folder = BUILD / "rec" / name
manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
if sys.argv[2] == "marks":
    times = [(label, t + 0.9) for label, t in manifest["marks"].items()]
else:
    times = [(a, float(a)) for a in sys.argv[2:]]
print("duration", manifest["duration"], "| frames", len(manifest["frames"]), "| marks", manifest["marks"])
print("events", manifest["events"])

thumbs = []
for label, t in times:
    frame = max((f for f in manifest["frames"] if f["t"] <= t), key=lambda f: f["t"], default=manifest["frames"][0])
    image = Image.open(folder / frame["f"])
    height = 620
    image = image.resize((round(image.width * height / image.height), height), Image.LANCZOS)
    ImageDraw.Draw(image).rectangle([0, 0, 190, 22], fill="black")
    ImageDraw.Draw(image).text((4, 4), f"{label} @{frame['t']}", fill="white")
    thumbs.append(image)
sheet = Image.new("RGB", (sum(t.width for t in thumbs) + 6 * (len(thumbs) - 1), 620), "white")
x = 0
for thumb in thumbs:
    sheet.paste(thumb, (x, 0))
    x += thumb.width + 6
out = BUILD / "probe" / f"peek-{name}.jpg"
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out, quality=88)
print("sheet", out, sheet.size)
