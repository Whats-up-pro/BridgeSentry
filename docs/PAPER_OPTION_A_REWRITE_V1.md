# BridgeSentry Option A — Manuscript Rewrite V1

**Date:** 2026-10-09  
**Purpose:** Exact replacement text for the latest author manuscript before new official experiments are available. This revision changes framing and claim discipline only; it does not invent results.

> Source-of-truth warning: repository `latex/paper.tex` is older than the current author manuscript. Apply these replacements only after the latest CAS/Elsevier source has been synchronized.

## 1. Title

Replace the current title with:

```latex
\shorttitle{BridgeSentry: Semantic-Guided Cross-Chain Exploit Validation}
\title[mode=title]{BridgeSentry: Semantic-Guided Cross-Chain Exploit Reconstruction and Validation in a Dual-EVM Harness}
```

Rationale: removes the implication of validated zero-day discovery while retaining the actual semantic/execution focus.

## 2. Working abstract before the official campaign

Replace the current abstract with:

```latex
\begin{abstract}
Cross-chain bridge failures can arise from interactions among source-chain contracts, relay or validator logic, and destination-chain contracts, making security testing difficult to reduce to a single contract or a single execution domain. Existing approaches provide complementary capabilities, including cross-chain static analysis, transaction monitoring, graph-based attack detection, and dynamic fuzzing. This paper presents BridgeSentry, a semantic-guided framework for reconstructing and validating exploit traces in EVM-compatible cross-chain bridges. BridgeSentry combines (1) hybrid semantic extraction using structured program analysis with optional LLM enrichment to construct Atomic Transfer Graphs (ATGs) and candidate invariants, (2) retrieval-grounded generation of threat-model-constrained action sequences from a structured historical-incident corpus, and (3) a dual-EVM execution harness with an explicit relay and semantic guidance.

\textbf{Current evaluation scope:} the retained legacy evaluation contains 12 reconstructed historical incidents: 10 EVM reconstructions, one EVM surrogate of a Solana vulnerability, and one scenario-layer-only case. Under a full-knowledge retrieval setting, all 12 target predicates are triggered, 11 cases execute target bytecode, and the mean fuzzing-only trigger time on successful legacy runs is 1.66 seconds. These quantities characterize target-aware reconstruction and do not constitute a valid-exploit rate or a zero-day discovery result. The current artifact does not yet contain a completed incident-disjoint, paired-patch, benign, or hard-negative campaign. We therefore treat invariant triggers as intermediate outcomes and reserve effectiveness claims for a fail-closed evaluation in which exploit evidence must be derived from runtime execution and rejected by paired patched controls.
\end{abstract}
```

Notes:
- `expert system` is intentionally removed until semantic-fidelity evidence is available;
- `LLM-based extraction` becomes `hybrid semantic extraction ... optional LLM enrichment`, matching the repository;
- `rational/economically motivated` is replaced by threat-model-constrained action sequences;
- the 12/12 and 1.66 s values remain, but are explicitly legacy reconstruction metrics.

## 3. Introduction — gap paragraph

Replace the paragraph beginning with “While these tools collectively advance...” with:

```latex
While these approaches substantially advance bridge security, they leave a narrower systems question insufficiently resolved: how can heterogeneous bridge artifacts be translated into explicit cross-domain security properties and execution guidance, while keeping historical-incident knowledge separate from the evidence used to validate an exploit trace? This distinction is important because a target-aware reconstruction can be useful for testing a harness without demonstrating generalization to an unseen vulnerability. We therefore study BridgeSentry first as a reconstruction-and-validation system and treat generalization under incident-, family-, class-, and temporal-disjoint knowledge as an empirical question rather than an assumed capability.
```

This replaces the broader and now vulnerable claim that no existing tool performs proactive cross-chain vulnerability discovery.

## 4. Introduction — system description

Use:

```latex
This paper presents BridgeSentry, a semantic-guided framework organized into three coordinated stages:

\begin{enumerate}
    \item A hybrid semantic extractor that uses Slither IR when available, a conservative parser fallback, and optional LLM enrichment to recover bridge entities, guards, asset/message flows, and an Atomic Transfer Graph (ATG). Candidate invariants are generated from this representation and remain distinct from empirically validated properties.
    \item A retrieval-augmented scenario generator that uses a structured corpus of documented bridge incidents to generate threat-model-constrained action sequences and semantic waypoints. Retrieval provenance is retained so that full-knowledge reconstruction can be separated from incident-, family-, class-, and temporal-holdout regimes.
    \item A dual-EVM execution harness connected through an explicit relay. Generated sequences act as seeds and guidance; exploit evidence is intended to come from observed execution state, traces, logs, storage changes, and relay state rather than from the scenario description itself.
\end{enumerate}
```

The last sentence is intentionally normative until A1 is implemented; do not state that the current legacy result already satisfies this property.

## 5. Introduction — contribution bullets before A3

Use conservative contribution language:

