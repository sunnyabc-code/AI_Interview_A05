from typing import List

from pathway.contracts import CandidateResource, PathPlan, PathTask, ProfileSnapshot


class PlannerService:
    """Convert ranked candidates into a practical day-by-day plan."""

    DIMENSION_LABELS = {
        "technical": "技术能力",
        "expression": "表达能力",
        "communication": "沟通能力",
        "logic": "逻辑能力",
        "adaptability": "应变能力",
    }

    def build_plan(
        self,
        snapshot: ProfileSnapshot,
        ranked_candidates: List[CandidateResource],
        cycle_days: int = 7,
    ) -> PathPlan:
        tasks: List[PathTask] = []
        if not ranked_candidates:
            raise ValueError("候选任务不足，无法生成计划")

        weakness_order = [w.key for w in snapshot.weaknesses]
        main_focus = weakness_order[0] if weakness_order else "technical"
        second_focus = weakness_order[1] if len(weakness_order) > 1 else "expression"

        needs_expression_focus = "expression" in weakness_order or "communication" in weakness_order

        selected: List[CandidateResource] = []
        used_keys = set()

        def _candidate_key(item: CandidateResource) -> str:
            return f"{item.source_type}:{item.source_id}:{item.title}"

        def _append_if_new(item: CandidateResource):
            key = _candidate_key(item)
            if key in used_keys:
                return
            used_keys.add(key)
            selected.append(item)

        # 1) 强制覆盖最低 5 个知识点任务
        required_kp = []
        for c in ranked_candidates:
            kp_tag = next((t for t in c.tags if t.startswith("kp:")), None)
            if kp_tag:
                required_kp.append(kp_tag)
        required_kp = sorted(set(required_kp))

        if len(required_kp) < 5:
            raise ValueError("知识点评分数据不足 5 项，无法生成可信的七日路径")

        for kp in required_kp[:5]:
            candidate = next((c for c in ranked_candidates if kp in c.tags), None)
            if not candidate:
                raise ValueError("最低分知识点未能匹配到可执行任务，请补充题库后重试")
            _append_if_new(candidate)

        # 2) 表达薄弱时，强制至少安排一项表达任务
        if needs_expression_focus:
            exp = next((c for c in ranked_candidates if "expression_focus" in c.tags), None)
            if not exp:
                raise ValueError("表达薄弱但缺少表达训练素材，无法生成计划")
            _append_if_new(exp)

        # 3) 强制包含场景题与项目题提升建议
        scenario = next((c for c in ranked_candidates if "required_scenario" in c.tags), None)
        if not scenario:
            raise ValueError("题库中缺少可用场景题，无法生成包含场景提升的七日路径")
        _append_if_new(scenario)

        project = next((c for c in ranked_candidates if "required_project" in c.tags), None)
        if not project:
            raise ValueError("题库中缺少可用项目题，无法生成包含项目提升的七日路径")
        _append_if_new(project)

        # 4) 其余天数使用真实候选补齐
        for c in ranked_candidates:
            if len(selected) >= cycle_days:
                break
            _append_if_new(c)

        if len(selected) < cycle_days:
            raise ValueError("候选任务不足 7 条，无法生成完整七日路径")

        for idx, candidate in enumerate(selected[:cycle_days]):

            task_type = "practice"
            if candidate.source_type == "learning_resource":
                task_type = "resource"
            elif candidate.source_type == "question":
                task_type = "question"

            priority = 1 if idx < 3 else 2
            tasks.append(
                PathTask(
                    day_index=idx + 1,
                    task_type=task_type,  # type: ignore[arg-type]
                    title=candidate.title,
                    reason=candidate.reason,
                    estimated_minutes=candidate.estimated_minutes,
                    source_type=candidate.source_type,
                    source_id=candidate.source_id,
                    priority=priority,
                )
            )

        expected_gain = {
            main_focus: 0.8,
            second_focus: 0.5,
        }

        main_focus_label = self.DIMENSION_LABELS.get(main_focus, main_focus)
        second_focus_label = self.DIMENSION_LABELS.get(second_focus, second_focus)
        summary = f"先覆盖最低分知识点，再重点提升{main_focus_label}与{second_focus_label}。"

        return PathPlan(
            user_id=snapshot.user_id,
            cycle_days=cycle_days,
            goal_summary=summary,
            expected_gain=expected_gain,
            tasks=tasks,
        )
