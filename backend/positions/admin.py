from django.contrib import admin
from .models import JobPosition, JobKnowledge


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'created_at']
    list_filter = ['code']
    search_fields = ['name', 'code']
    ordering = ['-created_at']


@admin.register(JobKnowledge)
class JobKnowledgeAdmin(admin.ModelAdmin):
    list_display = ['id_job_knowledge', 'name', 'serial_number', 'job_id']
    list_filter = ['job_id']
    search_fields = ['name']
    ordering = ['job_id', 'serial_number']
