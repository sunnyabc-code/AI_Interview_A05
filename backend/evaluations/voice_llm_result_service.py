import json
import re
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from django.db import transaction
from django.utils import timezone

from core.llm_client import LLMClient, LLMClientError
from evaluations.models import VoiceAnalysis, VoiceLLMResult
from interviews.models import Interview, InterviewRound

PROMPT_VERSION = "voice_llm_v1"
VOICE_LLM_BASE_URL = "https://api.siliconflow.cn/v1"
VOICE_LLM_API_KEY = "sk-dluftqepbembchzclitolntrxnmpfukijjivfjxkwyabtfnk"
VOICE_LLM_MODEL = "deepseek-ai/DeepSeek-V3.2"


class VoiceLLMResultServiceError(Exception):
    """Raised when interview-level voice summary generation fails."""


def _safe_decimal(value: Any, default: str = "0.0") -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001
        return Decimal(default)


def _extract_json(text: str) -> Dict[str, Any]:
    raw_text = (text or "").strip()
    if not raw_text:
        raise VoiceLLMResultServiceError("LLM 返回内容为空")

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.IGNORECASE)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise VoiceLLMResultServiceError(f"LLM 输出不是合法 JSON: {raw_text[:200]}")

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise VoiceLLMResultServiceError(f"LLM JSON 解析失败: {exc}") from exc

    if not isinstance(parsed, dict):
        raise VoiceLLMResultServiceError("LLM 输出 JSON 不是对象")
    return parsed


def _build_round_payloads(interview: Interview) -> Tuple[List[Dict[str, Any]], int]:
    rounds = list(
        InterviewRound.objects.filter(interview=interview)
        .order_by("round_number")
        .only("id", "round_number", "category_id")
    )

    analyses = VoiceAnalysis.objects.filter(round__interview=interview).select_related(
        "round"
    )
    analysis_map = {item.round_id: item for item in analyses if item.round_id}

    payloads: List[Dict[str, Any]] = []
    analyzed_count = 0
    for round_obj in rounds:
        analysis = analysis_map.get(round_obj.id)
        if analysis is None:
            payloads.append(
                {
                    "round_id": round_obj.id,
                    "round_number": round_obj.round_number,
                    "analysis_exists": False,
                }
            )
            continue

        analyzed_count += 1
        payloads.append(
            {
                "round_id": round_obj.id,
                "round_number": round_obj.round_number,
                "analysis_exists": True,
                "duration_seconds": analysis.duration_seconds,
                "speech_rate": analysis.speech_rate,
                "speech_rate_level": analysis.speech_rate_level,
                "audio_clarity_score": analysis.audio_clarity_score,
                "confidence_score": analysis.confidence_score,
                "emotion": analysis.emotion,
                "filler_word_total": analysis.filler_word_total,
                "filler_word_counts": analysis.filler_word_counts,
                "rms_mean": analysis.rms_mean,
                "rms_std": analysis.rms_std,
                "rms_cv": analysis.rms_cv,
                "silence_ratio": analysis.silence_ratio,
                "silence_ratio_level": analysis.silence_ratio_level,
                "imentiv_emotion_analysis": analysis.imentiv_emotion_analysis,
            }
        )

    return payloads, analyzed_count


