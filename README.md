# EvidenceArbitrator ;  GenLayer Intelligent Contract

## Why consensus, not just "AI decides X"

A single LLM call can't be trusted on-chain: it's non-deterministic, and a single model can be manipulated by adversarial input. GenLayer's Optimistic Democracy consensus solves this — but the *kind* of equivalence principle used matters. An earlier version of this contract used the non-comparative principle, where a leader proposes a verdict and validators only check it against loose criteria (e.g. "cites real evidence"). That's too weak for arbitration: two directly conflicting verdicts (favor claimant vs. favor respondent) could each satisfy those criteria independently, since both could plausibly "cite the evidence."

This version uses the **comparative** equivalence principle instead. Every validator — leader included — independently fetches the evidence and re-derives its own verdict from scratch. Consensus only forms if their independently computed answer is materially equivalent to the leader's, under an explicit equivalence principle that treats a claimant/respondent disagreement, or a large split-percentage mismatch, as non-equivalent. This is what actually binds the outcome rather than just checking that an answer looks reasonable in isolation.

## Purpose

Agreements between two parties often break down over a subjective question: did the obligated party actually deliver what was promised? Traditional smart contracts can only check deterministic conditions — they can't weigh conflicting evidence. `EvidenceArbitrator` is a standalone primitive that lets two parties point to verifiable evidence for a disputed claim and have it independently assessed and settled by decentralized AI consensus.

It's designed to be reusable across any agreement type where fulfillment is ambiguous — invoice financing, freelance escrow, marketplace delivery disputes, service-level agreements — rather than tied to one product.

## Evidence is verified, not asserted

Each party submits a URL, not free-typed prose. `resolve_dispute` has every validator independently call `gl.nondet.web.render()` on both URLs and read the actual content themselves — the contract never takes a party's self-written claim as fact. This matters because a purely text-based "evidence" field is trivial to fabricate; a URL pointing to a real delivery confirmation page, tracking API, or hosted document gives validators something they can independently verify.

## Structured, enforced settlement

The verdict is no longer a free-form string. `resolve_dispute` parses a structured JSON response into typed state: `resolution` ("claimant" / "respondent" / "split"), `split_percentage`, and computed, enforced amounts — `released_to_claimant` and `released_to_respondent` — derived deterministically from the dispute's escrow. This is a real settlement outcome recorded in contract state, not just a prose explanation a downstream system would have to re-parse.

## State design

- `disputes: TreeMap[str, Dispute]` — keyed by `dispute_id`.
- `Dispute` fields: `claimant`, `respondent`, `evidence_url_claimant`, `evidence_url_respondent`, `escrow`, `status` (`open`/`resolved`), `resolution`, `split_percentage`, `released_to_claimant`, `released_to_respondent`.

## Beyond a one-off demo

Because the contract only assumes two parties, verifiable evidence URLs, and an escrow amount, it can serve as a drop-in resolution layer for invoice financing, freelance marketplaces, escrow services, or SLA enforcement — any application where fulfillment is a judgment call rather than a deterministic check.

See `contract.py` for the source and `example_usage.py` for a walked-through scenario plus edge cases worth testing.