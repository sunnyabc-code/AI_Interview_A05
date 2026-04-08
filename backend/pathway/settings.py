import os
from dataclasses import dataclass

from django.conf import settings as django_settings


@dataclass
class PathwayLlmConfig:
    base_url: str
    api_key: str
    model: str
    endpoint_path: str
    temperature: float
    prompt_version: str
    timeout_seconds: int
    max_retries: int


def load_llm_config() -> PathwayLlmConfig:
    base_url = os.getenv("PATHWAY_LLM_BASE_URL") or getattr(django_settings, "LLM_BASE_URL", "")
    api_key = os.getenv("PATHWAY_LLM_API_KEY") or getattr(django_settings, "LLM_API_KEY", "")
    model = os.getenv("PATHWAY_LLM_MODEL") or getattr(django_settings, "LLM_MODEL", "")
    timeout_seconds = int(
        os.getenv("PATHWAY_LLM_TIMEOUT_SECONDS")
        or str(getattr(django_settings, "LLM_TIMEOUT_SECONDS", 30))
    )
    max_retries = int(
        os.getenv("PATHWAY_LLM_MAX_RETRIES")
        or str(getattr(django_settings, "LLM_RETRY_COUNT", 2))
    )

    return PathwayLlmConfig(
        base_url=base_url,
        api_key=api_key,
        model=model,
        endpoint_path=os.getenv("PATHWAY_LLM_ENDPOINT_PATH", "/chat/completions"),
        temperature=float(os.getenv("PATHWAY_LLM_TEMPERATURE", "0.3")),
        prompt_version=os.getenv("PATHWAY_LLM_PROMPT_VERSION", "v1"),
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )


def llm_ready() -> bool:
    cfg = load_llm_config()
    return bool(cfg.base_url and cfg.api_key and cfg.model)
