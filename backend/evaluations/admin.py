from django.contrib import admin
from .models import DifficultyConfig, Evaluation, VoiceAnalysis


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "interview",
        "overall_score",
        "technical_score",
        "communication_score",
        "logic_score",
        "created_at",
    ]
    list_filter = ["overall_score"]
    search_fields = ["interview__user__username"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(VoiceAnalysis)
class VoiceAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "round",
        "audio",
        "speech_rate",
        "audio_clarity_score",
        "asr_confidence",
        "overall_clarity",
        "confidence_score",
        "filler_word_total",
        "rms_cv",
        "silence_ratio",
        "created_at",
    ]
    list_filter = ["emotion"]
    search_fields = [
        "round__interview__user__username",
        "audio__file_name",
        "audio__file_key",
    ]
    ordering = ["-created_at"]
    readonly_fields = ["created_at"]


@admin.register(DifficultyConfig)
class DifficultyConfigAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "difficulty_code",
        "difficulty_name",
        "answer_time_seconds",
        "technical_chain_count",
        "project_chain_count",
        "scenario_chain_count",
        "updated_at",
    ]
    list_filter = ["difficulty_code"]
    search_fields = ["difficulty_code", "difficulty_name"]
    ordering = ["id"]
    readonly_fields = ["created_at", "updated_at"]
