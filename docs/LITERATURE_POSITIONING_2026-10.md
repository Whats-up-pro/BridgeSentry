# BridgeSentry Literature Positioning — October 2026

**Cutoff:** 2026-10-09  
**Purpose:** Re-evaluate BridgeSentry novelty after recent 2026 cross-chain and LLM-guided smart-contract security work.  
**Status:** Working literature audit; bibliographic entries should be merged into the submission bibliography after the latest manuscript source is synchronized.

## 1. Executive ruling

The paper must no longer rely on any of the following as its primary novelty claim:

- cross-chain fuzzing itself;
- combining an LLM with a fuzzer;
- using RAG/knowledge retrieval for smart-contract security;
- representing cross-chain behavior across more than one execution domain.

By October 2026, each of those ingredients has direct prior art. BridgeSentry remains potentially distinguishable through the **combination and evaluation discipline** of:

1. an explicit source–relay–destination semantic intermediate representation based on ATGs;
2. historical incident knowledge treated as potentially contaminating guidance, with incident/family/class/temporal leakage controls;
3. fail-closed separation between guidance/predicate triggers and execution-backed exploit evidence;
4. evaluation across heterogeneous bridge architectures rather than only one bridge family, if the final benchmark actually supports that claim.

The strongest defensible research question is therefore not “can LLM-guided dual-chain fuzzing discover bridge bugs?” but:

> Can an explicit cross-domain semantic representation and leakage-controlled historical guidance improve valid exploit reconstruction under runtime-grounded, paired-control validation?

## 2. Direct cross-chain dynamic-testing prior art

### BridgeFuzz — EuroSec 2026

**Citation:** Pascal Winkler, Christian Scholz, Jens-Rene Giesen, Noah Kappert, Lucas Davi. *Fuzzing Cross-Chain Vulnerabilities with BridgeFuzz.* EuroSec 2026, pp. 81–88. DOI: `10.1145/3803525.3804980`.

**What it establishes:** BridgeFuzz is a dedicated cross-chain fuzzing framework whose stated scope includes both on-chain contracts and off-chain relayers. It therefore invalidates any BridgeSentry claim that dual-/cross-chain fuzzing with relayer awareness is unprecedented.

**Implication for BridgeSentry:**
- treat BridgeFuzz as the primary dynamic baseline on the common EVM-supported subset;
- do not frame the dual-EVM harness alone as the novelty;
- compare supported scope, oracle semantics, guidance source, and exploit-validity criteria rather than presenting a generic win/loss table.

**Primary sources:**
- EuroSec 2026 program: https://eurosec-workshop.github.io/
- DBLP: https://dblp.org/rec/conf/eurosec/WinklerSGKD26

### IntentFuzz — arXiv:2609.13004, September 2026

**Citation:** André Augusto, Christof Ferreira Torres, André Vasconcelos, Miguel Correia. *IntentFuzz: A Protocol-Aware Fuzzer for Automated Invariant Violation Detection in Intent-Based Cross-Chain Bridges.* arXiv:2609.13004, 2026.

**Scope:** intent-based bridges. IntentFuzz statically recovers intent structures and deposit/fill roles from unannotated Solidity, creates multi-step transaction templates, checks bridge-specific invariants, and uses an LLM as a cold-start fallback when deterministic argument construction cannot satisfy protocol-specific inputs.

**Reported evaluation:**
- correct intent-structure recovery on 9/9 benchmark protocols;
- labelled-contract evaluation for structure/function classification;
- 23 planted mutants with paired secure baselines;
- 24 real-world deployments over forked state;
- 17 confirmed invariant violations in the heuristic-only configuration, rising to 22 with LLM-assisted recovery.

**Why this matters more than a generic citation:** IntentFuzz already demonstrates several things the previous BridgeSentry draft treated as open territory: automatic bridge semantic-role recovery, invariant-oriented cross-chain testing, multi-step source/destination action sequences, forked execution, and measured LLM contribution.

**Remaining distinction:** IntentFuzz is intentionally specialized to the intent/deposit/fill model and explicitly distinguishes locally enforceable invariants from settlement exposures. BridgeSentry can remain distinct if it demonstrates a broader source–relay–destination representation across heterogeneous bridge architectures and evaluates historical guidance under leakage controls. That distinction must be demonstrated, not merely stated.

**Primary source:** https://arxiv.org/abs/2609.13004

## 3. LLM-guided fuzzing prior art

### EchoFuzz — ICSE 2026

**Citation:** Juanen Li, Peng Qian, Guanyan Li, Rui Wang, Peixin Wang, Zhiqing Tang, Fuchen Ma, Yuanliang Chen, Lun Zhang. *EchoFuzz: Empowering Smart Contract Fuzzing with Large Language Models.* ICSE 2026 Research Track. DOI: `10.1145/3744916.3773166`; arXiv:2609.14475.

**Method:** combines static analysis and LLM reasoning to construct Vulnerable Function Call Sequences, then uses runtime feedback to redirect fuzzing toward unexplored branches.

**Reported result:** the paper reports approximately 29% branch-coverage improvement, 62% more vulnerabilities than the strongest compared methods, and 37 previously unknown findings.

**Implication for BridgeSentry:** “LLM + fuzzing” is no longer a novelty claim. BridgeSentry must explain why offline bridge-semantic preprocessing and leakage-aware incident retrieval solve a different problem from runtime LLM feedback.

**Primary sources:**
- ICSE program: https://conf.researchr.org/details/icse-2026/icse-2026-research-track/124/EchoFuzz-Empowering-Smart-Contract-Fuzzing-with-Large-Language-Models
- arXiv: https://arxiv.org/abs/2609.14475

