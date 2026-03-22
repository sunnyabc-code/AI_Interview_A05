from rest_framework import serializers
from interviews.models import Interview
from positions.models import JobPosition
from evaluations.models import DifficultyConfig


class InterviewCreateSerializer(serializers.Serializer):
    position = serializers.PrimaryKeyRelatedField(queryset=JobPosition.objects.all())
    name = serializers.CharField(required=False, allow_blank=True, default='')
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

    def calculate_total_rounds(self, validated_data):
        difficulty_config = validated_data.get('difficulty_config')
        enable_technical = validated_data.get('enable_technical_questions', True)
        enable_project = validated_data.get('enable_project_questions', True)
        enable_scenario = validated_data.get('enable_scenario_questions', True)
        
        if not difficulty_config:
            return 0
        
        total_rounds = 0
        
        if enable_technical:
            technical_count = getattr(difficulty_config, 'technical_chain_count', 0)
            technical_depth = getattr(difficulty_config, 'technical_max_followup_depth', 1)
            total_rounds += technical_count * technical_depth
        
        if enable_project:
            project_count = getattr(difficulty_config, 'project_chain_count', 0)
            project_depth = getattr(difficulty_config, 'project_max_followup_depth', 1)
            total_rounds += project_count * project_depth
        
        if enable_scenario:
            scenario_count = getattr(difficulty_config, 'scenario_chain_count', 0)
            scenario_depth = getattr(difficulty_config, 'scenario_max_followup_depth', 1)
            total_rounds += scenario_count * scenario_depth
        
        return total_rounds

    def validate(self, attrs):
        difficulty_config = attrs.get('difficulty_config')
        
        if not attrs.get('total_rounds'):
            attrs['total_rounds'] = self.calculate_total_rounds(attrs)
        
        return attrs


class InterviewSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    position_name = serializers.CharField(source='position.name', read_only=True)
    difficulty_config_id = serializers.IntegerField(source='difficulty_config.id', read_only=True, allow_null=True)

    class Meta:
        model = Interview
        fields = [
            'id',
            'user_id',
            'name',
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
    name = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    enable_technical_questions = serializers.BooleanField(required=False)
    enable_project_questions = serializers.BooleanField(required=False)
    enable_scenario_questions = serializers.BooleanField(required=False)
