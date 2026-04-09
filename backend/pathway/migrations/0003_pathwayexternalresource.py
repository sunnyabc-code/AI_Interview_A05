from django.db import migrations, models


def seed_external_resources(apps, schema_editor):
    Resource = apps.get_model("pathway", "PathwayExternalResource")
    rows = [
        {"title": "Redis 官方文档", "url": "https://redis.io/docs", "focus_area": "technical", "resource_type": "official", "topic": "Redis", "priority": 1},
        {"title": "MySQL 官方文档", "url": "https://dev.mysql.com/doc", "focus_area": "technical", "resource_type": "official", "topic": "MySQL", "priority": 1},
        {"title": "OpenJDK HotSpot 文档", "url": "https://openjdk.org/groups/hotspot/", "focus_area": "technical", "resource_type": "official", "topic": "JVM", "priority": 1},
        {"title": "Spring Boot 官方项目页", "url": "https://spring.io/projects/spring-boot", "focus_area": "technical", "resource_type": "official", "topic": "SpringBoot", "priority": 2},
        {"title": "Refactoring Guru 设计模式", "url": "https://refactoring.guru/design-patterns", "focus_area": "technical", "resource_type": "official", "topic": "设计模式", "priority": 2},
        {"title": "Attention Is All You Need", "url": "https://arxiv.org/abs/1706.03762", "focus_area": "technical", "resource_type": "official", "topic": "Transformer", "priority": 2},
        {"title": "LlamaIndex Docs", "url": "https://docs.llamaindex.ai/", "focus_area": "technical", "resource_type": "official", "topic": "RAG", "priority": 2},
        {"title": "NVIDIA NCCL Docs", "url": "https://docs.nvidia.com/deeplearning/nccl/", "focus_area": "technical", "resource_type": "official", "topic": "分布式训练", "priority": 3},
        {"title": "Interviewing.io Blog", "url": "https://interviewing.io/blog", "focus_area": "scenario", "resource_type": "mock", "topic": "模拟面试", "priority": 1},
        {"title": "Exponent 模拟面试频道", "url": "https://www.youtube.com/@ExponentTV", "focus_area": "scenario", "resource_type": "video", "topic": "模拟面试", "priority": 1},
        {"title": "Pramp 平台", "url": "https://www.pramp.com/", "focus_area": "scenario", "resource_type": "mock", "topic": "模拟面试", "priority": 2},
        {"title": "IGotAnOffer 技术面试", "url": "https://igotanoffer.com/blogs/tech", "focus_area": "scenario", "resource_type": "blog", "topic": "面试评分", "priority": 2},
        {"title": "System Design Primer", "url": "https://github.com/donnemartin/system-design-primer", "focus_area": "project", "resource_type": "official", "topic": "系统设计", "priority": 1},
        {"title": "ByteByteGo Blog", "url": "https://blog.bytebytego.com/", "focus_area": "project", "resource_type": "blog", "topic": "系统设计表达", "priority": 1},
        {"title": "AlgoExpert YouTube", "url": "https://www.youtube.com/@algoexpert", "focus_area": "project", "resource_type": "video", "topic": "白板沟通", "priority": 2},
        {"title": "NeetCode", "url": "https://neetcode.io/", "focus_area": "project", "resource_type": "video", "topic": "算法表达", "priority": 2},
        {"title": "Harvard Interviewing 101", "url": "https://careerservices.fas.harvard.edu/resources/interviewing-101/", "focus_area": "expression", "resource_type": "behavioral", "topic": "STAR", "priority": 1},
        {"title": "Amazon Interviewing 指南", "url": "https://www.amazon.jobs/content/en/how-we-hire/interviewing-at-amazon", "focus_area": "expression", "resource_type": "behavioral", "topic": "行为面试", "priority": 1},
        {"title": "The Muse 行为面试", "url": "https://www.themuse.com/advice/behavioral-interview-questions-answers-examples", "focus_area": "expression", "resource_type": "behavioral", "topic": "行为面试", "priority": 2},
        {"title": "CareerVidz", "url": "https://www.youtube.com/@CareerVidz", "focus_area": "expression", "resource_type": "video", "topic": "表达训练", "priority": 2},
        {"title": "Oxford Online English", "url": "https://www.youtube.com/@Oxfordonlineenglish1", "focus_area": "expression", "resource_type": "communication", "topic": "英语职场沟通", "priority": 3},
        {"title": "Coursera Successful Interviewing", "url": "https://www.coursera.org/learn/interview-research", "focus_area": "expression", "resource_type": "communication", "topic": "面试心理学", "priority": 3},
    ]

    for row in rows:
        Resource.objects.get_or_create(
            title=row["title"],
            defaults={
                "url": row["url"],
                "focus_area": row["focus_area"],
                "resource_type": row["resource_type"],
                "topic": row["topic"],
                "priority": row["priority"],
                "tags": [],
                "is_active": True,
            },
        )


def unseed_external_resources(apps, schema_editor):
    Resource = apps.get_model("pathway", "PathwayExternalResource")
    titles = [
        "Redis 官方文档",
        "MySQL 官方文档",
        "OpenJDK HotSpot 文档",
        "Spring Boot 官方项目页",
        "Refactoring Guru 设计模式",
        "Attention Is All You Need",
        "LlamaIndex Docs",
        "NVIDIA NCCL Docs",
        "Interviewing.io Blog",
        "Exponent 模拟面试频道",
        "Pramp 平台",
        "IGotAnOffer 技术面试",
        "System Design Primer",
        "ByteByteGo Blog",
        "AlgoExpert YouTube",
        "NeetCode",
        "Harvard Interviewing 101",
        "Amazon Interviewing 指南",
        "The Muse 行为面试",
        "CareerVidz",
        "Oxford Online English",
        "Coursera Successful Interviewing",
    ]
    Resource.objects.filter(title__in=titles).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pathway", "0002_pathwaygenerationjob"),
    ]

    operations = [
        migrations.CreateModel(
            name="PathwayExternalResource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=300, verbose_name="资源标题")),
                ("url", models.URLField(verbose_name="资源链接")),
                ("focus_area", models.CharField(choices=[("technical", "技术能力"), ("scenario", "场景题"), ("project", "项目题"), ("expression", "表达能力"), ("general", "通用")], default="technical", max_length=20, verbose_name="适用能力域")),
                ("resource_type", models.CharField(choices=[("official", "官方文档"), ("blog", "深度博客"), ("video", "视频/交互"), ("mock", "模拟面试"), ("behavioral", "行为面试"), ("communication", "沟通表达")], default="official", max_length=20, verbose_name="资源类型")),
                ("topic", models.CharField(blank=True, default="", max_length=120, verbose_name="主题")),
                ("tags", models.JSONField(default=list, verbose_name="标签")),
                ("priority", models.IntegerField(default=1, verbose_name="推荐优先级")),
                ("is_active", models.BooleanField(default=True, verbose_name="是否启用")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "路径外部资源",
                "verbose_name_plural": "路径外部资源",
                "db_table": "pathway_external_resources",
                "ordering": ["priority", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="pathwayexternalresource",
            index=models.Index(fields=["focus_area", "is_active", "priority"], name="pathway_ext_focus_i_0e657d_idx"),
        ),
        migrations.RunPython(seed_external_resources, unseed_external_resources),
    ]
