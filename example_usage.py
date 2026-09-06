"""
Example usage of EvidenceArbitrator.

Scenario: A supplier claims they delivered goods on time; a buyer disputes
this and withholds payment. $500 is held in escrow pending resolution.

NOTE ON IDENTITY: open_dispute and submit_evidence no longer take a
claimant/party parameter. The claimant is whoever's transaction actually
calls open_dispute (gl.message.sender_address), and submit_evidence
figures out which side you're on the same way. In this example, assume
each call below is made FROM that party's own wallet -- e.g. the
"supplier calls open_dispute" line is a transaction sent by the
supplier's own address, not a parameter naming the supplier.
"""

from contract import EvidenceArbitrator

contract = EvidenceArbitrator()

# 1. Supplier opens the dispute (sent from the supplier's own address --
#    the contract records them as claimant automatically). They name the
#    buyer as respondent and set the disputed escrow amount.
contract.open_dispute(
    dispute_id="inv-2201",
    respondent="buyer_0x9f8e",
    escrow=500,
)
# Calling open_dispute again with the same dispute_id is a no-op --
# a dispute can only be opened once.

# 2. Supplier submits their evidence (sent from the supplier's address --
#    the contract matches this sender against the stored claimant and
#    files the evidence on the correct side automatically).
contract.submit_evidence(
    dispute_id="inv-2201",
    evidence_url="https://carrier.example.com/track/DC-4471",
)
# A second submit_evidence call from the same sender is a no-op --
# evidence can only be submitted once per party.

# 3. Buyer submits their evidence (sent from the buyer's own address).
contract.submit_evidence(
    dispute_id="inv-2201",
    evidence_url="https://warehouse.example.com/logs/WL-991",
)

# 4. Resolution is triggered by either party (sent from the supplier's or
#    buyer's address -- an unrelated third party calling this is a no-op).
contract.resolve_dispute("inv-2201")

# Every validator independently fetches both URLs and derives its own
# {"resolution": ..., "split_percentage": ...} verdict from scratch. Before
# consensus is even checked, compute_verdict rounds the percentage to the
# nearest multiple of 10 (e.g. 74 -> 70, 76 -> 80), so minor model-to-model
# variance collapses into the same bucket. Consensus then requires EXACT
# agreement on both resolution and the bucketed percentage -- no tolerance.

print(contract.disputes["inv-2201"].resolution)               # e.g. "split"
print(contract.disputes["inv-2201"].split_bucket)              # e.g. 80 (always a multiple of 10)
print(contract.disputes["inv-2201"].released_to_claimant)      # parsed, enforced amount
print(contract.disputes["inv-2201"].released_to_respondent)    # parsed, enforced amount
print(contract.disputes["inv-2201"].status)                    # "resolved"


"""
Edge cases worth testing
-------------------------------------------------------------------------
Case                                          | Expected behavior
-------------------------------------------------------------------------
open_dispute called twice with the same       | Second call is a no-op;
dispute_id                                    | the original dispute is
                                               | untouched.

A party calls submit_evidence a second time   | No-op; their original
                                               | evidence is preserved,
                                               | can't be swapped after
                                               | seeing the other side.

A sender who is neither claimant nor          | submit_evidence and
respondent calls submit_evidence or           | resolve_dispute are both
resolve_dispute                               | no-ops for non-parties.

Claimant names themselves as respondent       | open_dispute rejects this
                                               | (no-op) -- prevents one
                                               | party controlling both
                                               | sides.

resolve_dispute called before both parties    | No-op; waits until both
have submitted evidence                       | evidence_url fields are
                                               | non-empty.

Two validators' LLMs produce 74% and 76%      | Both bucket to 80 and 70
                                               | respectively... wait, both
                                               | should land on nearby
                                               | buckets; if they still
                                               | land on DIFFERENT buckets
                                               | after rounding, consensus
                                               | correctly fails, since the
                                               | payout really would differ.

resolve_dispute called twice                  | Second call is a no-op,
                                               | since status is already
                                               | "resolved".
-------------------------------------------------------------------------
"""