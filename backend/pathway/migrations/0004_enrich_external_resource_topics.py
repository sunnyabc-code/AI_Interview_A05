from django.db import migrations


def enrich_resources(apps, schema_editor):
    Resource = apps.get_model("pathway", "PathwayExternalResource")

    updates = [
        ("Redis 官方文档", ["redis", "缓存", "cache", "数据结构"], "Redis"),
        ("MySQL 官方文档", ["mysql", "索引", "sql", "执行计划"], "MySQL"),
        ("OpenJDK HotSpot 文档", ["jvm", "虚拟机", "gc", "内存模型"], "JVM"),
        ("Spring Boot 官方项目页", ["spring", "springboot", "ioc", "web"], "SpringBoot"),
        ("Cloudflare Learning", ["tcp/ip", "http", "网络", "协议"], "计算机网络"),
        ("System Design Primer", ["系统设计", "trade-off", "高可用", "一致性"], "系统设计"),
        ("ByteByteGo Blog", ["系统设计", "架构", "高可用", "一致性"], "系统设计表达"),
        ("CareerVidz", ["表达", "语调", "沟通", "行为面试"], "表达训练"),
    ]

    for title, tags, topic in updates:
        obj = Resource.objects.filter(title=title).first()
        if not obj:
            continue
        obj.tags = tags
        obj.topic = topic
        obj.save(update_fields=["tags", "topic", "updated_at"])

    extras = [
        {
            "title": "Cloudflare Learning: What is HTTP?",
            "url": "https://www.cloudflare.com/learning/ddos/glossary/hypertext-transfer-protocol-http/",
            "focus_area": "technical",
            "resource_type": "official",
            "topic": "HTTP",
            "tags": ["http", "网络", "协议", "tcp/ip"],
            "priority": 1,
        },
        {
            "title": "Cloudflare Learning: What is TCP/IP?",
            "url": "https://www.cloudflare.com/learning/ddos/glossary/tcp-ip/",
            "focus_area": "technical",
            "resource_type": "official",
            "topic": "TCP/IP",
            "tags": ["tcp/ip", "tcp", "网络", "协议"],
            "priority": 1,
        },
        {
            "title": "Percona Blog: MySQL 索引优化",
            "url": "https://www.percona.com/blog/",
            "focus_area": "technical",
            "resource_type": "blog",
            "topic": "MySQL索引优化",
            "tags": ["mysql", "索引", "执行计划", "优化"],
            "priority": 1,
        },
        {
            "title": "Redis University",
            "url": "https://university.redis.com/",
            "focus_area": "technical",
            "resource_type": "video",
            "topic": "Redis缓存",
            "tags": ["redis", "缓存", "高可用", "一致性"],
            "priority": 1,
        },
    ]

    for row in extras:
        Resource.objects.get_or_create(
            title=row["title"],
            defaults={
                "url": row["url"],
                "focus_area": row["focus_area"],
                "resource_type": row["resource_type"],
                "topic": row["topic"],
                "tags": row["tags"],
                "priority": row["priority"],
                "is_active": True,
            },
        )


def rollback_enrich_resources(apps, schema_editor):
    Resource = apps.get_model("pathway", "PathwayExternalResource")
    Resource.objects.filter(
        title__in=[
            "Cloudflare Learning: What is HTTP?",
            "Cloudflare Learning: What is TCP/IP?",
            "Percona Blog: MySQL 索引优化",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pathway", "0003_pathwayexternalresource"),
    ]

    operations = [
        migrations.RunPython(enrich_resources, rollback_enrich_resources),
    ]
