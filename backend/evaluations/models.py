from django.db import models


class Evaluation(models.Model):
    interview = models.OneToOneField(
        "interviews.Interview",
        on_delete=models.CASCADE,
        related_name="evaluation",
        verbose_name="面试",
    )

    overall_score = models.FloatField(verbose_name="综合得分")
    overall_comment = models.TextField(verbose_name="综合评价")

    technical_score = models.FloatField(verbose_name="技术得分")
    communication_score = models.FloatField(verbose_name="沟通得分")
    logic_score = models.FloatField(verbose_name="逻辑得分")
    adaptability_score = models.FloatField(verbose_name="应变得分")

    highlights = models.JSONField(default=list, verbose_name="亮点")
    weaknesses = models.JSONField(default=list, verbose_name="不足")
    suggestions = models.JSONField(default=list, verbose_name="建议")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "evaluations"
        verbose_name = "评估记录"
        verbose_name_plural = "评估记录"

    def __str__(self):
        return f"{self.interview} - {self.overall_score}"


class VoiceAnalysis(models.Model):
    STATUS_CHOICES = [
        ("pending", "待处理"),
        ("running", "处理中"),
        ("success", "成功"),
        ("failed", "失败"),
    ]

    round = models.ForeignKey(
        "interviews.InterviewRound",
        on_delete=models.CASCADE,
        related_name="voice_analyses",
        null=True,
        blank=True,
        verbose_name="轮次",
    )
    audio = models.OneToOneField(
        "interviews.InterviewRoundAudio",
        on_delete=models.SET_NULL,
        related_name="voice_analysis",
        null=True,
        blank=True,
        verbose_name="音频",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="success",
        verbose_name="分析状态",
    )

    duration_seconds = models.FloatField(verbose_name="时长(秒)")
    speech_rate = models.FloatField(verbose_name="语速(字/分钟)")
    audio_clarity_score = models.FloatField(verbose_name="音频清晰度得分")
    asr_confidence = models.FloatField(default=0, verbose_name="ASR置信度")
    overall_clarity = models.FloatField(default=0, verbose_name="综合清晰度得分")
    confidence_score = models.FloatField(verbose_name="自信度得分")
    emotion = models.CharField(max_length=50, blank=True, verbose_name="情感")
    imentiv_status = models.CharField(
        max_length=50, blank=True, default="", verbose_name="iMentiv状态"
    )
    imentiv_emotion_analysis = models.JSONField(
        default=dict, verbose_name="iMentiv情绪分析"
    )

    filler_word_total = models.IntegerField(default=0, verbose_name="填充词总数")
    filler_word_counts = models.JSONField(default=dict, verbose_name="填充词明细")
    rms_mean = models.FloatField(default=0, verbose_name="平均RMS")
    rms_std = models.FloatField(default=0, verbose_name="RMS标准差")
    rms_cv = models.FloatField(default=0, verbose_name="RMS变异系数")
    silence_ratio = models.FloatField(default=0, verbose_name="无声占比")
    voiced_frames = models.IntegerField(default=0, verbose_name="有声帧数")
    total_frames = models.IntegerField(default=0, verbose_name="总帧数")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "voice_analyses"
        verbose_name = "语音分析"
        verbose_name_plural = "语音分析"

    def __str__(self):
        return f'{self.round or "未关联轮次"} - {self.speech_rate}字/分钟'


class DifficultyConfig(models.Model):
    difficulty_code = models.CharField(
        max_length=16, unique=True, verbose_name="难度编码"
    )
    difficulty_name = models.CharField(max_length=32, verbose_name="难度名称")
    answer_time_seconds = models.IntegerField(verbose_name="单轮默认答题时长(秒)")

    technical_chain_count = models.IntegerField(verbose_name="技术知识链数量")
    project_chain_count = models.IntegerField(verbose_name="项目深挖链数量")
    scenario_chain_count = models.IntegerField(verbose_name="场景题链数量")

    technical_max_followup_depth = models.IntegerField(
        verbose_name="技术链最大追问深度"
    )
    project_max_followup_depth = models.IntegerField(verbose_name="项目链最大追问深度")
    scenario_max_followup_depth = models.IntegerField(verbose_name="场景链最大追问深度")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "difficulty_config"
        verbose_name = "难度配置"
        verbose_name_plural = "难度配置"

    def __str__(self):
        return f"{self.difficulty_name}({self.difficulty_code})"
