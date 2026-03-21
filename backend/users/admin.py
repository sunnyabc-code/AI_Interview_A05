from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'phone', 'is_staff', 'is_active', 'interview_count', 'created_at']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'groups']
    search_fields = ['username', 'email', 'phone']
    ordering = ['-created_at']
    filter_horizontal = ['groups', 'user_permissions', 'target_positions']
    
    # 编辑页面字段分组
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('email', 'phone', 'avatar', 'target_positions')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
        ('面试统计', {'fields': ('interview_count',)}),
    )
    
    # 添加用户页面字段
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'phone'),
        }),
    )

    def get_queryset(self, request):
        """确保超级用户能看到所有用户"""
        qs = super().get_queryset(request)
        return qs

    def has_view_permission(self, request, obj=None):
        """允许查看权限"""
        return True

    def has_change_permission(self, request, obj=None):
        """允许修改权限"""
        return request.user.is_staff or request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """允许删除权限"""
        return request.user.is_superuser

    def has_add_permission(self, request):
        """允许添加权限"""
        return request.user.is_staff or request.user.is_superuser