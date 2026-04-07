"""
面试结束后：按轮次调用岗位对应百炼应用（或兼容 LLM）打分，写入 interview_round_analyses。
并提供按题型/追问链/技术知识点聚合的评估摘要数据。
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import QuerySet

from core.dashscope_application import (
    DashScopeApplicationError,
    generate_question_via_application,
    is_dashscope_configured_for_position,
    resolve_app_id_for_position,
)
from core.llm_client import LLMClient, LLMClientError
from interviews.answer_utils import is_effective_user_answer
from interviews.models import Interview, InterviewRound, InterviewRoundAnalysis


def _get_round_analysis(round_obj: InterviewRound) -> Optional[InterviewRoundAnalysis]:
    try:
        return round_obj.analysis
    except InterviewRoundAnalysis.DoesNotExist:
        return None


CATEGORY_LABELS = {
    "technical": "技术知识题",
    "project": "项目经历题",
    "scenario": "场景题",
}

DIMENSION_LABELS = {
    "technical_accuracy": "技术准确性",
    "communication": "沟通表达",
    "logic": "逻辑清晰",
    "adaptability": "应变与分析",
    "job_matching": "岗位匹配度",
}


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text or not text.strip():
        return None
    s = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.IGNORECASE)
    if fence:
        s = fence.group(1).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", s)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _f(data: Dict[str, Any], key: str, default: float = 0.0) -> float:
    v = data.get(key)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _str_list(data: Dict[str, Any], key: str) -> List[str]:
    v = data.get(key)
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()][:5]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


def build_scoring_prompt(interview: Interview, round_obj: InterviewRound) -> str:
    pos = interview.position
    cat_code = (round_obj.category.code if round_obj.category else "") or ""
    cat_name = CATEGORY_LABELS.get(cat_code, cat_code or "未知题型")
    topic = (round_obj.chain_topic_label or "").strip()
    topic_line = f"本链知识点主题：{topic}\n" if topic and cat_code == "technical" else ""

    jm_rule = ""
    if cat_code == "project":
        jm_rule = '必须包含 "job_matching_score": 0-100 的整数或小数（岗位匹配度）。\n'
    else:
        jm_rule = '"job_matching_score": null  （非项目题必须为 null）\n'

    return f"""请担任面试官，对以下回答打分（岗位：{pos.name}，code={pos.code}）。
题型：{cat_name}
{topic_line}
【面试问题】
{round_obj.question_content or ""}

【候选人回答】
{round_obj.user_answer or ""}

