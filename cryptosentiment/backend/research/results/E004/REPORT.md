# E004 — Regime Attribution of E001–E003 Ledgers

## Receipt

```
ID:              E004
Type:            analysis of existing ledgers (no new hypothesis)
Systems sliced:  S001 V1 band_revert · S002 band_reclaim · S003 trend_pullback
Ledgers:         48 trades, 37 blocked candidates (with fwd10)
Data:            Binance daily OHLC, 1000 bars/coin (~2.7y)
Regimes:         BULL/BEAR = close vs SMA200 (F001 rule);
                 TREND/RANGE = ADX(14) >= 25 (F001 threshold);
                 HIGH_VOL = trailing 30d sigma > 1.5x trailing 252d median
Assignment:      trades by entry-bar regime; candidates by bar, fwd10
Pre-registered:  if BULL_TREND positive AND BEAR/HIGH_VOL negative ->
                 D006 regime/vol filter proposal
Git:             6988fb5
Machine receipt: summary.json (same directory)
```

## TRADES by regime

**S001 V1 band_revert (35 trades):**

| regime | n | mean | median | win% | sum |
|---|---|---|---|---|---|
| BULL_TREND | 23 | **−1.84%** | −0.08% | 48% | −42.26 |
| BULL_RANGE | 12 | **+0.32%** | +1.77% | 67% | +3.90 |
| BEAR_* | 0 | — | — | — | — |

**S003 trend_pullback (13 trades):**

| regime | n | mean | median | win% | sum |
|---|---|---|---|---|---|
| BULL_TREND | 8 | **+0.79%** | +3.44% | 62% | +6.32 |
| BULL_RANGE | 5 | **−1.30%** | +3.05% | 60% | −6.49 |
| BEAR_* | 0 | — | — | — | — |

**Pooled (48):** BULL_TREND 31 trades, mean −1.16%, median +1.17%, 52% win,
sum −35.94 · BULL_RANGE 17 trades, mean −0.15%, median +1.77%, 65% win,
sum −2.59 · BEAR 0 (see Finding 1).

**Volatility overlay:** 0/48 entry bars were HIGH_VOL (flag verified
live: fires on 4.1–6.5% of bars per coin). Entries cluster on calm
pullback days. The trade-level vol question is unanswerable with this
data — recorded honestly, not smoothed over.

## BLOCKED CANDIDATES by regime (fwd10)

| regime | n | mean | median | win% | sum |
|---|---|---|---|---|---|
| BULL_TREND | 2 | −4.41% | +4.04% | 50% | −8.82 |
| BULL_RANGE | 7 | −3.08% | −3.71% | 14% | −21.53 |
| BEAR_TREND | 7 | −3.02% | −2.62% | 14% | −21.11 |
| **BEAR_RANGE** | **21** | **+4.38%** | +2.98% | 57% | **+91.98** |

## Finding 1: the pre-registered suspicion was WRONG

D005 suspected "SOL chop is the killer." The attribution says
something sharper: **the killer is TRENDING days inside bull markets,
not ranging chop.** Pooled BULL_TREND expectancy is −1.16%/trade
(dragged by V1's knife-catches: −1.84%/trade across 23 trades) while
BULL_RANGE is −0.15% and the only *positive* cells in the entire
project are S003-in-BULL_TREND (+0.79%) and V1-in-BULL_RANGE (+0.32%).

And there is no BEAR book to blame: **the F001 gate admits zero BEAR
trades by construction** (SMA200 requirement), so every trade in every
experiment was BULL_*. The losses were never bears; they were bull
trends eating mean-reversion entries. (SOL's losses specifically came
from high-ATR trending stretches — its trades and the blocked-candidate
evidence agree.)

## Finding 2: edge in this project is strategy×regime specific

| cell | n | exp/trade | reading |
|---|---|---|---|
| V1 × BULL_TREND | 23 | −1.84% | the killer cell — knife-catching in trends |
| V1 × BULL_RANGE | 12 | +0.32% | V1's only living cell |
| S003 × BULL_TREND | 8 | +0.79% | the only trend-entry cell that breathes |
| S003 × BULL_RANGE | 5 | −1.30% | pullback entries die in ranging bulls |

Each entry family has exactly one profitable regime cell — and they are
DIFFERENT cells. Neither family has enough cells to trade alone.

## Finding 3: the gate is right about bears, wrong about ranges (maybe)

Blocked candidates in BEAR_RANGE averaged **+4.38% fwd10** (21/37
candidates, sum +91.98) — the gate's bear veto may be discarding the
most promising mean-reversion window, at least in this window. BEAR_TREND
and BULL_RANGE blocks averaged −3%: there the veto earned its keep.
Sample sizes are small and this is one 2.7-year tape — AMBIGUOUS,
recorded, not concluded.

## Verdict (pre-registered rule applied honestly)

The rule as written ("BULL_TREND positive AND BEAR/HIGH_VOL negative →
filter proposal") does NOT fire: BULL_TREND is negative, and the bear/
vol cells have no trades. **No D006 filter proposal from this run.**
The suspicion that motivated the rule was wrong — that is the value of
pre-registration: a wrong belief died instead of becoming policy.

## What we KNOW

- All 48 trades across three systems occurred in BULL regimes (gate
  structure), so bear performance of the entries is UNTESTED, not good.
- BULL_TREND is the pooled killer (−1.16%/trade, n=31); V1 accounts for
  the drag (−1.84% × 23), S003 is positive there (+0.79% × 8).
- The only positive cells: S003×BULL_TREND (+0.79%), V1×BULL_RANGE
  (+0.32%). Different families own different cells.
- Blocked BEAR_RANGE candidates averaged +4.38% fwd10 (n=21) — the
  gate may be over-vetoing range-bear mean reversion (ambiguous, n
  small).
- No trade entered on a HIGH_VOL day (flag works, 4–6.5% incidence).

## What we SUSPECT

- A regime-conditional book (V1 in BULL_RANGE, S003 in BULL_TREND,
  nothing else) would have summed to roughly +$0/+3.9 +6.3 −6.5−... —
  small positive, but this is IN-SAMPLE cell selection and would need
  out-of-sample confirmation before any belief is invested in it.
- The gate's SMA200 veto throws away a possibly profitable BEAR_RANGE
  mean-reversion window.

## What we DON'T KNOW

- Anything out-of-sample. Every cell above is one 2.7y window.
- Whether the BEAR_RANGE counterfactual survives contact with real
  execution (stop-throughs, gaps) — it is currently an unexecuted
  counterfactual, not a result.
- Whether any cell clears costs with statistical significance (n per
  cell: 2–31; none does).

## Next

- **E005 (proposed, D-level)** — combine cells honestly: a
  regime-conditional book (V1 in BULL_RANGE, S003 in BULL_TREND, flat
  otherwise), tested FIRST in-sample, THEN on an untouched
  out-of-sample split. This is a composition of already-tested cells,
  not a new hypothesis; it requires a D-level note because it
  re-combines frozen components.
- Longer/multi-coin data (CoinGecko paid tier or exchange archives) to
  get cell sample sizes above n=30.
- The forward journal remains the only un-rewritable referee.
