from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0014_voiceanalysis_imentiv_full_payload"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_audio_id",
        ),
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_created_at",
        ),
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_description",
        ),
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_detected_speakers",
        ),
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_duration",
        ),
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_media_source_url",
        ),
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_media_type",
        ),
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_text_id",
        ),
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_title",
        ),
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_youtube_url",
        ),
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_raw_payload",
        ),
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="imentiv_speaker_count",
        ),
    ]
