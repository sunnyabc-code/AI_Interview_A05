"""
手动把已有 interview_round_analyses 同步进 user_knowledge_matrics（不重新调 LLM）。

用法（在项目 backend 目录）:
  python manage.py sync_user_knowledge_matrics <interview_id>

用于：线上结束面试走了别的服务、或本机 runserver 没接到请求时，在 CMD 直接对库补写并看诊断。
"""

from django.core.management.base import BaseCommand

from interviews.models import Interview
from interviews.scoring_service import sync_user_knowledge_matrics_from_analyses


class Command(BaseCommand):
    help = "按技术链从 interview_round_analyses 同步到 user_knowledge_matrics"

    def add_arguments(self, parser):
        parser.add_argument(
            "interview_id",
            type=int,
            help="interviews.id",
        )

    def handle(self, *args, **options):
        iid = options["interview_id"]
        interview = (
            Interview.objects.filter(id=iid).select_related("position").first()
        )
        if not interview:
            self.stderr.write(self.style.ERROR(f"interview id={iid} 不存在"))
            return

        rows, stats = sync_user_knowledge_matrics_from_analyses(interview)
        self.stdout.write(
            self.style.SUCCESS(
                f"完成 interview_id={iid} 写入 user_knowledge_matrics 行数={rows}"
            )
        )
        self.stdout.write(str(stats))
