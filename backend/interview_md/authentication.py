import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from interview_md.models import UserAccount


class UserAccountJWTAuthentication(BaseAuthentication):
    """Authorization: Bearer <jwt>，payload 含 user_id。"""

    def authenticate(self, request):
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return None
        token = auth[7:].strip()
        if not token:
            return None
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            uid = payload.get('user_id')
            if not uid:
                raise AuthenticationFailed('无效令牌')
            ua = UserAccount.objects.filter(pk=uid, status=1).first()
            if not ua:
                raise AuthenticationFailed('用户不存在或已禁用')
            return (ua, None)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('令牌已过期')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('令牌无效')


def issue_jwt(user_id: int) -> str:
    t = jwt.encode({'user_id': user_id}, settings.SECRET_KEY, algorithm='HS256')
    return t.decode('utf-8') if isinstance(t, bytes) else t
