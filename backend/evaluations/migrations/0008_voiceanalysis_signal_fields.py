from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0007_voiceanalysis_audio"),
    ]

    operations = [
        migrations.AddField(
            model_name="voiceanalysis",
            name="filler_word_counts",
            field=models.JSONField(default=dict, verbose_name="填充词明细"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="filler_word_total",
            field=models.IntegerField(default=0, verbose_name="填充词总数"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="rms_cv",
            field=models.FloatField(default=0, verbose_name="RMS变异系数"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="rms_mean",
            field=models.FloatField(default=0, verbose_name="平均RMS"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="rms_std",
            field=models.FloatField(default=0, verbose_name="RMS标准差"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="silence_ratio",
            field=models.FloatField(default=0, verbose_name="无声占比"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="total_frames",
            field=models.IntegerField(default=0, verbose_name="总帧数"),
        ),
        migrations.AddField(
            model_name="voiceanalysis",
            name="voiced_frames",
            field=models.IntegerField(default=0, verbose_name="有声帧数"),
        ),
    ]
