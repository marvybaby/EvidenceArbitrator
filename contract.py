# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import json
import typing


@allow_storage
@dataclass
class Dispute:
    claimant: Address
    respondent: Address
    evidence_url_claimant: str
    evidence_url_respondent: str
    escrow: u256
    status: str                # "open" | "resolved"
    resolution: str            # "" | "claimant" | "respondent" | "split"
    split_bucket: u256         # canonical bucket (0,10,20...100), exact agreement required
    released_to_claimant: u256
    released_to_respondent: u256


class EvidenceArbitrator(gl.Contract):
    disputes: TreeMap[str, Dispute]

    def __init__(self):
        self.disputes = TreeMap()

    @gl.public.write
    def open_dispute(self, dispute_id: str, respondent: str, escrow: int) -> None:
        # Overwrite protection: a dispute_id can only be opened once.
        if dispute_id in self.disputes:
            return  # no-op: dispute already exists

        respondent_address = Address(respondent)

        # Prevent self-dealing: a claimant cannot name themselves as the
        # respondent, which would let one party control both sides.
        if respondent_address == gl.message.sender_address:
            return  # no-op: claimant cannot be their own respondent

        # The caller opening the dispute IS the claimant -- there is no
        # separate "claimant" parameter to spoof. Only the party who
        # actually submits this transaction can be the claimant.
        self.disputes[dispute_id] = Dispute(
            claimant=gl.message.sender_address,
            respondent=respondent_address,
            evidence_url_claimant="",
            evidence_url_respondent="",
            escrow=u256(escrow),
            status="open",
            resolution="",
            split_bucket=u256(0),
            released_to_claimant=u256(0),
            released_to_respondent=u256(0),
        )

    @gl.public.write
    def submit_evidence(self, dispute_id: str, evidence_url: str) -> None:
        d = self.disputes[dispute_id]
        sender = gl.message.sender_address

        # Party authorization: only the actual claimant or respondent for
        # THIS dispute can submit evidence -- derived from the transaction
        # sender, never from a caller-supplied "party" string.
        if sender != d.claimant and sender != d.respondent:
            return  # no-op: sender is not a party to this dispute

        # Overwrite protection: evidence can only be submitted once per
        # party, preventing a party from replacing evidence after seeing
        # the other side's submission.
        if sender == d.claimant:
            if d.evidence_url_claimant != "":
                return  # no-op: claimant evidence already submitted
            d.evidence_url_claimant = evidence_url
        elif sender == d.respondent:
            if d.evidence_url_respondent != "":
                return  # no-op: respondent evidence already submitted
            d.evidence_url_respondent = evidence_url

    @gl.public.write
    def resolve_dispute(self, dispute_id: str) -> None:
        d = self.disputes[dispute_id]

        if d.status == "resolved":
            return  # no-op: already resolved

        sender = gl.message.sender_address

        # Authorization: only the claimant or respondent for THIS dispute
        # can trigger resolution -- prevents unrelated third parties from
        # forcing resolution attempts.
        if sender != d.claimant and sender != d.respondent:
            return  # no-op: sender is not a party to this dispute

        # Both parties must have submitted evidence before resolution can
        # be attempted. Without this, an empty evidence_url would be
        # fetched, producing an undefined/garbage verdict.
        if d.evidence_url_claimant == "" or d.evidence_url_respondent == "":
            return  # no-op: waiting on both parties' evidence

        def compute_verdict() -> str:
            evidence_a = gl.nondet.web.render(d.evidence_url_claimant, mode="text")
            evidence_b = gl.nondet.web.render(d.evidence_url_respondent, mode="text")

            prompt = f"""
            Claimant's evidence (fetched from source): {evidence_a}
            Respondent's evidence (fetched from source): {evidence_b}

            Decide how escrow should be released. Respond ONLY with JSON:
            {{"resolution": "<claimant|respondent|split>", "split_percentage": <0-100>}}

            "split_percentage" is the percentage released to the claimant when
            resolution is "split"; use 0 for a clean claimant/respondent decision.
            """
            result = gl.nondet.exec_prompt(prompt, response_format="json")

            # Canonical bucketing: round to the nearest multiple of 10
            # *inside* the non-deterministic block, before consensus is
            # even checked. This collapses small model-to-model variance
            # (e.g. 74 vs 76) into the same bucket (75 -> 80, 74 -> 70)
            # so exact agreement becomes achievable rather than requiring
            # every validator's LLM to output the identical raw number.
            raw_pct = int(result.get("split_percentage", 0))
            bucketed_pct = round(raw_pct / 10) * 10
            bucketed_pct = max(0, min(100, bucketed_pct))

            normalized = {
                "resolution": result["resolution"],
                "split_percentage": bucketed_pct,
            }
            return json.dumps(normalized, sort_keys=True)

        # Exact agreement required -- no tolerance window. Since the
        # percentage directly determines both parties' payout, a "close
        # enough" comparison would let two different payout outcomes both
        # reach consensus. Bucketing above makes exact agreement realistic;
        # this principle enforces it strictly on the canonical value.
        raw_verdict = gl.eq_principle.prompt_comparative(
            compute_verdict,
            principle="""
            resolution must match exactly. split_percentage must match
            exactly -- these are already canonical bucketed values (multiples
            of 10), so no tolerance is permitted. Any difference in either
            field means the verdicts are NOT equivalent.
            """,
        )

        parsed = json.loads(raw_verdict)
        resolution = parsed["resolution"]
        split_bucket = u256(int(parsed["split_percentage"]))

        # Validate the consensus result itself before touching any state.
        # An agreed-but-invalid resolution (anything other than exactly
        # these three values) must not be able to slip through and still
        # mark the dispute resolved with no real allocation.
        if resolution not in ("claimant", "respondent", "split"):
            raise Exception(
                f"Invalid resolution from consensus: {resolution!r}. "
                "Expected 'claimant', 'respondent', or 'split'."
            )

        if resolution == "claimant":
            d.released_to_claimant = d.escrow
            d.released_to_respondent = u256(0)
        elif resolution == "respondent":
            d.released_to_claimant = u256(0)
            d.released_to_respondent = d.escrow
        elif resolution == "split":
            claimant_share = (d.escrow * split_bucket) // u256(100)
            d.released_to_claimant = claimant_share
            d.released_to_respondent = d.escrow - claimant_share

        # Defensive completeness check: the allocation must fully account
        # for the escrow. If it doesn't (e.g. an unexpected split_bucket
        # value, or an integer division edge case), reject the resolution
        # rather than silently marking the dispute resolved with an
        # incomplete or mismatched payout.
        if d.released_to_claimant + d.released_to_respondent != d.escrow:
            raise Exception(
                "Allocation does not sum to escrow; rejecting resolution "
                f"(claimant={d.released_to_claimant}, "
                f"respondent={d.released_to_respondent}, escrow={d.escrow})."
            )

        d.resolution = resolution
        d.split_bucket = split_bucket
        d.status = "resolved"

    @gl.public.view
    def get_dispute(self, dispute_id: str) -> TreeMap[str, typing.Any]:
        return self.disputes.get(
            dispute_id,
            Dispute(
                claimant=Address("0x0000000000000000000000000000000000000000"),
                respondent=Address("0x0000000000000000000000000000000000000000"),
                evidence_url_claimant="",
                evidence_url_respondent="",
                escrow=u256(0),
                status="not_found",
                resolution="",
                split_bucket=u256(0),
                released_to_claimant=u256(0),
                released_to_respondent=u256(0),
            ),
        )
