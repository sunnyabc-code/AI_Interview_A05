import pymysql

pymysql.install_as_MySQLdb()

try:
    from .celery import app as celery_app
except ModuleNotFoundError:  # pragma: no cover
    celery_app = None

__all__ = ("celery_app",)
