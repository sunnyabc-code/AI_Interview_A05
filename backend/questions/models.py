from django.db import models


class QuestionCategory(models.Model):
    CATEGORY_CHOICES = [
        ('technical', '技术知识'),
        ('project', '项目经历'),
        ('scenario', '场景题'),
        ('behavioral', '行为题'),
    ]

    code = models.CharField(max_length=50, unique=True, choices=CATEGORY_CHOICES, verbose_name='分类代码')
    name = models.CharField(max_length=100, verbose_name='分类名称')
    description = models.TextField(blank=True, verbose_name='分类描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'question_categories'
        verbose_name = '题目分类'
        verbose_name_plural = '题目分类'

    def __str__(self):
        return self.name


class KnowledgePoint(models.Model):
    name = models.CharField(max_length=200, verbose_name='知识点名称')
    description = models.TextField(blank=True, verbose_name='知识点描述')
    position = models.ForeignKey('positions.JobPosition', on_delete=models.CASCADE, related_name='knowledge_points', verbose_name='所属岗位')
    difficulty = models.IntegerField(default=1, verbose_name='难度等级')
    vector_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='向量ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'knowledge_points'
        verbose_name = '知识点'
        verbose_name_plural = '知识点'

    def __str__(self):
        return self.name


class Question(models.Model):
    DIFFICULTY_CHOICES = [
        (1, '初级'),
        (2, '中级'),
        (3, '高级'),
    ]

    position = models.ForeignKey('positions.JobPosition', on_delete=models.CASCADE, related_name='questions', verbose_name='岗位')
    category = models.ForeignKey(QuestionCategory, on_delete=models.CASCADE, related_name='questions', verbose_name='分类')
    knowledge_points = models.ManyToManyField(KnowledgePoint, related_name='questions', blank=True, verbose_name='关联知识点')
    
    title = models.CharField(max_length=300, verbose_name='题目标题')
    content = models.TextField(verbose_name='题目内容')
    reference_answer = models.TextField(blank=True, verbose_name='参考答案')
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES, default=1, verbose_name='难度')
    tags = models.JSONField(default=list, verbose_name='标签')
    follow_up_questions = models.JSONField(default=list, blank=True, verbose_name='追问模板')
    
    usage_count = models.IntegerField(default=0, verbose_name='使用次数')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'questions'
        verbose_name = '面试题'
        verbose_name_plural = '面试题'

    def __str__(self):
        return self.title
