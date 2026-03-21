from django.db import models


class Report(models.Model):
    interview = models.OneToOneField('interviews.Interview', on_delete=models.CASCADE, related_name='report', verbose_name='面试')
    evaluation = models.OneToOneField('evaluations.Evaluation', on_delete=models.CASCADE, related_name='report', verbose_name='评估')
    
    title = models.CharField(max_length=200, verbose_name='报告标题')
    content = models.TextField(verbose_name='报告内容')
    
    pdf_file = models.CharField(max_length=500, blank=True, null=True, verbose_name='PDF文件URL')
    
    summary = models.TextField(verbose_name='摘要')
    key_findings = models.JSONField(default=list, verbose_name='关键发现')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'reports'
        verbose_name = '评估报告'
        verbose_name_plural = '评估报告'

    def __str__(self):
        return self.title
