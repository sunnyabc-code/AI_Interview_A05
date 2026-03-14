from django.contrib import admin
from .models import Evaluation, DimensionScore, VoiceAnalysis


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ['interview', 'overall_score', 'technical_score', 'communication_score', 'logic_score', 'created_at']
    list_filter = ['overall_score']
    search_fields = ['interview__user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DimensionScore)
class DimensionScoreAdmin(admin.ModelAdmin):
    list_display = ['evaluation', 'dimension', 'score', 'max_score']
    list_filter = ['dimension']
    search_fields = ['evaluation__interview__user__username', 'dimension__name']
    ordering = ['evaluation', 'dimension']


@admin.register(VoiceAnalysis)
class VoiceAnalysisAdmin(admin.ModelAdmin):
    list_display = ['message', 'duration_seconds', 'speech_rate', 'clarity_score', 'confidence_score', 'emotion']
    list_filter = ['emotion']
    search_fields = ['message__content']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
