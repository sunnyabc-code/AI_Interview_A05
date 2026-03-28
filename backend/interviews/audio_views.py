import os
from concurrent.futures import ThreadPoolExecutor
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import close_old_connections
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.asr_transcriber import ASRTranscriptionError, transcribe_audio_file
from core.response import APIResponse
from interviews.models import Interview, InterviewRound, InterviewRoundAudio
from interviews.serializers import (
    InterviewRoundAudioUploadRequestSerializer,
    InterviewRoundAudioUploadResponseSerializer,
)


_ASR_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="asr-worker")


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

        file_ext = os.path.splitext(audio_file.name)[1] or ".bin"
        file_key = (
            f"interview_audio/user_{request.user.id}/"
            f"interview_{interview.id}/round_{round_obj.id}/{uuid.uuid4().hex}{file_ext}"
        )

        try:
            saved_key = default_storage.save(file_key, audio_file)
            relative_url = default_storage.url(saved_key)
            file_url = request.build_absolute_uri(relative_url)
        except Exception as exc:
            return APIResponse.error(
                message="上传失败", code=500, errors={"detail": str(exc)}
            )

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
            "file_name": audio_file.name or "",
            "mime_type": mime_type,
            "codec": serializer.validated_data.get("codec", ""),
            "sample_rate": serializer.validated_data.get("sample_rate"),
            "channels": serializer.validated_data.get("channels"),
            "file_size_bytes": audio_file.size,
            "duration_seconds": serializer.validated_data.get("duration_seconds"),
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

        try:
            _enqueue_imentiv_analysis(audio_obj.id)
            _enqueue_local_asr(audio_obj.id, force_replace_answer=bool(existing_audio))
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
            audio_obj.asr_status = "failed"
            audio_obj.error_message = f"转写任务启动失败: {exc}"
            audio_obj.save(update_fields=["asr_status", "error_message", "updated_at"])
            return APIResponse.error(
                message="音频上传成功，但转写任务启动失败",
                code=500,
                errors={"detail": str(exc), "audio_id": audio_obj.id},
            )

        return APIResponse.success(
            data=self._build_audio_response(interview, round_obj, audio_obj),
            message=f"{message}，转写处理中",
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
