try:
    from celery import shared_task
except ModuleNotFoundError:  # pragma: no cover

    def shared_task(*dargs, **dkwargs):
        def decorator(func):
            return func

        return decorator


from interviews.models import InterviewRoundAudio

from evaluations.imentiv_analysis import (
    ImentivAnalysisError,
    ImentivAnalysisService,
    mark_imentiv_analysis_failed,
)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def analyze_imentiv_audio_task(self, audio_id: int):
    try:
        audio_obj = InterviewRoundAudio.objects.select_related("round").get(id=audio_id)
    except InterviewRoundAudio.DoesNotExist:
        return {"ok": False, "reason": "audio_not_found", "audio_id": audio_id}

    if audio_obj.imentiv_analysis_status == "running":
        return {"ok": False, "reason": "already_running", "audio_id": audio_id}

    audio_obj.imentiv_analysis_status = "running"
    audio_obj.imentiv_error_message = ""
    audio_obj.save(
        update_fields=[
            "imentiv_analysis_status",
            "imentiv_error_message",
            "updated_at",
        ]
    )

    service = ImentivAnalysisService()

    try:
        voice_analysis = service.analyze_and_save(audio_obj)
        return {
            "ok": True,
            "audio_id": audio_id,
            "voice_analysis_id": voice_analysis.id,
            "emotion": voice_analysis.emotion,
        }
    except ImentivAnalysisError as exc:
        mark_imentiv_analysis_failed(audio_obj, str(exc))
        return {"ok": False, "audio_id": audio_id, "reason": str(exc)}
    except Exception as exc:  # noqa: BLE001
        mark_imentiv_analysis_failed(audio_obj, str(exc))
        raise self.retry(exc=exc)
