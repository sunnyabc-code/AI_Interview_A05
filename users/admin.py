from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'phone', 'target_position', 'interview_count', 'is_active']
    list_filter = ['is_active', 'is_staff', 'target_position']
    search_fields = ['username', 'email', 'phone']
    ordering = ['-created_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('额外信息', {'fields': ('phone', 'avatar', 'target_position', 'interview_count')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('额外信息', {'fields': ('phone', 'target_position')}),
    )
