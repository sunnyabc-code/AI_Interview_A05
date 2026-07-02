from django.db import migrations, models


def ensure_updated_at_column(apps, schema_editor):
    # 该迁移仅用于 MySQL；SQLite/其他引擎由 SeparatedDatabaseAndState 的 state_operations 处理。
    if schema_editor.connection.vendor not in ("mysql", "mariadb"):
        return

    table_name = "voice_analyses"
    column_name = "updated_at"

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            col.name
            for col in schema_editor.connection.introspection.get_table_description(
                cursor, table_name
            )
        }

        if column_name not in existing_columns:
            cursor.execute(
                "ALTER TABLE voice_analyses ADD COLUMN updated_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0010_voiceanalysis_status_compat"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_updated_at_column, migrations.RunPython.noop
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="voiceanalysis",
                    name="updated_at",
                    field=models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
            ],
        ),
    ]
