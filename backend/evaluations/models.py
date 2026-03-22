from django.db import models


class Evaluation(models.Model):
    interview = models.OneToOneField('interviews.Interview', on_delete=models.CASCADE, related_name='evaluation', verbose_name='面试')
    
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
        db_table = 'evaluations'
        verbose_name = '评估记录'
        verbose_name_plural = '评估记录'

    def __str__(self):
        return f'{self.interview} - {self.overall_score}'


class VoiceAnalysis(models.Model):
    round = models.ForeignKey('interviews.InterviewRound', on_delete=models.CASCADE, related_name='voice_analyses', null=True, blank=True, verbose_name='轮次')
    
    duration_seconds = models.FloatField(verbose_name='时长(秒)')
    speech_rate = models.FloatField(verbose_name='语速(字/分钟)')
    clarity_score = models.FloatField(verbose_name='清晰度得分')
    confidence_score = models.FloatField(verbose_name='自信度得分')
    emotion = models.CharField(max_length=50, blank=True, verbose_name='情感')
    
    transcript = models.TextField(blank=True, verbose_name='转录文本')
    analysis_details = models.JSONField(default=dict, verbose_name='分析详情')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'voice_analyses'
        verbose_name = '语音分析'
        verbose_name_plural = '语音分析'

    def __str__(self):
        return f'{self.round or "未关联轮次"} - {self.speech_rate}字/分钟'


class DifficultyConfig(models.Model):
    DIFFICULTY_CODE_CHOICES = [
        ('easy', '简单'),
        ('medium', '中等'),
        ('hard', '困难'),
    ]

    difficulty_code = models.CharField(max_length=16, unique=True, choices=DIFFICULTY_CODE_CHOICES, verbose_name='难度编码')
    difficulty_name = models.CharField(max_length=32, verbose_name='难度名称')
    answer_time_seconds = models.IntegerField(verbose_name='单轮默认答题时长(秒)')

    technical_chain_count = models.IntegerField(verbose_name='技术知识链数量')
    project_chain_count = models.IntegerField(verbose_name='项目深挖链数量')
    scenario_chain_count = models.IntegerField(verbose_name='场景题链数量')

    technical_max_followup_depth = models.IntegerField(verbose_name='技术链最大追问深度')
    project_max_followup_depth = models.IntegerField(verbose_name='项目链最大追问深度')
    scenario_max_followup_depth = models.IntegerField(verbose_name='场景链最大追问深度')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'difficulty_config'
        verbose_name = '难度配置'
        verbose_name_plural = '难度配置'

    def __str__(self):
        return f'{self.difficulty_name}({self.difficulty_code})'
