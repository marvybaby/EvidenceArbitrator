# EvidenceArbitrator ; GenLayer Intelligent Contract

## Why consensus, not just "AI decides X"

A single LLM call can't be trusted on-chain: it's non-deterministic, and a single model can be manipulated by adversarial input. GenLayer's Optimistic Democracy consensus solves this — but getting the equivalence principle right took two iterations to get correct, and it's worth being explicit about why.

The first version used the non-comparative principle: a leader proposes a verdict, and validators only check it against loose criteria ("cites real evidence"). Two directly conflicting verdicts could both pass, since both could plausibly "cite the evidence."

The second version switched to the comparative principle with a 10-point tolerance on the settlement percentage. This was still wrong: the percentage directly determines both parties' payout, so allowing validators to agree on *close* percentages meant two genuinely different settlement outcomes could both reach consensus.

This version fixes that at the root: `compute_verdict` rounds the settlement percentage to the nearest multiple of 10 **inside** the non-deterministic block, before consensus is even evaluated. Small model-to-model variance (74 vs 76) collapses into the same bucket (both round to a canonical value) instead of being averaged or tolerated. The equivalence principle then requires **exact** agreement on that canonical value — no tolerance window at all. This is what makes the payout genuinely bound to a single, agreed-upon outcome.

## Purpose

Agreements between two parties often break down over a subjective question: did the obligated party actually deliver what was promised? Traditional smart contracts can only check deterministic conditions — they can't weigh conflicting evidence. `EvidenceArbitrator` is a standalone primitive that lets two parties point to verifiable evidence for a disputed claim and have it independently assessed and settled by decentralized AI consensus.

It's designed to be reusable across any agreement type where fulfillment is ambiguous — invoice financing, freelance escrow, marketplace delivery disputes, service-level agreements — rather than tied to one product.

## Party identity is derived, never asserted

Earlier versions accepted `claimant` and `party` as plain string parameters — which meant anyone could call `submit_evidence` claiming to be either side of a dispute they had nothing to do with. This version removes that entirely:

- `open_dispute` no longer takes a `claimant` parameter. The caller who submits the transaction **is** the claimant, taken directly from `gl.message.sender_address`. There is nothing to spoof.
- `submit_evidence` no longer takes a `party` parameter. The contract checks `gl.message.sender_address` against the dispute's stored `claimant` and `respondent` addresses and assigns evidence to the correct side automatically. A sender who isn't a party to the dispute is silently rejected (no-op).
- `resolve_dispute` similarly checks that the caller is the claimant or respondent before proceeding, preventing unrelated third parties from repeatedly triggering resolution attempts.
- A claimant cannot name themselves as the respondent (`open_dispute` rejects this), which would otherwise let one party control both sides of the dispute.

## Overwrite and missing-data protection

- `open_dispute` no-ops if the `dispute_id` already exists — a dispute can only be opened once.
- `submit_evidence` no-ops if that party has already submitted evidence — a party cannot replace their evidence after seeing (or reacting to) the other side's submission.
- `resolve_dispute` no-ops until **both** parties have submitted evidence — resolving with a missing side would fetch an empty URL and produce an undefined verdict.

## Evidence is verified, not asserted

Each party submits a URL, not free-typed prose. `resolve_dispute` has every validator independently call `gl.nondet.web.render()` on both URLs and read the actual content themselves — the contract never takes a party's self-written claim as fact.

## Structured, enforced settlement

The verdict is parsed into typed state: `resolution` ("claimant" / "respondent" / "split"), a canonical `split_bucket` (always a multiple of 10), and computed, enforced amounts — `released_to_claimant` and `released_to_respondent` — derived deterministically from the dispute's escrow.

## State design

- `disputes: TreeMap[str, Dispute]` — keyed by `dispute_id`.
- `Dispute` fields: `claimant: Address`, `respondent: Address`, `evidence_url_claimant`, `evidence_url_respondent`, `escrow`, `status` (`open`/`resolved`), `resolution`, `split_bucket`, `released_to_claimant`, `released_to_respondent`.

## Beyond a one-off demo

Because the contract only assumes two parties (identified by their own transaction senders, never a caller-supplied string), verifiable evidence URLs, and an escrow amount, it can serve as a drop-in resolution layer for invoice financing, freelance marketplaces, escrow services, or SLA enforcement.

See `contract.py` for the source and `example_usage.py` for a walked-through scenario plus edge cases worth testing.