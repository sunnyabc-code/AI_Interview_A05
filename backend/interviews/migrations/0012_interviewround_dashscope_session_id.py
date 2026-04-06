# Generated manually for 百炼 Application 会话追问

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("interviews", "0011_interviewroundaudio_imentiv_analysis_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="interviewround",
            name="dashscope_session_id",
            field=models.CharField(
                blank=True,
                default="",
                max_length=128,
                verbose_name="百炼会话ID",
            ),
        ),
    ]
