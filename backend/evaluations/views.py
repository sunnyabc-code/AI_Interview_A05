from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction

from core.response import APIResponse
from evaluations.models import DifficultyConfig, VoiceAnalysis, VoiceLLMResult
from interviews.models import Interview, InterviewRoundAudio, InterviewRound
from evaluations.tasks import analyze_imentiv_audio_task

from evaluations.audio_analysis import (
    AudioAnalysisError,
    AudioAnalysisService,
    mark_audio_analysis_failed,
)


class InterviewVoiceLLMResultView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Evaluation"],
        operation_summary="获取面试音频大模型总结",
        operation_description="根据 interview_id 获取该场面试的音频大模型总结结果。",
        security=[{"Bearer": []}],
        responses={200: openapi.Response("查询成功")},
    )
    def get(self, request, interview_id):
        interview = Interview.objects.filter(id=interview_id, user=request.user).first()
        if not interview:
            return APIResponse.error(message="面试不存在或无权限", code=404)

        result = VoiceLLMResult.objects.filter(interview_id=interview_id).first()
        if not result:
            return APIResponse.success(
                data={"interview_id": interview_id, "voice_llm_result": None},
                message="该面试尚未生成音频大模型总结",
                code=200,
            )

        return APIResponse.success(
            data={
                "interview_id": interview_id,
                "voice_llm_result": {
                    "id": result.id,
                    "status": result.status,
                    "overall_audio_score": result.overall_audio_score,
                    "speech_rate_and_rhythm_score": result.speech_rate_and_rhythm_score,
                    "speech_rate_and_rhythm": result.speech_rate_and_rhythm,
                    "fluency_score": result.fluency_score,
                    "fluency": result.fluency,
                    "confidence_and_voice_energy_score": result.confidence_and_voice_energy_score,
                    "confidence_and_voice_energy": result.confidence_and_voice_energy,
                    "emotional_stability_and_tone_score": result.emotional_stability_and_tone_score,
                    "emotional_stability_and_tone": result.emotional_stability_and_tone,
                    "strengths": result.strengths,
                    "improvements": result.improvements,
                    "position_communication_tips": result.position_communication_tips,
                    "encouragement": result.encouragement,
                    "llm_model": result.llm_model,
                    "prompt_version": result.prompt_version,
                    "generated_at": result.generated_at,
                    "error_message": result.error_message,
                    "retry_count": result.retry_count,
                    "created_at": result.created_at,
                    "updated_at": result.updated_at,
                },
            },
            message="查询成功",
            code=200,
        )


class InterviewVoiceLLMResultRunView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Evaluation"],
        operation_summary="手动触发面试音频大模型总结",
        operation_description="根据 interview_id 手动触发 voice_llm_result 生成，支持 force 重算。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "force": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="是否强制重算（true 时即使已有成功结果也会重算）",
                    default=False,
                ),
            },
        ),
        security=[{"Bearer": []}],
        responses={200: openapi.Response("触发成功")},
    )
    def post(self, request, interview_id):
        interview = Interview.objects.filter(id=interview_id, user=request.user).first()
        if not interview:
            return APIResponse.error(message="面试不存在或无权限", code=404)

        force = bool(request.data.get("force", False))
        existing = VoiceLLMResult.objects.filter(interview_id=interview_id).first()

        if existing and existing.status == "running":
            return APIResponse.error(message="该面试的音频总结正在生成中", code=409)

        if existing and existing.status == "success" and not force:
            return APIResponse.success(
                data={
                    "interview_id": interview_id,
                    "voice_llm_result_id": existing.id,
                    "status": existing.status,
                },
                message="已存在成功结果；如需重算请传 force=true",
                code=200,
            )

        try:
            from evaluations.voice_llm_result_service import (
                try_generate_interview_voice_llm_result_when_ready,
            )

            result, waiting_reason = try_generate_interview_voice_llm_result_when_ready(
                interview_id
            )
            if not result:
                return APIResponse.success(
                    data={
                        "interview_id": interview_id,
                        "voice_llm_result_id": None,
                        "status": "pending",
                        "waiting_reason": waiting_reason or "结果等待生成",
                    },
                    message="音频大模型总结等待生成",
                    code=202,
                )
        except Exception as exc:  # noqa: BLE001
            return APIResponse.error(
                message="音频大模型总结生成失败",
                code=500,
                errors={"detail": str(exc)},
            )

        return APIResponse.success(
            data={
                "interview_id": interview_id,
                "voice_llm_result_id": result.id,
                "status": result.status,
                "generated_at": result.generated_at,
            },
            message="音频大模型总结生成成功",
            code=200,
        )


class DifficultyConfigListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Evaluation"],
        operation_summary="难度配置列表",
        operation_description="获取所有难度配置列表",
        security=[{"Bearer": []}],
        responses={200: openapi.Response("获取成功")},
    )
    def get(self, request):
        configs = DifficultyConfig.objects.all().order_by("id")
        data = []
        for config in configs:
            data.append(
                {
                    "id": config.id,
                    "difficulty_code": config.difficulty_code,
                    "difficulty_name": config.difficulty_name,
                    "answer_time_seconds": config.answer_time_seconds,
                    "technical_chain_count": config.technical_chain_count,
                    "project_chain_count": config.project_chain_count,
                    "scenario_chain_count": config.scenario_chain_count,
                    "technical_max_followup_depth": config.technical_max_followup_depth,
                    "project_max_followup_depth": config.project_max_followup_depth,
                    "scenario_max_followup_depth": config.scenario_max_followup_depth,
                    "created_at": config.created_at,
                    "updated_at": config.updated_at,
                }
            )
        return APIResponse.success(data=data, message="获取成功", code=200)


class VoiceAnalysisRunView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Evaluation"],
        operation_summary="执行语音分析",
        operation_description="基于 InterviewRoundAudio 音频执行语速与自信度分析（填充词、RMS、停顿占比）并写入 VoiceAnalysis。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["audio_id"],
            properties={
                "audio_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="音频ID（interview_round_audios.id）",
                ),
                "transcript": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ASR转写文本，可选；为空时默认使用轮次 user_answer",
                ),
            },
        ),
        security=[{"Bearer": []}],
        responses={200: openapi.Response("分析成功")},
    )
    def post(self, request):
        audio_id = request.data.get("audio_id")
        transcript = (request.data.get("transcript") or "").strip()

        if not audio_id:
            return APIResponse.error(message="audio_id 不能为空", code=400)

        try:
            audio_obj = InterviewRoundAudio.objects.select_related(
                "round__interview"
            ).get(
                id=audio_id,
                round__interview__user=request.user,
            )
        except InterviewRoundAudio.DoesNotExist:
            return APIResponse.error(message="音频不存在或无权限", code=404)

        if not transcript:
            transcript = (audio_obj.round.user_answer or "").strip()

        service = AudioAnalysisService(vad_mode=2)

        try:
            with transaction.atomic():
                audio_obj.analysis_status = "running"
                audio_obj.error_message = ""
                audio_obj.save(
                    update_fields=["analysis_status", "error_message", "updated_at"]
                )

            voice_analysis = service.analyze_and_save(
                audio_obj,
                transcript=transcript,
            )
        except AudioAnalysisError as exc:
            mark_audio_analysis_failed(audio_obj, str(exc))
            return APIResponse.error(
                message="语音分析失败", code=400, errors={"detail": str(exc)}
            )
        except Exception as exc:
            mark_audio_analysis_failed(audio_obj, str(exc))
            return APIResponse.error(
                message="语音分析失败", code=500, errors={"detail": str(exc)}
            )

        return APIResponse.success(
            data={
                "voice_analysis_id": voice_analysis.id,
                "audio_id": audio_obj.id,
                "round_id": audio_obj.round_id,
                "duration_seconds": voice_analysis.duration_seconds,
                "speech_rate": voice_analysis.speech_rate,
                "audio_clarity_score": voice_analysis.audio_clarity_score,
                "confidence_score": voice_analysis.confidence_score,
                "filler_word_total": voice_analysis.filler_word_total,
                "filler_word_counts": voice_analysis.filler_word_counts,
                "rms_mean": voice_analysis.rms_mean,
                "rms_std": voice_analysis.rms_std,
                "rms_cv": voice_analysis.rms_cv,
                "silence_ratio": voice_analysis.silence_ratio,
                "voiced_frames": voice_analysis.voiced_frames,
                "total_frames": voice_analysis.total_frames,
                "analysis_status": audio_obj.analysis_status,
            },
            message="语音分析成功",
            code=200,
        )


