from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'interview', 'created_at']
    search_fields = ['title', 'interview__user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
