from django.contrib import admin
from .models import Recommendation, UserProgress


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'recommendation_type', 'priority', 'is_completed', 'created_at']
    list_filter = ['recommendation_type', 'priority', 'is_completed']
    search_fields = ['title', 'user__username']
    ordering = ['-priority', '-created_at']


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_interviews', 'avg_overall_score', 'avg_technical_score', 'avg_communication_score']
    search_fields = ['user__username']
    ordering = ['-avg_overall_score']
    readonly_fields = ['created_at', 'updated_at']
