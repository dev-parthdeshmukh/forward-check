# Evaluation report

24 of 24 gold items were run through the full pipeline.

| Measure | Result |
|---|---|
| Exact verdict match | 24 / 24 (100%) |
| Match, counting an accepted alternative | 24 / 24 (100%) |
| Said "cannot confirm" about a checkable claim | 0 / 20 |
| Gave a firm verdict on an uncheckable claim | 0 / 4 |
| Firm verdicts with no trusted source behind them | 0 |
| Sources cited, from trusted domains | 39 / 42 |
| Citations dropped because the page was never retrieved | 0 |
| Verdicts withdrawn by the code-side rules | 0 |
| Median time per message (22 live checks) | 27 s |
| Median tokens per message | 21886 in, 1580 out |

## Confusion matrix

Rows are the expected verdict, columns what the system said.

| Expected | VERIFIED | FALSE | OUTDATED | PARTLY_SUPPORTED | UNVERIFIABLE |
|---|---|---|---|---|---|
| VERIFIED | 5 | 0 | 0 | 0 | 0 |
| FALSE | 0 | 6 | 0 | 0 | 0 |
| OUTDATED | 0 | 0 | 5 | 0 | 0 |
| PARTLY_SUPPORTED | 0 | 0 | 0 | 4 | 0 |
| UNVERIFIABLE | 0 | 0 | 0 | 0 | 4 |

## Misses

None.

## Accepted alternatives

None.
