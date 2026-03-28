from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0016_alter_voiceanalysis_audio_clarity_score"),
    ]

    operations = [
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_status",
            field=models.CharField(
                max_length=50,
                blank=True,
                default="",
                verbose_name="iMentiv状态",
            ),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_emotion_analysis",
            field=models.JSONField(
                default=dict,
                verbose_name="iMentiv情绪分析",
            ),
        ),
    ]
