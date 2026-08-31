# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import json
import typing


@allow_storage
@dataclass
class Dispute:
    claimant: str
    respondent: str
    evidence_url_claimant: str    # verifiable source, not free-typed prose
    evidence_url_respondent: str
    escrow: u256
    status: str                    # "open" | "resolved"
    resolution: str                # "" | "claimant" | "respondent" | "split"
    split_percentage: u256         # meaningful only if resolution == "split"
    released_to_claimant: u256     # parsed, enforced settlement amounts
    released_to_respondent: u256


class EvidenceArbitrator(gl.Contract):
    disputes: TreeMap[str, Dispute]

    def __init__(self):
        self.disputes = TreeMap()

    @gl.public.write
    def open_dispute(
        self, dispute_id: str, claimant: str, respondent: str, escrow: int
    ) -> None:
        self.disputes[dispute_id] = Dispute(
            claimant=claimant,
            respondent=respondent,
            evidence_url_claimant="",
            evidence_url_respondent="",
            escrow=u256(escrow),
            status="open",
            resolution="",
            split_percentage=u256(0),
            released_to_claimant=u256(0),
            released_to_respondent=u256(0),
        )

    @gl.public.write
    def submit_evidence(self, dispute_id: str, party: str, evidence_url: str) -> None:
        # Evidence is a URL validators independently fetch and read themselves
        # (delivery confirmation page, tracking API, hosted document, etc.),
        # not a party-authored claim taken on faith.
        d = self.disputes[dispute_id]
        if party == d.claimant:
            d.evidence_url_claimant = evidence_url
        elif party == d.respondent:
            d.evidence_url_respondent = evidence_url

    @gl.public.write
    def resolve_dispute(self, dispute_id: str) -> None:
        d = self.disputes[dispute_id]

        if d.status == "resolved":
            return  # no-op: already resolved

        def compute_verdict() -> str:
            # Every validator (leader included) independently fetches the
            # underlying evidence and re-derives the verdict — nobody's
            # judgment is taken on the leader's word alone.
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
            return json.dumps(result, sort_keys=True)

        # Comparative principle: validators don't just check the leader's
        # answer against loose criteria — they independently recompute the
        # verdict from the fetched evidence, and consensus only forms if
        # their answer is materially equivalent to the leader's.
        raw_verdict = gl.eq_principle.prompt_comparative(
            compute_verdict,
            principle="""
            The resolution and split_percentage must represent the same
            underlying settlement decision. A "claimant" vs "respondent"
            disagreement is NOT equivalent. A split_percentage that differs
            by more than 5 points is NOT equivalent.
            """,
        )

        parsed = json.loads(raw_verdict)
        resolution = parsed["resolution"]
        split_pct = u256(int(parsed.get("split_percentage", 0)))

        # Structured, enforced settlement — not just a stored prose string.
        if resolution == "claimant":
            d.released_to_claimant = d.escrow
            d.released_to_respondent = u256(0)
        elif resolution == "respondent":
            d.released_to_claimant = u256(0)
            d.released_to_respondent = d.escrow
        elif resolution == "split":
            claimant_share = (d.escrow * split_pct) // u256(100)
            d.released_to_claimant = claimant_share
            d.released_to_respondent = d.escrow - claimant_share

        d.resolution = resolution
        d.split_percentage = split_pct
        d.status = "resolved"