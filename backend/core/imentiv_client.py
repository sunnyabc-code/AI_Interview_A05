import json
import time
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlsplit
from typing import Any, Dict, Optional, Tuple

from django.conf import settings


class ImentivClientError(Exception):
    """Raised when iMentiv API request fails or response is invalid."""


class ImentivClient:
    """Minimal iMentiv Audio Emotion API client without external dependencies."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        referer: str = "",
        is_internal: bool = False,
        timeout_seconds: int = 60,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.referer = referer or ""
        self.is_internal = bool(is_internal)
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(cls) -> "ImentivClient":
        return cls(
            base_url=getattr(settings, "IMENTIV_BASE_URL", "https://api.imentiv.ai"),
            api_key=getattr(settings, "IMENTIV_API_KEY", ""),
            referer=getattr(settings, "IMENTIV_REFERER", "http://127.0.0.1:8000/"),
            is_internal=getattr(settings, "IMENTIV_IS_INTERNAL", False),
            timeout_seconds=getattr(settings, "IMENTIV_TIMEOUT_SECONDS", 60),
        )

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }
        if self.referer:
            headers["Referer"] = self.referer
            parts = urlsplit(self.referer)
            if parts.scheme and parts.netloc:
                headers["Origin"] = f"{parts.scheme}://{parts.netloc}"
        if self.is_internal:
            headers["is_internal"] = "true"
            headers["is-internal"] = "true"
            headers["X-Is-Internal"] = "true"
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _request_json(
        self,
        method: str,
        endpoint: str,
        body: Optional[bytes] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        request = urllib.request.Request(
            url=f"{self.base_url}{endpoint}",
            data=body,
            headers=self._headers(content_type=content_type),
            method=method,
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ImentivClientError(
                f"iMentiv HTTP error: {exc.code}, {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ImentivClientError(f"iMentiv request failed: {exc.reason}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ImentivClientError(f"iMentiv unknown error: {exc}") from exc

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise ImentivClientError(
                f"iMentiv returned non-JSON body: {response_body}"
            ) from exc

    def _build_multipart_body(
        self,
        file_name: str,
        file_bytes: bytes,
        mime_type: str,
        language: str,
        title: str,
        description: str,
    ) -> Tuple[bytes, str]:
        boundary = "----CopilotImentivBoundary"
        safe_file_name = urllib.parse.quote(file_name or "audio.wav")
        content_type = mime_type or "audio/wav"

        parts = []

        def add_field(name: str, value: str) -> None:
            parts.append(f"--{boundary}\r\n".encode("utf-8"))
            parts.append(
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
            )
            parts.append(f"{value}\r\n".encode("utf-8"))

        add_field("title", title)
        add_field("description", description)
        add_field("language", language)
        add_field("speaker_diarization", "true")
        add_field("text_emotion_analysis", "true")

        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(
            (
                "Content-Disposition: form-data; "
                f'name="audio_file"; filename="{safe_file_name}"\r\n'
            ).encode("utf-8")
        )
        parts.append(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        parts.append(file_bytes)
        parts.append("\r\n".encode("utf-8"))

        parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)
        return body, f"multipart/form-data; boundary={boundary}"

    def submit_audio(
        self,
        file_name: str,
        file_bytes: bytes,
        mime_type: str,
        language: str,
        title: str,
        description: str,
    ) -> Dict[str, Any]:
        body, content_type = self._build_multipart_body(
            file_name=file_name,
            file_bytes=file_bytes,
            mime_type=mime_type,
            language=language,
            title=title,
            description=description,
        )
        return self._request_json(
            method="POST",
            endpoint="/v2/audios",
            body=body,
            content_type=content_type,
        )

    def get_audio_multimodal_insights(self, audio_id: str) -> Dict[str, Any]:
        return self._request_json(
            method="GET",
            endpoint=f"/v2/audios/{audio_id}/multimodal-analytics",
        )

    def wait_until_completed(
        self,
        audio_id: str,
        poll_interval_seconds: float,
        max_polls: int,
    ) -> Dict[str, Any]:
        polls = max(1, int(max_polls))
        for _ in range(polls):
            payload = self.get_audio_multimodal_insights(audio_id)
            status = str(payload.get("status") or "").lower()
            if status in {"completed", "success", "done"}:
                return payload
            if status in {"failed", "error", "canceled", "cancelled", "not_found"}:
                raise ImentivClientError(f"iMentiv analysis failed: {payload}")
            time.sleep(max(0.1, float(poll_interval_seconds)))

        raise ImentivClientError(
            f"iMentiv analysis timeout after {polls} polls, audio_id={audio_id}"
        )
