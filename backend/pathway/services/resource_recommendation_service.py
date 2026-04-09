import random
from typing import Dict, List, Sequence, Tuple

from django.db import DatabaseError

from pathway.models import PathwayExternalResource


class ResourceRecommendationService:
    TECH_KEYWORDS = [
        "redis",
        "mysql",
        "索引",
        "缓存",
        "jvm",
        "虚拟机",
        "spring",
        "springboot",
        "tcp/ip",
        "tcp",
        "http",
        "网络",
        "协议",
        "高可用",
        "一致性",
        "分布式",
    ]
    SCENARIO_KEYWORDS = ["场景", "system design", "系统设计", "trade-off", "架构"]
    PROJECT_KEYWORDS = ["项目", "复盘", "经验", "指标", "落地", "业务"]
    EXPRESSION_KEYWORDS = ["表达", "语速", "流畅", "语调", "停顿", "沟通", "star", "behavior"]

    def _normalize(self, text: str) -> str:
        return (text or "").strip().lower()

    def _contains_any(self, text: str, words: Sequence[str]) -> bool:
        return any(w for w in words if w and w in text)

    def _infer_focus_area(self, task_type: str, title: str, reason: str) -> str:
        text = f"{title} {reason}".lower()
        title_text = self._normalize(title)
        task_kind = self._normalize(task_type)

        # Prefix rules have highest priority to avoid noisy LLM phrasing misclassification.
        if title_text.startswith("技术"):
            return "technical"
        if title_text.startswith("表达") or task_kind == "practice":
            return "expression"
        if title_text.startswith("场景"):
            return "scenario"
        if title_text.startswith("项目"):
            return "project"

        # question tasks default to technical unless scenario/project signals are very explicit.
        if task_kind == "question":
            if self._contains_any(text, ["场景题", "scenario", "系统设计"]):
                return "scenario"
            if self._contains_any(text, ["项目题", "project"]):
                return "project"
            return "technical"

        if self._contains_any(text, self.EXPRESSION_KEYWORDS):
            return "expression"
        if self._contains_any(text, self.SCENARIO_KEYWORDS):
            return "scenario"
        if self._contains_any(text, self.PROJECT_KEYWORDS):
            return "project"
        return "technical"

    def _score_resource(
        self,
        resource: Dict,
        text: str,
        task_title_text: str,
        focus: str,
        matched_keywords: List[str],
    ) -> int:
        score = 0
        resource_focus = str(resource.get("focus_area") or "")
        if resource_focus == focus:
            score += 5
        elif resource_focus == "general":
            score += 1

        topic = self._normalize(str(resource.get("topic") or ""))
        if topic:
            if topic in task_title_text:
                score += 12
                matched_keywords.append(topic)
            elif topic in text:
                score += 10
                matched_keywords.append(topic)
            for kw in self.TECH_KEYWORDS + self.SCENARIO_KEYWORDS + self.PROJECT_KEYWORDS + self.EXPRESSION_KEYWORDS:
                if kw in topic and kw in task_title_text:
                    score += 6
                    matched_keywords.append(kw)
                elif kw in topic and kw in text:
                    score += 4
                    matched_keywords.append(kw)

        tags = resource.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                tag_text = self._normalize(str(tag))
                if tag_text and tag_text in text:
                    score += 6
                    matched_keywords.append(tag_text)

        resource_title_text = self._normalize(str(resource.get("title") or ""))
        if resource_title_text:
            for kw in self.TECH_KEYWORDS + self.SCENARIO_KEYWORDS + self.PROJECT_KEYWORDS + self.EXPRESSION_KEYWORDS:
                if kw in resource_title_text and kw in task_title_text:
                    # The resource title shares the same keyword as the task title.
                    score += 5
                    matched_keywords.append(kw)
                elif kw in resource_title_text and kw in text:
                    score += 3
                    matched_keywords.append(kw)

        return score

    def _pick_count(self, candidate_size: int) -> int:
        if candidate_size <= 1:
            return candidate_size
        if candidate_size == 2:
            return random.randint(1, 2)
        return random.randint(1, 3)

    def _select_random_no_repeat(
        self,
        ranked: List[Tuple[Dict, int, List[str]]],
        used_ids: set,
    ) -> List[Dict]:
        if not ranked:
            return []

        high_relevance = [item for item in ranked if item[1] >= 7]
        fallback_ranked = high_relevance or ranked

        max_pick = min(3, len(fallback_ranked))
        pick_count = self._pick_count(max_pick)

        not_used = [item for item in fallback_ranked if int(item[0]["id"]) not in used_ids]
        # Soft de-duplication: keep very strong matches even if used before.
        strong_used = [item for item in fallback_ranked if int(item[0]["id"]) in used_ids and item[1] >= 12]
        pool = (not_used + strong_used) or fallback_ranked

        strong_match = [item for item in pool if item[1] >= 10]
        selected: List[Dict] = []

        if strong_match:
            anchor = random.choice(strong_match[: min(4, len(strong_match))])[0]
            selected.append(anchor)

        remaining_pool = [item[0] for item in pool if item[0]["id"] not in {x["id"] for x in selected}]
        random.shuffle(remaining_pool)
        remain_need = max(0, pick_count - len(selected))
        selected.extend(remaining_pool[:remain_need])

        if len(selected) < pick_count:
            fallback_pool = [item[0] for item in fallback_ranked if item[0]["id"] not in {x["id"] for x in selected}]
            random.shuffle(fallback_pool)
            selected.extend(fallback_pool[: pick_count - len(selected)])

        return selected[:pick_count]

    def recommend_for_tasks(self, tasks: List[Dict], per_task: int = 3) -> Dict[str, List[Dict]]:
        try:
            resources = list(
                PathwayExternalResource.objects.filter(is_active=True)
                .order_by("priority", "id")
                .values("id", "title", "url", "focus_area", "resource_type", "topic", "tags", "priority")
            )
        except DatabaseError:
            return {}
        grouped: Dict[str, List[Dict]] = {}
        for item in resources:
            grouped.setdefault(item["focus_area"], []).append(item)

        result: Dict[str, List[Dict]] = {}
        used_ids = set()
        for task in tasks:
            key = str(task.get("id") or "")
            if not key:
                continue

            task_text = self._normalize(f"{task.get('title') or ''} {task.get('reason') or ''}")
            task_title_text = self._normalize(str(task.get("title") or ""))
            focus = self._infer_focus_area(
                str(task.get("taskType") or ""),
                str(task.get("title") or ""),
                str(task.get("reason") or ""),
            )

            candidates = (grouped.get(focus) or []) + (grouped.get("general") or [])
            if focus == "scenario":
                candidates += grouped.get("project") or []
            if focus == "project":
                candidates += grouped.get("scenario") or []

            ranked = [
                (
                    item,
                    self._score_resource(item, task_text, task_title_text, focus, matched_keywords := []),
                    sorted(set(matched_keywords)),
                )
                for item in candidates
            ]

            if focus == "technical":
                explicit_title_kws = [kw for kw in self.TECH_KEYWORDS if kw in task_title_text]
                if explicit_title_kws:
                    strict_ranked = [
                        row
                        for row in ranked
                        if any(kw in row[2] for kw in explicit_title_kws)
                    ]
                    if strict_ranked:
                        ranked = strict_ranked

            ranked = [x for x in ranked if x[1] > 0] or ranked
            ranked.sort(key=lambda x: (-x[1], int(x[0].get("priority") or 99), int(x[0].get("id") or 0)))

            selected_rows = self._select_random_no_repeat(ranked, used_ids)
            if per_task > 0:
                selected_rows = selected_rows[:per_task]

            for row in selected_rows:
                used_ids.add(int(row["id"]))

            result[key] = [
                {
                    "id": x["id"],
                    "title": x["title"],
                    "url": x["url"],
                    "resourceType": x["resource_type"],
                    "focusArea": x["focus_area"],
                    "topic": x["topic"],
                    "matchReason": f"focus={focus}",
                }
                for x in selected_rows
            ]

            ranked_reason = {int(item[0]["id"]): item[2] for item in ranked}
            for row in result[key]:
                kw = ranked_reason.get(int(row["id"])) or []
                if kw:
                    row["matchReason"] = f"focus={focus}; 命中关键词: {', '.join(kw[:3])}"
        return result
