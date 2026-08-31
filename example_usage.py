"""
Example usage of EvidenceArbitrator.

Scenario: A supplier claims they delivered goods on time; a buyer disputes
this and withholds payment. $500 is held in escrow pending resolution.

Evidence is now a URL each party controls/points to (e.g. a tracking page,
a hosted delivery confirmation, a warehouse log page) rather than free text
the party simply asserts. Validators independently fetch and read these
pages themselves via gl.nondet.web.render() before forming a verdict.
"""

from contract import EvidenceArbitrator

contract = EvidenceArbitrator()

# 1. Buyer opens the dispute, escrowing the disputed amount
contract.open_dispute(
    dispute_id="inv-2201",
    claimant="supplier_0x1a2b",
    respondent="buyer_0x9f8e",
    escrow=500
)

# 2. Supplier submits their evidence as a verifiable URL
contract.submit_evidence(
    dispute_id="inv-2201",
    party="supplier_0x1a2b",
    evidence_url="https://carrier.example.com/track/DC-4471"
)

# 3. Buyer submits their evidence as a verifiable URL
contract.submit_evidence(
    dispute_id="inv-2201",
    party="buyer_0x9f8e",
    evidence_url="https://warehouse.example.com/logs/WL-991"
)

# 4. Resolution is triggered
contract.resolve_dispute("inv-2201")

# Every validator independently fetches both URLs, reads the actual page
# content, and derives its own {"resolution": ..., "split_percentage": ...}
# verdict from scratch. Consensus (via the comparative equivalence
# principle) only forms if independently-derived verdicts agree with the
# leader's within the stated equivalence principle -- a claimant/respondent
# disagreement, or a >5-point split mismatch, fails consensus outright.

print(contract.disputes["inv-2201"].resolution)               # e.g. "split"
print(contract.disputes["inv-2201"].split_percentage)          # e.g. 76
print(contract.disputes["inv-2201"].released_to_claimant)      # parsed, enforced amount
print(contract.disputes["inv-2201"].released_to_respondent)    # parsed, enforced amount
print(contract.disputes["inv-2201"].status)                    # "resolved"


"""
Edge cases worth testing
-------------------------------------------------------------------------
Case                                          | Expected behavior
-------------------------------------------------------------------------
Only one party submits evidence               | The empty evidence_url
                                               | fetches nothing meaningful;
                                               | validators should converge
                                               | on favoring the party with
                                               | real, fetchable evidence.

Evidence URL is unreachable or returns an     | gl.nondet.web.render should
error                                         | surface this consistently to
                                               | every validator, so they
                                               | still converge (e.g. treat
                                               | as missing evidence) rather
                                               | than diverging on how to
                                               | handle the failure.

Two validators legitimately disagree on       | Consensus fails outright
resolution (claimant vs respondent)           | under the comparative
                                               | principle -- this is the
                                               | fix for the original
                                               | rejection, where both
                                               | outcomes could previously
                                               | pass independently.

resolve_dispute called twice                  | Second call is a no-op,
                                               | since status is already
                                               | "resolved".
-------------------------------------------------------------------------
"""