def _build_messages(
    interview: Interview, round_payloads: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    system_prompt = (
        "你是资深中文面试语音教练。"
        "你将基于一场面试的全部轮次音频分析数据，输出客观、可执行、鼓励式反馈。"
        "请严格只输出 JSON，不要输出任何额外文本。"
        "评分范围均为 0-100，保留 1 位小数。"
        "若数据不足，请在对应字段说明“数据不足”，但仍给出保守评分与建议。"
    )

    user_prompt = (
        "请分析以下面试音频数据，并严格按照指定的 JSON 格式输出评估结果。输出必须是合法的 JSON 对象，不要添加任何额外文字、前言、解释、问候语或 Markdown 代码块。直接以 { 开头，以 } 结束。\n"
        "\n"
        "输入数据：\n"
        f"interview_id: {interview.id}\n"
        f"position_name: {interview.position.name}\n"
        f"total_rounds: {interview.total_rounds}\n"
        f"rounds_voice_analyses: {json.dumps(round_payloads, ensure_ascii=False)}\n"
        "\n"
        "每个 round 的音频数据可能包含以下字段（请综合所有 round 的数据进行整体评估）：\n"
        "- round_number, duration_seconds, speech_rate, speech_rate_level\n"
        "- audio_clarity_score, confidence_score, emotion\n"
        "- filler_word_total, filler_word_counts\n"
        "- silence_ratio, silence_ratio_level\n"
        "- rms_mean, rms_std, rms_cv\n"
        "- imentiv_emotion_analysis\n"
        "\n"
        "输出必须严格遵循以下 JSON 结构，所有字段必须完整存在（不允许缺失或新增字段）：\n"
        "\n"
        "{\n"
        '  "overall_audio_score": 0.0,                    // 整体音频沟通表现评分，范围 0.0 - 100.0（保留一位小数）\n'
        '  "speech_rate_and_rhythm": {\n'
        '    "score": 0.0,                               // 0.0-100.0\n'
        '    "analysis": ["点1", "点2"]                  // 数组形式，每项为简短分析点，必须引用 speech_rate、silence_ratio 等具体数据\n'
        "  },\n"
        '  "fluency": {\n'
        '    "score": 0.0,                               // 0.0-100.0\n'
        '    "analysis": ["点1", "点2"]                  // 数组，必须明确引用 filler_word_total、filler_word_counts\n'
        "  },\n"
        '  "confidence_and_voice_energy": {\n'
        '    "score": 0.0,                               // 0.0-100.0\n'
        '    "analysis": ["点1", "点2"]                  // 数组，必须引用 confidence_score、rms_mean、rms_std、rms_cv\n'
        "  },\n"
        '  "emotional_stability_and_tone": {\n'
        '    "score": 0.0,                               // 0.0-100.0\n'
        '    "analysis": ["点1", "点2"]                  // 数组，引用 emotion 和 imentiv_emotion_analysis\n'
        "  },\n"
        '  "strengths": ["优势点1", "优势点2", "优势点3"],   // 数组，至少 3 个具体优势点（第二人称“你”），引用数据\n'
        '  "improvements": ["改进动作1", "改进动作2", "改进动作3"], // 数组，至少 3 条具体可执行的改进动作，每条简洁且可操作\n'
        '  "position_communication_tips": ["建议1", "建议2"], // 数组，至少 2-3 条，结合 position_name（大模型算法岗 或 Java后端工程师岗），聚焦技术讲解时的语音逻辑、清晰度等\n'
        '  "encouragement": ""                             // 一段积极、具体、不空泛的鼓励话语，语气像教练，提到具体优点\n'
        "}\n"
        "\n"
        "额外严格要求：\n"
        '- 所有 "analysis" 字段必须使用字符串数组（[]），每个元素是一个简短的分点，便于前端分点清晰展示。\n'
        "- strengths 和 position_communication_tips 也必须是数组。\n"
        "- 在所有评分和分析中，必须明确引用并解释：speech_rate、silence_ratio、filler_word_total、confidence_score 的具体数值或等级。\n"
        "- 语气整体采用第二人称“你”，亲切、建设性、鼓励性，像在帮助求职者提升。\n"
        "- position_communication_tips 必须紧密结合当前岗位的技术沟通需求（例如算法思路讲解或系统设计说明时的逻辑连贯性、清晰度等）。\n"
        "- improvements 至少给出 3 条具体可执行动作，不需要标序号。\n"
        "- encouragement 要积极但具体，指出可提升的空间同时给予肯定。\n"
        "- 确保 JSON 完全有效，无多余逗号、无注释。\n"
        "\n"
        "现在请基于输入数据生成评估结果。"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _fill_result_fields(
    result_obj: VoiceLLMResult, parsed: Dict[str, Any], snapshot: Dict[str, Any]
) -> None:
    speech_rate = parsed.get("speech_rate_and_rhythm") or {}
    fluency = parsed.get("fluency") or {}
    confidence = parsed.get("confidence_and_voice_energy") or {}
    emotional = parsed.get("emotional_stability_and_tone") or {}

    result_obj.overall_audio_score = _safe_decimal(parsed.get("overall_audio_score"))

    result_obj.speech_rate_and_rhythm_score = _safe_decimal(speech_rate.get("score"))
    result_obj.speech_rate_and_rhythm = str(speech_rate.get("analysis") or "")

    result_obj.fluency_score = _safe_decimal(fluency.get("score"))
    result_obj.fluency = str(fluency.get("analysis") or "")

    result_obj.confidence_and_voice_energy_score = _safe_decimal(
        confidence.get("score")
    )
    result_obj.confidence_and_voice_energy = str(confidence.get("analysis") or "")

    result_obj.emotional_stability_and_tone_score = _safe_decimal(
        emotional.get("score")
    )
    result_obj.emotional_stability_and_tone = str(emotional.get("analysis") or "")

    result_obj.strengths = str(parsed.get("strengths") or "")
    result_obj.improvements = str(parsed.get("improvements") or "")
    result_obj.position_communication_tips = str(
        parsed.get("position_communication_tips") or ""
    )
    result_obj.encouragement = str(parsed.get("encouragement") or "")

    result_obj.raw_output_json = parsed
    result_obj.raw_input_json = snapshot
    result_obj.status = "success"
    result_obj.error_message = ""
    result_obj.generated_at = timezone.now()


def generate_interview_voice_llm_result(interview_id: int) -> VoiceLLMResult:
    try:
        interview = Interview.objects.select_related("position").get(id=interview_id)
    except Interview.DoesNotExist as exc:
        raise VoiceLLMResultServiceError("面试不存在") from exc

    with transaction.atomic():
        result_obj, _ = VoiceLLMResult.objects.get_or_create(interview=interview)
        result_obj.status = "running"
        result_obj.retry_count = (result_obj.retry_count or 0) + 1
        result_obj.error_message = ""
        result_obj.prompt_version = PROMPT_VERSION
        result_obj.save(
            update_fields=[
                "status",
                "retry_count",
                "error_message",
                "prompt_version",
                "updated_at",
            ]
        )

    round_payloads, analyzed_count = _build_round_payloads(interview)
    if analyzed_count == 0:
        result_obj.status = "failed"
        result_obj.error_message = (
            "没有可用的轮次语音分析数据，请先完成 voice_analyses。"
        )
        result_obj.save(update_fields=["status", "error_message", "updated_at"])
        raise VoiceLLMResultServiceError(result_obj.error_message)

    snapshot = {
        "interview_id": interview.id,
        "position_name": interview.position.name,
        "total_rounds": interview.total_rounds,
        "analyzed_round_count": analyzed_count,
        "rounds_voice_analyses": round_payloads,
    }

    # 仅用于面试结束后的 voice_llm_result 生成，使用专用通义千问配置。
    client = LLMClient(
        base_url=VOICE_LLM_BASE_URL,
        api_key=VOICE_LLM_API_KEY,
        model=VOICE_LLM_MODEL,
        timeout_seconds=90,
        retry_count=2,
        retry_backoff_seconds=1.5,
    )
    if not client.is_configured():
        result_obj.status = "failed"
        result_obj.error_message = (
            "LLM 未配置，请检查 LLM_BASE_URL/LLM_API_KEY/LLM_MODEL"
        )
        result_obj.raw_input_json = snapshot
        result_obj.save(
            update_fields=["status", "error_message", "raw_input_json", "updated_at"]
        )
        raise VoiceLLMResultServiceError(result_obj.error_message)

    try:
        content = client.chat(
            messages=_build_messages(interview, round_payloads),
            temperature=0.2,
            max_tokens=1200,
        )
        parsed = _extract_json(content)
        result_obj.llm_model = client.model
        _fill_result_fields(result_obj, parsed, snapshot)
        result_obj.save()
        return result_obj
    except (
        LLMClientError,
        VoiceLLMResultServiceError,
        Exception,
    ) as exc:  # noqa: BLE001
        result_obj.status = "failed"
        result_obj.error_message = str(exc)
        result_obj.raw_input_json = snapshot
        result_obj.save(
            update_fields=["status", "error_message", "raw_input_json", "updated_at"]
        )
        raise VoiceLLMResultServiceError(str(exc)) from exc
