"""Builds the inputs the recordings send: the image forward and the voice message for the fake microphone.

The poster comes from PIB Fact Check's debunk graphic. Save that image as build/web_images/newsonair_laptop.jpg first:
https://newsonair.gov.in/wp-content/uploads/2026/06/HKxBio0bwAAxTpt-1.jpg
"""
from PIL import Image

from common import BUILD, ROOT, duration, ffmpeg

inputs = BUILD / "inputs"
inputs.mkdir(parents=True, exist_ok=True)

# The viral "free laptops" poster, cut out of PIB Fact Check's debunk graphic (left panel, above their FAKE stamp).
source = Image.open(BUILD / "web_images" / "newsonair_laptop.jpg").convert("RGB")
scale = source.width / 2000
poster = source.crop(tuple(round(v * scale) for v in (64, 69, 704, 572)))
poster = poster.resize((poster.width * 2, poster.height * 2), Image.LANCZOS)
poster.save(inputs / "laptop-forward.jpg", quality=92)
print("poster", poster.size)

# Chrome's fake microphone plays a WAV file; half a second of silence first so the recording does not clip the start.
voice = ROOT / "web" / "demo" / "voice-note-hi.mp3"
ffmpeg("-i", str(voice), "-af", "adelay=500:all=1,apad=pad_dur=1.5", "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(inputs / "mic.wav"))
print("voice note", round(duration(voice), 2), "s -> mic.wav", round(duration(inputs / "mic.wav"), 2), "s")
