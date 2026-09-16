"""E006 — Price-only vs information-enhanced (H005), forward-only.

Why forward-only: NewsAPI free tier has no deep history, so sentiment
cannot be historically backtested without survivorship-biased archives.
papertrade.py refuses to fake it. The journal is therefore the lab:
every coin-day logs BOTH arms from identical inputs (same bands, same
price, same headlines) — the arms differ in exactly one place, the
pre-registered FinBERT majority veto (BUY vetoed when neg > pos, SELL
vetoed when pos > neg; HOLDs never become trades on news alone).

VERDICT RULES (pre-registered, applied as written):
  settled per arm < MIN_SETTLED -> RUNNING (no verdict possible)
  info expectancy > price expectancy AND info PF > price PF
    AND vetoed price trades averaged <= 0 (vetoes blocked losers,
    not winners) -> ADVANCED (with caveats)
  else -> REJECTED (news adds no forward edge as composed)

Secondary (reported, never verdict-driving): confidence calibration —
does conf_info separate wins from losses better than conf_price?

Run from backend/:  ./cryptoenv/bin/python -m research.e006_price_vs_info
"""

import csv
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EXPERIMENT_ID = "E006"
HYPOTHESIS_ID = "H005"
MIN_SETTLED = 30

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", EXPERIMENT_ID)
JOURNAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "paper_journal.csv")


def _load():
    if not os.path.exists(JOURNAL):
        return []
    with open(JOURNAL, newline="") as f:
        return list(csv.DictReader(f))


def _arm(rows, net_key, conf_key):
    nets, confs_w, confs_l = [], [], []
    for r in rows:
        if not r.get(net_key):
            continue
        n = float(r[net_key])
        nets.append(n)
        try:
            c = float(r.get(conf_key, "") or "nan")
        except ValueError:
            c = float("nan")
        if n > 0 and c == c:
            confs_w.append(c)
        elif n <= 0 and c == c:
            confs_l.append(c)
    if not nets:
        return {"settled": 0}
    wins = [n for n in nets if n > 0]
    gp, gl = sum(wins), abs(sum(n for n in nets if n <= 0))
    out = {
        "settled": len(nets),
        "wins": len(wins),
        "losses": len(nets) - len(wins),
        "win_rate_pct": round(len(wins) / len(nets) * 100, 1),
        "expectancy_pct": round(sum(nets) / len(nets), 3),
        "total_net_pct": round(sum(nets), 2),
        "profit_factor": round(gp / gl, 3) if gl else (float("inf") if gp else 0.0),
    }
    if confs_w and confs_l:
        out["calibration"] = {
            "mean_conf_win": round(sum(confs_w) / len(confs_w), 2),
            "mean_conf_loss": round(sum(confs_l) / len(confs_l), 2),
            "separation": round(sum(confs_w) / len(confs_w)
                                - sum(confs_l) / len(confs_l), 2),
        }
    return out


def main():
    started = datetime.now(timezone.utc)
    print("=" * 70)
    print("E006 — PRICE-ONLY vs INFORMATION-ENHANCED (H005), forward-only")
    print("=" * 70)
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    print(f"Started: {started.isoformat()}   Git: {commit}   "
          f"Python: {platform.python_version()}")
    print(f"Verdict rules: settled/arm < {MIN_SETTLED} -> RUNNING; "
          f"info exp > price exp AND info PF > price PF "
          f"AND vetoed-price exp <= 0 -> ADVANCED; else REJECTED\n")

    rows = _load()
    print(f"Journal rows: {len(rows)}")
    price = _arm(rows, "net_price", "conf_price")
    info = _arm(rows, "net_info", "conf_info")

    # Counterfactual: on veto days (price traded, info held), what did
    # the price arm do? Negative expectancy = vetoes blocked losers.
    veto_nets = [float(r["net_price"]) for r in rows
                 if r.get("signal_price") != "HOLD"
                 and r.get("signal_info") == "HOLD" and r.get("net_price")]
    veto_exp = (round(sum(veto_nets) / len(veto_nets), 3)
                if veto_nets else None)
    n_vetoes = sum(1 for r in rows
                   if r.get("signal_price") != "HOLD"
                   and r.get("signal_info") == "HOLD")

    print(f"price arm: {price}")
    print(f"info arm : {info}")
    print(f"vetoes: {n_vetoes}, vetoed-price expectancy: {veto_exp}")

    if price.get("settled", 0) < MIN_SETTLED or info.get("settled", 0) < MIN_SETTLED:
        status = "RUNNING"
        why = (f"only {price.get('settled', 0)} price / "
               f"{info.get('settled', 0)} info settled (< {MIN_SETTLED}/arm): "
               f"no verdict possible yet — keep logging daily")
    elif (info["expectancy_pct"] > price["expectancy_pct"]
          and info["profit_factor"] > price["profit_factor"]
          and (veto_exp is not None and veto_exp <= 0)):
        status = "ADVANCED"
        why = ("info arm beats price arm on expectancy and profit factor, "
               f"and vetoes blocked losers (vetoed-price exp {veto_exp}%)")
    else:
        status = "REJECTED"
        why = ("info arm does not beat price arm on both expectancy and "
               "profit factor with supporting veto counterfactual — "
               "news adds no forward edge as composed")
    print(f"\nVERDICT: {status} — {why}")

    finished = datetime.now(timezone.utc)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    receipt = {
        "experiment_id": EXPERIMENT_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "design": ("dual-arm forward journal: identical inputs, "
                   "info arm = price signal + FinBERT majority veto; "
                   "HOLDs never become trades on news alone"),
        "pre_registered_rules": {
            "min_settled_per_arm": MIN_SETTLED,
            "advanced": ("info expectancy > price expectancy AND "
                         "info PF > price PF AND vetoed-price exp <= 0"),
        },
        "started": started.isoformat(),
        "finished": finished.isoformat(),
        "git_commit": commit,
        "python": platform.python_version(),
        "journal_rows": len(rows),
        "price": price,
        "info": info,
        "vetoes": n_vetoes,
        "vetoed_price_expectancy_pct": veto_exp,
        "verdict": {"status": status, "reason": why},
    }
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        json.dump(receipt, f, indent=2, default=str)
    print(f"\nReceipt written: research/results/{EXPERIMENT_ID}/summary.json")


if __name__ == "__main__":
    main()
