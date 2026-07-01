"""快速获取 JWT Token —— 注册 + 登录一体脚本"""
import requests
import sys

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000/api'
EMAIL = f'apitest_{__import__("time").time():.0f}@test.com'
PWD = 'test123456'

print(f'后端地址: {BASE}')

# 1. 注册
print('\n[1/2] 注册...')
r = requests.post(f'{BASE}/users/register/', json={
    'username': 'apitest_user',
    'password': PWD,
    'confirm_password': PWD,
    'email': EMAIL,
    'verification_code': '123456',
    'register_type': 'email',
})
print(f'  status={r.status_code}  body={r.text[:200]}')

# 2. 登录获取 Token
print('\n[2/2] 登录获取 Token...')
r = requests.post(f'{BASE}/users/login/', json={
    'login_type': 'email',
    'identifier': EMAIL,
    'password': PWD,
})
print(f'  status={r.status_code}  body={r.text[:500]}')

data = r.json()
token = data.get('data', {}).get('access') or data.get('data', {}).get('token') or ''
if token:
    print(f'\n✅ Token: {token}')
    print(f'\n运行测试:')
    print(f'  python tests/performance/load_test.py --token "{token}"')
    print(f'  python tests/api/test_api_smoke.py --token "{token}"')
else:
    print(f'\n⚠️ 未能自动提取 Token，请检查登录响应格式')
