# Research direction

The 19 October 2026 audit establishes the field and the first research instrument,
not an original algorithm. The project name is **tick-trap** throughout.

The first question is whether trajectory-specific certification can improve the
safety/performance/computation trade-off in a precisely restricted model class.
Polynomial trajectory minima provide a reference for that investigation.
Computation-aware execution is a possible second direction; learned uncertainty
is a later extension requiring its own validity argument.

## Stages

1. Establish exact low-dimensional dynamics, explicit properties, validated
   trajectory evaluation, published sufficient conditions, and repeatable reports.
   This repository implements that foundation for wall control and planar
   trajectory evaluation, plus a small offline identification experiment.
2. Complete the theorem-assumption comparison below and reproduce selected paper
   experiments. Planar HOCBF synthesis, finite-candidate filters, multiple-obstacle
   rollouts, matched tasks and a matched-control audit are now implemented. Full
   paper experiment reproduction and the complete theorem comparison remain open.
3. Measure where sufficient conditions exclude safe controls, lose recursive
   feasibility, or cost too much. Separate initial-set restrictions from actual
   safety violations. Extend uncertainty/delay models with justified bounds before
   claiming safety under those conditions.
   A restricted stored-continuation reference and exact saved-evidence replay are
   now implemented; see [the continuation validation](validation-continuations.md).
   The [sampling-aware comparison](validation-sampling.md) now includes a stronger
   modern condition and its permitted relaxation. The audit distinguishes
   geometric safety from auxiliary-set preservation and identifies specific
   controls preserving both properties that the Taylor test excludes. A next
   experiment must preserve this same property when comparing precision and cost;
   a geometric-only reference cannot by itself measure every high-order exclusion.
   Two high-order polynomial references now preserve both properties and compare
   minimum refinement with sign stopping on the same ordered candidates. They
   remain one-hold checks with no recursive-feasibility claim.
4. Select a narrower improvement only after a reproducible limitation and a
   targeted novelty search. State and prove the proposed guarantee, compare with
   the strongest applicable methods, then add a substantive safe-learning study.

## Literature ledger

Sources were checked on 19 October 2026. Access depth is recorded to prevent
abstract-level reading from becoming a claim of proof reconstruction.

| Reference | Access and implementation status | Required next comparison |
| --- | --- | --- |
| [Hsu, Hu, Fisac (2024)](https://doi.org/10.1146/annurev-control-071723-102940) | Publisher overview accessed; taxonomy reference | Align filter guarantees, feasible sets, and backup assumptions |
| [Breeden, Garg, Panagou (2021), v1](https://arxiv.org/html/2103.03677v1) | Relevant Theorem 1 statement/proof examined; local Lipschitz condition specialized and tested | Compare their tighter alternatives and full published examples |
| [Taylor et al. (2022), v2](https://arxiv.org/html/2203.11470v2) | Formulation and practical-safety discussion accessed; not implemented | Reconstruct consistency assumptions, set enlargement, and rate dependence |
| [Tan et al., 2411.17079v2 (2025)](https://arxiv.org/html/2411.17079v2) | Eq. (4), Lemma 1 and associated argument examined; local wall specialization implemented | Compare tighter flow/constraint bounds and original experiments |
| [Liu, Xiao, Belta (2025), v1](https://arxiv.org/html/2511.11897v1) | Section IV, Theorem 2 and relaxation argument examined; linear-gain planar condition and zero-target feasibility envelope implemented with exact candidate-specific bounds | Full slack-penalized QP, bound-estimation recipe, temporal constraints and original experiments remain open |
| [Pagnini, Malis (2026)](https://www.sciencedirect.com/science/article/abs/pii/S0947358026001354) | Publisher abstract and accessible sections checked; full proof pending | Segment guarantees versus curved physical trajectories |
| [Ambadkar et al. (ICLR 2026)](https://proceedings.iclr.cc/paper_files/paper/2026/hash/c1233cb30ef11a3fe6ab10aa96beabaf-Abstract-Conference.html) | Proceedings abstract verified; not reproduced | Predictive shielding under model error and delay |
| [Begzadic et al. (ACC 2026)](https://portal.fis.tum.de/en/publications/safe-event-triggered-learning-for-sampled-data-systems/) | Institutional publication record and abstract verified; not reproduced | GP validity conditions, event triggers, inter-sample bounds |
| [Wabersich, Zeilinger, 1812.05506v4 (2021)](https://arxiv.org/html/1812.05506v4) | Nominal construction, model/terminal assumptions and shrinking-plan argument examined in Section 4.1; restricted stored-plan reference implemented | Full MPC problem, uncertain-model theorem and original experiments are not reproduced |

Taylor's practical-safety formulation must not be scored as though it asserted
the same unrelaxed continuous safe-set invariance as every other method. The
implemented endpoint baseline is a simple diagnostic condition, not an
implementation of Taylor's paper. Likewise, the curved counterexample does not
refute a theorem whose guarantee covers only the connecting segment.

Before treating the instrument itself as novel, compare its scope with existing
test synthesis, safety-control benchmarks, validated polynomial optimization,
continuous collision detection, and barrier verification software. The original
audit's references on those topics remain a reading queue; this implementation
does not claim to replace them.

## Gates for a research claim

- A viable initial state, controller domain, and all guarantee assumptions are
  specified. A failure witness includes the actual control and continuous path.
- A comparison uses the same required property and task, not just common labels.
- Numerical and modeling errors are independently bounded where a certificate
  relies on them. Empirical model accuracy is not sufficient.
- Conservatism is measured through admitted safe controls or matched performance,
  alongside recursive feasibility and computation expense.
- A literature search confirms the exact claimed improvement is not already
  covered, and the method is compared with the strongest relevant baselines.

The current Bernstein certifier is a standard mathematical construction used as
research infrastructure. Its budget is a subdivision budget, not a real-time
guarantee. No new theorem, safety algorithm, or publication-level novelty is claimed.
