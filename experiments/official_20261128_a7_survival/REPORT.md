# A7: time-to-valid-exploit survival curves

Frozen analysis record, 2026-11-28. **No new fuzzing run.** The figure and the table are
computed from committed per-run results by `make_figure.py`:

- random seeds: `experiments/official_20261114_a1_hpc/official_runs/<b>/vulnerable/random/seed_*.json`
- grounded seeds, no-retrieval regime: `experiments/official_20261118_c3b_hpc/vulnerable/no_rag/official_runs/<b>/vulnerable/llm/seed_*.json`

Each run contributes its `first_valid_exploit_s` (the time of the first valid exploit) or a
right-censored observation at the 300 s budget when no valid exploit was found. The two
incidents shown, FEG SmartBridge and PolyNetwork, are the only two on which random seeds leave
room for guidance (Table `tab:seven`); on the other five, random seeds solve every run within
about a second, so a survival curve would be a vertical line.

## Survival estimate

All censoring is at the end of the study (the budget), so the Kaplan-Meier estimate reduces to
the empirical survival `S(t) = (runs with no valid exploit by time t) / 20`, a right-continuous
step function that floors at the censored fraction. `fig_survival_ttve.png` plots `S(t)` on a
logarithmic time axis for random against grounded (no-retrieval) seeds.

## Numbers (`survival_ttve.csv`), consistent with Tables `tab:seven` and `tab:seeds`

| Incident | Seeds | Valid-exploit runs | Censored | Median TTVE |
| --- | --- | --- | --- | --- |
| FEG SmartBridge | random | 16/20 | 4 | 72.3 s |
| FEG SmartBridge | grounded (no retrieval) | 20/20 | 0 | 0.0011 s |
| PolyNetwork | random | 1/20 | 19 | > 300 s |
| PolyNetwork | grounded (no retrieval) | 20/20 | 0 | 0.034 s |

The median is the median over all 20 runs with censored runs set to the budget, reported as
`> 300` when more than half are censored, exactly as in the manuscript's tables; the figure's
curves use the individual event times.

## Reading

The grounded survival curve drops to zero within milliseconds on both incidents, while the
random curve descends over tens of seconds on FEG SmartBridge and never leaves the top of the
plot on PolyNetwork (one run in 20). The figure is the distributional view behind the
log-rank tests reported for RQ3; the tables give only the medians and the counts.
