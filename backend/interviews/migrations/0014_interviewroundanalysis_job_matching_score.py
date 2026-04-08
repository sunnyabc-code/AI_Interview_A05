# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("interviews", "0013_interviewround_chain_topic_job_knowledge"),
    ]

    operations = [
        migrations.AddField(
            model_name="interviewroundanalysis",
            name="job_matching_score",
            field=models.FloatField(
                blank=True,
                null=True,
                verbose_name="岗位匹配度",
            ),
        ),
    ]
