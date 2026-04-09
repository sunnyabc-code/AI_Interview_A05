from typing import Dict, List

from interviews.models import InterviewRoundAnalysis
from recommendations.models import UserKnowledgeMatrics, VoiceLlmResult


class RecallService:
    """Collect real weak-signal context for LLM path generation."""

    @staticmethod
    def _extract_topic_label(analysis: InterviewRoundAnalysis, fallback: str) -> str:
        round_obj = analysis.round
        if round_obj.chain_topic_label:
            return round_obj.chain_topic_label.strip()
        if round_obj.question_content:
            return round_obj.question_content.strip()[:32]
        if round_obj.question and round_obj.question.title:
            return round_obj.question.title.strip()[:32]
        return fallback

    def _lowest_knowledge_points(self, user_id: int, top_k: int = 5) -> List[Dict]:
        records = list(
            UserKnowledgeMatrics.objects.filter(interview__user_id=user_id)
            .select_related("job_knowledge")
            .order_by("-id")
        )
        agg = {}
        for row in records:
            if not row.job_knowledge:
                continue
            key = row.job_knowledge_id
            item = agg.setdefault(
                key,
                {
                    "knowledge_id": key,
                    "knowledge_name": row.job_knowledge.name,
                    "logic_sum": 0.0,
                    "accuracy_sum": 0.0,
                    "count": 0,
                },
            )
            item["logic_sum"] += float(row.logic)
            item["accuracy_sum"] += float(row.accuracy)
            item["count"] += 1

        result = []
        for x in agg.values():
            if x["count"] <= 0:
                continue
            avg_logic = round(x["logic_sum"] / x["count"], 2)
            avg_accuracy = round(x["accuracy_sum"] / x["count"], 2)
            result.append(
                {
                    "knowledge_id": x["knowledge_id"],
                    "knowledge_name": x["knowledge_name"],
                    "avg_logic": avg_logic,
                    "avg_accuracy": avg_accuracy,
                    "avg_total": round((avg_logic + avg_accuracy) / 2, 2),
                    "attempt_count": x["count"],
                }
            )

        result.sort(key=lambda t: (t["avg_total"], t["knowledge_name"]))
        return result[:top_k]

    def _lowest_category_directions(self, user_id: int, category_code: str, top_k: int = 2) -> List[Dict]:
        analyses = list(
            InterviewRoundAnalysis.objects.filter(
                round__interview__user_id=user_id,
                round__category__code=category_code,
            )
            .select_related("round", "round__question", "round__category")
            .order_by("created_at", "id")
        )
        agg = {}
        for a in analyses:
            label = self._extract_topic_label(a, f"{category_code}方向")
            item = agg.setdefault(label, {"sum": 0.0, "count": 0})
            item["sum"] += float(a.overall_score)
            item["count"] += 1

        result = []
        for label, item in agg.items():
            if item["count"] <= 0:
                continue
            result.append(
                {
                    "direction": label,
                    "avg_score": round(item["sum"] / item["count"], 2),
                    "sample_count": item["count"],
                }
            )
        result.sort(key=lambda x: (x["avg_score"], x["direction"]))
        return result[:top_k]

    def _lowest_expression_dimensions(self, user_id: int, top_k: int = 2) -> Dict:
        records = list(
            VoiceLlmResult.objects.filter(interview__user_id=user_id, status="success")
            .order_by("-generated_at", "-created_at", "-id")[:10]
        )
        if not records:
            return {"weak_dimensions": [], "latest_improvements": ""}

        field_map = [
            ("speech_rate_and_rhythm_score", "语速与节奏"),
            ("fluency_score", "表达流畅度"),
            ("confidence_and_voice_energy_score", "自信与声音能量"),
            ("emotional_stability_and_tone_score", "情绪稳定与语调"),
        ]
        dims = []
        for field_name, label in field_map:
            values = [float(getattr(row, field_name)) for row in records if getattr(row, field_name, None) is not None]
            if not values:
                continue
            dims.append({"dimension": label, "avg_score": round(sum(values) / len(values), 2)})
        dims.sort(key=lambda x: (x["avg_score"], x["dimension"]))

        latest = records[0]
        improvements = str(latest.improvements or "").strip().replace("\n", " ")
        return {
            "weak_dimensions": dims[:top_k],
            "latest_improvements": improvements[:300],
        }

    def build_generation_context(self, user_id: int) -> Dict:
        return {
            "technical": {
                "lowest_knowledge_points": self._lowest_knowledge_points(user_id=user_id, top_k=5),
            },
            "scenario": {
                "lowest_directions": self._lowest_category_directions(user_id=user_id, category_code="scenario", top_k=2),
            },
            "project": {
                "lowest_directions": self._lowest_category_directions(user_id=user_id, category_code="project", top_k=2),
            },
            "expression": self._lowest_expression_dimensions(user_id=user_id, top_k=2),
        }
