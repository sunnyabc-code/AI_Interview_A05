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


class JobKnowledge(models.Model):
    id_job_knowledge = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=45)
    serial_number = models.IntegerField()
    job_id = models.BigIntegerField()

    class Meta:
        db_table = 'job_knowledge'
        managed = False
        verbose_name = '岗位知识点'
        verbose_name_plural = '岗位知识点'

    def __str__(self):
        return self.name


class UserKnowledgeMatrics(models.Model):
    id = models.BigAutoField(primary_key=True)
    interview = models.ForeignKey(
        'interviews.Interview',
        on_delete=models.CASCADE,
        db_column='interview_id',
        related_name='knowledge_matrics',
    )
    job_knowledge = models.ForeignKey(
        JobKnowledge,
        on_delete=models.CASCADE,
        db_column='id_job_knowledge',
        to_field='id_job_knowledge',
        related_name='user_knowledge_matrics',
    )
    logic = models.IntegerField()
    accuracy = models.IntegerField()

    class Meta:
        db_table = 'user_knowledge_matrics'
        ordering = ['-id']
        verbose_name = '用户知识点掌握记录'
        verbose_name_plural = '用户知识点掌握记录'
        managed = False

    def __str__(self):
        return f'{self.interview_id}-{self.job_knowledge_id}'


class VoiceLlmResult(models.Model):
    interview = models.OneToOneField(
        'interviews.Interview',
        on_delete=models.DO_NOTHING,
        db_column='interview_id',
        related_name='voice_llm_result',
    )

    status = models.CharField(max_length=20)
    overall_audio_score = models.DecimalField(max_digits=5, decimal_places=1)
    speech_rate_and_rhythm_score = models.DecimalField(max_digits=5, decimal_places=1)
    speech_rate_and_rhythm = models.TextField()
    fluency_score = models.DecimalField(max_digits=5, decimal_places=1)
    fluency = models.TextField()
    confidence_and_voice_energy_score = models.DecimalField(max_digits=5, decimal_places=1)
    confidence_and_voice_energy = models.TextField()
    emotional_stability_and_tone_score = models.DecimalField(max_digits=5, decimal_places=1)
    emotional_stability_and_tone = models.TextField()

    strengths = models.TextField()
    improvements = models.TextField()
    position_communication_tips = models.TextField()
    encouragement = models.TextField()

    llm_model = models.CharField(max_length=120)
    prompt_version = models.CharField(max_length=40)

    raw_input_json = models.JSONField(default=dict)
    raw_output_json = models.JSONField(default=dict)

    generated_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField()
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'voice_llm_results'
        managed = False
        verbose_name = '语音LLM分析结果'
        verbose_name_plural = '语音LLM分析结果'

    def __str__(self):
        return f'{self.interview_id}-{self.status}'
