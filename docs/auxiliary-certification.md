# Deriving geometric safety from the auxiliary barrier

For a differentiable exact path, positive `lambda1`, and
`psi(t)=h_dot(t)+lambda1*h(t)`,

```
d/dt [exp(lambda1*t)*h(t)] = exp(lambda1*t)*psi(t).
```

If `h(0)>=0` and a validated certificate proves `psi(t)>=0` throughout `[0,T]`,
integration gives `h(t)>=exp(-lambda1*t)*h(0)>=0` on that interval. Therefore a
second numerical sign query on `h` is unnecessary for this implication. This is
the standard linear high-order barrier comparison argument, not a new method.

`certify_auxiliary_path` constructs the exact auxiliary polynomial and queries
its sign. It records the comparison rule, initial `h`, gain, interval and whether
geometric nonnegativity follows. It supplies **no numerical geometric minimum
enclosure**. The original polynomial's exact coefficients and the auxiliary
certificate remain necessary to replay the inference. Invalid initial clearance
or a nonpositive gain is rejected. A negative or unresolved auxiliary certificate
gives no geometric conclusion; a negative auxiliary value alone does not prove
collision.

For tick-trap's robot, `h=||p-c||²-R²` is the declared geometric constraint,
`p_dot=v`, `v_dot=u`, and each action is held exactly. The argument assumes exact
state/model, a static inflated circle, the stated constant gain, and admissible
commands. It preserves both `h>=0` and `psi>=0` during the certified hold, without
establishing another feasible input or task convergence. Boundary contact is
permitted. Model error, observation error, delayed execution and moving obstacles
are not covered. The independent offline geometric oracle remains useful for
checking model/implementation consistency.

## Finite-work decisions need not match

Removing the geometric query changes available evidence at a limited budget;
it is not guaranteed to preserve every numerical classification of the dual
query, even though the required safety properties are the same.

For `p0=(-0.3,1.06)`, `v0=(1,0)`, `u=(0,0)`, unit circle at the origin, period
`T=1` and `lambda1=3`,

```
h(t)   = 0.2136 - 0.6*t + t²
psi(t) = 0.0408 + 0.2*t + 3*t².
```

At zero subdivisions, `h` has a negative Bernstein coefficient and its direct
sign query is unknown. All auxiliary coefficients are positive, so its sign is
proved immediately and the comparison argument proves geometric safety. The
constant height `1.06>1` independently confirms the geometric fact.

The converse loss of information can also occur. For `p0=(2,0)`, `v0=(-1,0)`,
`u=0`, unit circle, `T=2.9` and gain `2`, a negative endpoint `h` is an immediate
geometric witness. The auxiliary query at zero subdivisions remains unknown.
An auxiliary-only check must therefore return unknown rather than accept that
action. More work can resolve the auxiliary violation. The free-motion path is
a collision witness, not a physical contact simulation.

Both examples are exact rational reference cases. They show why cost comparisons
must retain unknowns and distinguish auxiliary violations from geometric ones,
rather than assuming an optimization preserves every reported answer.

## Cost and controller comparisons

The certification study accepts an explicit `strategies` list: `sacbf_relaxed`,
`minimum`, `sign`, and `auxiliary_sign`. The default retains the original first
three. The last strategy makes one auxiliary sign query per obstacle and derives
geometric safety by the rule above. Every method still targets the same two
properties. All inference records and auxiliary certificates are saved; there
are no fabricated geometric minimum bounds. Timings include exact evidence
construction, with search and the independent offline reference excluded.

`configs/auxiliary-cost.json` retains the eight previous fixed states and adds
both decision-difference examples. Besides accepted/rejected/unknown counts, the
report gives a paired transition table between dual-sign and auxiliary-only
answers. Unlike minimum versus sign stopping on identical polynomials, these
strategies are **not** required to classify every command identically at limited
work. A geometric negative witness can become an unknown, while an unresolved
geometric query can be replaced by a valid implication.

```sh
PYTHONPATH=src python -m tick_trap certification-study --config configs/auxiliary-cost.json --output results/auxiliary-cost
PYTHONPATH=src python -m tick_trap planar-sweep --config configs/auxiliary-baselines.json --output results/auxiliary-baselines
PYTHONPATH=src python -m tick_trap verify --runs results/auxiliary-baselines/runs.json --output results/auxiliary-verification
```

The saved-run verifier independently reconstructs the auxiliary polynomial and
checks its sign proof, work limit, initial geometric value, gain and duration.
It rejects altered implication rules, missing proofs, claimed geometric minimum
bounds or an unresolved auxiliary proof used to authorize a command. A negative
offline geometric witness contradicts a valid comparison proof. An unknown
offline geometric result stays unknown in that oracle's own record; the separate
comparison evidence is counted explicitly. The runner still stops on an
unresolved offline interval, as it does for the existing references. No physical
model validity or hard execution deadline is inferred from this replay.
