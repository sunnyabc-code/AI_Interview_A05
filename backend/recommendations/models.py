from django.db import models


class Recommendation(models.Model):
    TYPE_CHOICES = [
        ('knowledge', '知识点补充'),
        ('question', '题目推荐'),
        ('resource', '学习资源'),
        ('practice', '练习建议'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='recommendations', verbose_name='用户')
    interview = models.ForeignKey('interviews.Interview', on_delete=models.CASCADE, related_name='recommendations', null=True, blank=True, verbose_name='面试')
    
    recommendation_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='推荐类型')
    title = models.CharField(max_length=300, verbose_name='标题')
    description = models.TextField(verbose_name='描述')
    
    priority = models.IntegerField(default=1, verbose_name='优先级')
    is_completed = models.BooleanField(default=False, verbose_name='是否完成')
    
    related_dimension = models.CharField(max_length=100, blank=True, null=True, verbose_name='关联维度')
    related_knowledge_point = models.ForeignKey('questions.KnowledgePoint', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联知识点')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'recommendations'
        verbose_name = '推荐'
        verbose_name_plural = '推荐'
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return self.title


class UserProgress(models.Model):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='progress', verbose_name='用户')
    
    total_interviews = models.IntegerField(default=0, verbose_name='总面试次数')
    total_questions_answered = models.IntegerField(default=0, verbose_name='总答题数')
    
    avg_overall_score = models.FloatField(default=0, verbose_name='平均综合得分')
    avg_technical_score = models.FloatField(default=0, verbose_name='平均技术得分')
    avg_communication_score = models.FloatField(default=0, verbose_name='平均沟通得分')
    avg_logic_score = models.FloatField(default=0, verbose_name='平均逻辑得分')
    
    completed_recommendations = models.IntegerField(default=0, verbose_name='已完成推荐数')
    
    skill_gaps = models.JSONField(default=list, verbose_name='技能缺口')
    improvement_areas = models.JSONField(default=list, verbose_name='改进领域')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'user_progress'
        verbose_name = '用户进度'
        verbose_name_plural = '用户进度'

    def __str__(self):
        return f'{self.user.username} - {self.avg_overall_score}'
