"""
测试专用 Django settings —— 继承自主配置，将数据库切换为 SQLite 内存库。
确保单元测试不依赖外部 MySQL 服务器。

使用方式:
    DJANGO_SETTINGS_MODULE=AI_Interview.test_settings pytest
"""

from AI_Interview.settings import *

# ---- 覆盖数据库为 SQLite 内存库 ----
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# ---- 关闭密码验证（测试中用简单密码） ----
AUTH_PASSWORD_VALIDATORS = []

# ---- 加速测试 ----
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# ---- 确保 CORS 不会干扰测试 ----
CORS_ALLOW_ALL_ORIGINS = True
