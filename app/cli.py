"""Usage: python -m app.cli "message text"
          python -m app.cli --file screenshot.png | notice.pdf | voice.ogg | forward.txt
          python -m app.cli --url https://example.com/article
       Options: --lang Hindi   --json   --no-cache"""
import argparse
import sys
from pathlib import Path

from . import service
from .ingest import IngestError
from .llm import LLMError
from .schemas import CheckResult


def render(result: CheckResult) -> str:
    lines = [
        f"OVERALL: {result.overall_verdict.value} / {result.overall_label}   "
        f"(input: {result.source_kind}, language: {result.language_name}, backend: {result.backend}, {result.seconds}s)",
        f"tokens: {result.input_tokens} in, {result.output_tokens} out",
    ]
    if result.cached:
        lines.append(f"answered from an earlier check (asked {result.times_checked} times); --no-cache checks again")
    if result.source_kind in ("image", "audio") and result.input_text:
        lines += ["", f'read as: "{result.input_text[:600]}"']
    lines += ["", result.summary]
    for flag in result.risk_flags:
        lines.append(f"WARNING SIGN ({flag.code}): {flag.message}")
    for item in result.claims:
        lines += ["", "-" * 70, f"{item.claim.id}: {item.claim.text}", f'  from message: "{item.claim.original_span}"']
        verdict = f"  VERDICT: {item.verdict.value} (confidence: {item.confidence})"
        if item.downgraded_from:
            verdict += f"   [model proposed {item.downgraded_from.value}]"
        lines.append(verdict)
        for label, value in (
            ("why", item.explanation), ("what is wrong", item.what_is_wrong),
            ("correct info", item.correct_information), ("true as of", item.true_as_of),
            ("changed on", item.changed_on),
        ):
            if value:
                lines.append(f"  {label}: {value}")
        for ev in item.evidence:
            own = "" if ev.independent else " | the page being checked"
            lines.append(f"  [{ev.id}] {ev.source_name} | {ev.tier} | {ev.published_date or 'no date'} | {ev.stance}{own}")
            lines.append(f"       {ev.url}")
            if ev.quote:
                lines.append(f'       "{ev.quote[:300]}"')
        for note in item.validation_notes:
            lines.append(f"  ! {note}")
    for note in result.notes:
        lines.append(f"! {note}")
    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Fact-check a forwarded message.")
    parser.add_argument("text", nargs="?", help="the message text")
    parser.add_argument("--file", help="a screenshot, PDF, voice note or text file")
    parser.add_argument("--url", help="a link to check")
    parser.add_argument("--lang", help="reply language (default: same as the message)")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    parser.add_argument("--no-cache", action="store_true", help="check again even if this message was checked before")
    args = parser.parse_args()

    options = {"reply_language": args.lang, "use_cache": not args.no_cache}
    try:
        if args.file:
            path = Path(args.file)
            result = service.run_check(file=(path.name, path.read_bytes()), **options)
        elif args.url:
            result = service.run_check(url=args.url, **options)
        elif args.text and args.text.strip():
            result = service.run_check(text=args.text, **options)
        else:
            parser.error("give the message text, --file or --url")
    except (IngestError, LLMError, OSError) as exc:
        sys.exit(f"Could not check the message: {exc}")
    print(result.model_dump_json(indent=2) if args.json else render(result))


if __name__ == "__main__":
    main()
