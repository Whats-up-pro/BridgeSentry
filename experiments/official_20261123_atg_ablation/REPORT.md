# ATG-aware mutation ablation (execution-only oracle)

Frozen record. Tests whether ATG-aware mutation — biasing insertion toward functions
adjacent in the Atomic Transfer Graph, one of the design's "intelligent" search
components — improves the fuzzer's ability to reach valid exploits under the
execution-only oracle, versus plain uniform-random mutation.

## Setup

- Ablated component: `mutate_seq` (plain, atg0) vs `mutate_seq_atg` (ATG-adjacency
  biased, atg1), toggled by `BRIDGESENTRY_ATG_MUTATION`. The code is in commit
  `8b53a55` (also in `a9448c6`); everything else (oracle, seven gates, coverage
  selection, snapshot) is identical.
- Fixtures: the two incidents where random search leaves room for guidance per
  Table `tab:seven` — FEG SmartBridge (16/20 random) and PolyNetwork (1/20 random).
  The other five are solved by random seeds in under ~1 s, so mutation cannot help.
- Variant vulnerable, seeds random, 20 seeds (1042..20042), budget 300 s each.
  Evaluation mode official, empty-RPC local fixtures. Statically linked musl build on
  the UIT cluster (partition `normal`, QOS `mig2-35`, 8 CPU, no GPU), jobs 111610
  (FEG) / 111611 (PolyNetwork). 80 result JSONs under `runs_atg{0,1}/`.

## Result

| Fixture | atg0 (plain) valid | atg1 (ATG-aware) valid | Fisher p | median TTVE atg0 / atg1 |
|---|---|---|---|---|
| FEG SmartBridge | 16/20 | 16/20 | 1.0 | 45.1 s / 104.8 s |
| PolyNetwork | 0/20 | 1/20 | 1.0 | — / 117.2 s |

- Valid-exploit rate: no change on either fixture (Fisher exact p = 1.0 both).
- Time to first valid exploit, FEG: log-rank (censored at 300 s) chi2 = 0.175,
  **p = 0.68** — not significant. The median gap (45 s vs 105 s) is not backed by the
  distribution; the per-run TTVEs overlap heavily.
- Sanity: atg0 reproduces the random baseline of Table `tab:seven` (FEG 16/20;
  PolyNetwork 0/20 here vs 1/20 there, within noise), confirming the harness is
  identical apart from the mutation toggle.

## Conclusion

Under the execution-only oracle, ATG-aware mutation gives **no measurable benefit** —
neither in valid-exploit rate nor in time to first valid exploit — on the only two
incidents where search has room to matter. This is an honest negative result,
consistent with the paper's finding that the oracle and grounded seeds, not the search
guidance, determine what is reconstructed. It converts "ATG-aware mutation: not
evaluated" into "evaluated; no effect."
