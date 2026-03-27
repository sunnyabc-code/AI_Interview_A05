from django.core.management.base import BaseCommand

from evaluations.audio_analysis import (
    AudioAnalysisError,
    AudioAnalysisService,
    mark_audio_analysis_failed,
)
from interviews.models import InterviewRoundAudio


class Command(BaseCommand):
    help = "分析 interview_round_audios 中待处理语音（analysis_status=pending）并写入 voice_analyses。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=20, help="本次最多处理多少条，默认20"
        )
        parser.add_argument(
            "--force", action="store_true", help="强制重跑，包含 failed/success 状态"
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        force = options["force"]

        if force:
            queryset = InterviewRoundAudio.objects.select_related("round").order_by(
                "created_at"
            )
        else:
            queryset = (
                InterviewRoundAudio.objects.select_related("round")
                .filter(analysis_status="pending")
                .order_by("created_at")
            )

        audio_list = list(queryset[:limit])
        if not audio_list:
            self.stdout.write(self.style.WARNING("没有可处理的音频"))
            return

        service = AudioAnalysisService(vad_mode=2)
        success_count = 0
        failed_count = 0

        for audio_obj in audio_list:
            transcript = (audio_obj.round.user_answer or "").strip()
            audio_obj.analysis_status = "running"
            audio_obj.error_message = ""
            audio_obj.save(
                update_fields=["analysis_status", "error_message", "updated_at"]
            )

            try:
                service.analyze_and_save(audio_obj, transcript=transcript)
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"分析成功: audio_id={audio_obj.id}")
                )
            except AudioAnalysisError as exc:
                failed_count += 1
                mark_audio_analysis_failed(audio_obj, str(exc))
                self.stdout.write(
                    self.style.ERROR(f"分析失败(audio_id={audio_obj.id}): {exc}")
                )
            except Exception as exc:
                failed_count += 1
                mark_audio_analysis_failed(audio_obj, str(exc))
                self.stdout.write(
                    self.style.ERROR(f"分析失败(audio_id={audio_obj.id}): {exc}")
                )

        self.stdout.write(
            f"处理完成，总数={len(audio_list)}，成功={success_count}，失败={failed_count}"
        )
