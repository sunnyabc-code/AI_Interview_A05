from rest_framework import serializers
from interviews.models import Interview
from positions.models import JobPosition
from evaluations.models import DifficultyConfig


class InterviewCreateSerializer(serializers.Serializer):
    position = serializers.PrimaryKeyRelatedField(queryset=JobPosition.objects.all())
    mode = serializers.ChoiceField(choices=[choice[0] for choice in Interview.MODE_CHOICES], required=False, default='text')
    total_rounds = serializers.IntegerField(required=False, min_value=0, default=0)
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    difficulty_config = serializers.PrimaryKeyRelatedField(
        queryset=DifficultyConfig.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )
    enable_technical_questions = serializers.BooleanField(required=False, default=True)
    enable_project_questions = serializers.BooleanField(required=False, default=True)
    enable_scenario_questions = serializers.BooleanField(required=False, default=True)


class InterviewSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    position_name = serializers.CharField(source='position.name', read_only=True)
    difficulty_config_id = serializers.IntegerField(source='difficulty_config.id', read_only=True, allow_null=True)

    class Meta:
        model = Interview
        fields = [
            'id',
            'user_id',
            'position',
            'position_name',
            'difficulty_config',
            'difficulty_config_id',
            'status',
            'mode',
            'start_time',
            'end_time',
            'duration_seconds',
            'total_rounds',
            'enable_technical_questions',
            'enable_project_questions',
            'enable_scenario_questions',
            'notes',
            'created_at',
            'updated_at',
        ]


class InterviewUpdateSerializer(serializers.Serializer):
    position = serializers.PrimaryKeyRelatedField(queryset=JobPosition.objects.all(), required=False)
    difficulty_config = serializers.PrimaryKeyRelatedField(
        queryset=DifficultyConfig.objects.all(),
        required=False,
        allow_null=True,
    )
    status = serializers.ChoiceField(choices=[choice[0] for choice in Interview.STATUS_CHOICES], required=False)
    mode = serializers.ChoiceField(choices=[choice[0] for choice in Interview.MODE_CHOICES], required=False)
    total_rounds = serializers.IntegerField(required=False, min_value=0)
    duration_seconds = serializers.IntegerField(required=False, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True)

    enable_technical_questions = serializers.BooleanField(required=False)
    enable_project_questions = serializers.BooleanField(required=False)
    enable_scenario_questions = serializers.BooleanField(required=False)
