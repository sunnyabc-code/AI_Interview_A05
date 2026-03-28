import os
import sys
import tempfile
import threading
import time
import wave
from importlib import import_module
from typing import Optional, Tuple

from django.conf import settings
from django.core.files.storage import default_storage


class ASRTranscriptionError(Exception):
    """Raised when local ASR transcription fails."""


_FW_MODEL = None
_FW_MODEL_LOCK = threading.Lock()
_FW_MODEL_SIGNATURE = None
_OPENCC_CONVERTER = None
_OPENCC_LOCK = threading.Lock()


def _get_opencc_converter():
    global _OPENCC_CONVERTER
    if _OPENCC_CONVERTER is not None:
        return _OPENCC_CONVERTER

    with _OPENCC_LOCK:
        if _OPENCC_CONVERTER is None:
            module = import_module("opencc")
            OpenCC = getattr(module, "OpenCC")
            _OPENCC_CONVERTER = OpenCC("t2s")

    return _OPENCC_CONVERTER


def _normalize_chinese_text(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    force_simplified = bool(getattr(settings, "ASR_FORCE_SIMPLIFIED", True))
    if not force_simplified:
        return cleaned

    try:
        converter = _get_opencc_converter()
        return converter.convert(cleaned).strip()
    except Exception:
        # 转换失败时保留原始转写，避免影响主流程。
        return cleaned


def _preprocess_audio_for_asr(input_path: str) -> str:
    """
    语音前处理（尽量突出人声、抑制背景噪声）。
    返回处理后文件路径；若处理失败则返回原路径。
    """
    enabled = bool(getattr(settings, "ASR_PREPROCESS_ENABLED", True))
    if not enabled:
        return input_path

    try:
        np = import_module("numpy")
        librosa = import_module("librosa")
        signal = import_module("scipy.signal")
    except Exception:
        return input_path

    target_sr = int(getattr(settings, "ASR_TARGET_SR", 16000))
    trim_top_db = float(getattr(settings, "ASR_TRIM_TOP_DB", 30.0))
    noise_reduce_strength = float(getattr(settings, "ASR_NOISE_REDUCE_STRENGTH", 1.4))

    try:
        y, sr = librosa.load(input_path, sr=target_sr, mono=True)
        if y is None or len(y) == 0:
            return input_path

        # 去头尾静音，减少无效片段对识别的干扰。
        y_trimmed, _ = librosa.effects.trim(y, top_db=trim_top_db)
        if y_trimmed is not None and len(y_trimmed) > 0:
            y = y_trimmed

        # 去直流分量。
        y = y - float(np.mean(y))

        # 人声带通滤波：约 80Hz-7.6kHz。
        nyq = 0.5 * target_sr
        low = max(1.0, 80.0) / nyq
        high = min(7600.0, nyq * 0.98) / nyq
        if 0 < low < high < 1:
            b, a = signal.butter(4, [low, high], btype="band")
            y = signal.filtfilt(b, a, y)

        # 频谱降噪：估计噪声底并做软掩码抑制。
        n_fft = 512
        hop_length = 128
        stft = librosa.stft(y, n_fft=n_fft, hop_length=hop_length, win_length=n_fft)
        mag = np.abs(stft)
        phase = np.angle(stft)

        noise_profile = np.percentile(mag, 20, axis=1, keepdims=True)
        reduced = np.maximum(mag - noise_reduce_strength * noise_profile, 0.0)
        mask = np.clip(reduced / (mag + 1e-8), 0.0, 1.0) ** 1.1
        y = librosa.istft(mask * mag * np.exp(1j * phase), hop_length=hop_length, win_length=n_fft, length=len(y))

        # 预加重提升清晰度。
        y = librosa.effects.preemphasis(y, coef=0.97)

        # 音量归一化，避免过小或过大。
        rms = float(np.sqrt(np.mean(y**2) + 1e-12))
        target_rms = float(getattr(settings, "ASR_TARGET_RMS", 0.08))
        if rms > 0:
            gain = target_rms / rms
            gain = max(0.5, min(6.0, gain))
            y = y * gain
        y = np.clip(y, -1.0, 1.0)

        # 写入 16-bit PCM WAV，兼容性更好。
        fd, out_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        pcm16 = (y * 32767.0).astype(np.int16)
        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(target_sr)
            wf.writeframes(pcm16.tobytes())

        return out_path
    except Exception:
        return input_path


def _get_faster_whisper_model():
    global _FW_MODEL, _FW_MODEL_SIGNATURE

    model_size = str(getattr(settings, "ASR_MODEL_SIZE", "base"))
    device = str(getattr(settings, "ASR_DEVICE", "cpu"))
    compute_type = str(getattr(settings, "ASR_COMPUTE_TYPE", "int8"))
    signature = (model_size, device, compute_type)

    if _FW_MODEL is not None and _FW_MODEL_SIGNATURE == signature:
        return _FW_MODEL

    with _FW_MODEL_LOCK:
        if _FW_MODEL is None or _FW_MODEL_SIGNATURE != signature:
            module = import_module("faster_whisper")
            WhisperModel = getattr(module, "WhisperModel")
            # 复用单例模型，避免每次请求频繁创建线程池导致不稳定。
            _FW_MODEL = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                num_workers=1,
            )
            _FW_MODEL_SIGNATURE = signature
    return _FW_MODEL


