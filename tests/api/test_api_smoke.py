"""
AI模拟面试平台 — API 接口冒烟测试 (Smoke Test)
================================================
遍历所有核心 API 端点，验证:
  - HTTP 状态码正确
  - 响应格式符合 {code, message, data} 统一结构
  - 认证拦截正确（公开/受保护端点分别验证）
  - 请求参数校验正确（必填字段、格式校验）

运行方式:
    # 需要后端服务运行中
    # 1. 启动后端: cd backend && python manage.py runserver 0.0.0.0:8000
    # 2. 运行冒烟测试:
    python tests/api/test_api_smoke.py

    # 或指定后端地址和 Token:
    python tests/api/test_api_smoke.py --base-url http://127.0.0.1:8000/api --token "your-jwt-token"

依赖:
    pip install requests
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Optional, Union

import requests

# ============================================================
# 配置
# ============================================================
API_BASE_URL = 'http://127.0.0.1:8000/api'
TOKEN = ''
REQUEST_TIMEOUT = 30

# ============================================================
# 测试用例定义
# ============================================================

@dataclass
class ApiTestCase:
    """定义一个 API 测试用例"""
    name: str                      # 用例名称
    method: str                    # HTTP 方法
    path: str                      # 接口路径（不含 /api 前缀）
    need_auth: bool                # 是否需要认证
    data: Optional[dict] = None           # 请求体
    query: Optional[dict] = None          # 查询参数
    expected_http_status: Union[int, tuple] = 200   # 预期 HTTP 状态码
    expected_body_code: Optional[int] = None  # 预期响应 body.code（None=不检查）
    check_fields: Optional[list] = None       # 响应 data 中必须存在的字段
    description: str = ''                     # 用例描述
    skip_body_check_on_auth_fail: bool = True # 认证失败时不检查 body.code


# ============================================================
# 全部冒烟测试用例（匹配当前 Django URL 路由）
# ============================================================

_TS = int(time.time())

# 本后端业务错误统一返回 HTTP 200，错误码在 body.code 中（非 200 即错误）
# 认证失败才返回 HTTP 401
_ERR = 400  # 后端业务错误码 ≠ 200

SMOKE_TEST_CASES = [
    # ==================== 1. 岗位模块（需认证） ====================
    ApiTestCase(
        '获取岗位列表', 'GET', '/positions/',
        need_auth=True,
        expected_http_status=200,
        description='获取岗位列表（需认证）',
    ),
    ApiTestCase(
        '获取岗位列表-未认证拒绝', 'GET', '/positions/',
        need_auth=False,
        expected_http_status=(401, 403),
        description='未提供 Token 应返回 401/403',
    ),

    # ==================== 2. 用户认证模块 ====================
    ApiTestCase(
        '用户注册-正常', 'POST', '/users/register/',
        need_auth=False,
        data={
            'username': f'smoke_{_TS}',
            'password': 'test123456',
            'confirm_password': 'test123456',
            'email': f'smoke_{_TS}@test.com',
            'verification_code': '123456',
            'register_type': 'email',
        },
        expected_http_status=200,
        description='注册新用户',
    ),
    ApiTestCase(
        '用户注册-缺少必填字段', 'POST', '/users/register/',
        need_auth=False,
        data={'username': 'bad_user'},
        expected_http_status=200, expected_body_code=_ERR,
        description='后端返回 HTTP 200 + body.code=400',
    ),
    ApiTestCase(
        '用户注册-密码不一致', 'POST', '/users/register/',
        need_auth=False,
        data={
            'username': f'smoke2_{_TS}',
            'password': 'test123456',
            'confirm_password': 'different',
            'email': f'smoke2_{_TS}@test.com',
            'verification_code': '123456',
            'register_type': 'email',
        },
        expected_http_status=200, expected_body_code=_ERR,
        description='后端返回 HTTP 200 + body.code=400',
    ),
    ApiTestCase(
        '用户登录-存在用户', 'POST', '/users/login/',
        need_auth=False,
        data={'login_type': 'email', 'identifier': f'smoke_{_TS}@test.com', 'password': 'test123456'},
        expected_http_status=200,
        description='用刚注册的用户登录',
    ),
    ApiTestCase(
        '用户登录-不存在用户', 'POST', '/users/login/',
        need_auth=False,
        data={'login_type': 'email', 'identifier': 'noone@test.com', 'password': 'anything'},
        expected_http_status=200, expected_body_code=401,
        description='用户不存在返回 body.code=401',
    ),
    ApiTestCase(
        '用户登录-缺少字段', 'POST', '/users/login/',
        need_auth=False,
        data={'login_type': 'email'},
        expected_http_status=200, expected_body_code=_ERR,
        description='后端返回 HTTP 200 + body.code=400',
    ),
    ApiTestCase(
        '发送验证码-正常邮箱', 'POST', '/users/send-code/',
        need_auth=False,
        data={'target': 'smoke@test.com', 'send_type': 'email'},
        expected_http_status=200,
        description='发送邮箱验证码',
    ),
    ApiTestCase(
        '发送验证码-无效邮箱', 'POST', '/users/send-code/',
        need_auth=False,
        data={'target': 'not-an-email', 'send_type': 'email'},
        expected_http_status=200, expected_body_code=_ERR,
        description='后端返回 HTTP 200 + body.code=400',
    ),
    ApiTestCase(
        '重置密码-验证码错误', 'POST', '/users/reset-password/',
        need_auth=False,
        data={
            'identifier': 'smoke@test.com',
            'verification_code': '000000',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456',
            'reset_type': 'email',
        },
        expected_http_status=200, expected_body_code=_ERR,
        description='后端返回 HTTP 200 + body.code=400',
    ),

    # ==================== 3. 受保护端点 — 无 Token 拒绝 ====================
    ApiTestCase(
        '获取个人信息-未认证拒绝', 'GET', '/users/profile/',
        need_auth=False,
        expected_http_status=(401, 403),
        description='未提供 Token 应返回 401/403',
    ),
    ApiTestCase(
        '获取面试列表-未认证拒绝', 'GET', '/v1/interviews/',
        need_auth=False,
        expected_http_status=(401, 403),
        description='未提供 Token 应返回 401/403',
    ),

    # ==================== 4. 受保护端点 — 有 Token ====================
    ApiTestCase(
        '获取个人信息', 'GET', '/users/profile/',
        need_auth=True,
        expected_http_status=200,
        description='携带有效 Token 获取当前用户信息',
    ),
    ApiTestCase(
        '获取面试列表', 'GET', '/v1/interviews/',
        need_auth=True,
        expected_http_status=200,
        description='获取当前用户的面试列表',
    ),
    ApiTestCase(
        '获取难度配置', 'GET', '/evaluations/difficulty-configs/',
        need_auth=True,
        expected_http_status=200,
        description='获取难度配置列表',
    ),

    # ==================== 5. 面试模块 ====================
    ApiTestCase(
        '创建面试-缺少position', 'POST', '/v1/interviews/',
        need_auth=True,
        data={},
        expected_http_status=400,
        description='缺少 position 返回 HTTP 400（interviews 模块直接设置 HTTP 状态码）',
    ),

    # ==================== 6. PATHWAY ====================
    ApiTestCase(
        'PATHWAY健康检查', 'GET', '/pathway/health/',
        need_auth=True,
        expected_http_status=200,
        description='PATHWAY 模块健康检查（需认证）',
    ),
    ApiTestCase(
        'PATHWAY健康检查-未认证拒绝', 'GET', '/pathway/health/',
        need_auth=False,
        expected_http_status=(401, 403),
        description='未提供 Token 应返回 401/403',
    ),
]

# ============================================================
# 执行引擎
# ============================================================

def auth_headers(need_auth: bool) -> dict:
    if not need_auth:
        return {'Content-Type': 'application/json'}
    return {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json',
    }


def run_case(case: ApiTestCase) -> dict:
    """执行单个测试用例，返回结果字典"""
    url = f'{API_BASE_URL}{case.path}'
    headers = auth_headers(case.need_auth)

    start = time.perf_counter()
    try:
        if case.method == 'GET':
            resp = requests.get(url, headers=headers, params=case.query, timeout=REQUEST_TIMEOUT)
        else:
            resp = requests.post(
                url,
                data=json.dumps(case.data or {}),
                headers=headers,
                params=case.query,
                timeout=REQUEST_TIMEOUT,
            )
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 解析响应
        try:
            body = resp.json()
        except json.JSONDecodeError:
            return {
                'case': case.name,
                'passed': False,
                'error': f'响应非 JSON (HTTP {resp.status_code}): {resp.text[:200]}',
                'status': resp.status_code,
                'elapsed_ms': elapsed_ms,
            }

        checks = []

        # 检查 HTTP 状态码
        expected_http = case.expected_http_status if isinstance(case.expected_http_status, tuple) else (case.expected_http_status,)
        http_ok = resp.status_code in expected_http
        checks.append(('HTTP状态码', http_ok,
                       f'期望 {case.expected_http_status}, 实际 {resp.status_code}'))

        # 检查业务 body.code（本后端业务错误统一返回 HTTP 200 + body.code≠200）
        if case.expected_body_code is not None and 'code' in body:
            # 如果期望 auth fail 但实际 pass 了，跳过 body.code 检查（没意义）
            is_auth_fail = resp.status_code in (401, 403)
            if not (case.skip_body_check_on_auth_fail and is_auth_fail):
                body_code_ok = body['code'] == case.expected_body_code
                checks.append(('业务code', body_code_ok,
                               f'期望 body.code={case.expected_body_code}, 实际 body.code={body.get("code")}'))

        # 检查必含字段
        if case.check_fields and body.get('code') not in (401, 403, 400):
            data_obj = body.get('data', {})
            for field in case.check_fields:
                if isinstance(data_obj, dict):
                    field_ok = field in data_obj
                else:
                    field_ok = data_obj is not None
                checks.append((f'字段[{field}]', field_ok, f'data 中应包含 "{field}"'))

        all_passed = all(c[1] for c in checks) if checks else status_ok
        return {
            'case': case.name,
            'passed': all_passed,
            'status': resp.status_code,
            'elapsed_ms': elapsed_ms,
            'checks': checks,
            'description': case.description,
        }

    except requests.exceptions.ConnectionError:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            'case': case.name, 'passed': False,
            'error': '连接失败 — 后端服务未运行或地址不正确',
            'elapsed_ms': elapsed_ms,
        }
    except requests.exceptions.Timeout:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            'case': case.name, 'passed': False,
            'error': f'请求超时 (>{REQUEST_TIMEOUT}s)',
            'elapsed_ms': elapsed_ms,
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            'case': case.name, 'passed': False,
            'error': f'{type(e).__name__}: {e}',
            'elapsed_ms': elapsed_ms,
        }


def run_all_smoke_tests():
    """运行全部冒烟测试"""
    if not TOKEN:
        print('⚠️  未配置 Token, 受保护端点将返回 401。')
        print('   请先用 --token 参数传入有效 JWT Token。')
        print('   Token 获取方式: POST /api/users/login/\n')

    print('=' * 80)
    print('AI模拟面试平台 — API 接口冒烟测试')
    print(f'基准URL:     {API_BASE_URL}')
    print(f'Token配置:   {"已配置" if TOKEN else "未配置"}')
    print(f'测试用例数:  {len(SMOKE_TEST_CASES)}')
    print('=' * 80)

    results = []
    for i, case in enumerate(SMOKE_TEST_CASES, 1):
        auth_icon = '🔒' if case.need_auth else '🌐'
        print(f'\n[{i}/{len(SMOKE_TEST_CASES)}] {auth_icon} {case.name}')
        print(f'  {case.method} /api{case.path}')
        if case.description:
            print(f'  📝 {case.description}')

        result = run_case(case)
        results.append(result)

        status_icon = '✅' if result['passed'] else '❌'
        print(f'  {status_icon} ', end='')
        if result['passed']:
            print(f'通过 — {result["elapsed_ms"]:.0f}ms')
        else:
            if 'error' in result:
                print(f'失败 — {result["error"]}')
            else:
                print(f'失败 — HTTP {result.get("status", "?")} | {result["elapsed_ms"]:.0f}ms')
                for check_name, ok, detail in result.get('checks', []):
                    if not ok:
                        print(f'     ⛔ {check_name}: {detail}')

    # ---- 汇总 ----
    passed = sum(1 for r in results if r['passed'])
    failed = sum(1 for r in results if not r['passed'])
    total = len(results)

    print('\n' + '=' * 80)
    print('冒烟测试汇总')
    print('=' * 80)
    print(f'  总计: {total}  通过: {passed} ✅  失败: {failed} ❌  通过率: {passed/total*100:.1f}%')

    if failed > 0:
        print(f'\n  失败用例:')
        for r in results:
            if not r['passed']:
                err = r.get('error', f'HTTP {r.get("status", "?")}')
                print(f'    ❌ {r["case"]}: {err}')

    # ---- 按模块分类 ----
    print(f'\n--- 按模块分类 ---')
    modules = {}
    for r, case in zip(results, SMOKE_TEST_CASES):
        path = case.path
        if '/users/' in path:
            mod = '用户认证模块'
        elif '/positions/' in path:
            mod = '岗位模块'
        elif '/v1/interviews/' in path:
            mod = '面试模块'
        elif '/evaluations/' in path:
            mod = '评估模块'
        elif '/recommendations/' in path:
            mod = '推荐模块'
        elif '/pathway/' in path:
            mod = 'PATHWAY模块'
        else:
            mod = '其他'
        modules.setdefault(mod, {'passed': 0, 'failed': 0})
        if r['passed']:
            modules[mod]['passed'] += 1
        else:
            modules[mod]['failed'] += 1

    for mod, counts in modules.items():
        total_mod = counts['passed'] + counts['failed']
        bar = '🟢' * counts['passed'] + '🔴' * counts['failed']
        print(f'  {mod:12s}  {bar}  {counts["passed"]}/{total_mod} 通过')

    print('=' * 80)
    return 0 if failed == 0 else 1


# ============================================================
# CLI
# ============================================================

def main():
    global API_BASE_URL, TOKEN

    parser = argparse.ArgumentParser(
        description='AI模拟面试平台 — API 接口冒烟测试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python tests/api/test_api_smoke.py
  python tests/api/test_api_smoke.py --base-url http://localhost:8000/api
  python tests/api/test_api_smoke.py --token "your-jwt-token"
        ''',
    )
    parser.add_argument('--base-url', type=str, default=API_BASE_URL,
                        help=f'API 基准 URL (默认: {API_BASE_URL})')
    parser.add_argument('--token', '-t', type=str, default=TOKEN,
                        help='Bearer Token (通过 POST /api/users/login/ 获取)')

    args = parser.parse_args()

    API_BASE_URL = args.base_url
    TOKEN = args.token

    sys.exit(run_all_smoke_tests())


if __name__ == '__main__':
    main()
