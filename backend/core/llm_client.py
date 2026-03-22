import json
import time
import urllib.error
import urllib.request
from typing import List, Dict, Optional, Any

from django.conf import settings


class LLMClientError(Exception):
    """Raised when LLM request fails or response is invalid."""


class LLMClient:
    """Simple OpenAI-compatible chat client without extra dependencies."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 30,
        retry_count: int = 2,
        retry_backoff_seconds: float = 1.5,
    ):
        self.base_url = (base_url or '').rstrip('/')
        self.api_key = api_key or ''
        self.model = model or ''
        self.timeout_seconds = timeout_seconds
        self.retry_count = max(retry_count, 0)
        self.retry_backoff_seconds = max(retry_backoff_seconds, 0.0)

    @classmethod
    def from_settings(cls) -> "LLMClient":
        return cls(
            base_url=getattr(settings, 'LLM_BASE_URL', ''),
            api_key=getattr(settings, 'LLM_API_KEY', ''),
            model=getattr(settings, 'LLM_MODEL', ''),
            timeout_seconds=getattr(settings, 'LLM_TIMEOUT_SECONDS', 30),
            retry_count=getattr(settings, 'LLM_RETRY_COUNT', 2),
            retry_backoff_seconds=getattr(settings, 'LLM_RETRY_BACKOFF_SECONDS', 1.5),
        )

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def _headers(self) -> Dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }

    def _post_json(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = urllib.request.Request(
            url=f'{self.base_url}{endpoint}',
            data=json.dumps(payload).encode('utf-8'),
            headers=self._headers(),
            method='POST',
        )

        last_error = None
        total_attempts = self.retry_count + 1
        for attempt in range(1, total_attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    body = response.read().decode('utf-8')
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode('utf-8', errors='ignore')
                last_error = f'LLM HTTP error: {exc.code}, {detail}'
                retriable = exc.code == 429 or 500 <= exc.code <= 599
                if retriable and attempt < total_attempts:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                raise LLMClientError(last_error) from exc
            except urllib.error.URLError as exc:
                last_error = f'LLM request failed: {exc.reason}'
                if attempt < total_attempts:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                raise LLMClientError(last_error) from exc
            except Exception as exc:  # noqa: BLE001
                # TimeoutError / socket timeout often falls here depending on runtime.
                last_error = f'LLM unknown error: {exc}'
                if attempt < total_attempts:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                raise LLMClientError(last_error) from exc
        else:
            raise LLMClientError(last_error or 'LLM request failed after retries')

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise LLMClientError(f'LLM returned non-JSON body: {body}') from exc

    def _extract_text_from_chat_response(self, data: Dict[str, Any]) -> str:
        choices = data.get('choices')
        if isinstance(choices, list) and choices:
            first = choices[0] or {}

            message = first.get('message')
            if isinstance(message, dict):
                content = message.get('content')
                if isinstance(content, str) and content.strip():
                    return content.strip()

            text = first.get('text')
            if isinstance(text, str) and text.strip():
                return text.strip()

            delta = first.get('delta')
            if isinstance(delta, dict):
                delta_content = delta.get('content')
                if isinstance(delta_content, str) and delta_content.strip():
                    return delta_content.strip()

        output_text = data.get('output_text')
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        output = data.get('output')
        if isinstance(output, dict):
            out_text = output.get('text')
            if isinstance(out_text, str) and out_text.strip():
                return out_text.strip()

            out_choices = output.get('choices')
            if isinstance(out_choices, list) and out_choices:
                maybe_text = out_choices[0].get('text') if isinstance(out_choices[0], dict) else None
                if isinstance(maybe_text, str) and maybe_text.strip():
                    return maybe_text.strip()

        return ''

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        lines = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            lines.append(f'{role}: {content}')
        return '\n'.join(lines)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        if not self.is_configured():
            raise LLMClientError('LLM 未配置，请检查 LLM_BASE_URL/LLM_API_KEY/LLM_MODEL')

        chat_payload = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }

        data = self._post_json('/chat/completions', chat_payload)
        text = self._extract_text_from_chat_response(data)
        if text:
            return text

        # Some providers may not return chat choices but can still work with completions.
        completion_payload = {
            'model': self.model,
            'prompt': self._messages_to_prompt(messages),
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        completion_data = self._post_json('/completions', completion_payload)
        completion_text = self._extract_text_from_chat_response(completion_data)
        if completion_text:
            return completion_text

        # Keep diagnostics concise but useful.
        chat_diag = {
            'id': data.get('id'),
            'model': data.get('model'),
            'choices': data.get('choices'),
            'error': data.get('error'),
        }
        completion_diag = {
            'id': completion_data.get('id'),
            'model': completion_data.get('model'),
            'choices': completion_data.get('choices'),
            'error': completion_data.get('error'),
        }
        raise LLMClientError(
            f'LLM returned no usable content. chat={chat_diag}, completions={completion_diag}'
        )

    def generate_question_from_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 256,
    ) -> str:
        system_text = system_prompt or '你是一名严谨的中文技术面试官。请只输出一个问题，不要输出答案。'
        messages = [
            {'role': 'system', 'content': system_text},
            {'role': 'user', 'content': prompt},
        ]
        return self.chat(messages=messages, temperature=temperature, max_tokens=max_tokens)
