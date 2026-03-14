from django.contrib import admin
from .models import Evaluation, VoiceAnalysis


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ['interview', 'overall_score', 'technical_score', 'communication_score', 'logic_score', 'created_at']
    list_filter = ['overall_score']
    search_fields = ['interview__user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(VoiceAnalysis)
class VoiceAnalysisAdmin(admin.ModelAdmin):
    list_display = ['round', 'duration_seconds', 'speech_rate', 'clarity_score', 'confidence_score', 'emotion']
    list_filter = ['emotion']
    search_fields = ['round__interview__user__username', 'transcript']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
