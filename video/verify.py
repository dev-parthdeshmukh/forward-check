"""Checks the finished film: streams, length, loudness, and a contact sheet of frames pulled from the MP4 itself.

usage: verify.py [t1 t2 ...]
"""
import re
import subprocess
import sys

from PIL import Image

from common import BUILD, FFMPEG, VIDEO

film = VIDEO / "forward-check-demo.mp4"
info = subprocess.run([FFMPEG, "-hide_banner", "-i", str(film)], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
for line in info.splitlines():
    if re.search(r"Duration|Stream", line):
        print(line.strip())

for name in ("forward-check-demo.mp4", "forward-check-demo-voice-only.mp4"):
    loud = subprocess.run([FFMPEG, "-hide_banner", "-i", str(VIDEO / name), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    summary = loud[loud.rfind("Summary:"):]
    print(name, "|", " ".join(re.findall(r"(?:I|LRA|Peak):\s+-?[\d.]+ \w+", summary)))

# How loud the music is on its own, and the gaps between narration lines.
quiet = subprocess.run([FFMPEG, "-hide_banner", "-i", str(BUILD / "audio" / "voice.wav"), "-af", "silencedetect=noise=-40dB:d=0.6", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
print("silences in narration:", ", ".join(f"{float(a):.1f}-{float(b):.1f}" for a, b in
                                         zip(re.findall(r"silence_start: ([\d.]+)", quiet), re.findall(r"silence_end: ([\d.]+)", quiet))))

times = [float(a) for a in sys.argv[1:]] or [2.5, 8.2, 10.3, 14.5, 20.3, 25.5, 30.9, 37.5, 43.3, 47.8, 51.0, 56.0]
frames = []
for t in times:
    out = BUILD / "probe" / f"final-{t:06.2f}.jpg"
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(t), "-i", str(film), "-frames:v", "1", "-q:v", "3", str(out)], check=True)
    frames.append(Image.open(out).resize((640, 360), Image.LANCZOS))
columns = 3
sheet = Image.new("RGB", (640 * columns, 360 * -(-len(frames) // columns)))
for i, frame in enumerate(frames):
    sheet.paste(frame, ((i % columns) * 640, (i // columns) * 360))
sheet.save(BUILD / "probe" / "final-sheet.jpg", quality=88)
print("sheet:", BUILD / "probe" / "final-sheet.jpg")