## 4. LLM + retrieval prior art

### PropertyGPT — NDSS 2025

Already cited in the manuscript. It is a direct comparison for retrieval-augmented property generation and formal verification. BridgeSentry cannot treat RAG-assisted security-property generation as unique.

### ParaVul — IEEE TIFS 2026

**Citation:** Tenghui Huang, Jinbo Wen, Jiawen Kang, Siyong Chen, Zhengtao Li, Tao Zhang, Dongning Liu, Jiacheng Wang, Chengjun Cai, Yinqiu Liu, et al. *ParaVul: A Parallel Large Language Model and Retrieval-Augmented Framework for Smart Contract Vulnerability Detection.* IEEE Transactions on Information Forensics and Security, vol. 21, pp. 5017–5030, 2026. DOI: `10.1109/TIFS.2026.3694661`.

**Method:** combines an LLM-based detector with hybrid BM25+dense retrieval and gated verification.

**Implication for BridgeSentry:** RAG itself cannot carry novelty. The contribution must lie in what is retrieved, how retrieval provenance/leakage is controlled, how retrieved evidence influences execution, and how that influence is evaluated.

**Primary source:** https://ieeexplore.ieee.org/document/11523597/

## 5. Architecture-focused bridge-security context

### SoK: Cross-Chain Bridging Architectural Design Flaws and Mitigations — final journal version 2026

**Citation:** Jakob Svennevik Notland, Jinguye Li, Mariusz Nowostawski, Peter Halland Haro. *SoK: Cross-chain bridging architectural design flaws and mitigations.* Blockchain: Research and Applications, 7(1), 100315, 2026. DOI: `10.1016/j.bcra.2025.100315`.

**Relevance:** identifies recurring bridge architectural components and relates them to design flaws and mitigations. This supports a more precise BridgeSentry motivation: bridge properties are architecture- and trust-model-dependent, so universal generic invariants are unsafe.

**Primary source:** https://www.sciencedirect.com/science/article/pii/S2096720925000429

## 6. Adjacent preprint: neuro-symbolic formal verification

### COBALT-TLA — arXiv:2604.12172

COBALT-TLA couples an LLM with TLA+/TLC in a feedback loop and evaluates three cross-chain targets, including a Nomad model. It is not a direct fuzzing baseline, and its small/preprint evaluation makes it inappropriate as a primary comparator, but it should be considered when claiming that LLM-assisted cross-chain semantic reasoning or invariant-oriented verification is unexplored.

**Primary source:** https://arxiv.org/abs/2604.12172

## 7. Revised novelty matrix

| Capability | BridgeFuzz | IntentFuzz | EchoFuzz | PropertyGPT / ParaVul | BridgeSentry target position |
|---|---|---|---|---|---|
| Cross-chain dynamic testing | Yes | Yes, intent-specific | No | No | Yes |
| Explicit off-chain/relay concern | Yes | Settlement boundary | No | No | Yes |
| Automatic semantic-role recovery | Limited/not headline | Strong, intent roles | Function-sequence semantics | Property/vulnerability semantics | ATG source–relay–destination semantics |
| LLM-guided fuzzing | No headline LLM role | Fallback for failed input construction | Runtime feedback | Not fuzzing | Preprocessing/guidance |
| Historical retrieval | No headline | No headline | No | Yes for property/verification | Yes, incident corpus |
| Leakage-controlled historical guidance | Not central | Not central | Not central | Not Bridge-specific | **Must be demonstrated** |
| Paired secure/patched controls | Tool-dependent | Strong mutant + secure baseline design | Dataset-specific | Classification datasets | **Must be added** |
| Fail-closed exploit trace validation | Different oracle model | Invariant-specific success/revert oracles | Vulnerability-specific | Detection/verification | **Target differentiator; must be implemented** |
| Heterogeneous bridge-family scope | Bridge deployments | Intent bridges | General smart contracts | General smart contracts | **Potential differentiator; must be evidenced** |

## 8. Concrete manuscript changes required

1. Replace “the convergence of LLMs and fuzzing remains underexplored in the cross-chain context” with a narrower statement that explicitly acknowledges IntentFuzz and EchoFuzz.
2. Replace any “most/all fuzzers are single-chain” absolute statement with a qualified description acknowledging BridgeFuzz and IntentFuzz.
3. Add IntentFuzz to the Related Work comparison table and discuss its secure-baseline/mutant methodology because it raises the empirical bar for BridgeSentry.
4. Add EchoFuzz to the LLM-fuzzing subsection and distinguish offline preprocessing from runtime LLM feedback.
5. Add ParaVul as evidence that hybrid RAG + LLM vulnerability verification is established prior art.
6. Add the 2026 architectural SoK to motivate protocol-specific rather than universal invariant generation.
7. Do not claim superiority over any of these systems until the common-scope experiment is actually run.

## 9. Reviewer-facing interpretation

The arrival of IntentFuzz does **not** make BridgeSentry unpublishable. It removes the easiest novelty story and forces a better one. A strong final BridgeSentry paper should be able to state, with evidence:

- what semantic information its ATG representation captures that intent-specific role recovery does not;
- whether that information improves valid exploit reconstruction under clean holdouts;
- whether historical retrieval helps after direct target leakage is removed;
- whether findings survive execution-derived validation and paired patched controls;
- which bridge architectures are supported, unsupported, or abstained from.

If those questions are answered rigorously, the contribution becomes more scientifically meaningful than a generic “LLM-guided cross-chain fuzzer” claim.