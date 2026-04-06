from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("positions", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProject",
            fields=[
                ("project_id", models.BigAutoField(primary_key=True, serialize=False, verbose_name="项目ID")),
                ("project_name", models.CharField(max_length=255, verbose_name="项目名称")),
                ("project_role", models.CharField(max_length=255, verbose_name="项目角色")),
                ("project_description", models.TextField(verbose_name="项目描述")),
                ("project_result", models.TextField(verbose_name="项目成果")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "position",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_projects",
                        to="positions.jobposition",
                        verbose_name="关联岗位",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_projects",
                        to="users.user",
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "用户项目",
                "verbose_name_plural": "用户项目",
                "db_table": "user_projects",
                "ordering": ["-updated_at", "-project_id"],
            },
        ),
    ]
