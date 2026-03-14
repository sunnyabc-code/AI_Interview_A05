from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='手机号')
    avatar = models.CharField(max_length=500, blank=True, null=True, verbose_name='头像URL')
    target_position = models.ForeignKey('positions.JobPosition', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='目标岗位')
    interview_count = models.IntegerField(default=0, verbose_name='面试次数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.username
