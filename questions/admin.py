from django.contrib import admin
from .models import QuestionCategory, KnowledgePoint, Question


@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']
    ordering = ['code']


@admin.register(KnowledgePoint)
class KnowledgePointAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'difficulty', 'created_at']
    list_filter = ['position', 'difficulty']
    search_fields = ['name', 'description']
    ordering = ['position', 'name']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'position', 'category', 'difficulty', 'usage_count', 'is_active']
    list_filter = ['position', 'category', 'difficulty', 'is_active']
    search_fields = ['title', 'content']
    ordering = ['-created_at']
    
    filter_horizontal = ['knowledge_points']
