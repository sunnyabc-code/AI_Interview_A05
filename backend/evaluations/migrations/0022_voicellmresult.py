from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("interviews", "0013_interviewround_chain_topic_job_knowledge"),
        ("evaluations", "0021_create_user_knowledge_matrics"),
    ]

    operations = [
        migrations.CreateModel(
            name="VoiceLLMResult",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "待处理"),
                            ("running", "处理中"),
                            ("success", "成功"),
                            ("failed", "失败"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="生成状态",
                    ),
                ),
                (
                    "overall_audio_score",
                    models.DecimalField(
                        decimal_places=1,
                        default=0,
                        max_digits=5,
                        verbose_name="整体音频表现评分",
                    ),
                ),
                (
                    "speech_rate_and_rhythm_score",
                    models.DecimalField(
                        decimal_places=1,
                        default=0,
                        max_digits=5,
                        verbose_name="语速与面试节奏评分",
                    ),
                ),
                (
                    "speech_rate_and_rhythm",
                    models.TextField(blank=True, verbose_name="语速与面试节奏"),
                ),
                (
                    "fluency_score",
                    models.DecimalField(
                        decimal_places=1,
                        default=0,
                        max_digits=5,
                        verbose_name="回答流畅度评分",
                    ),
                ),
                ("fluency", models.TextField(blank=True, verbose_name="回答流畅度")),
                (
                    "confidence_and_voice_energy_score",
                    models.DecimalField(
                        decimal_places=1,
                        default=0,
                        max_digits=5,
                        verbose_name="自信度与声音能量评分",
                    ),
                ),
                (
                    "confidence_and_voice_energy",
                    models.TextField(blank=True, verbose_name="自信度与声音能量"),
                ),
                (
                    "emotional_stability_and_tone_score",
                    models.DecimalField(
                        decimal_places=1,
                        default=0,
                        max_digits=5,
                        verbose_name="情感稳定性与语气评分",
                    ),
                ),
                (
                    "emotional_stability_and_tone",
                    models.TextField(blank=True, verbose_name="情感稳定性与语气"),
                ),
                ("strengths", models.TextField(blank=True, verbose_name="你的优势亮点")),
                ("improvements", models.TextField(blank=True, verbose_name="改进建议")),
                (
                    "position_communication_tips",
                    models.TextField(blank=True, verbose_name="针对岗位的沟通提升点"),
                ),
                ("encouragement", models.TextField(blank=True, verbose_name="鼓励语")),
                (
                    "llm_model",
                    models.CharField(blank=True, max_length=120, verbose_name="模型名称"),
                ),
                (
                    "prompt_version",
                    models.CharField(
                        default="voice_llm_v1",
                        max_length=40,
                        verbose_name="Prompt版本",
                    ),
                ),
                (
                    "raw_input_json",
                    models.JSONField(default=dict, verbose_name="模型输入快照"),
                ),
                (
                    "raw_output_json",
                    models.JSONField(default=dict, verbose_name="模型输出快照"),
                ),
                (
                    "generated_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="结果时间"),
                ),
                ("error_message", models.TextField(blank=True, verbose_name="错误信息")),
                ("retry_count", models.IntegerField(default=0, verbose_name="重试次数")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "interview",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voice_llm_result",
                        to="interviews.interview",
                        verbose_name="面试",
                    ),
                ),
            ],
            options={
                "verbose_name": "面试音频大模型总结",
                "verbose_name_plural": "面试音频大模型总结",
                "db_table": "voice_llm_results",
            },
        ),
    ]