```latex
The present work makes the following contributions:

\begin{itemize}
    \item We adapt the Atomic Transfer Graph abstraction to bridge security testing by representing source, relay, and destination dependencies together with canonical per-transfer/per-message security properties. The representation is used as an intermediate form between artifact analysis and dynamic execution rather than as a secure-by-construction protocol specification.
    \item We integrate semantic modeling, provenance-aware historical retrieval, and a dual-EVM relay harness into a single reconstruction workflow. Full-knowledge retrieval is treated as a diagnostic setting; the paper explicitly separates it from leakage-controlled generalization experiments.
    \item We define a fail-closed notion of exploit evidence that distinguishes an invariant trigger from a bytecode-backed, causally valid, capability-compliant, reproducible trace with material impact and paired patched-version rejection. The legacy evaluation does not yet report this metric.
    \item We characterize the limitations of the current 12-incident reconstruction set, including target leakage, a non-EVM surrogate, a scenario-layer-only case, saturated predicate-trigger metrics, and the absence of completed patched and benign controls. These limitations motivate the official evaluation protocol specified in Section~\ref{sec:experiments}.
\end{itemize}
```

Important: after A3, replace the fourth bullet with actual empirical findings. Do not leave “evaluation protocol” as a headline contribution in the submission version unless the campaign remains incomplete and the paper is intentionally scoped as a methodology paper.

## 6. Problem statement — separate reconstruction from discovery/generalization

Replace the current one-sentence problem statement with:

```latex
\subsection{Problem Statement}

BridgeSentry distinguishes two tasks that should not be conflated.

\textbf{Historical exploit reconstruction.} Given a bridge protocol $\mathcal{B}$, its executable artifacts, an explicit adversary capability model, and a historical-knowledge regime $\mathcal{K}_r$, construct an action sequence $s$ whose observed execution violates a target security property and satisfies the exploit-validity conditions defined below. The reconstruction setting may include historical knowledge related to the target, but the retrieval regime must be reported.

\textbf{Generalization under restricted knowledge.} Under the same execution model, restrict $\mathcal{K}_r$ so that the target incident, bridge family, vulnerability class, or post-cutoff incidents are excluded. The task is to determine empirically whether semantic and retrieval guidance still increases the probability of obtaining valid exploit evidence. Success under full knowledge is not counted as evidence for this task.

For an execution trace $\pi$, we define valid exploit evidence as a conjunction of required gates:
\begin{equation}
\operatorname{Valid}(\pi) = B(\pi) \land C(\pi) \land M(\pi) \land A(\pi) \land R(\pi) \land I(\pi) \land P(\pi),
\end{equation}
where $B$ denotes target-bytecode execution, $C$ a valid cross-chain causal path, $M$ a material committed state change, $A$ compliance with the stated adversary capability model, $R$ reproducibility, $I$ demonstrated security or financial impact, and $P$ rejection of the same trace by a paired patched revision. If a required gate cannot be observed, the trace is unevaluable for Valid Exploit Rate rather than implicitly accepted.
```

## 7. Methodology terminology fixes

### Module 1 heading

Change:

```latex
\subsection{Module 1: LLM-Based Semantic Extraction}
```

to:

```latex
\subsection{Module 1: Hybrid Semantic Extraction and Candidate Invariant Synthesis}
```

### Invariant lifecycle paragraph

Replace wording that says candidate invariants are “validated” after schema/deduplication with:

```latex
We distinguish four invariant states. A \emph{generated} invariant has been emitted by a parser or language model. A \emph{schema-valid} invariant satisfies the structural output contract. A \emph{semantically admissible} invariant is supported by the protocol artifacts required by that property; for example, timeliness is admissible only when the target protocol defines an explicit timeout and refund path. An \emph{empirically validated} invariant has additionally been checked against independently labelled normal and violating traces and relevant paired controls. The current legacy artifact does not provide the ground truth required for the final stage, so we do not interpret generated candidates as validated security specifications.
```

### Module 2 adversary wording

Replace:

```text
rational adversary / economically motivated attack strategies
```

with:

```text
threat-model-constrained adversarial action sequences
```

unless a quantitative utility/profit objective is later introduced.

## 8. Experiments — new research questions

Replace the current RQ list with:

```latex
\begin{itemize}
    \item \textbf{RQ1 --- Semantic fidelity:} How accurately does BridgeSentry recover security-relevant bridge entities, roles, cross-domain ATG edges, and admissible invariants from bridge artifacts?
    \item \textbf{RQ2 --- Guidance generalization:} Does semantic and retrieval-based guidance improve valid exploit reconstruction when target-specific historical knowledge is excluded at the incident, bridge-family, vulnerability-class, and temporal levels?
    \item \textbf{RQ3 --- Exploit validity and precision:} Can BridgeSentry distinguish vulnerable implementations from paired patched revisions, benign systems, and hard negatives under the fail-closed exploit criterion?
    \item \textbf{RQ4 --- Component attribution:} Holding the harness, oracle, target population, capability model, budget, and seeds fixed, what incremental effect do semantic extraction, historical retrieval, LLM enrichment, and (where specifically tested) synchronized snapshots have on valid exploit evidence and false reports?
\end{itemize}
```

