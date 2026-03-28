from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0013_remove_voiceanalysis_analysis_details"),
    ]

    operations = [
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_audio_id",
            field=models.CharField(
                blank=True, default="", max_length=100, verbose_name="iMentiv音频ID"
            ),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_created_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="iMentiv创建时间"
            ),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_description",
            field=models.TextField(blank=True, default="", verbose_name="iMentiv描述"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_detected_speakers",
            field=models.JSONField(default=list, verbose_name="iMentiv说话人识别"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_duration",
            field=models.FloatField(default=0, verbose_name="iMentiv时长"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_emotion_analysis",
            field=models.JSONField(default=dict, verbose_name="iMentiv情绪分析"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_media_source_url",
            field=models.TextField(
                blank=True, default="", verbose_name="iMentiv媒体来源URL"
            ),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_media_type",
            field=models.CharField(
                blank=True, default="", max_length=50, verbose_name="iMentiv媒体类型"
            ),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_raw_payload",
            field=models.JSONField(default=dict, verbose_name="iMentiv完整返回"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_speaker_count",
            field=models.IntegerField(default=0, verbose_name="iMentiv说话人数"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_status",
            field=models.CharField(
                blank=True, default="", max_length=50, verbose_name="iMentiv状态"
            ),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_text_id",
            field=models.CharField(
                blank=True, default="", max_length=100, verbose_name="iMentiv文本ID"
            ),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_title",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="iMentiv标题"
            ),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="imentiv_youtube_url",
            field=models.TextField(
                blank=True, default="", verbose_name="iMentiv YouTube URL"
            ),
        ),
    ]
