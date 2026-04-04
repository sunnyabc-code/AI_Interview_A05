from django.db import models


class JobPosition(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name='岗位代码')
    name = models.CharField(max_length=100, verbose_name='岗位名称')
    description = models.TextField(blank=True, verbose_name='岗位描述')
    tech_stack = models.JSONField(default=list, verbose_name='技术栈')
    required_skills = models.JSONField(default=list, verbose_name='必备技能')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'job_positions'
        verbose_name = '岗位'
        verbose_name_plural = '岗位'

    def __str__(self):
        return self.name


class JobKnowledge(models.Model):
    """
    与 MySQL 表 job_knowledge 对齐（岗位关联知识点，serial_number 1~7 等）。
    仅查询，不由 Django 迁移管理表结构。
    """

    id_job_knowledge = models.AutoField(
        primary_key=True,
        db_column="id_job_knowledge",
    )
    name = models.CharField(max_length=255, verbose_name="知识点名称")
    serial_number = models.IntegerField(verbose_name="序号")
    job_id = models.IntegerField(db_column="job_id", verbose_name="岗位ID")

    class Meta:
        managed = False
        db_table = "job_knowledge"
        verbose_name = "岗位知识点"
        verbose_name_plural = "岗位知识点"

    def __str__(self):
        return f"{self.name}({self.serial_number})"
