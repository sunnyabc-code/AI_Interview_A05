from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0011_voiceanalysis_updated_at_compat"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="voiceanalysis",
            name="transcript",
        ),
    ]
