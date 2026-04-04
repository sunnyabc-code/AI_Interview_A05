from django.db import migrations


def create_user_knowledge_matrics(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    if vendor in ("mysql", "mariadb"):
        schema_editor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_knowledge_matrics (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                interview_id BIGINT NOT NULL,
                id_job_knowledge INT NOT NULL,
                logic INT NOT NULL,
                accuracy INT NOT NULL,
                CONSTRAINT fk_ukm_interview
                    FOREIGN KEY (interview_id)
                    REFERENCES interviews (id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_ukm_job_knowledge
                    FOREIGN KEY (id_job_knowledge)
                    REFERENCES job_knowledge (id_job_knowledge)
                    ON DELETE CASCADE,
                INDEX idx_ukm_interview_id (interview_id),
                INDEX idx_ukm_job_knowledge (id_job_knowledge)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        return

    if vendor == "sqlite":
        schema_editor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_knowledge_matrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interview_id INTEGER NOT NULL,
                id_job_knowledge INTEGER NOT NULL,
                logic INTEGER NOT NULL,
                accuracy INTEGER NOT NULL,
                FOREIGN KEY (interview_id) REFERENCES interviews (id) ON DELETE CASCADE,
                FOREIGN KEY (id_job_knowledge) REFERENCES job_knowledge (id_job_knowledge) ON DELETE CASCADE
            );
            """
        )
        schema_editor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ukm_interview_id ON user_knowledge_matrics (interview_id);"
        )
        schema_editor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ukm_job_knowledge ON user_knowledge_matrics (id_job_knowledge);"
        )
        return

    raise RuntimeError(f"Unsupported DB vendor: {vendor}")


def drop_user_knowledge_matrics(apps, schema_editor):
    schema_editor.execute("DROP TABLE IF EXISTS user_knowledge_matrics;")


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("evaluations", "0020_voiceanalysis_silence_ratio_level"),
    ]

    operations = [
        migrations.RunPython(
            create_user_knowledge_matrics,
            reverse_code=drop_user_knowledge_matrics,
        ),
    ]
