import io
import re
import tempfile

import librosa
import numpy as np
import webrtcvad
from django.core.files.storage import default_storage
from django.db import transaction

from evaluations.models import VoiceAnalysis


class AudioAnalysisError(Exception):
    """Raised when audio analysis cannot be completed."""


class AudioAnalysisService:
    FILLER_WORDS = ["那个", "然后", "呃", "啊"]
    TARGET_SR = 16000

    def __init__(self, vad_mode=2):
        self.vad = webrtcvad.Vad(vad_mode)

    def analyze_and_save(self, audio_obj, transcript="", asr_confidence=None):
        transcript = (transcript or "").strip()

        y, sr = self._load_audio_from_storage(audio_obj.file_key)
        duration_seconds = self._safe_duration(
            y, sr, fallback=audio_obj.duration_seconds
        )

        filler_counts = self._count_fillers(transcript)
        filler_total = sum(filler_counts.values())

        rms_stats = self._compute_rms_stats(y)
        silence_stats = self._compute_silence_ratio(y, sr)
        speech_rate = self._compute_speech_rate(transcript, duration_seconds)

        confidence_score = self._compute_confidence_score(
            filler_total=filler_total,
            transcript=transcript,
            silence_ratio=silence_stats["silence_ratio"],
            rms_mean=rms_stats["mean_rms"],
            rms_cv=rms_stats["cv_rms"],
        )
        audio_clarity_score = self._compute_clarity_score(
            speech_rate=speech_rate,
            silence_ratio=silence_stats["silence_ratio"],
            rms_cv=rms_stats["cv_rms"],
        )
        overall_clarity = self._compute_overall_clarity(
            audio_clarity_score, asr_confidence
        )

        defaults = {
            "round": audio_obj.round,
            "status": "success",
            "duration_seconds": duration_seconds,
            "speech_rate": speech_rate,
            "audio_clarity_score": audio_clarity_score,
            "asr_confidence": self._normalize_asr_confidence(asr_confidence),
            "overall_clarity": overall_clarity,
            "confidence_score": confidence_score,
            "filler_word_total": filler_total,
            "filler_word_counts": filler_counts,
            "rms_mean": rms_stats["mean_rms"],
            "rms_std": rms_stats["std_rms"],
            "rms_cv": rms_stats["cv_rms"],
            "silence_ratio": silence_stats["silence_ratio"],
            "voiced_frames": silence_stats["voiced_frames"],
            "total_frames": silence_stats["total_frames"],
        }

        with transaction.atomic():
            duplicate_qs = (
                VoiceAnalysis.objects.select_for_update()
                .filter(audio=audio_obj)
                .order_by("-id")
            )
            voice_analysis = duplicate_qs.first()

            if voice_analysis is not None:
                duplicate_ids = list(duplicate_qs.values_list("id", flat=True)[1:])
                if duplicate_ids:
                    # 历史脏数据兼容：保留最新记录，将其余记录解绑音频避免 OneToOne 冲突
                    VoiceAnalysis.objects.filter(id__in=duplicate_ids).update(
                        audio=None
                    )

                for field, value in defaults.items():
                    setattr(voice_analysis, field, value)
                # emotion 由外部情绪模型维护；仅在当前为空时保底置空
                if not voice_analysis.emotion:
                    voice_analysis.emotion = ""
                voice_analysis.save()
            else:
                voice_analysis = VoiceAnalysis.objects.create(
                    audio=audio_obj,
                    emotion="",
                    **defaults,
                )

            audio_obj.analysis_status = "success"
            if transcript:
                audio_obj.asr_status = "success"
            audio_obj.error_message = ""
            audio_obj.save(
                update_fields=[
                    "analysis_status",
                    "asr_status",
                    "error_message",
                    "updated_at",
                ]
            )

        return voice_analysis

    def _load_audio_from_storage(self, file_key):
        if not default_storage.exists(file_key):
            raise AudioAnalysisError("音频文件不存在或已被删除")

        with default_storage.open(file_key, "rb") as fp:
            raw_bytes = fp.read()

        if not raw_bytes:
            raise AudioAnalysisError("音频文件为空，无法分析")

        try:
            y, sr = librosa.load(io.BytesIO(raw_bytes), sr=self.TARGET_SR, mono=True)
            return y, sr
        except Exception:
            # 一些格式在 BytesIO 中无法直接解码，退化为临时文件读取
            with tempfile.NamedTemporaryFile(suffix=".audio", delete=True) as tmp:
                tmp.write(raw_bytes)
                tmp.flush()
                y, sr = librosa.load(tmp.name, sr=self.TARGET_SR, mono=True)
                return y, sr

    def _safe_duration(self, y, sr, fallback=None):
        if y is not None and len(y) > 0 and sr > 0:
            return round(float(len(y) / sr), 4)
        if fallback:
            return float(fallback)
        return 0.0

    def _count_fillers(self, transcript):
        counts = {}
        for token in self.FILLER_WORDS:
            counts[token] = len(re.findall(re.escape(token), transcript))
        return counts

    def _compute_rms_stats(self, y):
        if y is None or len(y) == 0:
            return {
                "mean_rms": 0.0,
                "std_rms": 0.0,
                "cv_rms": 1.0,
            }

        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        mean_rms = float(np.mean(rms))
        std_rms = float(np.std(rms))
        cv_rms = std_rms / (mean_rms + 1e-8)
        return {
            "mean_rms": round(mean_rms, 6),
            "std_rms": round(std_rms, 6),
            "cv_rms": round(float(cv_rms), 6),
        }

    def _compute_silence_ratio(self, y, sr):
        if y is None or len(y) == 0 or sr <= 0:
            return {
                "silence_ratio": 1.0,
                "voiced_frames": 0,
                "total_frames": 0,
            }

        pcm16 = np.clip(y, -1.0, 1.0)
        pcm16 = (pcm16 * 32767).astype(np.int16)

        frame_duration_ms = 30
        frame_size = int(sr * frame_duration_ms / 1000)
        if frame_size <= 0:
            return {
                "silence_ratio": 1.0,
                "voiced_frames": 0,
                "total_frames": 0,
            }

        total_frames = 0
        voiced_frames = 0

        for start in range(0, len(pcm16) - frame_size + 1, frame_size):
            frame = pcm16[start : start + frame_size]
            is_speech = self.vad.is_speech(frame.tobytes(), sample_rate=sr)
            total_frames += 1
            if is_speech:
                voiced_frames += 1

        if total_frames == 0:
            silence_ratio = 1.0
        else:
            silence_ratio = 1 - (voiced_frames / total_frames)

        return {
            "silence_ratio": round(float(silence_ratio), 6),
            "voiced_frames": voiced_frames,
            "total_frames": total_frames,
        }

    def _compute_speech_rate(self, transcript, duration_seconds):
        clean_text = re.sub(r"\s+", "", transcript or "")
        if duration_seconds <= 0:
            return 0.0
        chars_per_minute = (len(clean_text) / duration_seconds) * 60
        return round(float(chars_per_minute), 2)

    def _compute_confidence_score(
        self, filler_total, transcript, silence_ratio, rms_mean, rms_cv
    ):
        text_len = max(1, len(re.sub(r"\s+", "", transcript or "")))
        filler_density = filler_total / text_len

        filler_penalty = min(35.0, filler_density * 300)
        silence_penalty = min(35.0, max(0.0, silence_ratio - 0.20) * 100)

        # 音量稳定性与区间双重惩罚：波动越大、平均音量偏离正常区间越多，扣分越高
        target_rms = 0.08
        rms_range_penalty = min(15.0, abs(rms_mean - target_rms) * 180)
        rms_stability_penalty = min(15.0, rms_cv * 60)

        score = (
            100.0
            - filler_penalty
            - silence_penalty
            - rms_range_penalty
            - rms_stability_penalty
        )
        return round(max(0.0, min(100.0, score)), 2)

    def _compute_clarity_score(self, speech_rate, silence_ratio, rms_cv):
        if speech_rate <= 0:
            rate_score = 55.0
        else:
            # 常见中文口语舒适区约 150-220 字/分钟
            ideal = 185.0
            rate_score = max(0.0, 100.0 - abs(speech_rate - ideal) * 0.8)

        pause_score = max(0.0, 100.0 - silence_ratio * 100.0)
        stability_score = max(0.0, 100.0 - rms_cv * 90.0)

        clarity = 0.45 * rate_score + 0.30 * pause_score + 0.25 * stability_score
        return round(max(0.0, min(100.0, clarity)), 2)

    def _normalize_asr_confidence(self, asr_confidence):
        if asr_confidence is None:
            return 0.0
        return round(max(0.0, min(1.0, float(asr_confidence))), 6)

    def _compute_overall_clarity(self, audio_clarity_score, asr_confidence):
        if asr_confidence is None:
            return round(float(audio_clarity_score), 2)

        normalized_asr = self._normalize_asr_confidence(asr_confidence) * 100.0
        overall = 0.5 * float(audio_clarity_score) + 0.5 * normalized_asr
        return round(max(0.0, min(100.0, overall)), 2)


def mark_audio_analysis_failed(audio_obj, message):
    audio_obj.analysis_status = "failed"
    audio_obj.error_message = message
    audio_obj.save(update_fields=["analysis_status", "error_message", "updated_at"])
