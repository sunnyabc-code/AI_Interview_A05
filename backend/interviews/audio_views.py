import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
import tempfile
import wave
import uuid
from importlib import import_module

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.db import close_old_connections
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.asr_transcriber import ASRTranscriptionError, transcribe_audio_file
from core.response import APIResponse
from evaluations.audio_analysis import (
    AudioAnalysisError,
    AudioAnalysisService,
    mark_audio_analysis_failed,
)
from interviews.models import Interview, InterviewRound, InterviewRoundAudio
from interviews.serializers import (
    InterviewRoundAudioUploadRequestSerializer,
    InterviewRoundAudioUploadResponseSerializer,
)


_ASR_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="asr-worker")
_ANALYSIS_EXECUTOR = ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="analysis-worker"
)


def _run_async_transcription(audio_id: int, force_replace_answer: bool = False):
    # 后台线程单独管理数据库连接，避免复用已关闭连接。
    close_old_connections()
    try:
        audio_obj = InterviewRoundAudio.objects.select_related("round").get(id=audio_id)
    except InterviewRoundAudio.DoesNotExist:
        close_old_connections()
        return

    audio_obj.asr_status = "running"
    audio_obj.error_message = ""
    audio_obj.save(update_fields=["asr_status", "error_message", "updated_at"])

    try:
        transcript, _ = transcribe_audio_file(
            audio_obj.file_key,
            language=getattr(settings, "ASR_LANGUAGE", "zh"),
        )
    except ASRTranscriptionError as exc:
        audio_obj.asr_status = "failed"
        audio_obj.error_message = str(exc)
        audio_obj.save(update_fields=["asr_status", "error_message", "updated_at"])
        close_old_connections()
        return

    if not transcript:
        # 业务要求：空转写视为正常，不作为异常。
        audio_obj.asr_status = "success"
        audio_obj.error_message = ""
        audio_obj.save(update_fields=["asr_status", "error_message", "updated_at"])
        close_old_connections()
        return

    round_obj = audio_obj.round
    current_answer = (round_obj.user_answer or "").strip()
    should_replace_answer = force_replace_answer or (not current_answer or current_answer == "1")
    if should_replace_answer:
        round_obj.user_answer = transcript
        round_obj.save(update_fields=["user_answer"])

    audio_obj.asr_status = "success"
    audio_obj.error_message = ""
    audio_obj.save(update_fields=["asr_status", "error_message", "updated_at"])
    close_old_connections()


def _enqueue_local_asr(audio_id: int, force_replace_answer: bool = False):
    _ASR_EXECUTOR.submit(_run_async_transcription, audio_id, force_replace_answer)


def _resolve_ffmpeg_executable() -> str | None:
    """settings.FFMPEG_BINARY →可执行文件路径；可为目录（自动找 bin\\ffmpeg.exe）。"""
    raw = (getattr(settings, "FFMPEG_BINARY", None) or "").strip()
    if raw:
        p = os.path.normpath(os.path.expanduser(raw))
        if os.path.isfile(p):
            return p
        if os.path.isdir(p):
            for candidate in (
                os.path.join(p, "bin", "ffmpeg.exe"),
                os.path.join(p, "ffmpeg.exe"),
                os.path.join(p, "bin", "ffmpeg"),
                os.path.join(p, "ffmpeg"),
            ):
                if os.path.isfile(candidate):
                    return candidate
    return shutil.which("ffmpeg")


def _wav_duration_seconds(path: str) -> float:
    with wave.open(path, "rb") as wf:
        n = wf.getnframes()
        fr = wf.getframerate() or 1
        return float(n) / float(fr)


