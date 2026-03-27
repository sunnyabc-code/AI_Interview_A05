from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0012_remove_voiceanalysis_transcript"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="analysis_details",
        ),
    ]
