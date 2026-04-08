import json
from typing import Dict, List
from urllib import error, request

from pathway.contracts import PathPlan, PathTask, ProfileSnapshot
from pathway.settings import llm_ready, load_llm_config


# LLM prompt config area (you can customize these texts directly).
SYSTEM_PROMPT = """
你是一位资深面试教练。请根据输入的用户弱项，生成严格可执行的 7 日个性化提升路径。
要求：
1) 必须覆盖技术、场景、项目、表达四个方面。
2) 技术部分必须覆盖输入中的最低分知识点（尽量全部覆盖）。
3) 场景题、项目题要围绕各自最低分方向安排任务。
4) 表达任务要围绕表达弱项维度安排。
5) 输出必须是 JSON，不要输出任何解释文字。
""".strip()

USER_PROMPT_TEMPLATE = """
请基于以下用户弱项信息，生成 {cycle_days} 天路径任务。

弱项信息(JSON):
{context_json}

输出 JSON 结构（字段名保持一致）：
{{
  "goal_summary": "...",
  "expected_gain": {{"technical": 0.0, "expression": 0.0, "scenario": 0.0, "project": 0.0}},
  "tasks": [
    {{
      "day_index": 1,
      "task_type": "question",
      "title": "...",
      "reason": "...",
      "estimated_minutes": 20,
      "priority": 1,
      "focus_area": "technical_knowledge|scenario|project|expression",
      "knowledge_points_covered": ["知识点A", "知识点B"]
    }}
  ]
}}
""".strip()


