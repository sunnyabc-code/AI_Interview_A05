import json
import re

import requests
from django.conf import settings


def call_llm(system_prompt: str, history_messages: list | None = None) -> str:
    """OpenAI 兼容 /v1/chat/completions；后续可切换百炼同路径。"""
    base = getattr(settings, 'LLM_BASE_URL', '').rstrip('/')
    key = getattr(settings, 'LLM_API_KEY', '')
    model = getattr(settings, 'LLM_MODEL', 'qwen-turbo')
    if not base or not key:
        raise RuntimeError('未配置 LLM：请在环境变量设置 LLM_BASE_URL / LLM_API_KEY，或在 settings 中配置')

    messages = [{'role': 'system', 'content': system_prompt}]
    if history_messages:
        messages.extend(history_messages)

    body = {'model': model, 'messages': messages, 'temperature': 0.6}
    low = system_prompt.lower()
    if 'json' in low:
        body['response_format'] = {'type': 'json_object'}

    url = base + '/chat/completions'
    r = requests.post(
        url,
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
        json=body,
        timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError(f'LLM HTTP {r.status_code}: {r.text[:500]}')
    data = r.json()
    try:
        return data['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError):
        return ''


def extract_json_obj(text: str) -> dict:
    if not text:
        return {}
    t = text.replace('```json', '').replace('```', '').strip()
    m = re.search(r'\{[\s\S]*\}', t)
    if m:
        t = m.group(0)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return {}
