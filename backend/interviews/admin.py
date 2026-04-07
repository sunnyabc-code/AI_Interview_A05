from django.contrib import admin
from .models import (
    Interview,
    InterviewRound,
    InterviewRoundAnalysis,
    InterviewRoundAudio,
)


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "position",
        "difficulty_config",
        "status",
        "mode",
        "total_rounds",
        "enable_technical_questions",
        "enable_project_questions",
        "enable_scenario_questions",
        "start_time",
        "duration_seconds",
    ]
    list_filter = [
        "status",
        "mode",
        "position",
        "difficulty_config",
        "enable_technical_questions",
        "enable_project_questions",
        "enable_scenario_questions",
    ]
    search_fields = ["user__username", "position__name"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(InterviewRound)
class InterviewRoundAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "interview",
        "round_number",
        "category",
        "question",
        "start_time",
    ]
    list_filter = ["category", "question"]
    search_fields = [
        "interview__user__username",
        "question__title",
        "question_content",
        "user_answer",
    ]
    ordering = ["interview", "round_number"]


@admin.register(InterviewRoundAnalysis)
class InterviewRoundAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "round",
        "overall_score",
        "technical_score",
        "communication_score",
        "logic_score",
        "job_matching_score",
        "created_at",
    ]
    search_fields = ["round__interview__user__username", "overall_comment"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(InterviewRoundAudio)
class InterviewRoundAudioAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "round",
        "uploaded_by",
        "file_name",
        "upload_status",
        "asr_status",
        "analysis_status",
        "imentiv_analysis_status",
        "created_at",
    ]
    list_filter = [
        "upload_status",
        "asr_status",
        "analysis_status",
        "imentiv_analysis_status",
    ]
    search_fields = ["round__interview__user__username", "file_name", "file_key"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]
