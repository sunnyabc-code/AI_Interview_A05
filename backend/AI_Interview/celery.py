import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AI_Interview.settings")

app = Celery("AI_Interview")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