def _transcribe_with_faster_whisper(file_path: str, language: str) -> Tuple[str, Optional[float]]:
    global _FW_MODEL, _FW_MODEL_SIGNATURE

    last_exc = None
    for attempt in range(2):
        if sys.is_finalizing():
            raise ASRTranscriptionError("Python 解释器正在退出，无法执行转写")

        try:
            model = _get_faster_whisper_model()
            beam_size = int(getattr(settings, "ASR_BEAM_SIZE", 5))
            segments, info = model.transcribe(
                file_path,
                language=language or "zh",
                beam_size=max(1, beam_size),
                temperature=0,
                vad_filter=True,
            )
            text = " ".join((seg.text or "").strip() for seg in segments).strip()
            text = _normalize_chinese_text(text)
            confidence = None
            if getattr(info, "language_probability", None) is not None:
                confidence = float(info.language_probability)
            return text, confidence
        except RuntimeError as exc:
            message = str(exc).lower()
            if "cannot schedule new futures after interpreter shutdown" not in message:
                raise

            # 进程热重载或线程池异常时，重建模型并重试一次。
            last_exc = exc
            with _FW_MODEL_LOCK:
                _FW_MODEL = None
                _FW_MODEL_SIGNATURE = None
            if attempt == 0:
                time.sleep(0.2)
                continue
            raise ASRTranscriptionError(
                "faster-whisper 线程池不可用（可能是服务热重载中），请重试请求"
            ) from exc

    if last_exc is not None:
        raise ASRTranscriptionError(f"faster-whisper 转写失败: {last_exc}") from last_exc
    raise ASRTranscriptionError("faster-whisper 转写失败")


def _transcribe_with_whisper(file_path: str, language: str) -> Tuple[str, Optional[float]]:
    whisper = import_module("whisper")

    model_size = str(getattr(settings, "ASR_MODEL_SIZE", "base"))
    beam_size = int(getattr(settings, "ASR_BEAM_SIZE", 5))
    model = whisper.load_model(model_size)
    result = model.transcribe(
        file_path,
        language=language or "zh",
        beam_size=max(1, beam_size),
        temperature=0,
    )
    text = (result.get("text") or "").strip()
    text = _normalize_chinese_text(text)

    confidence = None
    segments = result.get("segments") or []
    if segments:
        probs = []
        for seg in segments:
            try:
                # avg_logprob is log(p), convert to p and clamp.
                p = float(seg.get("avg_logprob", 0.0))
                probs.append(max(0.0, min(1.0, pow(2.718281828, p))))
            except Exception:
                continue
        if probs:
            confidence = sum(probs) / len(probs)

    return text, confidence


def transcribe_audio_file(file_key: str, language: str = "zh") -> Tuple[str, Optional[float]]:
    if not file_key:
        raise ASRTranscriptionError("音频文件标识为空")

    if not default_storage.exists(file_key):
        raise ASRTranscriptionError("音频文件不存在或已被删除")

    with default_storage.open(file_key, "rb") as fp:
        raw = fp.read()

    if not raw:
        raise ASRTranscriptionError("音频文件为空，无法转写")

    fd, tmp_path = tempfile.mkstemp(suffix=".audio")
    processed_path = None
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(raw)
            tmp.flush()

        processed_path = _preprocess_audio_for_asr(tmp_path)
        asr_input_path = processed_path or tmp_path

        try:
            return _transcribe_with_faster_whisper(asr_input_path, language)
        except ModuleNotFoundError:
            pass
        except Exception as exc:
            raise ASRTranscriptionError(f"faster-whisper 转写失败: {exc}") from exc

        try:
            return _transcribe_with_whisper(asr_input_path, language)
        except ModuleNotFoundError:
            pass
        except Exception as exc:
            raise ASRTranscriptionError(f"whisper 转写失败: {exc}") from exc
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        try:
            if processed_path and processed_path != tmp_path and os.path.exists(processed_path):
                os.remove(processed_path)
        except OSError:
            pass

    raise ASRTranscriptionError(
        "未安装可用的本地转写库，请安装 faster-whisper 或 openai-whisper"
    )
