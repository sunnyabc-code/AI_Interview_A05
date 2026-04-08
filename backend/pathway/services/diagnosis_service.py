from typing import Iterable, List, Optional

from interviews.models import InterviewRoundAnalysis
from recommendations.models import VoiceLlmResult
from pathway.contracts import ProfileSnapshot, WeaknessItem


class DiagnosisService:
    """Build user profile snapshot from existing interview/evaluation data.

    This is a scaffold only; it should be wired to your current models later.
    """

    @staticmethod
    def _safe_avg(values: Iterable[Optional[float]]) -> Optional[float]:
        nums = [float(v) for v in values if isinstance(v, (int, float))]
        if not nums:
            return None
        return round(sum(nums) / len(nums), 2)

    @staticmethod
    def _detect_upper_bound(values: List[float]) -> float:
        if not values:
            return 100.0
        max_val = max(values)
        if max_val <= 5.5:
            return 5.0
        if max_val <= 10.5:
            return 10.0
        return 100.0

    @staticmethod
    def _split_text_blob(text: str) -> List[str]:
        if not text:
            return []
        chunks = []
        for raw in text.replace("[", "").replace("]", "").split("\n"):
            part = raw.strip().strip('"').strip("'")
            if part and len(part) > 1:
                chunks.append(part)
        return chunks

    @staticmethod
    def _trend_delta(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        tail = values[-3:]
        return round(tail[-1] - tail[0], 2)

    def build_snapshot(self, user_id: int) -> ProfileSnapshot:
        round_analyses = list(
            InterviewRoundAnalysis.objects.filter(round__interview__user_id=user_id)
            .select_related("round__interview")
            .order_by("created_at", "id")
        )
        voice_results = list(
            VoiceLlmResult.objects.filter(interview__user_id=user_id, status="success")
            .select_related("interview")
            .order_by("generated_at", "created_at", "id")
        )

        technical_values = [a.technical_score for a in round_analyses]
        communication_values = [a.communication_score for a in round_analyses]
        logic_values = [a.logic_score for a in round_analyses]
        adaptability_values = [a.adaptability_score for a in round_analyses]
        expression_values = [float(v.overall_audio_score) for v in voice_results]

        technical_score = self._safe_avg(technical_values)
        communication_score = self._safe_avg(communication_values)
        logic_score = self._safe_avg(logic_values)
        adaptability_score = self._safe_avg(adaptability_values)
        expression_score = self._safe_avg(expression_values)

        all_numeric_values = [
            float(v)
            for v in [
                technical_score,
                communication_score,
                logic_score,
                adaptability_score,
                expression_score,
            ]
            if isinstance(v, (int, float))
        ]
        upper = self._detect_upper_bound(all_numeric_values)

        weakness_map = {
            "technical": technical_score,
            "communication": communication_score,
            "logic": logic_score,
            "adaptability": adaptability_score,
            "expression": expression_score,
        }

        trend_map = {
            "technical": self._trend_delta([float(v) for v in technical_values if isinstance(v, (int, float))]),
            "communication": self._trend_delta([float(v) for v in communication_values if isinstance(v, (int, float))]),
            "logic": self._trend_delta([float(v) for v in logic_values if isinstance(v, (int, float))]),
            "adaptability": self._trend_delta([float(v) for v in adaptability_values if isinstance(v, (int, float))]),
            "expression": self._trend_delta([float(v) for v in expression_values if isinstance(v, (int, float))]),
        }

        weaknesses: List[WeaknessItem] = []
        for key, score in weakness_map.items():
            if score is None:
                continue
            severity = round(max(0.0, min(100.0, (upper - float(score)) / upper * 100.0)), 2)
            if severity < 20:
                continue
            weaknesses.append(
                WeaknessItem(
                    key=key,
                    weakness_type=key,  # type: ignore[arg-type]
                    severity=severity,
                    trend=trend_map.get(key, 0.0),
                    evidence=[f"avg={score}", f"trend={trend_map.get(key, 0.0)}"],
                )
            )

        weaknesses.sort(key=lambda x: x.severity, reverse=True)

        strengths: List[str] = []
        for item in round_analyses[-12:]:
            if isinstance(item.highlights, list):
                strengths.extend([str(h).strip() for h in item.highlights if str(h).strip()])
        for item in voice_results[-5:]:
            strengths.extend(self._split_text_blob(item.strengths))

        seen = set()
        dedup_strengths = []
        for text in strengths:
            if text in seen:
                continue
            seen.add(text)
            dedup_strengths.append(text)

        sample_count = len(round_analyses) + len(voice_results)
        confidence_level = round(min(100.0, sample_count * 8.0), 2)

        return ProfileSnapshot(
            user_id=user_id,
            technical_score=technical_score,
            expression_score=expression_score,
            dimensions={
                "technical": technical_score,
                "communication": communication_score,
                "logic": logic_score,
                "adaptability": adaptability_score,
                "expression": expression_score,
                "score_upper_bound": upper,
            },
            weaknesses=weaknesses[:8],
            strengths=dedup_strengths[:10],
            confidence_level=confidence_level,
        )
