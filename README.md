# EvidenceArbitrator ; GenLayer Intelligent Contract

## Why consensus, not just "AI decides X"

A single LLM call can't be trusted on-chain: it's non-deterministic, and a single model can be manipulated by adversarial input — for example, evidence text that contains a hidden prompt injection attempting to force a favorable verdict. GenLayer's Optimistic Democracy consensus solves both problems. A leader validator proposes a verdict; the remaining validators — each potentially running a different, undisclosed model — independently check that verdict against explicit criteria rather than trying to reproduce it exactly. Consensus forms around whether the verdict is *justified*, not whether it's word-for-word identical, which is the only way to reach agreement on open-ended reasoning. Because validators run different underlying models, evidence crafted to fool one model is far less likely to fool the group — this is what makes the arbitration trustworthy rather than a single opaque AI call.

## Purpose

Agreements between two parties often break down over a subjective question: did the obligated party actually deliver what was promised? Traditional smart contracts can only check deterministic conditions (a signature, a timestamp, a balance) — they can't weigh conflicting evidence. `EvidenceArbitrator` is a standalone primitive that lets two parties submit evidence for a disputed claim and have that evidence judged by decentralized AI consensus, producing a verdict that can gate fund release, reputation updates, or any downstream deterministic logic.

It's designed to be reusable across any agreement type where fulfillment is ambiguous — invoice financing, freelance escrow, marketplace delivery disputes, service-level agreements — rather than tied to one product.

## State design

- `disputes: dict[str, dict]` — keyed by `dispute_id`, holding `claimant`, `respondent`, `evidence_claimant`, `evidence_respondent`, `escrow`, `status`, `verdict`.
- Status moves through `open → resolved`, deliberately kept minimal so the contract stays a primitive rather than a full workflow engine.

## How consensus is used

`resolve_dispute` calls `gl.eq_principle.prompt_non_comparative`, which is the non-comparative Equivalence Principle: the leader validator generates a candidate verdict, and every other validator independently evaluates whether that verdict satisfies the stated criteria — without needing to generate an identical string themselves. This is the mechanism GenLayer provides specifically for reaching consensus on open-ended, non-deterministic LLM output.

`resolve_dispute` only produces a `verdict` string — releasing escrow based on that verdict is a separate, fully deterministic step, kept apart intentionally so the non-deterministic (LLM) portion of the contract stays as small and auditable as possible.

## Beyond a one-off demo

Because the contract takes arbitrary evidence and arbitrary parties, any two-party agreement app can call `open_dispute` / `submit_evidence` / `resolve_dispute` as a drop-in resolution layer instead of building bespoke dispute logic — this is the intended reusability.

See `contract.py` for the source and `example_usage.py` for a walked-through scenario plus edge cases worth testing.
