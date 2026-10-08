"""Speaks the narration, one file per line, and saves when each word is said (build/voice/words.json)
so the pictures can be cut to the words.
"""
import asyncio
import json

import edge_tts

from common import BUILD, VIDEO, duration

VOICE = "en-IN-NeerjaNeural"
RATE = "+12%"


async def speak(text: str, path) -> list:
    words = []
    with open(path, "wb") as out:
        async for chunk in edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary").stream():
            if chunk["type"] == "audio":
                out.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append([round(chunk["offset"] / 1e7, 2), chunk["text"]])
    return words


async def main() -> None:
    lines = json.loads((VIDEO / "narration.json").read_text(encoding="utf-8"))
    out = BUILD / "voice"
    out.mkdir(parents=True, exist_ok=True)
    timing = {}
    for line in lines:
        path = out / f"{line['id']}.mp3"
        words = await speak(line["text"], path)
        timing[line["id"]] = {"seconds": round(duration(path), 2), "words": words}
        print(f"{line['id']:9s} {timing[line['id']]['seconds']:5.2f}s  " + " ".join(f"{w}@{t}" for t, w in words))
    (out / "words.json").write_text(json.dumps(timing, ensure_ascii=False), encoding="utf-8")


asyncio.run(main())
