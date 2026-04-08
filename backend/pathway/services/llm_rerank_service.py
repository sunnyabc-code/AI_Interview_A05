from typing import List

from pathway.contracts import CandidateResource, ProfileSnapshot
from pathway.settings import llm_ready


class LlmRerankService:
    """LLM rerank/justification layer.

    Current version keeps deterministic fallback to avoid runtime impact.
    """

    def rerank(self, snapshot: ProfileSnapshot, candidates: List[CandidateResource]) -> List[CandidateResource]:
        if not llm_ready():
            return sorted(candidates, key=lambda x: x.base_score, reverse=True)

        # TODO: integrate real LLM API call with strict JSON schema response.
        return sorted(candidates, key=lambda x: x.base_score, reverse=True)
