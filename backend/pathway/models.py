from django.db import models


class PathwayProfile(models.Model):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="pathway_profiles",
        verbose_name="用户",
    )
    technical_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="技术总分",
    )
    expression_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="表达总分",
    )
    dimensions_json = models.JSONField(default=dict, verbose_name="维度分数")
    weaknesses_json = models.JSONField(default=list, verbose_name="短板列表")
    strengths_json = models.JSONField(default=list, verbose_name="优势列表")
    confidence_level = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="结论置信度",
    )
    snapshot_time = models.DateTimeField(verbose_name="快照时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "pathway_profiles"
        verbose_name = "路径画像快照"
        verbose_name_plural = "路径画像快照"
        ordering = ["-snapshot_time", "-id"]
        indexes = [
            models.Index(fields=["user", "snapshot_time"]),
        ]


class PathwayPlan(models.Model):
    STATUS_CHOICES = [
        ("draft", "草稿"),
        ("active", "进行中"),
        ("completed", "已完成"),
        ("paused", "已暂停"),
    ]

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="pathway_plans",
        verbose_name="用户",
    )
    profile = models.ForeignKey(
        PathwayProfile,
        on_delete=models.CASCADE,
        related_name="plans",
        verbose_name="画像快照",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        verbose_name="计划状态",
    )
    cycle_days = models.IntegerField(default=7, verbose_name="周期天数")
    goal_summary = models.TextField(verbose_name="目标总结")
    expected_gain_json = models.JSONField(default=dict, verbose_name="预计提升")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "pathway_plans"
        verbose_name = "路径计划"
        verbose_name_plural = "路径计划"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]


class PathwayTask(models.Model):
    TASK_TYPE_CHOICES = [
        ("resource", "学习资源"),
        ("question", "题目练习"),
        ("practice", "表达训练"),
        ("review", "复盘任务"),
    ]
    STATUS_CHOICES = [
        ("pending", "待完成"),
        ("done", "已完成"),
        ("skipped", "已跳过"),
    ]

    plan = models.ForeignKey(
        PathwayPlan,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="所属计划",
    )
    day_index = models.IntegerField(verbose_name="第几天")
    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPE_CHOICES,
        verbose_name="任务类型",
    )
    source_type = models.CharField(max_length=30, verbose_name="来源类型")
    source_id = models.BigIntegerField(null=True, blank=True, verbose_name="来源ID")
    title = models.CharField(max_length=300, verbose_name="任务标题")
    reason = models.TextField(verbose_name="推荐理由")
    estimated_minutes = models.IntegerField(default=20, verbose_name="预计时长")
    priority = models.IntegerField(default=1, verbose_name="优先级")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="完成状态",
    )
    completion_note = models.TextField(blank=True, default="", verbose_name="完成备注")
    done_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "pathway_tasks"
        verbose_name = "路径任务"
        verbose_name_plural = "路径任务"
        ordering = ["day_index", "priority", "id"]
        indexes = [
            models.Index(fields=["plan", "day_index"]),
            models.Index(fields=["plan", "status"]),
        ]


class PathwayEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ("generated", "路径生成"),
        ("task_done", "任务完成"),
        ("reviewed", "复盘完成"),
        ("adjusted", "计划调整"),
    ]

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="pathway_events",
        verbose_name="用户",
    )
    plan = models.ForeignKey(
        PathwayPlan,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="关联计划",
    )
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        verbose_name="事件类型",
    )
    payload_json = models.JSONField(default=dict, verbose_name="事件详情")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "pathway_events"
        verbose_name = "路径事件"
        verbose_name_plural = "路径事件"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["plan", "event_type"]),
        ]


class PathwayGenerationJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "排队中"),
        ("running", "生成中"),
        ("success", "成功"),
        ("failed", "失败"),
    ]

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="pathway_generation_jobs",
        verbose_name="用户",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="任务状态",
    )
    cycle_days = models.IntegerField(default=7, verbose_name="周期天数")
    current_day = models.IntegerField(default=0, verbose_name="当前生成到第几天")
    total_days = models.IntegerField(default=7, verbose_name="总天数")
    progress_percent = models.IntegerField(default=0, verbose_name="进度百分比")
    message = models.CharField(max_length=255, blank=True, default="", verbose_name="状态文案")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")
    plan = models.ForeignKey(
        PathwayPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_jobs",
        verbose_name="生成结果计划",
    )
    meta_json = models.JSONField(default=dict, verbose_name="元信息")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")

    class Meta:
        db_table = "pathway_generation_jobs"
        verbose_name = "路径生成任务"
        verbose_name_plural = "路径生成任务"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["created_at"]),
        ]


class PathwayExternalResource(models.Model):
    FOCUS_AREA_CHOICES = [
        ("technical", "技术能力"),
        ("scenario", "场景题"),
        ("project", "项目题"),
        ("expression", "表达能力"),
        ("general", "通用"),
    ]
    RESOURCE_TYPE_CHOICES = [
        ("official", "官方文档"),
        ("blog", "深度博客"),
        ("video", "视频/交互"),
        ("mock", "模拟面试"),
        ("behavioral", "行为面试"),
        ("communication", "沟通表达"),
    ]

    title = models.CharField(max_length=300, verbose_name="资源标题")
    url = models.URLField(verbose_name="资源链接")
    focus_area = models.CharField(max_length=20, choices=FOCUS_AREA_CHOICES, default="technical", verbose_name="适用能力域")
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES, default="official", verbose_name="资源类型")
    topic = models.CharField(max_length=120, blank=True, default="", verbose_name="主题")
    tags = models.JSONField(default=list, verbose_name="标签")
    priority = models.IntegerField(default=1, verbose_name="推荐优先级")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "pathway_external_resources"
        verbose_name = "路径外部资源"
        verbose_name_plural = "路径外部资源"
        ordering = ["priority", "id"]
        indexes = [
            models.Index(fields=["focus_area", "is_active", "priority"]),
        ]

    def __str__(self):
        return self.title
