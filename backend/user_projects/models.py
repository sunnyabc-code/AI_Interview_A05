from django.db import models


class UserProject(models.Model):
    project_id = models.BigAutoField(primary_key=True, verbose_name="项目ID")
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="user_projects",
        verbose_name="用户",
    )
    position = models.ForeignKey(
        "positions.JobPosition",
        on_delete=models.CASCADE,
        related_name="user_projects",
        verbose_name="关联岗位",
    )
    project_name = models.CharField(max_length=255, verbose_name="项目名称")
    project_role = models.CharField(max_length=255, verbose_name="项目角色")
    project_description = models.TextField(verbose_name="项目描述")
    project_result = models.TextField(verbose_name="项目成果")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "user_projects"
        verbose_name = "用户项目"
        verbose_name_plural = "用户项目"
        ordering = ["-updated_at", "-project_id"]

    def __str__(self):
        return f"{self.user_id}-{self.project_name}"
