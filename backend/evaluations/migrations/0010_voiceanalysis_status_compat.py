from django.db import migrations, models


def ensure_status_column(apps, schema_editor):
    table_name = "voice_analyses"
    column_name = "status"

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            col.name
            for col in schema_editor.connection.introspection.get_table_description(
                cursor, table_name
            )
        }

        if column_name not in existing_columns:
            # MySQL: add a non-null status column with default and backfill existing rows.
            cursor.execute(
                "ALTER TABLE voice_analyses ADD COLUMN status varchar(20) NOT NULL DEFAULT 'success'"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0009_voiceanalysis_clarity_fields"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_status_column, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="voiceanalysis",
                    name="status",
                    field=models.CharField(
                        choices=[
                            ("pending", "待处理"),
                            ("running", "处理中"),
                            ("success", "成功"),
                            ("failed", "失败"),
                        ],
                        default="success",
                        max_length=20,
                        verbose_name="分析状态",
                    ),
                ),
            ],
        ),
    ]
