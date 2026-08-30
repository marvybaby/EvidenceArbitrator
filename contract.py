# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import typing


class EvidenceArbitrator(gl.Contract):
    disputes: dict[str, dict]  # dispute_id -> {claimant, respondent, evidence_claimant, evidence_respondent, escrow, status, verdict}

    def __init__(self):
        self.disputes = {}

    @gl.public.write
    def open_dispute(self, dispute_id: str, claimant: str, respondent: str, escrow: int) -> None:
        self.disputes[dispute_id] = {
            "claimant": claimant,
            "respondent": respondent,
            "evidence_claimant": "",
            "evidence_respondent": "",
            "escrow": escrow,
            "status": "open",
            "verdict": "",
        }

    @gl.public.write
    def submit_evidence(self, dispute_id: str, party: str, evidence: str) -> None:
        d = self.disputes[dispute_id]
        if party == d["claimant"]:
            d["evidence_claimant"] = evidence
        elif party == d["respondent"]:
            d["evidence_respondent"] = evidence

    @gl.public.write
    def resolve_dispute(self, dispute_id: str) -> None:
        d = self.disputes[dispute_id]

        if d["status"] == "resolved":
            return  # no-op: already resolved

        def get_verdict() -> str:
            return f"""
            Claimant's evidence: {d['evidence_claimant']}
            Respondent's evidence: {d['evidence_respondent']}
            Determine who fulfilled their obligation and how escrow should be released.
            """

        verdict = gl.eq_principle.prompt_non_comparative(
            get_verdict,
            task="Judge this dispute based only on the submitted evidence and decide fund release: full to claimant, full to respondent, or split.",
            criteria="""
            The verdict must reference specific evidence from both parties.
            The verdict must state a clear resolution: 'claimant', 'respondent', or 'split:<percentage>'.
            The verdict must not fabricate evidence not submitted by either party.
            If one party submitted no evidence, the verdict must explicitly note the missing submission.
            """
        )

        d["verdict"] = verdict
        d["status"] = "resolved"
