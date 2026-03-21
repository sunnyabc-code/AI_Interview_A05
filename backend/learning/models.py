from django.db import models


class LearningResource(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('article', '文章'),
        ('video', '视频'),
        ('book', '书籍'),
        ('course', '课程'),
        ('practice', '练习题'),
    ]

    title = models.CharField(max_length=300, verbose_name='资源标题')
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES, verbose_name='资源类型')
    
    url = models.URLField(blank=True, verbose_name='链接')
    content = models.TextField(blank=True, verbose_name='内容')
    
    knowledge_points = models.ManyToManyField('questions.KnowledgePoint', related_name='resources', blank=True, verbose_name='关联知识点')
    position = models.ForeignKey('positions.JobPosition', on_delete=models.CASCADE, related_name='resources', verbose_name='岗位')
    
    difficulty = models.IntegerField(default=1, verbose_name='难度')
    estimated_time = models.IntegerField(blank=True, null=True, verbose_name='预计学习时长(分钟)')
    
    tags = models.JSONField(default=list, verbose_name='标签')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'learning_resources'
        verbose_name = '学习资源'
        verbose_name_plural = '学习资源'

    def __str__(self):
        return self.title


class LearningPath(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='learning_paths', verbose_name='用户')
    position = models.ForeignKey('positions.JobPosition', on_delete=models.CASCADE, related_name='learning_paths', verbose_name='岗位')
    
    title = models.CharField(max_length=200, verbose_name='路径标题')
    description = models.TextField(verbose_name='描述')
    
    resources = models.ManyToManyField(LearningResource, through='LearningPathItem', verbose_name='资源')
    
    progress = models.FloatField(default=0, verbose_name='进度')
    is_completed = models.BooleanField(default=False, verbose_name='是否完成')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'learning_paths'
        verbose_name = '学习路径'
        verbose_name_plural = '学习路径'

    def __str__(self):
        return self.title


class LearningPathItem(models.Model):
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name='items', verbose_name='学习路径')
    resource = models.ForeignKey(LearningResource, on_delete=models.CASCADE, verbose_name='资源')
    
    order = models.IntegerField(verbose_name='顺序')
    is_completed = models.BooleanField(default=False, verbose_name='是否完成')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'learning_path_items'
        verbose_name = '学习路径项'
        verbose_name_plural = '学习路径项'
        unique_together = ['learning_path', 'resource']

    def __str__(self):
        return f'{self.learning_path} - {self.resource.title}'
