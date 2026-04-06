"""阿里云百炼 Model Studio 应用调用（Application.call），支持 session 多轮追问。"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Optional, Tuple

from django.conf import settings


class DashScopeApplicationError(Exception):
    """百炼应用调用失败。"""


def resolve_app_id_for_position(position) -> str:
    """
    按岗位 code 解析百炼应用 ID（与面试题型无关：同一套 next-question 逻辑，仅 app_id 不同）。
    job_positions.code 建议与 JSON 键一致，例如 java_backend、llm（大小写不敏感）。

    优先级：DASHSCOPE_APP_IDS_JSON 中的键（大小写不敏感）
    -> DASHSCOPE_APP_ID_JAVA_BACKEND（java_backend）
    -> DASHSCOPE_APP_ID_LLM（llm / llm_position）
    -> DASHSCOPE_APP_ID_DEFAULT
    """
    code = (getattr(position, "code", None) or "").strip().lower()
    raw = getattr(settings, "DASHSCOPE_APP_IDS_JSON", "") or "{}"
    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError:
        mapping = {}
    if isinstance(mapping, dict):
        lower_map = {str(k).lower(): v for k, v in mapping.items()}
        if code in lower_map and lower_map[code]:
            return str(lower_map[code]).strip()
    if code == "java_backend":
        v = getattr(settings, "DASHSCOPE_APP_ID_JAVA_BACKEND", "") or ""
        if v.strip():
            return v.strip()
    if code in ("llm", "llm_position"):
        v = getattr(settings, "DASHSCOPE_APP_ID_LLM", "") or ""
        if v.strip():
            return v.strip()
    default = getattr(settings, "DASHSCOPE_APP_ID_DEFAULT", "") or ""
    return default.strip()


def is_dashscope_configured_for_position(position) -> bool:
    api_key = getattr(settings, "DASHSCOPE_API_KEY", "") or ""
    return bool(api_key.strip() and resolve_app_id_for_position(position))


def generate_question_via_application(
    *,
    prompt: str,
    app_id: str,
    session_id: Optional[str] = None,
) -> Tuple[str, str]:
    """
    调用百炼应用生成文本。

    Returns:
        (question_text, new_session_id)
    """
    from dashscope import Application

    api_key = getattr(settings, "DASHSCOPE_API_KEY", "") or ""
    if not api_key.strip():
        raise DashScopeApplicationError("未配置 DASHSCOPE_API_KEY")
    if not (app_id or "").strip():
        raise DashScopeApplicationError("未配置百炼 app_id")

    kwargs = {
        "api_key": api_key.strip(),
        "app_id": app_id.strip(),
        "prompt": prompt,
    }
    if session_id and session_id.strip():
        kwargs["session_id"] = session_id.strip()

    response = Application.call(**kwargs)

    if response.status_code != HTTPStatus.OK:
        msg = getattr(response, "message", "") or ""
        req = getattr(response, "request_id", "") or ""
        raise DashScopeApplicationError(
            f"百炼应用错误 status={response.status_code} request_id={req} message={msg}"
        )

    out = response.output
    text = (getattr(out, "text", None) or "").strip()
    new_session = (getattr(out, "session_id", None) or "").strip()
    if not text:
        raise DashScopeApplicationError("百炼返回内容为空")
    return text, new_session
