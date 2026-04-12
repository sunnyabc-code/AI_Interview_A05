from rest_framework import serializers
from interviews.models import Interview, InterviewRound
from positions.models import JobPosition
from evaluations.models import DifficultyConfig
from user_projects.models import UserProject


class InterviewCreateSerializer(serializers.Serializer):
    position = serializers.PrimaryKeyRelatedField(queryset=JobPosition.objects.all())
    name = serializers.CharField(required=False, allow_blank=True, default="")
    mode = serializers.ChoiceField(
        choices=[choice[0] for choice in Interview.MODE_CHOICES],
        required=False,
        default="text",
    )
    total_rounds = serializers.IntegerField(required=False, min_value=0, default=0)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    difficulty_config = serializers.PrimaryKeyRelatedField(
        queryset=DifficultyConfig.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )
    enable_technical_questions = serializers.BooleanField(required=False, default=True)
    enable_project_questions = serializers.BooleanField(required=False, default=True)
    enable_scenario_questions = serializers.BooleanField(required=False, default=True)

    def calculate_total_rounds(self, validated_data):
        difficulty_config = validated_data.get("difficulty_config")
        enable_technical = validated_data.get("enable_technical_questions", True)
        enable_project = validated_data.get("enable_project_questions", True)
        enable_scenario = validated_data.get("enable_scenario_questions", True)

        if not difficulty_config:
            return 0

        total_rounds = 0

        if enable_technical:
            technical_count = getattr(difficulty_config, "technical_chain_count", 0)
            technical_depth = getattr(
                difficulty_config, "technical_max_followup_depth", 1
            )
            total_rounds += technical_count * technical_depth

        if enable_project:
            project_count = getattr(difficulty_config, "project_chain_count", 0)
            project_depth = getattr(difficulty_config, "project_max_followup_depth", 1)
            total_rounds += project_count * project_depth

        if enable_scenario:
            scenario_count = getattr(difficulty_config, "scenario_chain_count", 0)
            scenario_depth = getattr(
                difficulty_config, "scenario_max_followup_depth", 1
            )
            total_rounds += scenario_count * scenario_depth

        return total_rounds

    def validate(self, attrs):
        difficulty_config = attrs.get("difficulty_config")

        if not attrs.get("total_rounds"):
            attrs["total_rounds"] = self.calculate_total_rounds(attrs)

        request = self.context.get("request")
        enable_project = attrs.get("enable_project_questions", True)
        position = attrs.get("position")

        if (
            request
            and getattr(request, "user", None)
            and request.user.is_authenticated
            and enable_project
            and position
        ):
            if not UserProject.objects.filter(
                user=request.user, position_id=position.id
            ).exists():
                raise serializers.ValidationError(
                    {
                        "enable_project_questions": "已勾选项目经历题，请先在个人中心为该岗位填写至少一条项目经历后再创建面试。"
                    }
                )

        return attrs


class InterviewSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True)
    difficulty_config_id = serializers.IntegerField(
        source="difficulty_config.id", read_only=True, allow_null=True
    )
    difficulty_name = serializers.CharField(
        source="difficulty_config.difficulty_name", read_only=True, allow_null=True
    )

    class Meta:
        model = Interview
        fields = [
            "id",
            "user_id",
            "name",
            "position",
            "position_name",
            "difficulty_config",
            "difficulty_config_id",
            "difficulty_name",
            "status",
            "mode",
            "start_time",
            "end_time",
            "duration_seconds",
            "total_rounds",
            "enable_technical_questions",
            "enable_project_questions",
            "enable_scenario_questions",
            "notes",
            "created_at",
            "updated_at",
        ]


class InterviewUpdateSerializer(serializers.Serializer):
    position = serializers.PrimaryKeyRelatedField(
        queryset=JobPosition.objects.all(), required=False
    )
    difficulty_config = serializers.PrimaryKeyRelatedField(
        queryset=DifficultyConfig.objects.all(),
        required=False,
        allow_null=True,
    )
    status = serializers.ChoiceField(
        choices=[choice[0] for choice in Interview.STATUS_CHOICES], required=False
    )
    mode = serializers.ChoiceField(
        choices=[choice[0] for choice in Interview.MODE_CHOICES], required=False
    )
    total_rounds = serializers.IntegerField(required=False, min_value=0)
    duration_seconds = serializers.IntegerField(required=False, min_value=0)
    name = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    enable_technical_questions = serializers.BooleanField(required=False)
    enable_project_questions = serializers.BooleanField(required=False)
    enable_scenario_questions = serializers.BooleanField(required=False)


class NextQuestionRequestSerializer(serializers.Serializer):
    force_category = serializers.ChoiceField(
        choices=["technical", "project", "scenario"],
        required=False,
        allow_null=True,
        default=None,
    )


class InterviewRoundSerializer(serializers.Serializer):
    round_id = serializers.IntegerField(required=False, allow_null=True)
    interview_id = serializers.IntegerField()
    round_number = serializers.IntegerField(required=False, allow_null=True)
    chain_index = serializers.IntegerField()
    followup_depth = serializers.IntegerField()
    category = serializers.CharField(allow_null=True)
    category_name = serializers.CharField(allow_null=True)
    question_id = serializers.IntegerField(allow_null=True)
    question_content = serializers.CharField(allow_blank=True)
    answer_time_seconds = serializers.IntegerField(allow_null=True)
    start_time = serializers.DateTimeField(required=False, allow_null=True)
    need_llm_generation = serializers.BooleanField(required=False, default=False)
    question_source = serializers.CharField(required=False)
    llm_prompt = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    chain_topic_label = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    job_knowledge_serial = serializers.IntegerField(
        required=False, allow_null=True
    )
    user_project_id = serializers.IntegerField(required=False, allow_null=True)


