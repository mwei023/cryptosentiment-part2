# E003 — Trend Pullback Entry (H002)

## Receipt

```
ID:              E003
Hypothesis:      H002 (trend pullback continuation)
Control:         S001 V1 band mean-reversion (standing control)
Treatment:       S003 trend pullback (research/strategies.py:run_pullback)
Foundation:      F001 (frozen) — gates, sizing, stops, targets, trail,
                 kill switch, costs byte-identical between arms
Trigger:         T1 SMA20>SMA50 yesterday · T2 yesterday closed below
                 SMA20 · T3 today reclaims SMA20 · T4 today breaks
                 yesterday's high. Textbook values, zero tuned params.
Git commit:      6988fb5
Started:         2026-09-16T10:23:31Z
Data:            Binance daily OHLC, 1000 bars/coin (~2.7y)
Costs:           0.1% fee + 0.05% slippage per side, both arms
Pre-registered:  pooled trades < 10 -> INCONCLUSIVE; ADVANCED requires
                 positive pooled expectancy AND beating control
Machine receipt: summary.json (same directory)
```

## Head-to-head

| | BTC ret | ETH ret | SOL ret | Pooled trades | Pooled PF | Pooled exp |
|---|---|---|---|---|---|---|
| buy_hold (~2.7y) | +30.60% | −21.64% | −31.24% | — | — | — |
| S001 V1 (control) | −1.06% | +1.28% | −4.70% | 35 | 0.68 | −1.10% |
| **S003 H002** | +0.61% | +0.34% | −1.13% | **13** | **0.995** | **−0.01%** |

Per-coin S003: BTC 4 trades (PF 1.83, exp +1.07%, WR 75%), ETH 3 (PF
2.16, exp +1.85%), SOL 6 (PF 0.64, exp −1.67%).

**Verdict: REJECTED** (pre-registered rule: pooled expectancy not
positive after costs). 13 pooled trades cleared the minimum, so this
verdict is legitimate — no excuse-making on sample size.

## Finding 1: the E002 structural thesis generalizes

Trigger/gate compatibility (the diagnostic E002 was built to add):

| Hypothesis | Family | Triggers fired | Gate OPEN | Gate CLOSED |
|---|---|---|---|---|
| H001 band reclaim | mean-reversion | 10 | **0 (0%)** | 10 |
| H002 trend pullback | trend-aligned | 40 | **13 (33%)** | 27 |

Trend-aligned entries CAN live under the F001 gate; mean-reversion
entries cannot. This is now a measured, mechanistic result across two
hypotheses, not a suspicion. S003 also beat the control on both pooled
metrics (exp −0.01% vs −1.10%; PF 0.995 vs 0.68) — the direction of the
thesis is right even though the edge is absent.

## Finding 2: SOL is the recurring book-killer

| Coin | V1 exp/trade | S003 exp/trade |
|---|---|---|
| BTC | −0.19% | +1.07% |
| ETH | +2.20% | +1.85% |
| SOL | **−5.28%** | **−1.67%** |

Across both entry families and two experiments, BTC and ETH are
breakeven-to-positive after costs; SOL loses in every configuration.
The failure is not the entry family — it is regime selection on
high-volatility alts. This is now the single most evidenced problem in
the project.

## Finding 3: one trade that LOOKS like a risk breach isn't one

SOL bar 650→658: entry $235 → stop exit $188 = **−19.97% at the
position level**. Mechanics: in a violent regime 2×ATR was ~20% below
entry (passing the <50% guard); sizing is inverse to stop distance
(`coins = 1%·equity / stop_dist`), so the position was ~5% of equity
and the **equity** impact was the designed ~1%. The risk model held.
Recorded here so nobody misreads the ledger: `net_pct` is per-position,
not per-equity.

## Counterfactual: this time the gate may have cost money

27 blocked candidates, fwd10 returns: **mean +1.55%, median −0.31%, up
12/27**. Unlike E002 (where the gate blocked losers), the mean is
positive — driven by outliers (median says most blocked candidates were
duds). Honest read: at this sample size the gate's net veto value is
AMBIGUOUS — it clearly blocks capitulation knives (E002) but may also
block some would-be winners in established uptrends (E003). Accumulate
the ledger; do not conclude.

## Verdict

```
STATUS:  REJECTED

H002 — Trend Pullback
REASON: pooled expectancy −0.01% after costs (13 trades). Positive on
BTC/ETH, destroyed by SOL. Direction correct (beats control on both
metrics) but zero edge is zero edge.
```

## What we KNOW

- Trend-aligned entries are gate-compatible (33% of triggers pass) where
  mean-reversion entries are not (0%) — two-hypothesis measured result.
- S003 produced 13 trades, pooled exp −0.01%, PF 0.995: exactly
  breakeven after costs. REJECTED by pre-registered rule.
- SOL loses money under every entry family tested so far.
- Position-level net_pct can reach −20% under the frozen stop model
  while equity risk remains ~1% by construction (sizing inverse to stop
  distance).

## What we SUSPECT

- The edge, if any exists in this architecture, lives in the
  BTC/ETH-trending segments and dies in SOL-style chop — i.e., the
  missing component is regime classification, not entry selection.
- The F001 gate's veto is net-positive against capitulation but
  net-ambiguous against pullback entries in uptrends (counterfactual
  means: E002 −0.12%, E003 +1.55%).

## What we DON'T KNOW

- Whether per-regime performance would show a positive BTC/ETH
  trend-regime book that a better SOL filter could keep — untested; the
  trade and rejection ledgers to answer it already exist.
- Whether these results hold out-of-sample (everything so far is one
  ~2.7y window).
- Whether 13 trades says anything statistically. It does not.

## Next

- **E004 (recommended)** — regime attribution of EXISTING ledgers
  (E001–E003 trades + rejections): per-regime expectancy/wr/PF tables
  (bull/range/bear/high-vol per MARK's step 6). No new hypothesis; this
  is analysis of data already collected, and it directly tests the
  "SOL chop is the killer" suspicion.
- The D-level question is now pre-registered: if regime attribution
  confirms chop-driven losses, the next hypothesis family is a
  volatility/regime FILTER change at the D-level (supersedes part of
  D002's freeze), not another entry trigger.
