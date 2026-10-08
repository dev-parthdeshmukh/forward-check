"""Run the gold set through the real pipeline.

    python -m eval.run            check every item not yet in eval/results.jsonl
    python -m eval.run --fresh    start over
    python -m eval.run --limit 5  stop after five new checks

Each check spends model usage. The run is resumable, and it stops as soon as the main backend
fails, because an answer from the fallback would measure the wrong system.
"""
import argparse
import json
import sys
from pathlib import Path

from app import config, service
from app.llm import LLMError

HERE = Path(__file__).parent
GOLD = HERE / "gold.json"
RESULTS = HERE / "results.jsonl"


def summarize(item: dict, result) -> dict:
    evidence = [ev for claim in result.claims for ev in claim.evidence]
    return {
        "id": item["id"],
        "gold": item["gold"],
        "accept": item.get("accept", []),
        "got": result.overall_verdict.value,
        "claims": len(result.claims),
        "evidence": len(evidence),
        "trusted_evidence": sum(1 for ev in evidence if ev.tier != "other"),
        "withdrawn": sum(1 for claim in result.claims if claim.downgraded_from),
        "dropped_citations": sum(
            1 for claim in result.claims for note in claim.validation_notes if note.startswith("Dropped a cited source")
        ),
        "lookups": sum(len(claim.steps) for claim in result.claims),
        "seconds": result.seconds,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "from_cache": result.cached,
        "language": result.language_code,
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run the evaluation set.")
    parser.add_argument("--fresh", action="store_true", help="discard earlier results")
    parser.add_argument("--limit", type=int, default=0, help="stop after this many new checks")
    args = parser.parse_args()

    if args.fresh:
        RESULTS.unlink(missing_ok=True)
    done = set()
    if RESULTS.exists():
        done = {json.loads(line)["id"] for line in RESULTS.read_text(encoding="utf-8").splitlines() if line.strip()}

    items = [item for item in json.loads(GOLD.read_text(encoding="utf-8")) if item["id"] not in done]
    print(f"{len(done)} done, {len(items)} to run")
    for count, item in enumerate(items, start=1):
        if args.limit and count > args.limit:
            break
        try:
            result = service.run_check(text=item["text"])
        except LLMError as exc:
            print(f"STOPPED at {item['id']}: {exc}")
            break
        if result.backend != config.LLM_BACKEND:
            print(f"STOPPED at {item['id']}: answered by the fallback backend ({result.backend}); {result.notes[:1]}")
            break
        row = summarize(item, result)
        with RESULTS.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        mark = "ok " if row["got"] == row["gold"] else "alt" if row["got"] in row["accept"] else "MISS"
        print(f"{mark} {item['id']}: gold {row['gold']}, got {row['got']} ({row['seconds']}s, {row['input_tokens']} in)")


if __name__ == "__main__":
    main()
