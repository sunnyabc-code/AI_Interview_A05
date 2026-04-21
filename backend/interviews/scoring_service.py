"""
面试结束后：按轮次调用岗位对应百炼应用（或兼容 LLM）打分，写入 interview_round_analyses。
并提供按题型/追问链/技术知识点聚合的评估摘要数据。
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from collections import defaultdict

from django.conf import settings
from typing import Any, Dict, List, Optional, Tuple

from django.db import DatabaseError, transaction
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
from positions.models import JobKnowledge
from recommendations.models import UserKnowledgeMatrics


def _analysis_for_round_id(round_id: int) -> Optional[InterviewRoundAnalysis]:
    """直接查 interview_round_analyses，避免 reverse OneToOne 缓存/未预取导致同步漏读。"""
    return InterviewRoundAnalysis.objects.filter(round_id=round_id).first()


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


def _clamp_score_int(value: float) -> int:
    return max(0, min(100, int(round(float(value)))))


def _resolve_job_knowledge_pk(position_id: int, serial: Optional[int]) -> Optional[int]:
    if serial is None:
        return None
    row = JobKnowledge.objects.filter(job_id=position_id, serial_number=serial).first()
    return int(row.id_job_knowledge) if row else None


def _ukm_console(msg: str) -> None:
    """同步/打分相关提示：写到 stderr，在 Windows CMD 里一般比 stdout 更不易被缓冲吞掉。"""
    if not getattr(settings, "UKM_SYNC_CONSOLE_LOG", True):
        return
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def _resolve_job_knowledge_pk_for_chain(
    position_id: int,
    rs_sorted: List[InterviewRound],
) -> Tuple[Optional[int], str]:
    """
    user_knowledge_matrics.id_job_knowledge 对应 job_knowledge.id_job_knowledge。

    解析规则（仅技术题链会用）：
    1) 在链上任取第一个非空的 interview_round.job_knowledge_serial，
       用 job_knowledge(job_id=岗位主键 position_id, serial_number=该 serial) 定位行；
    2) 若无 serial，则用链上非空的 chain_topic_label 与 job_knowledge.name
       先不区分大小写精确匹配，再宽松子串匹配（同 job_id）。
    """
    serial: Optional[int] = None
    for r in rs_sorted:
        if r.job_knowledge_serial is not None:
            serial = r.job_knowledge_serial
            break
    if serial is not None:
        row = JobKnowledge.objects.filter(job_id=position_id, serial_number=serial).first()
        if row:
            return int(row.id_job_knowledge), f"serial={serial}"
        return None, f"no_job_knowledge_row_for_serial={serial}"

    label = ""
    for r in rs_sorted:
        t = (r.chain_topic_label or "").strip()
        if t:
            label = t
            break
    if label:
        row = JobKnowledge.objects.filter(job_id=position_id, name__iexact=label).first()
        if row:
            return int(row.id_job_knowledge), f"name_iexact={label!r}"
        for jk in JobKnowledge.objects.filter(job_id=position_id).order_by("serial_number"):
            n = (jk.name or "").strip()
            if not n:
                continue
            lo, ln = label.lower(), n.lower()
            if ln in lo or lo in ln:
                return int(jk.id_job_knowledge), f"name_fuzzy={label!r}~{n!r}"
        return None, f"no_job_knowledge_for_label={label!r}"

    return None, "no_job_knowledge_serial_and_empty_chain_topic_label"


def sync_user_knowledge_matrics_from_analyses(interview: Interview) -> Tuple[int, Dict[str, Any]]:
    """
    仅从 interview_round_analyses 取分，写入 user_knowledge_matrics。

    仅「技术题」链写入：非技术题（项目/场景等）不会进入本表。

    id_job_knowledge：对应 job_knowledge 主键；由本链 interview_round 的
    job_knowledge_serial（及必要时 chain_topic_label）在
    job_knowledge(job_id=interviews.position_id, serial_number/name) 中解析得到，
    与 interview_round.job_knowledge_serial 含义一致（serial 即知识点编号）。

    按链一行：logic ← 该链各轮 logic_score 均值；accuracy ← technical_score 均值（0–100 整数）。

    Returns:
        (写入行数, 诊断信息)
    """
    position_id = int(interview.position_id)
    _ukm_console(
        "[user_knowledge_matrics] 开始同步 "
        f"interview_id={interview.id} position_id={position_id} "
        "（仅技术链；id_job_knowledge 由 job_knowledge 表按 serial/名称解析）"
    )
    rounds = list(
        InterviewRound.objects.filter(interview=interview)
        .select_related("category", "analysis")
        .order_by("round_number")
    )
    chain_rounds: Dict[int, List[InterviewRound]] = defaultdict(list)
    for r in rounds:
        code = (r.category.code or "").strip().lower() if r.category else ""
        if code != "technical":
            continue
        chain_rounds[r.chain_index].append(r)

    stats: Dict[str, Any] = {
        "technical_chains": len(chain_rounds),
        "chains_skipped_no_serial": 0,
        "chains_skipped_no_job_knowledge_match": 0,
        "chains_skipped_no_analysis": 0,
        "chains_written": 0,
        "unresolved_notes": [],
    }

    to_create: List[UserKnowledgeMatrics] = []
    for chain_idx, rs in sorted(chain_rounds.items(), key=lambda x: x[0]):
        rs_sorted = sorted(rs, key=lambda x: x.round_number)
        jk_pk, resolve_note = _resolve_job_knowledge_pk_for_chain(position_id, rs_sorted)
        if jk_pk is None:
            if resolve_note == "no_job_knowledge_serial_and_empty_chain_topic_label":
                stats["chains_skipped_no_serial"] += 1
            else:
                stats["chains_skipped_no_job_knowledge_match"] += 1
            note = f"chain_index={chain_idx} 跳过: {resolve_note}"
            stats["unresolved_notes"].append(note[:220])
            _ukm_console(f"[user_knowledge_matrics] {note}")
            continue
        logic_vals: List[float] = []
        acc_vals: List[float] = []
        for r in rs_sorted:
            a = _analysis_for_round_id(r.id)
            if not a:
                continue
            logic_vals.append(float(a.logic_score))
            acc_vals.append(float(a.technical_score))
        if not logic_vals or not acc_vals:
            stats["chains_skipped_no_analysis"] += 1
            note = (
                f"chain_index={chain_idx} id_job_knowledge={jk_pk} ({resolve_note}) "
                "跳过: 链上无 interview_round_analyses 分数"
            )
            stats["unresolved_notes"].append(note[:220])
            _ukm_console(f"[user_knowledge_matrics] {note}")
            continue
        logic_int = _clamp_score_int(sum(logic_vals) / len(logic_vals))
        acc_int = _clamp_score_int(sum(acc_vals) / len(acc_vals))
        to_create.append(
            UserKnowledgeMatrics(
                interview_id=interview.id,
                job_knowledge_id=jk_pk,
                logic=logic_int,
                accuracy=acc_int,
            )
        )
        stats["chains_written"] += 1
        _ukm_console(
            "[user_knowledge_matrics] 将写入 "
            f"interview_id={interview.id} chain_index={chain_idx} "
            f"id_job_knowledge={jk_pk} ({resolve_note}) "
            f"logic={logic_int} accuracy={acc_int} rounds_with_analysis={len(logic_vals)}"
        )

    if not to_create:
        try:
            UserKnowledgeMatrics.objects.filter(interview_id=interview.id).delete()
        except DatabaseError:
            pass
        if stats["technical_chains"] == 0:
            stats["hint"] = "本场无技术题轮次；user_knowledge_matrics 仅记录技术链知识点。"
        elif stats["chains_skipped_no_analysis"] == stats["technical_chains"]:
            stats["hint"] = "技术链均无 interview_round_analyses；请先保证各轮打分成功。"
        elif stats["chains_skipped_no_job_knowledge_match"] > 0:
            stats["hint"] = (
                "无法在 job_knowledge 中解析 id_job_knowledge（核对 job_id 与 position_id、"
                "serial 或 chain_topic_label 与 name）；详见 unresolved_notes。"
            )
        elif stats["chains_skipped_no_serial"] > 0:
            stats["hint"] = (
                "技术链缺少 job_knowledge_serial 且无法用 chain_topic_label 匹配知识点；"
                "详见 unresolved_notes。"
            )
        else:
            stats["hint"] = "未写入行；请查看控制台 [user_knowledge_matrics] 与 unresolved_notes。"
        stats["unresolved_notes"] = stats["unresolved_notes"][:12]
        _ukm_console(
            f"[user_knowledge_matrics] interview_id={interview.id} 未写入任何行。hint={stats.get('hint')}"
        )
        return 0, stats

    with transaction.atomic():
        UserKnowledgeMatrics.objects.filter(interview_id=interview.id).delete()
        # 逐条 INSERT：部分环境下 unmanaged + bulk_create 可能不落库，save(force_insert=True) 更稳。
        for row in to_create:
            row.save(force_insert=True)

    n = len(to_create)
    cnt = UserKnowledgeMatrics.objects.filter(interview_id=interview.id).count()
    if cnt != n:
        _ukm_console(
            f"[user_knowledge_matrics] 警告 interview_id={interview.id}: "
            f"保存后表里 COUNT={cnt} 与预期行数={n} 不一致，请查 DB 权限/从库延迟/连接库是否同一实例。"
        )

    stats["hint"] = "ok"
    stats["unresolved_notes"] = stats["unresolved_notes"][:12]
    stats["db_row_count_after"] = cnt
    _ukm_console(
        f"[user_knowledge_matrics] interview_id={interview.id} 已写入 {n} 行；"
        f"当前库中本场 COUNT={cnt}。"
    )
    return n, stats


def run_scoring_for_interview(interview: Interview) -> Dict[str, Any]:
    """
    对已结束面试的所有已作答轮次打分；已有 analysis 的轮次跳过。
    """
    _ukm_console(
        f"[scoring] interview_id={interview.id} run_scoring_for_interview 开始 "
        f"（若本窗口始终无此类行，说明请求未打到当前 Django 进程）"
    )
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

    knowledge_rows = 0
    knowledge_stats: Dict[str, Any] = {}
    try:
        knowledge_rows, knowledge_stats = sync_user_knowledge_matrics_from_analyses(
            interview
        )
    except Exception as exc:
        _ukm_console(
            "[user_knowledge_matrics] run_scoring 内同步异常 "
            f"(非仅 DatabaseError，请全文查看):\n{traceback.format_exc()}"
        )
        errors.append(f"knowledge_matrics sync: {exc}")
        knowledge_rows = 0
        knowledge_stats = {}

    _ukm_console(
        f"[scoring] interview_id={interview.id} 结束 "
        f"scored_rounds={scored} skipped_existing={skipped} "
        f"knowledge_matrics_rows={knowledge_rows} errors={len(errors)}"
    )

    return {
        "scored_rounds": scored,
        "skipped_existing": skipped,
        "errors": errors,
        "knowledge_matrics_rows": knowledge_rows,
        "knowledge_matrics": knowledge_stats,
    }


def _avg(nums: List[float]) -> Optional[float]:
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


def build_evaluation_summary(
    interview: Interview,
    *,
    run_knowledge_sync: bool = False,
) -> Dict[str, Any]:
    """供 GET evaluation-summary 使用。run_knowledge_sync=True 时顺带幂等写入 user_knowledge_matrics。"""
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
        code = (r.category.code or "").strip().lower()
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
            analyses = [a for r in rs_sorted if (a := _analysis_for_round_id(r.id))]
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
        analyses = [a for r in rs_sorted if (a := _analysis_for_round_id(r.id))]
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

    out: Dict[str, Any] = {
        "interview_id": interview.id,
        "position_name": interview.position.name,
        "position_code": interview.position.code,
        "status": interview.status,
        "enabled_aspects": enabled,
        "aspects": aspects,
        "technical_knowledge_points": technical_knowledge_points,
        "summary_schema_version": 2,
    }

    km_sync: Dict[str, Any] = {
        "written_rows": 0,
        "hint": "",
        "error": "",
        "skipped": True,
        "reason": "run_knowledge_sync=False",
    }
    if run_knowledge_sync:
        km_sync["skipped"] = False
        km_sync["reason"] = ""
        try:
            wr, st = sync_user_knowledge_matrics_from_analyses(interview)
            km_sync = {
                "written_rows": wr,
                "hint": st.get("hint", ""),
                "technical_chains": st.get("technical_chains", 0),
                "db_row_count_after": st.get("db_row_count_after"),
                "unresolved_notes": (st.get("unresolved_notes") or [])[:8],
                "skipped": False,
                "reason": "",
            }
        except Exception as exc:
            km_sync["error"] = str(exc)
            km_sync["hint"] = "sync_exception"
            sys.stderr.write(
                "[user_knowledge_matrics] build_evaluation_summary 内同步异常:\n"
                f"{traceback.format_exc()}\n"
            )
            sys.stderr.flush()
    out["knowledge_matrics_sync"] = km_sync

    return out
