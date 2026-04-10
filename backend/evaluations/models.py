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
    SPEECH_RATE_LEVEL_CHOICES = [
        ("slow", "慢"),
        ("normal", "正常"),
        ("fast", "快"),
    ]
    speech_rate_level = models.CharField(
        max_length=8,
        choices=SPEECH_RATE_LEVEL_CHOICES,
        default="normal",
        verbose_name="语速评价（慢/正常/快）",
        help_text="根据speech_rate自动划分：慢(<180)，正常(180-260)，快(>260)",
    )
    audio_clarity_score = models.FloatField(verbose_name="音频清晰度得分")
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
    SILENCE_RATIO_LEVEL_CHOICES = [
        ("fluent", "流利"),
        ("good", "良好"),
        ("medium", "中等偏下"),
        ("poor", "较差"),
    ]
    silence_ratio_level = models.CharField(
        max_length=12,
        choices=SILENCE_RATIO_LEVEL_CHOICES,
        default="good",
        verbose_name="静音比例评价",
        help_text="依据silence_ratio自动划分：流利(<=0.15)，良好(<=0.25)，中等偏下(<=0.35)，较差(>0.35)",
    )
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


class VoiceLLMResult(models.Model):
    STATUS_CHOICES = [
        ("pending", "待处理"),
        ("running", "处理中"),
        ("success", "成功"),
        ("failed", "失败"),
    ]

    interview = models.OneToOneField(
        "interviews.Interview",
        on_delete=models.CASCADE,
        related_name="voice_llm_result",
        verbose_name="面试",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="生成状态",
    )

    overall_audio_score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0,
        verbose_name="整体音频表现评分",
    )

    speech_rate_and_rhythm_score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0,
        verbose_name="语速与面试节奏评分",
    )
    speech_rate_and_rhythm = models.TextField(blank=True, verbose_name="语速与面试节奏")

    fluency_score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0,
        verbose_name="回答流畅度评分",
    )
    fluency = models.TextField(blank=True, verbose_name="回答流畅度")

    confidence_and_voice_energy_score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0,
        verbose_name="自信度与声音能量评分",
    )
    confidence_and_voice_energy = models.TextField(
        blank=True,
        verbose_name="自信度与声音能量",
    )

    emotional_stability_and_tone_score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0,
        verbose_name="情感稳定性与语气评分",
    )
    emotional_stability_and_tone = models.TextField(
        blank=True,
        verbose_name="情感稳定性与语气",
    )

    strengths = models.TextField(blank=True, verbose_name="你的优势亮点")
    improvements = models.TextField(blank=True, verbose_name="改进建议")
    position_communication_tips = models.TextField(
        blank=True,
        verbose_name="针对岗位的沟通提升点",
    )
    encouragement = models.TextField(blank=True, verbose_name="鼓励语")

    llm_model = models.CharField(max_length=120, blank=True, verbose_name="模型名称")
    prompt_version = models.CharField(
        max_length=40,
        default="voice_llm_v1",
        verbose_name="Prompt版本",
    )
    raw_input_json = models.JSONField(default=dict, verbose_name="模型输入快照")
    raw_output_json = models.JSONField(default=dict, verbose_name="模型输出快照")

    generated_at = models.DateTimeField(null=True, blank=True, verbose_name="结果时间")
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    retry_count = models.IntegerField(default=0, verbose_name="重试次数")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "voice_llm_results"
        verbose_name = "面试音频大模型总结"
        verbose_name_plural = "面试音频大模型总结"

    def __str__(self):
        return f"{self.interview_id} - {self.status}"


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
