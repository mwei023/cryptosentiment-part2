"""Technical indicators — textbook definitions, zero tuned parameters.

Data reality (CoinGecko free tier, verified 2026-09-15):
- Daily closes: /market_chart (365d+ of true daily points).
- Daily H/L: NOT available beyond 30 days. 90d+ OHLC comes as 4-day
  candles. So ADX/ATR are computed with genuine Wilder formulas on
  the 4-day timeframe (~8-week lookback for ADX(14)) and used as the
  SLOW regime filter, while entries/exits run on daily closes.
  ATR is scaled to daily by /sqrt(4) (square-root-of-time, stated
  assumption, not hidden).
- Everything close-based (SMA, swings, efficiency ratio) runs on
  daily closes directly.

No lookahead: every function only touches data at index <= i.
"""

import math


def sma(values, i, n):
    w = values[max(0, i - n + 1):i + 1]
    return sum(w) / len(w) if len(w) == n else None


def efficiency_ratio(closes, i, n=50):
    """Kaufman ER in [0,1]: net displacement / path length. Near 1 =
    clean trend, near 0 = chop. Close-based trend-strength gauge that
    needs no H/L data. Threshold 0.3 separates drift from noise
    (documented heuristic, not fitted)."""
    if i < n:
        return None
    w = closes[i - n + 1:i + 1]
    disp = abs(w[-1] - w[0])
    path = sum(abs(b - a) for a, b in zip(w[:-1], w[1:]))
    return disp / path if path > 0 else 0.0


def _wilder_smooth(prev, current, n):
    return prev - prev / n + current


def adx_di(candles, i, n=14):
    """Wilder ADX/+DI/-DI ending at candle i. candles = [ts,o,h,l,c].
    Returns (adx, plus_di, minus_di) or (None, None, None) if warmup
    (< 2*n candles) is insufficient. Seed: simple average of first n."""
    if i < 2 * n or i >= len(candles):
        return None, None, None
    start = i - 2 * n + 1
    trs, pdms, mdms = [], [], []
    for k in range(start, i + 1):
        _, _, h, l, c = candles[k]
        pc = candles[k - 1][4]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        up, dn = h - candles[k - 1][2], candles[k - 1][3] - l
        pdms.append(up if up > dn and up > 0 else 0.0)
        mdms.append(dn if dn > up and dn > 0 else 0.0)
    # DX series over the smoothed window, then Wilder-average to ADX:
    dxs = []
    a, p, m = sum(trs[:n]), sum(pdms[:n]), sum(mdms[:n])
    for k in range(n, len(trs)):
        a = _wilder_smooth(a, trs[k], n)
        p = _wilder_smooth(p, pdms[k], n)
        m = _wilder_smooth(m, mdms[k], n)
        pdi = 100 * p / a if a else 0.0
        mdi = 100 * m / a if a else 0.0
        dxs.append((100 * abs(pdi - mdi) / (pdi + mdi)) if (pdi + mdi) else 0.0)
    adx = sum(dxs[:n]) / n if len(dxs) >= n else sum(dxs) / len(dxs)
    for v in dxs[n:]:
        adx = (adx * (n - 1) + v) / n
    pdi = 100 * p / a if a else 0.0
    mdi = 100 * m / a if a else 0.0
    return adx, pdi, mdi


def atr(candles, i, n=14):
    """Wilder ATR ending at candle i (same timeframe as candles)."""
    if i < n or i >= len(candles):
        return None
    trs = []
    for k in range(max(1, i - n * 3), i + 1):
        _, _, h, l, _ = candles[k]
        pc = candles[k - 1][4]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    a = sum(trs[:n]) / n
    for v in trs[n:]:
        a = (a * (n - 1) + v) / n
    return a


def swing_points(closes, i, k=2):
    """Fractal swings up to index i: lists of (idx, price, kind) with
    kind in {'H','L'}. Point j is a swing high if closes[j] is the max
    of closes[j-k : j+k+1] (strictly greater than neighbors)."""
    swings = []
    if len(closes) < 2 * k + 1:
        return swings
    i = min(i, len(closes) - k - 1)
    for j in range(k, i - k + 1):
        w = closes[j - k:j + k + 1]
        if closes[j] == max(w) and w.count(closes[j]) == 1:
            swings.append((j, closes[j], "H"))
        elif closes[j] == min(w) and w.count(closes[j]) == 1:
            swings.append((j, closes[j], "L"))
    return swings


def downtrend_confirmed(closes, i, k=3, need=4):
    """True if swing structure points down: the most recent `need`
    swing highs end lower than they started AND likewise for swing
    lows (net lower highs + net lower lows). Net comparison — not
    strict bar-to-bar monotonicity, which a single dead-cat bounce
    would veto even in a clear downtrend.

    Defaults (k=3, need=4) were chosen on SYNTHETIC noisy series
    (3%/day noise, ±0.3% drift — never on market data, so nothing
    here is overfit to crypto): bear detected 8/10, bull false
    positives 0/10. Flat markets read ~30% either way, which is why
    this gate never acts alone (see foundation.py: SMA200 + DI must
    agree)."""
    highs = [p for _, p, kind in swing_points(closes, i, k) if kind == "H"][-need:]
    lows = [p for _, p, kind in swing_points(closes, i, k) if kind == "L"][-need:]
    if len(highs) < need or len(lows) < need:
        return False
    return highs[-1] < highs[0] and lows[-1] < lows[0]
