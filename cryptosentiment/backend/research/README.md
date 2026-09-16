# Research Record — CryptoSentiment

The code is the experiment. This directory is the evidence of what the
experiment actually proved. Everything here is written so that another
engineer (or MARK) can reconstruct and audit any claim later.

## Structure

    research/
    ├── README.md            <- this file: conventions
    ├── registry.json        <- every experiment/hypothesis/decision, one line each
    ├── DECISIONS.md         <- permanent decision log (append-only)
    ├── results/
    │   └── E001/
    │       ├── summary.json <- machine-readable receipt
    │       └── REPORT.md    <- human-readable analysis
    └── e001_foundation_validation.py   <- the runnable harness

## ID scheme

| Prefix | Meaning | Examples |
|---|---|---|
| `H###` | Hypothesis (an entry idea to test) | H001 lower-band reversal confirmation |
| `E###` | Experiment (a run against data) | E001 foundation validation |
| `F###` | Foundation (frozen risk/regime framework) | F001 |
| `S###` | Strategy implementation | S001 band mean-reversion (V1 control) |
| `D###` | Decision (append-only, with evidence) | D001 V1 rejected as live strategy |

Rule: six months from now we want "H001 was tested in E002 on dataset X
under foundation F001 and rejected because pooled expectancy was −0.8%
after costs" — not "I think that lower-band thing worked once".

## The three truths

Every report separates exactly what the evidence supports:

- **What we KNOW** — directly demonstrated by a run in this directory.
- **What we SUSPECT** — hypotheses consistent with evidence, untested.
- **What we DON'T KNOW** — open questions, explicitly listed.

No hypothesis graduates to fact because it appeared in an earlier report.

## Rules of the layer

1. Negative results are first-class. Rejected hypotheses are recorded
   with reasons, forever. They prevent re-testing dead ideas.
2. Strategies are never deleted. V1 (band mean-reversion) is the
   permanent control; every future strategy must beat it under
   identical conditions.
3. Experiments run under identical data, costs, and foundation. No
   strategy gets a better window, tighter costs, or looser gates.
4. Every experiment persists a receipt (summary.json) with git commit,
   timestamps, and full metrics — no eyeball claims.
5. The forward journal (`paper_journal.csv`) is the live referee. It is
   never reset for new strategies; strategy versions are recorded per
   row so competing entries can coexist.
