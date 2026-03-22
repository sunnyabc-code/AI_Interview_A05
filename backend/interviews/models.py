from django.db import models


class Interview(models.Model):
    STATUS_CHOICES = [
        ('pending', '待开始'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    MODE_CHOICES = [
        ('text', '文本模式'),
        ('voice', '语音模式'),
        ('mixed', '混合模式'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='interviews', verbose_name='用户')
    position = models.ForeignKey('positions.JobPosition', on_delete=models.CASCADE, related_name='interviews', verbose_name='岗位')
    difficulty_config = models.ForeignKey('evaluations.DifficultyConfig', on_delete=models.SET_NULL, related_name='interviews', null=True, blank=True, verbose_name='难度配置')
    
    name = models.CharField(max_length=200, default='', verbose_name='面试名称')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='text', verbose_name='交互模式')
    
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration_seconds = models.IntegerField(default=0, verbose_name='时长(秒)')
    
    total_rounds = models.IntegerField(default=0, verbose_name='总轮次')
    enable_technical_questions = models.BooleanField(default=True, verbose_name='是否选择技术知识题')
    enable_project_questions = models.BooleanField(default=True, verbose_name='是否选择项目经历题')
    enable_scenario_questions = models.BooleanField(default=True, verbose_name='是否选择场景题')
    
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'interviews'
        verbose_name = '面试记录'
        verbose_name_plural = '面试记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.position.name}'


class InterviewRound(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='rounds', verbose_name='面试')
    round_number = models.IntegerField(verbose_name='轮次')
    chain_index = models.IntegerField(default=1, verbose_name='提问链编号')
    followup_depth = models.IntegerField(default=0, verbose_name='追问深度')
    category = models.ForeignKey('questions.QuestionCategory', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='题目分类')
    question = models.ForeignKey('questions.Question', on_delete=models.SET_NULL, null=True, blank=True, related_name='interview_rounds', verbose_name='题目')
    question_content = models.TextField(blank=True, verbose_name='问题内容快照')
    user_answer = models.TextField(blank=True, verbose_name='用户回答')
    
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'interview_rounds'
        verbose_name = '面试轮次'
        verbose_name_plural = '面试轮次'
        unique_together = ['interview', 'round_number']

    def __str__(self):
        return f'{self.interview} - 第{self.round_number}轮'


class InterviewRoundAnalysis(models.Model):
    round = models.OneToOneField(InterviewRound, on_delete=models.CASCADE, related_name='analysis', verbose_name='面试轮次')

    overall_score = models.FloatField(verbose_name='综合得分')
    overall_comment = models.TextField(verbose_name='综合评价')

    technical_score = models.FloatField(verbose_name='技术得分')
    communication_score = models.FloatField(verbose_name='沟通得分')
    logic_score = models.FloatField(verbose_name='逻辑得分')
    adaptability_score = models.FloatField(verbose_name='应变得分')

    highlights = models.JSONField(default=list, verbose_name='亮点')
    weaknesses = models.JSONField(default=list, verbose_name='不足')
    suggestions = models.JSONField(default=list, verbose_name='建议')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'interview_round_analyses'
        verbose_name = '轮次分析结果'
        verbose_name_plural = '轮次分析结果'

    def __str__(self):
        return f'{self.round} - {self.overall_score}'
