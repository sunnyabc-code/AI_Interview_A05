from django.db import models


class Interview(models.Model):
    STATUS_CHOICES = [
        ('pending', '待开始'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    MODE_CHOICES = [
        ('text', '文本模式'),
        ('voice', '语音模式'),
        ('mixed', '混合模式'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='interviews', verbose_name='用户')
    position = models.ForeignKey('positions.JobPosition', on_delete=models.CASCADE, related_name='interviews', verbose_name='岗位')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='text', verbose_name='交互模式')
    
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration_seconds = models.IntegerField(default=0, verbose_name='时长(秒)')
    
    total_questions = models.IntegerField(default=0, verbose_name='总题数')
    answered_questions = models.IntegerField(default=0, verbose_name='已答题数')
    
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'interviews'
        verbose_name = '面试记录'
        verbose_name_plural = '面试记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.position.name}'


class InterviewRound(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='rounds', verbose_name='面试')
    round_number = models.IntegerField(verbose_name='轮次')
    category = models.ForeignKey('questions.QuestionCategory', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='题目分类')
    
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'interview_rounds'
        verbose_name = '面试轮次'
        verbose_name_plural = '面试轮次'
        unique_together = ['interview', 'round_number']

    def __str__(self):
        return f'{self.interview} - 第{self.round_number}轮'


class InterviewMessage(models.Model):
    ROLE_CHOICES = [
        ('interviewer', '面试官'),
        ('candidate', '候选人'),
        ('system', '系统'),
    ]

    MESSAGE_TYPE_CHOICES = [
        ('question', '问题'),
        ('answer', '回答'),
        ('follow_up', '追问'),
        ('feedback', '反馈'),
        ('system', '系统消息'),
    ]

    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='messages', verbose_name='面试')
    round = models.ForeignKey(InterviewRound, on_delete=models.CASCADE, related_name='messages', verbose_name='轮次')
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='角色')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, verbose_name='消息类型')
    
    content = models.TextField(verbose_name='内容')
    audio_file = models.CharField(max_length=500, blank=True, null=True, verbose_name='语音文件URL')
    
    question = models.ForeignKey('questions.Question', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联题目')
    
    sequence = models.IntegerField(verbose_name='序号')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'interview_messages'
        verbose_name = '面试消息'
        verbose_name_plural = '面试消息'
        ordering = ['sequence']

    def __str__(self):
        return f'{self.role}: {self.content[:50]}'
