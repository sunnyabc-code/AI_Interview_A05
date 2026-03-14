from django.contrib import admin
from .models import Interview, InterviewRound, InterviewRoundAnalysis


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'position', 'status', 'mode', 'total_rounds', 'start_time', 'duration_seconds']
    list_filter = ['status', 'mode', 'position']
    search_fields = ['user__username', 'position__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InterviewRound)
class InterviewRoundAdmin(admin.ModelAdmin):
    list_display = ['interview', 'round_number', 'category', 'question', 'start_time']
    list_filter = ['category', 'question']
    search_fields = ['interview__user__username', 'question__title', 'question_content', 'user_answer']
    ordering = ['interview', 'round_number']


@admin.register(InterviewRoundAnalysis)
class InterviewRoundAnalysisAdmin(admin.ModelAdmin):
    list_display = ['round', 'overall_score', 'technical_score', 'communication_score', 'logic_score', 'created_at']
    search_fields = ['round__interview__user__username', 'overall_comment']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
