"""
API 响应时间性能测试
测量各核心端点的 P50/P95/P99 延迟，用于评估系统是否满足面试场景的实时性要求。

使用方式:
    python test_response_time.py

可配置项见下方常量区。
"""
import time
import statistics
import requests

# ============================================================
# 配置区域 —— 按实际环境修改
# ============================================================
API_BASE_URL = 'http://127.0.0.1:8001/api'
# 测试用的 Token（先通过注册/登录接口获取，或使用 issue_jwt 生成）
TOKEN = 'sk-530baff969b44e438a997e96cb12774f'
# 测试轮数
REPEAT = 5

# 测试端点列表
ENDPOINTS = [
    ('GET', '/scenario/list/', None),
    ('GET', '/profile/trend/?userId=1&days=7', None),
    ('GET', '/profile/history/?userId=1&page=1&size=10', None),
]


def get_auth_headers():
    if not TOKEN:
        return {}
    return {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}


def measure(endpoint: str, method: str = 'GET', data: dict = None) -> dict:
    """单次请求并返回耗时(秒)和状态码"""
    url = f'{API_BASE_URL}{endpoint}'
    start = time.perf_counter()
    try:
        if method == 'GET':
            resp = requests.get(url, headers=get_auth_headers(), timeout=30)
        else:
            resp = requests.post(url, json=data or {}, headers=get_auth_headers(), timeout=30)
        elapsed = time.perf_counter() - start
        return {'endpoint': endpoint, 'status': resp.status_code, 'time': elapsed, 'error': None}
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {'endpoint': endpoint, 'status': 0, 'time': elapsed, 'error': str(e)}


def run_benchmark():
    print('=' * 70)
    print('AI模拟面试平台 — API 响应时间性能测试')
    print(f'基准URL: {API_BASE_URL}')
    print(f'每端点重复: {REPEAT} 次')
    print(f'Token配置: {"已配置" if TOKEN else "未配置（公开端点可测，受保护端点将返回 401/403）"}')
    print('=' * 70)

    for method, endpoint, data in ENDPOINTS:
        times = []
        errors = 0
        statuses = []

        for i in range(REPEAT):
            result = measure(endpoint, method, data)
            times.append(result['time'])
            statuses.append(result['status'])
            if result['error']:
                errors += 1

        if not times:
            continue

        p50 = statistics.median(times)
        p95 = sorted(times)[int(len(times) * 0.95 - 0.5)] if len(times) >= 3 else max(times)
        p99 = sorted(times)[int(len(times) * 0.99 - 0.5)] if len(times) >= 3 else max(times)
        avg = statistics.mean(times)

        print(f'\n[{method}] {endpoint}')
        print(f'  请求: {REPEAT}次, 成功: {REPEAT - errors}, 失败: {errors}')
        print(f'  P50: {p50*1000:.0f}ms  P95: {p95*1000:.0f}ms  P99: {p99*1000:.0f}ms  Avg: {avg*1000:.0f}ms')
        print(f'  状态码分布: {dict((c, statuses.count(c)) for c in set(statuses))}')

    print('\n' + '=' * 70)
    print('测试完成。建议标准:')
    print('  公开端点 P95 < 200ms')
    print('  受保护端点 P95 < 500ms')
    print('  LLM 相关端点（dialogue/next/）P95 < 30s')
    print('=' * 70)


if __name__ == '__main__':
    run_benchmark()
