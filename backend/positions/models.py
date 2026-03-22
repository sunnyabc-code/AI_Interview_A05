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
