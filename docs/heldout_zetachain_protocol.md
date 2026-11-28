# Held-out protocol: grounded LLM seeds on an unseen incident (registered before seed generation)

Registered 2026-11-28, before any grounded seed set is generated for the new
incident and before its fixture is used to generate seeds. Results will be
reported whatever they show, next to the C3b grounded campaign.

## Why this campaign exists

C3b (`docs/C3b_protocol.md`, `experiments/official_20261118_c3b_hpc/`) showed
that grounded seeds reach a valid exploit faster than random seeds, but the
grounded configuration was **designed after** observing the ungrounded campaign
on the same five incidents, and no further incident was available to hold out.
That is the one weakness the C3b report states about itself.

This campaign removes it. It adds a single incident that was **not** among the
five used to design grounded generation and that **postdates the model's stated
training cutoff**, and it runs the C3b grounded pipeline on it **unchanged**. If
grounded seeds reconstruct the unseen incident, neither tuning to the design
incidents nor pretraining exposure explains the result.

## The incident (held out)

ZetaChain GatewayEVM, 26 April 2026 (after the 06/2024 cutoff of gpt-oss-120b
and the mid-2024 cutoff of DeepSeek-V3; not in the C3b design set). Public
technical analysis: SolidityScan, "ZetaChain Gateway Hack Analysis". Root cause,
a source -> relay -> destination chain:

- Source (ZetaChain zEVM): `GatewayZEVM.call(receiver, zrc20, message,
  callOptions, revertOptions)` has no caller authentication and copies
  `callOptions.IsArbitraryCall` from the caller into the emitted cross-chain
  event.
- Relay: the protocol's validators (TSS) sign a destination transaction from
  that event. The harness models this legitimate delivery with its faithful
  relay, executed under the relayer identity granted the signer role in setup.
- Destination (Ethereum): `GatewayEVM.execute(messageContext, destination,
  data)` is gated by the signer role but, when `messageContext.sender == 0`
  (the arbitrary-call branch the attacker selects), runs `destination.call(data)`
  with attacker-controlled `data`. A deny-list blocks only two selectors, not
  ERC-20 `transferFrom`, so a token that a victim had approved to the gateway is
  drained by `transferFrom(victim, attacker, amount)`.

The fix authenticates the caller so the destination cannot receive an
attacker-chosen `messageContext.sender == 0`, i.e. removes the arbitrary-call
branch. The patched variant applies exactly this.

## Method under test (frozen; no code change)

The grounded generation pipeline is used **exactly as registered in C3b**:
`src/module2_rag/grounding.py`, `prompts/system_adversary_grounded.txt`,
`seed_compiler.py`, the mutator, the oracle, and the fuzzer binary are
unchanged. Only a new fixture is added under `benchmarks/zetachain_2026/`
(vulnerable and patched re-implementation, execution specification, deterministic
test). Adding a fixture is not a change to the method: no prompt, compiler rule,
or protocol step names this incident or its exploit.

Positive control (must pass before any seed is generated): the documented
exploit of `zetachain_2026`, compiled by `seed_compiler.py`, yields a valid
exploit at the first execution on the vulnerable variant and no alert on the
patched variant (`scripts/official/seed_channel_control.py`). If the positive
control fails, the fixture is not a faithful harness of the incident; that is
reported and the campaign is not run.

## Design

- Fixture: `zetachain_2026` only.
- Regime: `no_rag` (no retrieval). This is the clean held-out claim: the model
  is shown only the comment-free source, ABIs, deployment and relay rule of the
  target, with no incident retrieved and none in its training data. One grounded
  seed set, generated once, under the frozen pipeline, for each model that C3b
  and the cross-model campaign used: gpt-oss-120b and DeepSeek-V3.
- Runs: 20 fuzzing seeds (1042..20042) x 300 s x {vulnerable, patched}; strict
  LLM seeds; empty RPC; same binary and job logic as C3b.
- Baseline on the same fixture, same binary, seeds and budget: random seeds
  (`BRIDGESENTRY_OFFICIAL_SEEDS=random`), 20 seeds x 300 s x {vulnerable,
  patched}, so the incident has its own random baseline rather than borrowing
  one.

## Hypotheses and analysis (fixed now)

- H1 (held-out reconstruction): grounded no-retrieval seeds reach a valid
  exploit on `zetachain_2026` in more runs, or sooner, than random seeds.
- Primary outcome: time to first valid exploit (fuzzing only), runs without one
  censored at 300 s; log-rank test. Secondary: valid-exploit runs out of 20,
  Fisher exact test. 95% Clopper-Pearson intervals for the rates.
- Patched variants: every alert is a false alarm; reported as alert runs / 80
  (2 models x 20 grounded + 1 random x 20, all patched).
- Seed-channel diagnostics: actions written vs resolved, repair rounds used.
- Cost: generation tokens, USD at list price and wall-clock per seed set.

## Stopping rule and deviations

One campaign. A run is repeated only for an infrastructure failure (non-zero rc
or missing result JSON), and then every condition of that job is rerun. Any
deviation is recorded in the campaign REPORT.md with its reason. If H1 fails, the
negative result is reported; it would mean grounded seeds do not transfer to an
unseen incident, which is itself a finding. Changing the method after seeing the
outcome (for example, adding execution feedback) would be a separate, newly
registered campaign.
