from django.contrib import admin
from .models import LearningResource, LearningPath, LearningPathItem


@admin.register(LearningResource)
class LearningResourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'resource_type', 'position', 'difficulty', 'is_active']
    list_filter = ['resource_type', 'position', 'difficulty', 'is_active']
    search_fields = ['title', 'content']
    ordering = ['-created_at']
    
    filter_horizontal = ['knowledge_points']


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'position', 'progress', 'is_completed']
    list_filter = ['position', 'is_completed']
    search_fields = ['title', 'user__username']
    ordering = ['-created_at']


@admin.register(LearningPathItem)
class LearningPathItemAdmin(admin.ModelAdmin):
    list_display = ['learning_path', 'resource', 'order', 'is_completed']
    list_filter = ['is_completed']
    search_fields = ['learning_path__title', 'resource__title']
    ordering = ['learning_path', 'order']
