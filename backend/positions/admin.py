from django.contrib import admin
from .models import JobPosition


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'created_at']
    list_filter = ['code']
    search_fields = ['name', 'code']
    ordering = ['-created_at']