## 9. Experiments — metric hierarchy

Use this order in the paper:

1. Valid Exploit Rate (primary once available).
2. Patched-control rejection / precision / specificity.
3. TTVE with right-censored non-triggers.
4. Deduplicated actionable root causes.
5. Normalized execution coverage.
6. Invariant-trigger rate only as an intermediate diagnostic.
7. XCC_ATG only as an internal progress measure.

Do not use legacy ITR as the dependent variable for a robustness or contribution claim.

## 10. Legacy ablation wording

Replace:

```text
The full pipeline's invariants and scenarios are strictly necessary to drive meaningful bytecode execution.
```

with:

```latex
On the saturated legacy reconstruction set, the full configuration is associated with bytecode-executing triggers, whereas the $-SE$ and $-RAG$ variants produce predicate triggers without executing target bytecode. This observation exposes a construct-validity failure in invariant-trigger rate; it does not establish that either component is strictly necessary under holdout conditions.
```

Replace the ablation summary with:

```latex
\textbf{Legacy ablation summary.} The legacy experiment shows that invariant-trigger rate is saturated and can remain 12/12 even for configurations that do not execute target bytecode. The $-Sync$ result shows no measurable synchronization effect on the current reconstruction set. Component attribution is therefore deferred to the fail-closed, controlled evaluation described above.
```

## 11. Remove sensitivity plots from the main narrative

Remove Figures currently showing:
- constant 100% ITR versus retrieval depth $k$;
- saturated ITR versus short time budget.

Move the raw sweeps to supplementary material as legacy diagnostics. Replace the main-text paragraph with:

```latex
Legacy sweeps over retrieval depth, reward weights, and short fuzzing budgets saturate on invariant-trigger rate and therefore provide no useful robustness evidence. We retain these measurements only as diagnostic evidence that the historical positive-only set is too easy for ITR. Parameter sensitivity in the official campaign is evaluated using fail-closed exploit outcomes and censored time-to-valid-exploit under leakage-controlled splits.
```

## 12. Discussion — synchronize runtime/model claims with the artifact

Do not name Gemini/GPT-4o in the limitations section unless the official run manifest pins those exact resolved models. Replace model-specific contamination wording with:

```latex
\textbf{LLM pretraining contamination.} Public bridge incidents, source code, postmortems, and exploit analyses may appear in the pretraining data of the language model used by an experiment. This confound is distinct from explicit RAG leakage: excluding an incident from retrieval does not remove knowledge memorized parametrically. Each official run therefore records the resolved model identifier and date, and generalization results are interpreted together with temporal/model-cutoff controls and parser-only ablations where feasible.
```

## 13. Working conclusion before A3

Use:

```latex
\section{Conclusion}\label{sec:conclusion}

This paper presents BridgeSentry as a semantic-guided architecture for reconstructing and validating EVM-compatible cross-chain exploit traces. Its central design is an explicit source--relay--destination representation that connects artifact analysis, historical guidance, and dual-EVM execution while preserving a distinction between guidance and exploit evidence.

The retained legacy study demonstrates target-aware reconstruction behavior but does not establish valid-exploit rate, false-positive rate, generalization to unseen exploit families, zero-day discovery, or a measurable benefit from synchronized snapshots. In particular, the saturated invariant-trigger metric and zero-bytecode ablation triggers show why predicate satisfaction alone is insufficient evidence of an exploit. The next evidentiary step is therefore a leakage-controlled, fail-closed campaign with execution-derived oracle state, paired vulnerable/patched revisions, benign and hard-negative controls, complete provenance, and right-censored stochastic analysis. Claims in the final manuscript will be restricted to the outcomes supported by that campaign.
```

After A3, rewrite this conclusion around actual findings rather than future protocol.

## 14. Submission side files that must be synchronized

The following existing author files contain obsolete discovery claims and must be updated together with the main manuscript:

- `title_page.tex`: remove “Vulnerability Discovery” title;
- `highlights.tex`: remove “proactively discovers” and “Detects 12/12 vulnerabilities”;
- `references.bib`: complete the October 2026 literature audit before final submission;
- figures/captions: do not label ITR plots as “Discovery Rate”.

Suggested working highlights before the official campaign:

```latex
\begin{itemize}
\item Models cross-chain source, relay, and destination semantics using an ATG-based intermediate representation.
\item Uses provenance-aware historical retrieval to guide exploit reconstruction without treating full-knowledge results as generalization.
\item Separates invariant triggers from fail-closed, execution-backed exploit evidence.
\item Evaluates historical reconstruction scope explicitly, including surrogate and scenario-layer cases.
\item Defines leakage-controlled holdout and paired-control experiments for final effectiveness claims.
\end{itemize}
```

These highlights should be updated again after A3 so the submission contains actual findings rather than an evaluation plan.