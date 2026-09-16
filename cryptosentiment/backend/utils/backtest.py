"""Walk-forward backtesting for the 1-day Prophet pipeline.

Method (expanding window, no lookahead):
- Take a daily close series. For each fold, train Prophet on
  ``prices[0 : train_end]`` (train_end grows by ``step`` each fold),
  forecast 1 day ahead, and score against the REAL next close.
- Baselines scored on the same folds:
  - naive: tomorrow == today (last train close). The model must beat this.
  - sma7: mean of last 7 train closes.
- Metrics: MAE, RMSE, MAPE, directional accuracy (did we get up/down
  right vs last close?), interval coverage (% of actuals inside the
  80% interval). Coverage far below 80% means overconfident bands.

A model that can't beat naive on MAE *and* direction has no trading
skill — this module exists to say that out loud.
"""

import logging
import math

logger = logging.getLogger(__name__)


def _metrics(actuals, preds):
    n = len(actuals)
    if n == 0:
        return {}
    ae = [abs(a - p) for a, p in zip(actuals, preds)]
    se = [(a - p) ** 2 for a, p in zip(actuals, preds)]
    ape = [abs((a - p) / a) * 100 for a, p in zip(actuals, preds) if a != 0]
    mae = sum(ae) / n
    rmse = math.sqrt(sum(se) / n)
    mape = sum(ape) / len(ape) if ape else float("nan")
    return {"n": n, "mae": mae, "rmse": rmse, "mape": mape}


def walk_forward_validate(prices, horizon=1, min_train=180, step=7, max_folds=12,
                          verbose=True):
    """Run expanding-window validation over ``[[ts_ms, price], ...]``.

    Uses the most recent folds (best reflection of current regime).
    Each fold trains a fresh Prophet model — slow but honest.
    """
    from utils.prediction_utils import prepare_data, train_prophet_model, make_prediction

    if horizon != 1:
        raise ValueError("Only 1-day horizon is validated. Got %s." % horizon)
    closes = [float(p[1]) for p in prices if p[1] is not None and float(p[1]) > 0]
    n = len(closes)
    if n < min_train + max_folds:
        raise ValueError(
            f"Need >= {min_train + max_folds} closes for validation, got {n}."
        )

    # Most recent folds: last fold's test index = n - 1 (last close).
    fold_ends = []
    end = n - 1
    for _ in range(max_folds):
        train_end = end - horizon  # train on [0:train_end], test = closes[end]
        if train_end < min_train:
            break
        fold_ends.append(train_end)
        end -= step
    fold_ends.reverse()  # chronological

    folds = []
    for train_end in fold_ends:
        train_slice = [[i * 86400000, c] for i, c in enumerate(closes[:train_end])]
        # NOTE: synthetic timestamps spaced 1 day apart — Prophet only
        # needs ordering + daily spacing for this pipeline, and using
        # synthetic ts avoids timezone gaps in CoinGecko data. The
        # actual DATE is taken from the fold position for reporting.
        try:
            df = prepare_data(train_slice, min_history=min_train)
            model = train_prophet_model(df)
            pred = make_prediction(model, periods=horizon)[-1]
            yhat = float(pred["predicted"])
            lower = float(pred["lower"])
            upper = float(pred["upper"])
        except Exception as e:
            logger.warning(f"Fold train_end={train_end} failed: {e}")
            continue

        last_close = closes[train_end - 1]
        actual = closes[train_end]
        naive = last_close
        sma7 = sum(closes[train_end - 7:train_end]) / 7

        actual_dir = 1 if actual > last_close else (-1 if actual < last_close else 0)
        folds.append({
            "train_end": train_end,
            "last_close": last_close,
            "actual": actual,
            "prophet": yhat,
            "lower": lower,
            "upper": upper,
            "naive": naive,
            "sma7": sma7,
            "prophet_dir_ok": (1 if yhat > last_close else (-1 if yhat < last_close else 0)) == actual_dir,
            "naive_dir_ok": True,  # naive predicts no change; counted separately below
            "sma7_dir_ok": (1 if sma7 > last_close else (-1 if sma7 < last_close else 0)) == actual_dir,
            "covered": (lower <= actual <= upper),
        })

    if not folds:
        raise RuntimeError("All folds failed to train.")

    out = {"folds": folds, "horizon": horizon, "min_train": min_train}
    for name in ("prophet", "naive", "sma7"):
        actuals = [f["actual"] for f in folds]
        preds = [f[name] for f in folds]
        out[name] = _metrics(actuals, preds)
    out["prophet"]["directional_acc"] = sum(f["prophet_dir_ok"] for f in folds) / len(folds)
    out["sma7"]["directional_acc"] = sum(f["sma7_dir_ok"] for f in folds) / len(folds)
    # Naive predicts zero change: direction skill measured as MAE-ratio instead.
    out["prophet"]["coverage"] = sum(f["covered"] for f in folds) / len(folds)
    out["prophet"]["mae_vs_naive"] = (
        out["naive"]["mae"] / out["prophet"]["mae"] if out["prophet"]["mae"] else float("nan")
    )
    out["skill"] = {
        "beats_naive_mae": out["prophet"]["mae"] < out["naive"]["mae"],
        "beats_sma7_mae": out["prophet"]["mae"] < out["sma7"]["mae"],
        "directional_acc": out["prophet"]["directional_acc"],
        "coverage_80_nominal": out["prophet"]["coverage"],
    }
    if verbose:
        logger.info(
            f"Folds={len(folds)} Prophet MAE={out['prophet']['mae']:.2f} "
            f"vs naive {out['naive']['mae']:.2f} | dir={out['prophet']['directional_acc']:.0%} "
            f"| coverage={out['prophet']['coverage']:.0%} (nominal 80%)"
        )
    return out


def validate_coin(coin_id, history_days=365, **kwargs):
    """Fetch real CoinGecko history and walk-forward validate it."""
    from utils.market_data import get_historical_prices
    data = get_historical_prices(coin_id, days=history_days)
    prices = data.get("prices", [])
    if not prices:
        raise RuntimeError(f"No CoinGecko data for {coin_id}.")
    result = walk_forward_validate(prices, **kwargs)
    result["coin_id"] = coin_id
    result["history_rows"] = len(prices)
    return result
