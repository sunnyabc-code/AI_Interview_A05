from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'phone', 'target_positions_display', 'interview_count', 'is_active']
    list_filter = ['is_active', 'is_staff', 'target_positions']
    search_fields = ['username', 'email', 'phone']
    ordering = ['-created_at']
    filter_horizontal = ['target_positions']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('额外信息', {'fields': ('phone', 'avatar', 'target_positions', 'interview_count')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('额外信息', {'fields': ('phone', 'target_positions')}),
    )

    def target_positions_display(self, obj):
        return '、'.join(obj.target_positions.values_list('name', flat=True)) or '-'

    target_positions_display.short_description = '目标岗位'
