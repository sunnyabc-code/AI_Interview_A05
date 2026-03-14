from django.contrib import admin
from .models import JobPosition, PositionDimension


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    list_filter = ['code']
    search_fields = ['name', 'code']
    ordering = ['-created_at']


@admin.register(PositionDimension)
class PositionDimensionAdmin(admin.ModelAdmin):
    list_display = ['position', 'code', 'name', 'weight']
    list_filter = ['position', 'code']
    search_fields = ['name', 'position__name']
    ordering = ['position', 'code']