class LlmPathwayService:
    def _extract_json(self, text: str) -> Dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]

        return json.loads(text)

    def _call_llm(self, cycle_days: int, context: Dict) -> Dict:
        cfg = load_llm_config()
        payload = {
            "model": cfg.model,
            "temperature": cfg.temperature,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(
                        cycle_days=cycle_days,
                        context_json=json.dumps(context, ensure_ascii=False),
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
        }

        url = f"{cfg.base_url.rstrip('/')}{cfg.endpoint_path}"
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {cfg.api_key}",
            },
            method="POST",
        )

        with request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
            content = (
                parsed.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if not content:
                raise ValueError("LLM 返回为空")
            return self._extract_json(content)

    def _task_from_item(self, item: Dict, day_index: int) -> PathTask:
        task_type = str(item.get("task_type") or "question").strip().lower()
        if task_type not in {"question", "practice", "resource", "review"}:
            task_type = "question"

        try:
            estimated = int(item.get("estimated_minutes") or 20)
        except (TypeError, ValueError):
            estimated = 20
        estimated = max(10, min(60, estimated))

        try:
            priority = int(item.get("priority") or 2)
        except (TypeError, ValueError):
            priority = 2
        priority = max(1, min(3, priority))

        title = str(item.get("title") or "训练任务").strip()
        reason = str(item.get("reason") or "基于弱项生成的训练任务").strip()

        return PathTask(
            day_index=day_index,
            task_type=task_type,  # type: ignore[arg-type]
            title=title,
            reason=reason,
            estimated_minutes=estimated,
            source_type="llm_plan",
            source_id=None,
            priority=priority,
        )

    def _validate_or_raise(self, result: Dict, context: Dict, cycle_days: int) -> None:
        tasks = result.get("tasks")
        if not isinstance(tasks, list) or len(tasks) < cycle_days:
            raise ValueError("LLM 任务数量不足")

        tech_points = [x.get("knowledge_name") for x in context.get("technical", {}).get("lowest_knowledge_points", [])]
        required_tech = {str(x).strip() for x in tech_points if str(x).strip()}

        all_text = "\n".join(
            f"{t.get('title', '')} {t.get('reason', '')} {' '.join(t.get('knowledge_points_covered', []) if isinstance(t.get('knowledge_points_covered', []), list) else [])}"
            for t in tasks
        )

        missed = [kp for kp in required_tech if kp not in all_text]
        if missed:
            raise ValueError(f"LLM 输出未覆盖最低分知识点: {missed}")

        text = all_text
        if "场景" not in text and "scenario" not in text.lower():
            raise ValueError("LLM 输出缺少场景题提升任务")
        if "项目" not in text and "project" not in text.lower():
            raise ValueError("LLM 输出缺少项目题提升任务")
        if "表达" not in text and "语速" not in text and "流畅" not in text:
            raise ValueError("LLM 输出缺少表达提升任务")

    def _pad_to_cycle_days(self, raw: List[Dict], cycle_days: int) -> List[Dict]:
        # 最低保障：不足时自动追加可执行复盘任务，保证永远可生成完整计划。
        while len(raw) < cycle_days:
            raw.append(
                {
                    "task_type": "review",
                    "title": "阶段复盘与巩固",
                    "reason": "用于巩固当前学习成果，并为下一步训练做准备。",
                    "estimated_minutes": 15,
                    "priority": 3,
                }
            )
        return raw[:cycle_days]

    def _fallback_plan(self, snapshot: ProfileSnapshot, context: Dict, cycle_days: int) -> PathPlan:
        tech = context.get("technical", {}).get("lowest_knowledge_points", [])
        scenario = context.get("scenario", {}).get("lowest_directions", [])
        project = context.get("project", {}).get("lowest_directions", [])
        expr = context.get("expression", {}).get("weak_dimensions", [])

        tech_names = [x.get("knowledge_name") for x in tech if x.get("knowledge_name")]
        while len(tech_names) < 5:
            tech_names.append(f"技术基础项{len(tech_names) + 1}")

        scenario_name = (
            scenario[0].get("direction")
            if scenario and isinstance(scenario[0], dict)
            else "高压场景应答"
        )
        project_name = (
            project[0].get("direction")
            if project and isinstance(project[0], dict)
            else "项目亮点与指标表达"
        )
        expr_names = [x.get("dimension") for x in expr if x.get("dimension")]
        if not expr_names:
            expr_names = ["表达流畅度", "语速与节奏"]

        k1 = [tech_names[0], tech_names[1]]
        k2 = [tech_names[2], tech_names[3]]
        k3 = [tech_names[4]]

        raw = [
            {
                "task_type": "question",
                "title": f"知识点攻坚：{k1[0]}、{k1[1]}",
                "reason": "覆盖当前最低分知识点，先做基础理解与答题结构训练。",
                "estimated_minutes": 25,
                "priority": 1,
            },
            {
                "task_type": "question",
                "title": f"场景题提升：{scenario_name}",
                "reason": "针对场景题弱项方向进行结构化作答训练。",
                "estimated_minutes": 22,
                "priority": 1,
            },
            {
                "task_type": "question",
                "title": f"知识点攻坚：{k2[0]}、{k2[1]}",
                "reason": "继续覆盖低分知识点，补齐技术问答短板。",
                "estimated_minutes": 25,
                "priority": 1,
            },
            {
                "task_type": "question",
                "title": f"项目题提升：{project_name}",
                "reason": "围绕项目题弱项方向，强化项目背景、决策和结果表达。",
                "estimated_minutes": 24,
                "priority": 1,
            },
            {
                "task_type": "practice",
                "title": f"表达强化：{expr_names[0]}" + (f"、{expr_names[1]}" if len(expr_names) > 1 else ""),
                "reason": "针对表达薄弱维度进行语音与叙述训练。",
                "estimated_minutes": 18,
                "priority": 2,
            },
            {
                "task_type": "question",
                "title": f"知识点攻坚：{k3[0]}",
                "reason": "完成最低分知识点全覆盖，形成技术闭环。",
                "estimated_minutes": 20,
                "priority": 2,
            },
            {
                "task_type": "review",
                "title": "综合复盘：技术+场景+项目+表达",
                "reason": "回顾本周任务，整理改进点并形成下阶段行动清单。",
                "estimated_minutes": 20,
                "priority": 2,
            },
        ]

        raw = self._pad_to_cycle_days(raw, cycle_days)
        tasks = [self._task_from_item(item, i + 1) for i, item in enumerate(raw)]

        return PathPlan(
            user_id=snapshot.user_id,
            cycle_days=cycle_days,
            goal_summary="覆盖最低分知识点，并同步提升场景题、项目题和表达能力。",
            expected_gain={
                "technical": 0.9,
                "scenario": 0.6,
                "project": 0.6,
                "expression": 0.8,
            },
            tasks=tasks,
            generation_meta={"mode": "fallback", "llm_used": False},
        )

    def generate_plan(self, snapshot: ProfileSnapshot, context: Dict, cycle_days: int = 7) -> PathPlan:
        cycle_days = max(7, int(cycle_days or 7))

        if not llm_ready():
            return self._fallback_plan(snapshot, context, cycle_days)

        last_error = None
        cfg = load_llm_config()
        for _ in range(max(1, cfg.max_retries)):
            try:
                result = self._call_llm(cycle_days=cycle_days, context=context)
                self._validate_or_raise(result, context=context, cycle_days=cycle_days)

                tasks_raw = result.get("tasks") or []
                tasks = [
                    self._task_from_item(item, day_index=i + 1)
                    for i, item in enumerate(tasks_raw[:cycle_days])
                ]

                if len(tasks) < cycle_days:
                    raise ValueError("LLM 任务不足")

                goal = str(result.get("goal_summary") or "基于弱项画像生成的 7 日提升路径").strip()
                expected_gain = result.get("expected_gain") if isinstance(result.get("expected_gain"), dict) else {}
                expected_gain = {k: float(v) for k, v in expected_gain.items() if isinstance(v, (int, float))}
                if "technical" not in expected_gain:
                    expected_gain["technical"] = 0.8
                if "expression" not in expected_gain:
                    expected_gain["expression"] = 0.8
                if "scenario" not in expected_gain:
                    expected_gain["scenario"] = 0.6
                if "project" not in expected_gain:
                    expected_gain["project"] = 0.6

                return PathPlan(
                    user_id=snapshot.user_id,
                    cycle_days=cycle_days,
                    goal_summary=goal,
                    expected_gain=expected_gain,
                    tasks=tasks,
                    generation_meta={
                        "mode": "llm",
                        "llm_used": True,
                        "llm_model": cfg.model,
                        "prompt_version": cfg.prompt_version,
                    },
                )
            except (ValueError, error.URLError, json.JSONDecodeError) as exc:
                last_error = exc

        if last_error:
            plan = self._fallback_plan(snapshot, context, cycle_days)
            plan.generation_meta = {
                "mode": "fallback",
                "llm_used": False,
                "fallback_reason": str(last_error),
            }
            return plan

        return self._fallback_plan(snapshot, context, cycle_days)