请只输出一个 JSON 对象，不要输出其它任何文字。字段要求：
- "overall_score": 0-100
- "overall_comment": 字符串，简短综合评价
- "technical_score": 0-100，技术准确性（技术题侧重知识点；项目题可含技术栈相关）
- "communication_score": 0-100，沟通表达
- "logic_score": 0-100，逻辑清晰
- "adaptability_score": 0-100，应变与分析（场景题侧重）
{jm_rule}- "highlights": 字符串数组，1-3 条
- "weaknesses": 字符串数组，1-3 条
- "suggestions": 字符串数组，1-3 条
"""


def score_round_with_llm(interview: Interview, round_obj: InterviewRound) -> InterviewRoundAnalysis:
    """调用岗位对应 app 或兼容 LLM，写入一条 InterviewRoundAnalysis。"""
    prompt = build_scoring_prompt(interview, round_obj)
    raw_text = ""
    if is_dashscope_configured_for_position(interview.position):
        app_id = resolve_app_id_for_position(interview.position)
        try:
            raw_text, _ = generate_question_via_application(
                prompt=prompt,
                app_id=app_id,
                session_id=None,
            )
        except DashScopeApplicationError:
            raw_text = ""
    if not raw_text.strip():
        client = LLMClient.from_settings()
        raw_text = client.chat(
            messages=[
                {
                    "role": "system",
                    "content": "你只输出合法 JSON 对象，不要 markdown，不要解释。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
        )

    data = _extract_json_object(raw_text) or {}
    cat_code = (round_obj.category.code if round_obj.category else "") or ""

    jm = data.get("job_matching_score")
    if cat_code != "project":
        jm_val = None
    else:
        try:
            jm_val = float(jm) if jm is not None else None
        except (TypeError, ValueError):
            jm_val = None

    with transaction.atomic():
        analysis, _ = InterviewRoundAnalysis.objects.update_or_create(
            round=round_obj,
            defaults={
                "overall_score": _f(data, "overall_score"),
                "overall_comment": str(data.get("overall_comment") or "")[:2000],
                "technical_score": _f(data, "technical_score"),
                "communication_score": _f(data, "communication_score"),
                "logic_score": _f(data, "logic_score"),
                "adaptability_score": _f(data, "adaptability_score"),
                "job_matching_score": jm_val,
                "highlights": _str_list(data, "highlights"),
                "weaknesses": _str_list(data, "weaknesses"),
                "suggestions": _str_list(data, "suggestions"),
            },
        )
    return analysis


def run_scoring_for_interview(interview: Interview) -> Dict[str, Any]:
    """
    对已结束面试的所有已作答轮次打分；已有 analysis 的轮次跳过。
    """
    rounds: QuerySet[InterviewRound] = (
        InterviewRound.objects.filter(interview=interview)
        .select_related("category")
        .order_by("round_number")
    )
    scored = 0
    skipped = 0
    errors: List[str] = []
    for r in rounds:
        if not is_effective_user_answer(r.user_answer):
            continue
        if InterviewRoundAnalysis.objects.filter(round=r).exists():
            skipped += 1
            continue
        try:
            score_round_with_llm(interview, r)
            scored += 1
        except (LLMClientError, DashScopeApplicationError, Exception) as exc:
            errors.append(f"round {r.id}: {exc}")

    return {"scored_rounds": scored, "skipped_existing": skipped, "errors": errors}


def _avg(nums: List[float]) -> Optional[float]:
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


def build_evaluation_summary(interview: Interview) -> Dict[str, Any]:
    """供 GET evaluation-summary 使用。"""
    rounds = list(
        InterviewRound.objects.filter(interview=interview)
        .select_related("category", "analysis")
        .order_by("round_number")
    )

    enabled = {
        "technical": interview.enable_technical_questions,
        "project": interview.enable_project_questions,
        "scenario": interview.enable_scenario_questions,
    }

    # (category_code, chain_index) -> list of rounds with analysis
    chain_groups: Dict[Tuple[str, int], List[InterviewRound]] = defaultdict(list)
    for r in rounds:
        if not r.category:
            continue
        code = r.category.code
        if code not in ("technical", "project", "scenario"):
            continue
        chain_groups[(code, r.chain_index)].append(r)

    aspects: Dict[str, Any] = {}
    for cat in ("technical", "project", "scenario"):
        if not enabled.get(cat):
            aspects[cat] = {"chains": []}
            continue
        chain_list = []
        for (c_code, c_idx), rs in sorted(
            chain_groups.items(), key=lambda x: (x[0][0], x[0][1])
        ):
            if c_code != cat:
                continue
            rs_sorted = sorted(rs, key=lambda x: x.round_number)
            analyses = [a for r in rs_sorted if (a := _get_round_analysis(r))]
            if not analyses:
                dims_payload = {}
            else:
                ta = [float(a.technical_score) for a in analyses if a.technical_score is not None]
                co = [
                    float(a.communication_score)
                    for a in analyses
                    if a.communication_score is not None
                ]
                lo = [float(a.logic_score) for a in analyses if a.logic_score is not None]
                ad = [
                    float(a.adaptability_score)
                    for a in analyses
                    if a.adaptability_score is not None
                ]
                jm = [
                    float(a.job_matching_score)
                    for a in analyses
                    if a.job_matching_score is not None
                ]
                dims_payload = {
                    "technical_accuracy": {
                        "label": DIMENSION_LABELS["technical_accuracy"],
                        "score": _avg(ta),
                    },
                    "communication": {
                        "label": DIMENSION_LABELS["communication"],
                        "score": _avg(co),
                    },
                    "logic": {
                        "label": DIMENSION_LABELS["logic"],
                        "score": _avg(lo),
                    },
                    "adaptability": {
                        "label": DIMENSION_LABELS["adaptability"],
                        "score": _avg(ad),
                    },
                }
                if cat == "project":
                    dims_payload["job_matching"] = {
                        "label": DIMENSION_LABELS["job_matching"],
                        "score": _avg(jm),
                    }

            chain_list.append(
                {
                    "chain_index": c_idx,
                    "round_count": len(rs_sorted),
                    "dimensions": dims_payload,
                }
            )
        aspects[cat] = {"chains": chain_list}

    # 技术知识点：按技术链聚合，技术准确性 = 该链各轮 technical_score 平均
    technical_knowledge_points: List[Dict[str, Any]] = []
    for (c_code, c_idx), rs in chain_groups.items():
        if c_code != "technical":
            continue
        rs_sorted = sorted(rs, key=lambda x: x.round_number)
        label = (rs_sorted[0].chain_topic_label or "").strip() or None
        serial = rs_sorted[0].job_knowledge_serial
        analyses = [a for r in rs_sorted if (a := _get_round_analysis(r))]
        ta = [float(a.technical_score) for a in analyses if a.technical_score is not None]
        technical_knowledge_points.append(
            {
                "chain_index": c_idx,
                "chain_topic_label": label,
                "job_knowledge_serial": serial,
                "technical_accuracy": _avg(ta),
                "round_count": len(rs_sorted),
            }
        )
    technical_knowledge_points.sort(key=lambda x: x["chain_index"])

    return {
        "interview_id": interview.id,
        "position_name": interview.position.name,
        "position_code": interview.position.code,
        "status": interview.status,
        "enabled_aspects": enabled,
        "aspects": aspects,
        "technical_knowledge_points": technical_knowledge_points,
    }
