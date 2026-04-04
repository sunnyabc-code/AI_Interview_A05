from django.db import models


class Interview(models.Model):
    STATUS_CHOICES = [
        ("pending", "待开始"),
        ("in_progress", "进行中"),
        ("completed", "已完成"),
        ("cancelled", "已取消"),
    ]

    MODE_CHOICES = [
        ("text", "文本模式"),
        ("voice", "语音模式"),
        ("mixed", "混合模式"),
    ]

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="interviews",
        verbose_name="用户",
    )
    position = models.ForeignKey(
        "positions.JobPosition",
        on_delete=models.CASCADE,
        related_name="interviews",
        verbose_name="岗位",
    )
    difficulty_config = models.ForeignKey(
        "evaluations.DifficultyConfig",
        on_delete=models.SET_NULL,
        related_name="interviews",
        null=True,
        blank=True,
        verbose_name="难度配置",
    )

    name = models.CharField(max_length=200, default="", verbose_name="面试名称")

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="状态"
    )
    mode = models.CharField(
        max_length=20, choices=MODE_CHOICES, default="text", verbose_name="交互模式"
    )

    start_time = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    pause_time = models.DateTimeField(null=True, blank=True, verbose_name="暂停时间")
    duration_seconds = models.IntegerField(default=0, verbose_name="时长(秒)")
    total_pause_duration = models.IntegerField(default=0, verbose_name="总暂停时长(秒)")
    actual_duration = models.IntegerField(default=0, verbose_name="实际面试时长(秒)")
    pause_count = models.IntegerField(default=0, verbose_name="暂停次数")

    total_rounds = models.IntegerField(default=0, verbose_name="总轮次")
    enable_technical_questions = models.BooleanField(
        default=True, verbose_name="是否选择技术知识题"
    )
    enable_project_questions = models.BooleanField(
        default=True, verbose_name="是否选择项目经历题"
    )
    enable_scenario_questions = models.BooleanField(
        default=True, verbose_name="是否选择场景题"
    )

    notes = models.TextField(blank=True, verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "interviews"
        verbose_name = "面试记录"
        verbose_name_plural = "面试记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.position.name}"


class InterviewRound(models.Model):
    interview = models.ForeignKey(
        Interview, on_delete=models.CASCADE, related_name="rounds", verbose_name="面试"
    )
    round_number = models.IntegerField(verbose_name="轮次")
    chain_index = models.IntegerField(default=1, verbose_name="提问链编号")
    followup_depth = models.IntegerField(default=0, verbose_name="追问深度")
    category = models.ForeignKey(
        "questions.QuestionCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="题目分类",
    )
    question = models.ForeignKey(
        "questions.Question",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_rounds",
        verbose_name="题目",
    )
    question_content = models.TextField(blank=True, verbose_name="问题内容快照")
    user_answer = models.TextField(blank=True, verbose_name="用户回答")

    # 百炼 Application 多轮会话：追问需带上上一轮返回的 session_id
    dashscope_session_id = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="百炼会话ID",
    )

    # 技术链：与 job_knowledge 对齐；主问随机 serial 1~7，追问沿用同链知识点
    job_knowledge_serial = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="知识点序号",
    )
    chain_topic_label = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="本链知识点/主题标签",
    )

    start_time = models.DateTimeField(auto_now_add=True, verbose_name="开始时间")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "interview_rounds"
        verbose_name = "面试轮次"
        verbose_name_plural = "面试轮次"
        unique_together = ["interview", "round_number"]

    def __str__(self):
        return f"{self.interview} - 第{self.round_number}轮"


class InterviewRoundAnalysis(models.Model):
    round = models.OneToOneField(
        InterviewRound,
        on_delete=models.CASCADE,
        related_name="analysis",
        verbose_name="面试轮次",
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
        db_table = "interview_round_analyses"
        verbose_name = "轮次分析结果"
        verbose_name_plural = "轮次分析结果"

    def __str__(self):
        return f"{self.round} - {self.overall_score}"


class InterviewRoundAudio(models.Model):
    UPLOAD_STATUS_CHOICES = [
        ("uploaded", "已上传"),
        ("failed", "上传失败"),
        ("deleted", "已删除"),
    ]
    PROCESS_STATUS_CHOICES = [
        ("pending", "待处理"),
        ("running", "处理中"),
        ("success", "成功"),
        ("failed", "失败"),
    ]

    round = models.OneToOneField(
        InterviewRound,
        on_delete=models.CASCADE,
        related_name="audio",
        verbose_name="轮次",
    )
    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_audios",
        verbose_name="上传用户",
    )

    file_url = models.CharField(max_length=500, verbose_name="音频URL")
    file_key = models.CharField(max_length=255, unique=True, verbose_name="存储Key")
    file_name = models.CharField(max_length=255, blank=True, verbose_name="文件名")
    mime_type = models.CharField(max_length=100, blank=True, verbose_name="MIME类型")
    codec = models.CharField(max_length=50, blank=True, verbose_name="编码")
    sample_rate = models.IntegerField(null=True, blank=True, verbose_name="采样率")
    channels = models.IntegerField(null=True, blank=True, verbose_name="声道数")
    file_size_bytes = models.BigIntegerField(default=0, verbose_name="文件大小(字节)")
    duration_seconds = models.FloatField(null=True, blank=True, verbose_name="时长(秒)")

    upload_status = models.CharField(
        max_length=20,
        choices=UPLOAD_STATUS_CHOICES,
        default="uploaded",
        verbose_name="上传状态",
    )
    asr_status = models.CharField(
        max_length=20,
        choices=PROCESS_STATUS_CHOICES,
        default="pending",
        verbose_name="转写状态",
    )
    analysis_status = models.CharField(
        max_length=20,
        choices=PROCESS_STATUS_CHOICES,
        default="pending",
        verbose_name="分析状态",
    )
    imentiv_analysis_status = models.CharField(
        max_length=20,
        choices=PROCESS_STATUS_CHOICES,
        default="pending",
        verbose_name="iMentiv分析状态",
    )
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    imentiv_error_message = models.TextField(blank=True, verbose_name="iMentiv错误信息")
    retry_count = models.IntegerField(default=0, verbose_name="重试次数")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "interview_round_audios"
        verbose_name = "轮次音频"
        verbose_name_plural = "轮次音频"
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["asr_status"]),
            models.Index(fields=["analysis_status"]),
            models.Index(fields=["imentiv_analysis_status"]),
        ]

    def __str__(self):
        return f"{self.round} - {self.file_name or self.file_key}"
