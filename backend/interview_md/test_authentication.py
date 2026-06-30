"""
JWT 认证单元测试
覆盖: issue_jwt, UserAccountJWTAuthentication
"""
from datetime import datetime, timedelta

import jwt
import pytest
from django.conf import settings
from django.test import override_settings
from rest_framework.exceptions import AuthenticationFailed

from interview_md.authentication import (
    UserAccountJWTAuthentication,
    issue_jwt,
)


class TestIssueJwt:
    """测试 JWT 令牌签发"""

    def test_签发有效令牌(self):
        token = issue_jwt(42)
        assert len(token) > 0
        assert isinstance(token, str)

    def test_令牌包含user_id(self):
        token = issue_jwt(99)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        assert payload['user_id'] == 99

    def test_不同用户令牌不同(self):
        token1 = issue_jwt(1)
        token2 = issue_jwt(2)
        assert token1 != token2

    def test_令牌可解码验证(self):
        token = issue_jwt(100)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        assert 'user_id' in payload


class TestAuthentication:
    """测试 UserAccountJWTAuthentication"""

    def test_无Authorization头返回None(self, create_tables):
        """没有 Authorization header 时返回 None（允许其他认证类处理）"""
        from django.test import RequestFactory
        auth = UserAccountJWTAuthentication()
        request = RequestFactory().get('/')
        result = auth.authenticate(request)
        assert result is None

    def test_Authorization头不包含Bearer返回None(self, create_tables):
        """Authorization 头存在但不是 Bearer 格式"""
        from django.test import RequestFactory
        auth = UserAccountJWTAuthentication()
        request = RequestFactory().get('/', HTTP_AUTHORIZATION='Basic xyz')
        result = auth.authenticate(request)
        assert result is None

    def test_空Bearer令牌返回None(self, create_tables):
        from django.test import RequestFactory
        auth = UserAccountJWTAuthentication()
        request = RequestFactory().get('/', HTTP_AUTHORIZATION='Bearer ')
        result = auth.authenticate(request)
        assert result is None

    def test_有效令牌认证成功(self, create_tables, make_user, now):
        """签发有效令牌 → 用户存在且状态正常 → 认证成功"""
        user = make_user(username='authtest')
        token = issue_jwt(user.id)

        from django.test import RequestFactory
        auth = UserAccountJWTAuthentication()
        request = RequestFactory().get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
        result = auth.authenticate(request)

        assert result is not None
        authenticated_user, _ = result
        assert authenticated_user.id == user.id
        assert authenticated_user.username == 'authtest'

    def test_令牌payload缺少user_id抛出异常(self, create_tables):
        """payload 中没有 user_id → AuthenticationFailed"""
        bad_token = jwt.encode({'not_user_id': 1}, settings.SECRET_KEY, algorithm='HS256')

        from django.test import RequestFactory
        auth = UserAccountJWTAuthentication()
        request = RequestFactory().get('/', HTTP_AUTHORIZATION=f'Bearer {bad_token}')

        with pytest.raises(AuthenticationFailed, match='无效令牌'):
            auth.authenticate(request)

    def test_用户不存在抛出异常(self, create_tables):
        """令牌有效但用户 ID 不存在 → AuthenticationFailed"""
        token = issue_jwt(99999)  # 不存在的用户 ID

        from django.test import RequestFactory
        auth = UserAccountJWTAuthentication()
        request = RequestFactory().get('/', HTTP_AUTHORIZATION=f'Bearer {token}')

        with pytest.raises(AuthenticationFailed, match='用户不存在或已禁用'):
            auth.authenticate(request)

    def test_用户状态为禁用抛出异常(self, create_tables, make_user, now):
        """用户 status != 1 → AuthenticationFailed"""
        user = make_user(username='disabled_user', status=0)
        token = issue_jwt(user.id)

        from django.test import RequestFactory
        auth = UserAccountJWTAuthentication()
        request = RequestFactory().get('/', HTTP_AUTHORIZATION=f'Bearer {token}')

        with pytest.raises(AuthenticationFailed, match='用户不存在或已禁用'):
            auth.authenticate(request)

    def test_伪造令牌抛出异常(self, create_tables):
        """恶意构造的令牌 → AuthenticationFailed"""
        from django.test import RequestFactory
        auth = UserAccountJWTAuthentication()
        request = RequestFactory().get('/', HTTP_AUTHORIZATION='Bearer this.is.not.valid')

        with pytest.raises(AuthenticationFailed):
            auth.authenticate(request)

    def test_过期令牌抛出异常(self, create_tables, make_user):
        """过期令牌 → AuthenticationFailed"""
        user = make_user(username='exp_user')
        expired_token = jwt.encode(
            {'user_id': user.id, 'exp': datetime.utcnow() - timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm='HS256',
        )

        from django.test import RequestFactory
        auth = UserAccountJWTAuthentication()
        request = RequestFactory().get('/', HTTP_AUTHORIZATION=f'Bearer {expired_token}')

        with pytest.raises(AuthenticationFailed, match='令牌已过期'):
            auth.authenticate(request)
