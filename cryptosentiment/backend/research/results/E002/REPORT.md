# E002 — Band Reclaim Entry (H001)

## Receipt

```
ID:              E002
Hypothesis:      H001 (lower-band reversal confirmation)
Control:         S001 V1 band mean-reversion (foundation.run)
Treatment:       S002 band reclaim (research/strategies.py)
Foundation:      F001 (frozen) — gates, sizing, stops, targets, trail,
                 kill switch, costs byte-identical between arms
Git commit:      6988fb5
Python:          3.13.9
Started:         2026-09-16T10:03:41Z
Data:            Binance daily OHLC, 1000 bars/coin (~2.7y, 2024-01 → 2026-09)
Costs:           0.1% fee + 0.05% slippage per side, both arms
Look-ahead:      NONE (trigger uses bar i-1 band + bar i close/high;
                 fwd5/fwd10 in the ledger are analysis-only fields)
Machine receipt: summary.json (same directory)
```

## Entry definitions (the only delta)

- **S001 V1 (control):** close < trailing lower band → BUY. Knife catch.
- **S002 H001 (treatment):** yesterday closed below the lower band (R1) →
  today closed back inside (R2) → today's close broke yesterday's
  candle high (R3) → BUY candidate → foundation gates → trade.

## Head-to-head results

| | BTC ret | ETH ret | SOL ret | Pooled trades | Pooled PF | Pooled exp/trade |
|---|---|---|---|---|---|---|
| buy_hold (~2.7y) | +30.60% | −21.64% | −31.24% | — | — | — |
| S001 V1 (control) | −1.06% | +1.28% | −4.70% | 35 | 0.68 | −1.10% |
| **S002 H001** | **0 trades** | **0 trades** | **0 trades** | **0** | — | — |

The comparison is vacuous by construction: **S002 never traded.**

## The finding: H001 and F001 are structurally incompatible

Trigger-frequency diagnostic over ~800 evaluated bars/coin:

| Coin | R1 fails | R2 fails | R3 fails | **fired** | fired w/ gate OPEN | fired w/ gate CLOSED |
|---|---|---|---|---|---|---|
| BTC | 731 | 12 | 52 | 5 | **0** | 5 |
| ETH | 731 | 12 | 54 | 3 | **0** | 3 |
| SOL | 731 | 15 | 52 | 2 | **0** | 2 |

10 triggers in ~2,400 bars, and **100% were vetoed by the foundation
gate**. This is not bad luck — it is mechanical:

- R1 requires yesterday to close below the 80% lower band = a sharp
  capitulation day.
- F001's gate vetoes exactly those windows: a capitulation day pushes
  −DI above +DI (gate condition 2), drags price toward/below SMA200
  (condition 1), and confirms swing-structure downtrends (condition 3).
- One reclaim day is not enough for +DI to flip or price to recover
  above SMA200.

A mean-reversion trigger and a trend-family gate are members of
opposite families. The gate is doing its job; the trigger cannot live
under it. **The hypothesis "reclaim improves expectancy" is not
testable inside F001 as composed.**

## Counterfactual evidence (recorded, small n)

1. **The 10 blocked candidates** (fired while gate closed), forward
   10-day returns from the rejection ledger: mean **−0.12%**, median
   **−1.11%**, up 3/10 (30%). The gate vetoed trades that would have
   lost on average. Not significant at n=10, but directionally
   consistent with the gate earning its keep.
2. **V1 entries "skipped" by S002** (all 35, since S002 never traded),
   blind fwd10: BTC +0.70%, ETH +0.62%, SOL −2.53% — mixed; no evidence
   the gate misses obvious winners.

## Verdict

```
STATUS:  REJECTED (as composed)

H001 — Band Reclaim
REASON: trigger and foundation gate are mutually exclusive by
construction; 0 trades across ~2,400 bars/coin. Where candidates did
fire, the gate's veto was directionally correct (blocked candidates
fwd10 mean −0.12%).

Per protocol: H001 is NOT modified and NOT retried with loosened gates.
It is recorded and archived. Next hypothesis is from a different
family: H002 Trend Pullback (trend-aligned entry), which the structural
finding above directly motivates.
```

Note for future researchers: H001 was never tested as a STANDALONE
system without F001. That experiment is deliberately not run — the
foundation is frozen (D002) and its veto of capitulation entries is the
whole point of the architecture. Anyone wishing to test standalone
H001 must open a new decision to supersede D002 first.

## What we KNOW

- S002 as composed cannot trade inside F001: 10 triggers / 2,400 bars,
  100% vetoed, mechanically explained by trigger/gate family conflict.
- The 10 blocked candidates lost money on average over the next 10
  days (mean −0.12%, median −1.11%, n=10).
- V1 control re-confirmed on the longer window: pooled PF 0.68,
  expectancy −1.10%/trade over 35 trades (consistent with E001/D001).
- On this ~2.7y Binance window, buy_hold was +30.6% (BTC), −21.6%
  (ETH), −31.2% (SOL): the window contains a strong BTC bull segment,
  unlike the E001 read that emphasized the bear segment.

## What we SUSPECT

- Any mean-reversion entry (band touch, RSI dip, volatility shock
  reversal) will hit the same structural wall under F001. If H002
  (trend pullback) also fails, the right question may be whether the
  gate family or the entry family is wrong — that is a D-level
  decision, not a tuning exercise.

## What we DON'T KNOW

- Whether reclaim entries have edge in any regime — untested here.
- Whether the gate's veto of capitulation is net-positive across a
  larger sample of blocked candidates (n=10 so far; the ledger keeps
  accumulating).
- Whether H002 trend pullback produces trades the gate will actually
  allow (its trigger exists in uptrends, so it should — but that is
  what we said about mean reversion, in reverse).

## Next

- **E003** — H002 Trend Pullback: bullish regime → trend established →
  pullback → exhaustion → trend resumes → LONG. Identical data, costs,
  foundation. V1 remains the standing control; V2 is archived REJECTED.
- Correction appended to E001's report regarding the data window
  (Binance rows span ~2.7y, not 365d — see E001 REPORT addendum).
