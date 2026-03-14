from django.contrib import admin
from .models import Interview, InterviewRound, InterviewMessage


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'position', 'status', 'mode', 'start_time', 'duration_seconds']
    list_filter = ['status', 'mode', 'position']
    search_fields = ['user__username', 'position__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InterviewRound)
class InterviewRoundAdmin(admin.ModelAdmin):
    list_display = ['interview', 'round_number', 'category', 'start_time']
    list_filter = ['category']
    search_fields = ['interview__user__username']
    ordering = ['interview', 'round_number']


@admin.register(InterviewMessage)
class InterviewMessageAdmin(admin.ModelAdmin):
    list_display = ['interview', 'role', 'message_type', 'sequence', 'created_at']
    list_filter = ['role', 'message_type']
    search_fields = ['content']
    ordering = ['sequence']
    readonly_fields = ['created_at']
