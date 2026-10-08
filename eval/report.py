"""Turn eval/results.jsonl into eval/report.md.     python -m eval.report"""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / "results.jsonl"
REPORT = HERE / "report.md"
VERDICTS = ["VERIFIED", "FALSE", "OUTDATED", "PARTLY_SUPPORTED", "UNVERIFIABLE"]


def metrics(rows: list[dict]) -> dict:
    total = len(rows)
    exact = [r for r in rows if r["got"] == r["gold"]]
    lenient = [r for r in rows if r["got"] == r["gold"] or r["got"] in r.get("accept", [])]
    checkable = [r for r in rows if r["gold"] != "UNVERIFIABLE"]
    uncheckable = [r for r in rows if r["gold"] == "UNVERIFIABLE"]
    live = [r for r in rows if not r.get("from_cache")]
    evidence = sum(r["evidence"] for r in rows)
    return {
        "total": total,
        "exact": len(exact),
        "lenient": len(lenient),
        "matrix": {g: {v: sum(1 for r in rows if r["gold"] == g and r["got"] == v) for v in VERDICTS} for g in VERDICTS},
        # Said "cannot confirm" about something that reliable sources do settle.
        "over_abstained": sum(1 for r in checkable if r["got"] == "UNVERIFIABLE"),
        "checkable": len(checkable),
        # Gave a firm verdict on something nobody can check: the dangerous kind of error.
        "over_confident": sum(1 for r in uncheckable if r["got"] != "UNVERIFIABLE" and r["got"] not in r.get("accept", [])),
        "uncheckable": len(uncheckable),
        "evidence": evidence,
        "trusted_evidence": sum(r["trusted_evidence"] for r in rows),
        "dropped_citations": sum(r["dropped_citations"] for r in rows),
        "withdrawn": sum(r["withdrawn"] for r in rows),
        "decisive_without_evidence": sum(1 for r in rows if r["got"] != "UNVERIFIABLE" and r["trusted_evidence"] == 0),
        "live": len(live),
        "median_seconds": statistics.median(r["seconds"] for r in live) if live else 0,
        "median_input_tokens": statistics.median(r["input_tokens"] for r in live) if live else 0,
        "median_output_tokens": statistics.median(r["output_tokens"] for r in live) if live else 0,
        "misses": [r for r in rows if r not in lenient],
        "alternates": [r for r in lenient if r["got"] != r["gold"]],
    }


def percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "n/a"


def render(m: dict, gold_size: int) -> str:
    lines = [
        "# Evaluation report",
        "",
        f"{m['total']} of {gold_size} gold items were run through the full pipeline.",
        "",
        "| Measure | Result |",
        "|---|---|",
        f"| Exact verdict match | {m['exact']} / {m['total']} ({percent(m['exact'], m['total'])}) |",
        f"| Match, counting an accepted alternative | {m['lenient']} / {m['total']} ({percent(m['lenient'], m['total'])}) |",
        f"| Said \"cannot confirm\" about a checkable claim | {m['over_abstained']} / {m['checkable']} |",
        f"| Gave a firm verdict on an uncheckable claim | {m['over_confident']} / {m['uncheckable']} |",
        f"| Firm verdicts with no trusted source behind them | {m['decisive_without_evidence']} |",
        f"| Sources cited, from trusted domains | {m['trusted_evidence']} / {m['evidence']} |",
        f"| Citations dropped because the page was never retrieved | {m['dropped_citations']} |",
        f"| Verdicts withdrawn by the code-side rules | {m['withdrawn']} |",
        f"| Median time per message ({m['live']} live checks) | {m['median_seconds']:.0f} s |",
        f"| Median tokens per message | {m['median_input_tokens']:.0f} in, {m['median_output_tokens']:.0f} out |",
        "",
        "## Confusion matrix",
        "",
        "Rows are the expected verdict, columns what the system said.",
        "",
        "| Expected | " + " | ".join(VERDICTS) + " |",
        "|---|" + "---|" * len(VERDICTS),
    ]
    for gold in VERDICTS:
        lines.append(f"| {gold} | " + " | ".join(str(m["matrix"][gold][v]) for v in VERDICTS) + " |")
    for title, rows in (("Misses", m["misses"]), ("Accepted alternatives", m["alternates"])):
        lines += ["", f"## {title}", ""]
        lines += [f"- `{r['id']}`: expected {r['gold']}, got {r['got']}" for r in rows] or ["None."]
    return "\n".join(lines) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not RESULTS.exists():
        sys.exit("No results yet. Run: python -m eval.run")
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    gold_size = len(json.loads((HERE / "gold.json").read_text(encoding="utf-8")))
    text = render(metrics(rows), gold_size)
    REPORT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