class ImentivAnalysisRunView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Evaluation"],
        operation_summary="触发 iMentiv 情感分析任务",
        operation_description="按 audio_id 触发 iMentiv 异步情感分析（Celery）。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["audio_id"],
            properties={
                "audio_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="音频ID（interview_round_audios.id）",
                ),
                "force": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="是否强制重跑（true 时将状态重置为 pending）",
                    default=False,
                ),
            },
        ),
        security=[{"Bearer": []}],
        responses={200: openapi.Response("任务已投递")},
    )
    def post(self, request):
        audio_id = request.data.get("audio_id")
        force = bool(request.data.get("force", False))

        if not audio_id:
            return APIResponse.error(message="audio_id 不能为空", code=400)

        try:
            audio_obj = InterviewRoundAudio.objects.select_related(
                "round__interview"
            ).get(
                id=audio_id,
                round__interview__user=request.user,
            )
        except InterviewRoundAudio.DoesNotExist:
            return APIResponse.error(message="音频不存在或无权限", code=404)

        if audio_obj.imentiv_analysis_status == "running" and not force:
            return APIResponse.error(message="iMentiv 分析任务正在执行中", code=409)

        if force:
            audio_obj.imentiv_analysis_status = "pending"
            audio_obj.imentiv_error_message = ""
            audio_obj.save(
                update_fields=[
                    "imentiv_analysis_status",
                    "imentiv_error_message",
                    "updated_at",
                ]
            )

        try:
            task = analyze_imentiv_audio_task.delay(audio_obj.id)
        except Exception as exc:  # noqa: BLE001
            audio_obj.imentiv_analysis_status = "failed"
            audio_obj.imentiv_error_message = f"任务投递失败: {exc}"
            audio_obj.save(
                update_fields=[
                    "imentiv_analysis_status",
                    "imentiv_error_message",
                    "updated_at",
                ]
            )
            return APIResponse.error(
                message="iMentiv 分析任务投递失败",
                code=503,
                errors={"detail": str(exc)},
            )

        return APIResponse.success(
            data={
                "audio_id": audio_obj.id,
                "round_id": audio_obj.round_id,
                "imentiv_analysis_status": audio_obj.imentiv_analysis_status,
                "task_id": task.id,
            },
            message="iMentiv 分析任务已投递",
            code=200,
        )


class ImentivAnalysisStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Evaluation"],
        operation_summary="查询 iMentiv 情感分析状态",
        operation_description="根据 audio_id 查询 iMentiv 分析状态与结果。",
        security=[{"Bearer": []}],
        responses={200: openapi.Response("查询成功")},
    )
    def get(self, request, audio_id):
        try:
            audio_obj = InterviewRoundAudio.objects.select_related(
                "round__interview", "voice_analysis"
            ).get(
                id=audio_id,
                round__interview__user=request.user,
            )
        except InterviewRoundAudio.DoesNotExist:
            return APIResponse.error(message="音频不存在或无权限", code=404)

        voice_analysis = getattr(audio_obj, "voice_analysis", None)
        return APIResponse.success(
            data={
                "audio_id": audio_obj.id,
                "round_id": audio_obj.round_id,
                "interview_id": audio_obj.round.interview_id,
                "analysis_status": audio_obj.analysis_status,
                "error_message": audio_obj.error_message,
                "imentiv_analysis_status": audio_obj.imentiv_analysis_status,
                "imentiv_error_message": audio_obj.imentiv_error_message,
                "voice_analysis_id": voice_analysis.id if voice_analysis else None,
                "emotion": voice_analysis.emotion if voice_analysis else "",
                "imentiv_status": (
                    voice_analysis.imentiv_status if voice_analysis else ""
                ),
                "imentiv_emotion_analysis": (
                    voice_analysis.imentiv_emotion_analysis if voice_analysis else {}
                ),
                "updated_at": audio_obj.updated_at,
            },
            message="查询成功",
            code=200,
        )


class RoundAudioAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Evaluation"],
        operation_summary="获取轮次音频分析结果",
        operation_description="根据轮次ID获取该轮的音频分析结果，包括语音分析和情感分析。",
        security=[{"Bearer": []}],
        responses={200: openapi.Response("查询成功")},
    )
    def get(self, request, round_id):
        try:
            round_obj = InterviewRound.objects.select_related("interview").get(
                id=round_id,
                interview__user=request.user,
            )
        except InterviewRound.DoesNotExist:
            return APIResponse.error(message="轮次不存在或无权限", code=404)

        # 获取该轮次的音频
        try:
            audio = InterviewRoundAudio.objects.select_related("voice_analysis").get(
                round_id=round_id
            )
        except InterviewRoundAudio.DoesNotExist:
            return APIResponse.success(
                data={
                    "round_id": round_obj.id,
                    "interview_id": round_obj.interview_id,
                    "round_number": round_obj.round_number,
                    "category": round_obj.category.name if round_obj.category else None,
                    "question_content": round_obj.question_content,
                    "user_answer": round_obj.user_answer,
                    "audio_data": None,
                },
                message="轮次音频不存在",
                code=200,
            )

        voice_analysis = getattr(audio, "voice_analysis", None)

        audio_data = {
            "audio_id": audio.id,
            "file_url": audio.file_url,
            "file_name": audio.file_name,
            "file_size_bytes": audio.file_size_bytes,
            "duration_seconds": audio.duration_seconds,
            "upload_status": audio.upload_status,
            "asr_status": audio.asr_status,
            "analysis_status": audio.analysis_status,
            "error_message": audio.error_message,
            "imentiv_analysis_status": audio.imentiv_analysis_status,
            "imentiv_error_message": audio.imentiv_error_message,
            "voice_analysis": None,
        }

        if voice_analysis:
            audio_data["voice_analysis"] = {
                "voice_analysis_id": voice_analysis.id,
                "duration_seconds": voice_analysis.duration_seconds,
                "speech_rate": voice_analysis.speech_rate,
                "speech_rate_level": voice_analysis.speech_rate_level,
                "audio_clarity_score": voice_analysis.audio_clarity_score,
                "confidence_score": voice_analysis.confidence_score,
                "emotion": voice_analysis.emotion,
                "imentiv_status": voice_analysis.imentiv_status,
                "imentiv_emotion_analysis": voice_analysis.imentiv_emotion_analysis,
                "filler_word_total": voice_analysis.filler_word_total,
                "filler_word_counts": voice_analysis.filler_word_counts,
                "rms_mean": voice_analysis.rms_mean,
                "rms_std": voice_analysis.rms_std,
                "rms_cv": voice_analysis.rms_cv,
                "silence_ratio": voice_analysis.silence_ratio,
                "silence_ratio_level": voice_analysis.silence_ratio_level,
                "voiced_frames": voice_analysis.voiced_frames,
                "total_frames": voice_analysis.total_frames,
                "created_at": voice_analysis.created_at,
                "updated_at": voice_analysis.updated_at,
            }

        round_data = {
            "round_id": round_obj.id,
            "interview_id": round_obj.interview_id,
            "round_number": round_obj.round_number,
            "category": round_obj.category.name if round_obj.category else None,
            "question_content": round_obj.question_content,
            "user_answer": round_obj.user_answer,
            "audio_data": audio_data,
        }

        return APIResponse.success(
            data=round_data,
            message="查询成功",
            code=200,
        )