class InterviewRoundAnswerRequestSerializer(serializers.Serializer):
    user_answer = serializers.CharField(required=True, allow_blank=False)


class InterviewRoundAnswerResponseSerializer(serializers.Serializer):
    interview_id = serializers.IntegerField()
    round_id = serializers.IntegerField()
    round_number = serializers.IntegerField()
    chain_index = serializers.IntegerField()
    followup_depth = serializers.IntegerField()
    category = serializers.CharField(allow_null=True)
    category_name = serializers.CharField(allow_null=True)
    question_id = serializers.IntegerField(allow_null=True)
    question_content = serializers.CharField(allow_blank=True)
    user_answer = serializers.CharField()
    end_time = serializers.DateTimeField(allow_null=True)
    already_answered = serializers.BooleanField(default=False)


class InterviewRoundAnalysisSerializer(serializers.Serializer):
    """轮次分析数据序列化器"""

    overall_score = serializers.FloatField(allow_null=True)
    overall_comment = serializers.CharField(allow_blank=True)
    technical_score = serializers.FloatField(allow_null=True)
    communication_score = serializers.FloatField(allow_null=True)
    logic_score = serializers.FloatField(allow_null=True)
    adaptability_score = serializers.FloatField(allow_null=True)
    job_matching_score = serializers.FloatField(allow_null=True, required=False)
    highlights = serializers.ListField(child=serializers.CharField(), default=list)
    weaknesses = serializers.ListField(child=serializers.CharField(), default=list)
    suggestions = serializers.ListField(child=serializers.CharField(), default=list)


class InterviewRoundListSerializer(serializers.ModelSerializer):
    round_id = serializers.IntegerField(source="id", read_only=True)
    interview_id = serializers.IntegerField(source="interview.id", read_only=True)
    category = serializers.CharField(
        source="category.code", read_only=True, allow_null=True
    )
    category_name = serializers.CharField(
        source="category.name", read_only=True, allow_null=True
    )
    question_id = serializers.IntegerField(
        source="question.id", read_only=True, allow_null=True
    )
    audio_file_url = serializers.CharField(
        source="audio.file_url", read_only=True, allow_blank=True, allow_null=True
    )
    analysis = serializers.SerializerMethodField()
    asr_status = serializers.SerializerMethodField()

    class Meta:
        model = InterviewRound
        fields = [
            "round_id",
            "interview_id",
            "round_number",
            "chain_index",
            "followup_depth",
            "category",
            "category_name",
            "question_id",
            "question_content",
            "user_answer",
            "audio_file_url",
            "asr_status",
            "start_time",
            "end_time",
            "created_at",
            "analysis",
        ]

    def _to_nullable_float(self, value):
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_text(self, value):
        if value is None:
            return ""
        return str(value)

    def _to_text_list(self, value):
        if value is None:
            return []

        if isinstance(value, list):
            return [
                str(item) for item in value if item is not None and str(item).strip()
            ]

        if isinstance(value, dict):
            return [f"{key}: {item}" for key, item in value.items()]

        text = str(value).strip()
        return [text] if text else []

    def get_asr_status(self, obj):
        audio = getattr(obj, "audio", None)
        if not audio:
            return ""
        return (getattr(audio, "asr_status", None) or "").strip()

    def get_analysis(self, obj):
        """获取关联的轮次分析数据，并兼容历史脏数据类型。"""
        try:
            analysis = obj.analysis
        except Exception:
            return None

        if not analysis:
            return None

        return {
            "overall_score": self._to_nullable_float(
                getattr(analysis, "overall_score", None)
            ),
            "overall_comment": self._to_text(getattr(analysis, "overall_comment", "")),
            "technical_score": self._to_nullable_float(
                getattr(analysis, "technical_score", None)
            ),
            "communication_score": self._to_nullable_float(
                getattr(analysis, "communication_score", None)
            ),
            "logic_score": self._to_nullable_float(
                getattr(analysis, "logic_score", None)
            ),
            "adaptability_score": self._to_nullable_float(
                getattr(analysis, "adaptability_score", None)
            ),
            "job_matching_score": self._to_nullable_float(
                getattr(analysis, "job_matching_score", None)
            ),
            "highlights": self._to_text_list(getattr(analysis, "highlights", [])),
            "weaknesses": self._to_text_list(getattr(analysis, "weaknesses", [])),
            "suggestions": self._to_text_list(getattr(analysis, "suggestions", [])),
        }


class InterviewRoundAudioUploadRequestSerializer(serializers.Serializer):
    audio_file = serializers.FileField(required=True)
    duration_seconds = serializers.FloatField(required=False, min_value=0)
    codec = serializers.CharField(required=False, allow_blank=True, max_length=50)
    sample_rate = serializers.IntegerField(required=False, min_value=1)
    channels = serializers.IntegerField(required=False, min_value=1)


class InterviewRoundAudioUploadResponseSerializer(serializers.Serializer):
    audio_id = serializers.IntegerField()
    interview_id = serializers.IntegerField()
    round_id = serializers.IntegerField()
    file_name = serializers.CharField()
    file_key = serializers.CharField()
    file_url = serializers.CharField()
    mime_type = serializers.CharField(allow_blank=True)
    file_size_bytes = serializers.IntegerField()
    duration_seconds = serializers.FloatField(allow_null=True)
    codec = serializers.CharField(allow_blank=True)
    sample_rate = serializers.IntegerField(allow_null=True)
    channels = serializers.IntegerField(allow_null=True)
    upload_status = serializers.CharField()
    asr_status = serializers.CharField()
    analysis_status = serializers.CharField()
    imentiv_analysis_status = serializers.CharField()
    imentiv_error_message = serializers.CharField(allow_blank=True)
    transcript = serializers.CharField(allow_blank=True, required=False)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
