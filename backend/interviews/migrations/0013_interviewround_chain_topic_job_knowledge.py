# 技术链知识点标签与 job_knowledge 序号

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("interviews", "0012_interviewround_dashscope_session_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="interviewround",
            name="job_knowledge_serial",
            field=models.IntegerField(
                blank=True,
                null=True,
                verbose_name="知识点序号",
            ),
        ),
        migrations.AddField(
            model_name="interviewround",
            name="chain_topic_label",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="本链知识点/主题标签",
            ),
        ),
    ]
