from typing import Any, Dict, Optional

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction

from core.imentiv_client import ImentivClient, ImentivClientError
from evaluations.models import VoiceAnalysis


class ImentivAnalysisError(Exception):
    """Raised when iMentiv emotion analysis cannot be completed."""


class ImentivAnalysisService:
    def __init__(self):
        self.client = ImentivClient.from_settings()

    def analyze_and_save(self, audio_obj) -> VoiceAnalysis:
        if not self.client.is_configured():
            raise ImentivAnalysisError(
                "iMentiv 未配置，请检查 IMENTIV_BASE_URL/IMENTIV_API_KEY"
            )

        if not default_storage.exists(audio_obj.file_key):
            raise ImentivAnalysisError("音频文件不存在或已被删除")

        with default_storage.open(audio_obj.file_key, "rb") as fp:
            file_bytes = fp.read()

        if not file_bytes:
            raise ImentivAnalysisError("音频文件为空，无法进行 iMentiv 分析")

        submit_payload = self.client.submit_audio(
            file_name=audio_obj.file_name or "audio.wav",
            file_bytes=file_bytes,
            mime_type=audio_obj.mime_type or "audio/wav",
            language=getattr(settings, "IMENTIV_LANGUAGE", "zh"),
            title=self._build_submit_title(audio_obj),
            description=self._build_submit_description(audio_obj),
        )

        audio_id = submit_payload.get("id")
        if not audio_id:
            raise ImentivAnalysisError(
                f"iMentiv 上传接口未返回音频ID: {submit_payload}"
            )

        result_payload = self.client.wait_until_completed(
            audio_id=str(audio_id),
            poll_interval_seconds=getattr(settings, "IMENTIV_POLL_INTERVAL_SECONDS", 2),
            max_polls=getattr(settings, "IMENTIV_MAX_POLLS", 30),
        )

        emotion = self._extract_primary_emotion(result_payload)
        imentiv_status = self._safe_text(result_payload.get("status"))
        imentiv_emotion_analysis = result_payload.get("emotion_analysis")
        if not isinstance(imentiv_emotion_analysis, dict):
            imentiv_emotion_analysis = {}

        voice_analysis = self._upsert_voice_analysis(
            audio_obj,
            emotion=emotion,
            imentiv_status=imentiv_status,
            imentiv_emotion_analysis=imentiv_emotion_analysis,
        )

        audio_obj.imentiv_analysis_status = "success"
        audio_obj.imentiv_error_message = ""
        audio_obj.save(
            update_fields=[
                "imentiv_analysis_status",
                "imentiv_error_message",
                "updated_at",
            ]
        )

        return voice_analysis

    def _build_submit_title(self, audio_obj) -> str:
        round_obj = getattr(audio_obj, "round", None)
        interview_obj = getattr(round_obj, "interview", None) if round_obj else None

        candidates = [
            getattr(round_obj, "question_content", ""),
            getattr(interview_obj, "name", ""),
            getattr(audio_obj, "file_name", ""),
        ]

        for raw in candidates:
            if isinstance(raw, str):
                text = raw.strip()
                if text:
                    return text[:200]

        return f"interview-audio-{audio_obj.id}"

    def _build_submit_description(self, audio_obj) -> str:
        round_obj = getattr(audio_obj, "round", None)
        interview_obj = getattr(round_obj, "interview", None) if round_obj else None

        candidates = [
            getattr(round_obj, "user_answer", ""),
            getattr(round_obj, "question_content", ""),
            getattr(interview_obj, "name", ""),
            getattr(audio_obj, "file_name", ""),
        ]

        for raw in candidates:
            if isinstance(raw, str):
                text = raw.strip()
                if text:
                    return text[:1000]

        return f"Interview audio analysis for audio_id={audio_obj.id}"

    def _upsert_voice_analysis(
        self,
        audio_obj,
        emotion: str,
        imentiv_status: str,
        imentiv_emotion_analysis: Dict[str, Any],
    ) -> VoiceAnalysis:
        with transaction.atomic():
            voice_analysis = (
                VoiceAnalysis.objects.select_for_update()
                .filter(audio=audio_obj)
                .order_by("-id")
                .first()
            )

            create_kwargs = {
                "round": audio_obj.round,
                "audio": audio_obj,
                "status": "pending",
                "duration_seconds": float(audio_obj.duration_seconds or 0),
                "speech_rate": 0,
                "audio_clarity_score": 0,
                "asr_confidence": 0,
                "overall_clarity": 0,
                "confidence_score": 0,
                "emotion": emotion,
                "imentiv_status": imentiv_status,
                "imentiv_emotion_analysis": imentiv_emotion_analysis,
                "filler_word_total": 0,
                "filler_word_counts": {},
                "rms_mean": 0,
                "rms_std": 0,
                "rms_cv": 0,
                "silence_ratio": 0,
                "voiced_frames": 0,
                "total_frames": 0,
            }

            if voice_analysis is None:
                voice_analysis = VoiceAnalysis.objects.create(**create_kwargs)
            else:
                voice_analysis.emotion = emotion
                voice_analysis.imentiv_status = imentiv_status
                voice_analysis.imentiv_emotion_analysis = imentiv_emotion_analysis
                voice_analysis.save(
                    update_fields=[
                        "emotion",
                        "imentiv_status",
                        "imentiv_emotion_analysis",
                        "updated_at",
                    ]
                )

        return voice_analysis

    def _safe_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _extract_primary_emotion(self, payload: Dict[str, Any]) -> str:
        # 官方结构优先：emotion_analysis.overall.audio
        official_scores = (
            (
                ((payload.get("emotion_analysis") or {}).get("overall") or {}).get(
                    "audio"
                )
            )
            if isinstance(payload, dict)
            else None
        )
        if isinstance(official_scores, dict):
            normalized = {}
            for key, value in official_scores.items():
                try:
                    normalized[str(key)] = float(value)
                except (TypeError, ValueError):
                    continue
            if normalized:
                return max(normalized.items(), key=lambda x: x[1])[0]

        direct_candidates = [
            payload.get("emotion"),
            payload.get("primary_emotion"),
            (
                (payload.get("result") or {}).get("emotion")
                if isinstance(payload.get("result"), dict)
                else None
            ),
            (
                (payload.get("data") or {}).get("emotion")
                if isinstance(payload.get("data"), dict)
                else None
            ),
        ]

        for item in direct_candidates:
            if isinstance(item, str) and item.strip():
                return item.strip()

        scores = self._find_emotion_scores(payload)
        if scores:
            return max(scores.items(), key=lambda x: float(x[1]))[0]

        return "unknown"

    def _find_emotion_scores(
        self, payload: Dict[str, Any]
    ) -> Optional[Dict[str, float]]:
        if not isinstance(payload, dict):
            return None

        queue = [payload]
        while queue:
            current = queue.pop(0)
            for key, value in current.items():
                key_l = str(key).lower()
                if key_l in {"emotions", "emotion_scores", "scores"} and isinstance(
                    value, dict
                ):
                    normalized = {}
                    for k, v in value.items():
                        try:
                            normalized[str(k)] = float(v)
                        except (TypeError, ValueError):
                            continue
                    if normalized:
                        return normalized
                if isinstance(value, dict):
                    queue.append(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            queue.append(item)
        return None


def mark_imentiv_analysis_failed(audio_obj, message: str) -> None:
    audio_obj.imentiv_analysis_status = "failed"
    audio_obj.imentiv_error_message = str(message)
    audio_obj.save(
        update_fields=[
            "imentiv_analysis_status",
            "imentiv_error_message",
            "updated_at",
        ]
    )
