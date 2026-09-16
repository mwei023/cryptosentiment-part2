# E005 — Regime-Conditional Book (H004): DEV vs OUT-OF-SAMPLE

## Receipt

```
ID:              E005
Hypothesis:      H004 (composition: V1 in BULL_RANGE, S003 in BULL_TREND,
                 flat otherwise) — authorized by D006
Split:           bars 200-760 dev (2024-07-09 → 2026-01-19)
                 bars 760-1000 OOS (2026-01-20 → 2026-09-16), untouched
Rules:           pre-registered before any run: OOS trades < 5 ->
                 INCONCLUSIVE; OOS exp > 0 -> ADVANCED; else REJECTED
Leak disclosure: E004's attribution used the FULL window, so the cells
                 were partly informed by OOS data. Handled by NOT
                 re-selecting cells on dev (D006 named them) and by
                 treating dev numbers as optimistic-biased.
Git:             6988fb5
Machine receipt: summary.json
```

## Results

**POOLED (3 coins, position-level %; equity risk ~1%/trade by sizing):**

| arm | trades | PF | exp/trade | win% | sum |
|---|---|---|---|---|---|
| DEV (2024-07→2026-01) | 20 | 1.80 | **+1.41%** | 75% | +28.28 |
| OOS (2026-01→2026-09) | **2** | 0.00 | −5.09% | 0% | −10.17 |

DEV cells: BULL_RANGE(V1) +0.84% × 14 · BULL_TREND(S003) +2.75% × 6.
OOS cells: BULL_RANGE(V1) **n=0** · BULL_TREND(S003) −5.09% × 2.

Per coin OOS: BTC 0 trades · ETH 1 (−4.79%) · SOL 1 (−5.38%).

## Finding 1: the out-of-sample window went SILENT, not bad

**0 BULL_RANGE candidates fired in 8 months across all three coins.**
The regime cell the book depends on for most of its dev profit simply
did not exist in 2026: after January, the tape offered no bull-range
pullback-to-band structure under the gate. The only OOS activity came
from the S003 cell — two pullback entries, both stopped (−4.79%,
−5.38%).

This is not an OOS collapse that disproves the dev edge; it is
**regime non-stationarity**: the profitable cells are rare, and their
existence is a property of the market year, not of the calendar
"dev/OOS" split. A book defined by two narrow regime cells is a
fair-weather system.

## Finding 2: the dispatch did its job — there was just no edge to protect

OOS baselines on the same window: V1-alone fired BTC 2 trades
(+2.01% exp — those were BULL_TREND bars, where the book correctly does
NOT run V1) and SOL 1 trade (−6.91%, correctly skipped). S003-alone
matched the book exactly. Every skipped or filtered OOS trade either
lost or was a trend-knife-catch the book is designed to refuse. The
composition logic works; the market just stopped offering its cells.

## Finding 3: the dev edge is real in-sample but optimistic by construction

PF 1.80 / +1.41% / 75% win over 20 trades is the best number any
configuration has produced in this project. But it inherits the
disclosed leak (cells named from full-window attribution) and n=20.
The honest label is: **promising in-sample composition, insufficient
out-of-sample evidence, no statistical significance anywhere.**

## Verdict (pre-registered rule applied as written)

```
STATUS:  INCONCLUSIVE — only 2 OOS trades (< 5): the book's cells
barely exist in the out-of-sample window. No verdict possible, and
that absence is itself the finding.
```

## The composite conclusion after five experiments

Three entry families tested (D001, D004, D005), one attribution (D006),
one composition (D007/E005). Every pre-registered verdict has been
applied as written. The record now shows:

- No entry family has demonstrated positive cost-adjusted expectancy.
- The only in-sample-positive configuration (this book) could not be
  validated out-of-sample because its regime cells ceased to exist.
- Nothing in this architecture has an edge that survives honesty.

Per D006's pre-commitment: that is a legitimate, valuable ending. The
defensible next moves are (a) longer/multi-venue data for statistical
power, (b) the forward journal as the only un-rewritable referee, and
(c) accepting the null until new evidence arrives. Building a fourth
entry family on this tape would be re-rolling dice with extra steps.

## What we KNOW / SUSPECT / DON'T KNOW

**KNOW:** dev-window composition PF 1.80 (+1.41%, n=20); OOS produced 2
trades and zero BULL_RANGE candidates in 8 months; the book skipped
every OOS loser the components took alone; INCONCLUSIVE by rule.
**SUSPECT:** regime-cell rarity is structural (2026's tape had no
bull-range windows); dev numbers are optimistic via the disclosed leak.
**DON'T KNOW:** whether the dev edge is real with more data; whether
the cells return in future regimes; whether any configuration here has
true (out-of-sample) edge — the forward journal is the only instrument
that can answer that.

## Next

- Keep the forward journal running daily (the only live referee).
- If/when ~30+ settled journal rows exist, compare them against this
  record — that comparison, not more backtests, is the next experiment
  (E006, journal vs record).
- Longer history (exchange archives / paid tier) only if the goal is
  more statistical power for these same cells — and only with a new
  pre-registered split.
