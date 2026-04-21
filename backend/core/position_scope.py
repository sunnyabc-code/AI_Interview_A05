"""岗位归类：用于场景题 prompt 与百炼 app_id 解析，避免 code 与预设不一致时落到泛化/Java 默认。"""

from __future__ import annotations

from typing import Any


def position_is_llm_scenario_scope(position: Any) -> bool:
    """
    是否按「大模型 / AIGC / 生成式」岗位约束场景题，并优先走 LLM 百炼应用。

    - code 精确匹配常见别名，或包含 llm、large_model、aigc、genai 等片段；
    - 或岗位名称含强特征词（大模型、AIGC、生成式、LLM 等），便于 DB 里 code 仍为自定义中文岗名的情况。
    """
    code = (getattr(position, "code", None) or "").strip().lower()
    if code in ("llm", "llm_position", "large_model", "aigc", "genai", "llm_algorithm"):
        return True
    if code == "java_backend":
        return False
    for frag in ("llm", "large_model", "aigc", "genai", "gpt", "chatglm", "qwen"):
        if frag in code:
            return True

    name = (getattr(position, "name", None) or "").strip()
    if not name:
        return False
    name_lower = name.lower()
    ascii_markers = ("llm", "aigc", "genai", "gpt", "nlp transformer")
    if any(m in name_lower for m in ascii_markers):
        return True
    for m in ("大模型", "AIGC", "生成式", "多模态", "Agent", "RAG", "通义", "文心", "智谱"):
        if m in name:
            return True
    return False
