from django.utils import timezone

from recommendations.models import VoiceLlmResult


def main():
    now = timezone.now()
    samples = [
        (42, 3.9, 4.1, 4.2, 3.6, 3.8),
        (35, 3.4, 3.5, 3.7, 3.2, 3.3),
        (33, 4.3, 4.0, 4.6, 4.1, 4.2),
    ]

    result = []
    for interview_id, overall, sr, flu, conf, emo in samples:
        obj, created = VoiceLlmResult.objects.update_or_create(
            interview_id=interview_id,
            defaults={
                "status": "success",
                "overall_audio_score": overall,
                "speech_rate_and_rhythm_score": sr,
                "speech_rate_and_rhythm": '["stable pace"]',
                "fluency_score": flu,
                "fluency": '["clear flow"]',
                "confidence_and_voice_energy_score": conf,
                "confidence_and_voice_energy": '["good energy"]',
                "emotional_stability_and_tone_score": emo,
                "emotional_stability_and_tone": '["steady tone"]',
                "strengths": '["clear structure", "accurate terms"]',
                "improvements": '["shorter sentences", "add pauses"]',
                "position_communication_tips": '["conclusion first", "layered explanation"]',
                "encouragement": "Keep this rhythm and confidence in each round.",
                "llm_model": "qwen-plus",
                "prompt_version": "voice_llm_v1",
                "raw_input_json": {"interview_id": interview_id, "mock": True},
                "raw_output_json": {"mock": True},
                "generated_at": now,
                "error_message": "",
                "retry_count": 0,
                "created_at": now,
                "updated_at": now,
            },
        )
        result.append((obj.interview_id, "created" if created else "updated"))

    print("UPSERT:", result)
    print(
        "SUCCESS_CNT_USER3:",
        VoiceLlmResult.objects.filter(interview__user_id=3, status="success").count(),
    )


if __name__ == "__main__":
    main()