def _ffmpeg_pcm_wav(src: str, dest_wav: str, target_sr: int) -> None:
    exe = _resolve_ffmpeg_executable()
    if not exe:
        raise RuntimeError(
            "未找到 ffmpeg。请在 .env 设置 FFMPEG_BINARY=你的ffmpeg.exe路径，"
            "或将 ffmpeg 加入系统 PATH。"
        )
    cmd = [
        exe,
        "-y",
        "-i",
        src,
        "-ar",
        str(target_sr),
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        dest_wav,
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    completed = subprocess.run(
        cmd,
        capture_output=True,
        timeout=120,
        text=True,
        creationflags=creationflags,
    )
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()
        tail = err[-600:] if err else "无输出"
        raise RuntimeError(f"ffmpeg 失败: {tail}")


def _convert_uploaded_audio_to_wav(audio_file, round_id: int):
    """将上传音频统一转换为 wav，返回临时文件路径和元数据。"""
    temp_input_path = None
    temp_output_path = None

    try:
        temp_input = tempfile.NamedTemporaryFile(
            suffix=os.path.splitext(getattr(audio_file, "name", ""))[1] or ".audio",
            delete=False,
        )
        temp_input_path = temp_input.name
        with temp_input:
            for chunk in audio_file.chunks():
                temp_input.write(chunk)

        librosa = import_module("librosa")
        numpy = import_module("numpy")

        target_sr = int(getattr(settings, "AUDIO_CONVERT_TARGET_SR", 16000))
        librosa_err: Exception | None = None
        try:
            y, sr = librosa.load(temp_input_path, sr=target_sr, mono=True)
        except Exception as exc:
            librosa_err = exc
            y = None
            sr = None

        if y is not None:
            if len(y) == 0:
                raise ValueError("音频文件为空，无法转换为 WAV")

            y = numpy.clip(y, -1.0, 1.0)
            pcm16 = (y * 32767.0).astype(numpy.int16)

            temp_output = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_output_path = temp_output.name
            temp_output.close()

            with wave.open(temp_output_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(target_sr)
                wav_file.writeframes(pcm16.tobytes())

            duration_seconds = float(len(y) / sr) if sr else float(len(y) / target_sr)
        else:
            temp_output = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_output_path = temp_output.name
            temp_output.close()
            try:
                _ffmpeg_pcm_wav(temp_input_path, temp_output_path, target_sr)
            except Exception as ff_exc:
                raise ValueError(
                    f"无法将音频转换为 WAV。librosa: {librosa_err!s}；{ff_exc!s}"
                ) from ff_exc
            try:
                duration_seconds = _wav_duration_seconds(temp_output_path)
            except OSError:
                duration_seconds = 0.0

        original_name = os.path.splitext(os.path.basename(getattr(audio_file, "name", "")))[0].strip()
        if not original_name:
            original_name = f"round_{round_id}"

        return {
            "wav_path": temp_output_path,
            "file_name": f"{original_name}.wav",
            "mime_type": "audio/wav",
            "codec": "pcm_s16le",
            "sample_rate": target_sr,
            "channels": 1,
            "duration_seconds": duration_seconds,
        }
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"无法将音频转换为 WAV: {exc}") from exc
    finally:
        try:
            if temp_input_path and os.path.exists(temp_input_path):
                os.remove(temp_input_path)
        except OSError:
            pass


def _cleanup_temp_file(file_path: str | None):
    if not file_path:
        return
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass


def _run_async_voice_analysis(audio_id: int):
    # 后台线程单独管理数据库连接，避免复用已关闭连接。
    close_old_connections()
    try:
        audio_obj = InterviewRoundAudio.objects.select_related("round").get(id=audio_id)
    except InterviewRoundAudio.DoesNotExist:
        close_old_connections()
        return

    audio_obj.analysis_status = "running"
    audio_obj.error_message = ""
    audio_obj.save(update_fields=["analysis_status", "error_message", "updated_at"])

    transcript = (audio_obj.round.user_answer or "").strip()
    service = AudioAnalysisService(vad_mode=2)

    try:
        service.analyze_and_save(audio_obj, transcript=transcript)
    except AudioAnalysisError as exc:
        mark_audio_analysis_failed(audio_obj, str(exc))
    except Exception as exc:
        mark_audio_analysis_failed(audio_obj, str(exc))
    finally:
        close_old_connections()


def _enqueue_local_voice_analysis(audio_id: int):
    _ANALYSIS_EXECUTOR.submit(_run_async_voice_analysis, audio_id)

def _enqueue_imentiv_analysis(audio_id):
    from evaluations.tasks import analyze_imentiv_audio_task

    analyze_imentiv_audio_task.delay(audio_id)


class InterviewRoundAudioUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _get_user_interview(self, user, interview_id):
        return Interview.objects.filter(id=interview_id, user=user).first()

    def _build_audio_response(self, interview, round_obj, audio_obj):
        return {
            "audio_id": audio_obj.id,
            "interview_id": interview.id,
            "round_id": round_obj.id,
            "file_name": audio_obj.file_name,
            "file_key": audio_obj.file_key,
            "file_url": audio_obj.file_url,
            "mime_type": audio_obj.mime_type,
            "file_size_bytes": audio_obj.file_size_bytes,
            "duration_seconds": audio_obj.duration_seconds,
            "codec": audio_obj.codec,
            "sample_rate": audio_obj.sample_rate,
            "channels": audio_obj.channels,
            "upload_status": audio_obj.upload_status,
            "asr_status": audio_obj.asr_status,
            "analysis_status": audio_obj.analysis_status,
            "imentiv_analysis_status": audio_obj.imentiv_analysis_status,
            "imentiv_error_message": audio_obj.imentiv_error_message,
            "transcript": (round_obj.user_answer or "").strip(),
            "created_at": audio_obj.created_at,
            "updated_at": audio_obj.updated_at,
        }

    @swagger_auto_schema(
        tags=["Interview"],
        operation_summary="获取单轮音频详情",
        operation_description="获取指定面试轮次的音频详情（轮次与音频一对一）",
        security=[{"Bearer": []}],
        responses={
            200: openapi.Response(
                "获取成功", InterviewRoundAudioUploadResponseSerializer
            ),
            401: openapi.Response("未登录"),
            404: openapi.Response("面试、轮次或音频不存在"),
        },
    )
    def get(self, request, interview_id, round_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message="面试记录不存在", code=404)

        round_obj = InterviewRound.objects.filter(
            id=round_id, interview=interview
        ).first()
        if not round_obj:
            return APIResponse.error(message="轮次不存在", code=404)

        audio_obj = getattr(round_obj, "audio", None)
        if not audio_obj:
            return APIResponse.error(message="该轮次暂无音频", code=404)

        return APIResponse.success(
            data=self._build_audio_response(interview, round_obj, audio_obj),
            message="获取音频详情成功",
            code=200,
        )

    @swagger_auto_schema(
        tags=["Interview"],
        operation_summary="上传轮次音频",
        operation_description="为指定面试轮次上传或覆盖一条音频记录（轮次与音频一对一）",
        request_body=InterviewRoundAudioUploadRequestSerializer,
        consumes=["multipart/form-data"],
        manual_parameters=[
            openapi.Parameter(
                name="audio_file",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="音频文件",
            ),
        ],
        security=[{"Bearer": []}],
        responses={
            201: openapi.Response(
                "上传成功", InterviewRoundAudioUploadResponseSerializer
            ),
            200: openapi.Response(
                "覆盖成功", InterviewRoundAudioUploadResponseSerializer
            ),
            400: openapi.Response("参数错误"),
            401: openapi.Response("未登录"),
            404: openapi.Response("面试或轮次不存在"),
        },
    )
    def post(self, request, interview_id, round_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message="面试记录不存在", code=404)

        round_obj = InterviewRound.objects.filter(
            id=round_id, interview=interview
        ).first()
        if not round_obj:
            return APIResponse.error(message="轮次不存在", code=404)

        serializer = InterviewRoundAudioUploadRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="参数错误", code=400, errors=serializer.errors
            )

        audio_file = serializer.validated_data["audio_file"]
        mime_type = getattr(audio_file, "content_type", "") or ""
        if mime_type and not mime_type.startswith("audio/"):
            return APIResponse.error(message="仅支持音频文件上传", code=400)

        max_bytes = getattr(settings, "AUDIO_UPLOAD_MAX_BYTES", 20 * 1024 * 1024)
        if audio_file.size > max_bytes:
            return APIResponse.error(
                message=f"文件大小不能超过 {max_bytes // (1024 * 1024)}MB",
                code=400,
            )

        try:
            converted_audio = _convert_uploaded_audio_to_wav(audio_file, round_obj.id)
        except ValueError as exc:
            return APIResponse.error(message=str(exc), code=400)

        file_key = (
            f"interview_audio/user_{request.user.id}/"
            f"interview_{interview.id}/round_{round_obj.id}/{uuid.uuid4().hex}.wav"
        )

        try:
            with open(converted_audio["wav_path"], "rb") as converted_fp:
                saved_key = default_storage.save(file_key, File(converted_fp))
            relative_url = default_storage.url(saved_key)
            file_url = request.build_absolute_uri(relative_url)
            converted_file_size = os.path.getsize(converted_audio["wav_path"])
        except Exception as exc:
            _cleanup_temp_file(converted_audio.get("wav_path"))
            return APIResponse.error(
                message="上传失败", code=500, errors={"detail": str(exc)}
            )
        finally:
            _cleanup_temp_file(converted_audio.get("wav_path"))

        existing_audio = getattr(round_obj, "audio", None)
        if (
            existing_audio
            and existing_audio.file_key
            and existing_audio.file_key != saved_key
        ):
            try:
                if default_storage.exists(existing_audio.file_key):
                    default_storage.delete(existing_audio.file_key)
            except Exception:
                # 删除历史文件失败不影响本次上传成功
                pass

        payload = {
            "uploaded_by": request.user,
            "file_url": file_url,
            "file_key": saved_key,
            "file_name": converted_audio["file_name"],
            "mime_type": converted_audio["mime_type"],
            "codec": converted_audio["codec"],
            "sample_rate": converted_audio["sample_rate"],
            "channels": converted_audio["channels"],
            "file_size_bytes": converted_file_size,
            "duration_seconds": serializer.validated_data.get("duration_seconds")
            or converted_audio["duration_seconds"],
            "upload_status": "uploaded",
            "asr_status": "pending",
            "analysis_status": "pending",
            "imentiv_analysis_status": "pending",
            "error_message": "",
            "imentiv_error_message": "",
        }

        if existing_audio:
            for field, value in payload.items():
                setattr(existing_audio, field, value)
            existing_audio.save()
            audio_obj = existing_audio
            status_code = 200
            message = "音频已覆盖上传"
        else:
            audio_obj = InterviewRoundAudio.objects.create(round=round_obj, **payload)
            status_code = 201
            message = "音频上传成功"

        warning_messages = []

        try:
            _enqueue_local_voice_analysis(audio_obj.id)
        except Exception as exc:
            # 兜底策略：线程池投递失败时同步执行一次分析，避免状态长期停留 pending。
            warning_messages.append(f"本地语音分析异步任务投递失败，已降级为同步分析: {exc}")
            _run_async_voice_analysis(audio_obj.id)

        try:
            _enqueue_imentiv_analysis(audio_obj.id)
        except Exception as exc:
            audio_obj.imentiv_analysis_status = "failed"
            audio_obj.imentiv_error_message = f"任务投递失败: {exc}"
            audio_obj.save(
                update_fields=[
                    "imentiv_analysis_status",
                    "imentiv_error_message",
                    "updated_at",
                ]
            )
            warning_messages.append("iMentiv任务投递失败")

        try:
            _enqueue_local_asr(audio_obj.id, force_replace_answer=bool(existing_audio))
        except Exception as exc:
            # 兜底策略：线程池投递失败时同步执行一次转写，避免前端因为500中断流程。
            warning_messages.append(f"ASR异步任务投递失败，已降级为同步转写: {exc}")
            _run_async_transcription(audio_obj.id, force_replace_answer=bool(existing_audio))

        response_message = f"{message}，转写处理中"
        if warning_messages:
            response_message = f"{message}，{'; '.join(warning_messages)}"

        return APIResponse.success(
            data=self._build_audio_response(interview, round_obj, audio_obj),
            message=response_message,
            code=status_code,
        )

    @swagger_auto_schema(
        tags=["Interview"],
        operation_summary="删除单轮音频",
        operation_description="删除指定面试轮次的音频记录，并尝试删除存储中的文件",
        security=[{"Bearer": []}],
        responses={
            200: openapi.Response("删除成功"),
            401: openapi.Response("未登录"),
            404: openapi.Response("面试、轮次或音频不存在"),
        },
    )
    def delete(self, request, interview_id, round_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message="面试记录不存在", code=404)

        round_obj = InterviewRound.objects.filter(
            id=round_id, interview=interview
        ).first()
        if not round_obj:
            return APIResponse.error(message="轮次不存在", code=404)

        audio_obj = getattr(round_obj, "audio", None)
        if not audio_obj:
            return APIResponse.error(message="该轮次暂无音频可删除", code=404)

        file_key = audio_obj.file_key
        audio_id = audio_obj.id
        audio_obj.delete()

        if file_key:
            try:
                if default_storage.exists(file_key):
                    default_storage.delete(file_key)
            except Exception:
                # 存储文件删除失败不影响数据库删除结果
                pass

        return APIResponse.success(
            data={
                "audio_id": audio_id,
                "interview_id": interview.id,
                "round_id": round_obj.id,
            },
            message="音频删除成功",
            code=200,
        )
