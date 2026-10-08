"""Builds the soundtrack (narration placed on the timeline, plus a quiet synthesised music bed) and
joins it to build/picture.mp4.

    mix.py      -> forward-check-demo.mp4 (voice + music) and forward-check-demo-voice-only.mp4
"""
import json
import wave

import numpy as np

from common import BUILD, VIDEO, ffmpeg

TIMELINE = json.loads((VIDEO / "timeline.json").read_text(encoding="utf-8"))
LENGTH = TIMELINE["duration"]
RATE = 48000


def note(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def music() -> np.ndarray:
    """A soft pad over four chords with a light plucked pattern; all sine waves, so nothing harsh."""
    total = int(LENGTH * RATE)
    t = np.arange(total) / RATE
    left, right = np.zeros(total), np.zeros(total)
    bar = 2.5  # 96 beats a minute
    chords = [[50, 57, 60, 64, 65], [46, 53, 57, 62, 65], [41, 53, 57, 60, 64], [48, 55, 60, 62, 64]]  # Dm9, Bbmaj7, Fmaj7, Cadd9
    span = 2 * bar
    for index in range(int(LENGTH / span) + 1):
        chord, start = chords[index % 4], index * span
        local = t - start
        envelope = np.clip(local / 1.1, 0, 1) * np.clip((span + 1.3 - local) / 1.3, 0, 1) * (local > 0)
        for voice, midi in enumerate(chord):
            f = note(midi)
            tone = np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 1.003 * t + voice) + .18 * np.sin(2 * np.pi * 2 * f * t)
            level = .34 if voice == 0 else .2
            pan = .5 + .32 * np.sin(voice * 1.9)
            left += tone * envelope * level * (1 - pan)
            right += tone * envelope * level * pan
        # Plucked notes on the half-beat, from the title onwards, walking up and down the chord.
        step = bar / 8
        order = [1, 2, 3, 4, 3, 2, 4, 3, 1, 2, 3, 4, 3, 2, 3, 1]
        for i, pick in enumerate(order):
            at = start + i * step
            if at < TIMELINE["scenes"]["title"][0] or at > LENGTH - 3:
                continue
            f = note(chord[pick] + 12)
            local = t - at
            pluck = np.sin(2 * np.pi * f * t) * np.exp(-np.clip(local, 0, None) / .2) * np.clip(local / .004, 0, 1) * (local > 0)
            echo = np.roll(pluck, int(.47 * RATE)) * .35
            echo[: int(.47 * RATE)] = 0
            side = i % 2
            left += (pluck * (.085 if side else .05) + echo * (.03 if side else .07))
            right += (pluck * (.05 if side else .085) + echo * (.07 if side else .03))
    mix = np.stack([left, right], axis=1)
    mix *= (np.clip(t / 1.5, 0, 1) * np.clip((LENGTH - t) / 2.8, 0, 1))[:, None]
    mix /= np.abs(mix).max()
    return mix


def save(path, samples: np.ndarray) -> None:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())


audio = BUILD / "audio"
audio.mkdir(parents=True, exist_ok=True)
save(audio / "music.wav", music())

# Narration: each line starts at its time on the timeline.
lines = list(TIMELINE["voice"].items())
inputs, graph = [], []
for i, (name, at) in enumerate(lines):
    inputs += ["-i", str(BUILD / "voice" / f"{name}.mp3")]
    graph.append(f"[{i}:a]aresample={RATE},adelay={round(at * 1000)}:all=1[v{i}]")
graph.append("".join(f"[v{i}]" for i in range(len(lines))) + f"amix=inputs={len(lines)}:normalize=0:duration=longest,"
             f"apad=whole_dur={LENGTH},atrim=0:{LENGTH},loudnorm=I=-16:TP=-1.5:LRA=11,aresample={RATE},aformat=channel_layouts=stereo[out]")
ffmpeg(*inputs, "-filter_complex", ";".join(graph), "-map", "[out]", "-c:a", "pcm_s16le", str(audio / "voice.wav"))

# The bed sits well under the voice.
ffmpeg("-i", str(audio / "voice.wav"), "-i", str(audio / "music.wav"), "-filter_complex",
       "[1:a]volume=-25dB[m];[0:a][m]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[out]",
       "-map", "[out]", "-c:a", "pcm_s16le", str(audio / "mix.wav"))

for track, name in (("mix.wav", "forward-check-demo.mp4"), ("voice.wav", "forward-check-demo-voice-only.mp4")):
    ffmpeg("-i", str(BUILD / "picture.mp4"), "-i", str(audio / track), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(VIDEO / name))
    print("wrote", VIDEO / name, f"{(VIDEO / name).stat().st_size / 1e6:.1f} MB")
