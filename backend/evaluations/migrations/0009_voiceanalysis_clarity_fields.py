from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0008_voiceanalysis_signal_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="voiceanalysis",
            old_name="clarity_score",
            new_name="audio_clarity_score",
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="asr_confidence",
            field=models.FloatField(default=0, verbose_name="ASR置信度"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="overall_clarity",
            field=models.FloatField(default=0, verbose_name="综合清晰度得分"),
        ),
    ]
