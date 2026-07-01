"""
AI模拟面试平台 — 并发负载性能测试
=====================================
模拟多用户同时访问核心 API，测量系统在负载下的表现。

测试维度:
  - 并发请求下的响应时间 (P50/P90/P95/P99)
  - 吞吐量 (requests/sec)
  - 错误率
  - 各端点在负载下的表现差异

使用方式:
    # 默认配置（10并发，每个端点20次请求）
    python tests/performance/load_test.py

    # 自定义并发和请求数
    python tests/performance/load_test.py --concurrent 20 --requests 50

    # 仅测试特定端点
    python tests/performance/load_test.py --endpoint position_list

    # 指定后端地址
    python tests/performance/load_test.py --base-url http://localhost:8000/api

依赖:
    pip install requests
"""

import argparse
import concurrent.futures
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

# ============================================================
# 配置区域 —— 按实际环境修改
# ============================================================
API_BASE_URL = 'http://127.0.0.1:8000/api'

# 测试 Token（通过 /api/users/login/ 获取）
TOKEN = ''

# 默认并发数 & 每端点请求总数
DEFAULT_CONCURRENT = 10
DEFAULT_REQUESTS_PER_ENDPOINT = 20

# 请求超时（秒）
REQUEST_TIMEOUT = 30

# ============================================================
# 测试端点定义（匹配当前 Django URL 路由）
# ============================================================

@dataclass
class Endpoint:
    """定义一个待测试的 API 端点"""
    name: str                # 简短标识名
    method: str              # GET / POST
    path: str                # 接口路径（不含 /api 前缀）
    data: Optional[dict] = None   # POST 请求体
    query: Optional[dict] = None  # GET 查询参数
    need_auth: bool = True        # 是否需要认证


# 覆盖全部核心模块 —— 路径匹配 backend/AI_Interview/urls.py 路由表
ENDPOINTS = [
    # ===== 公开端点（无需 Token） =====
    Endpoint('user_register',       'POST', '/users/register/',
             data={'username': 'perf_test', 'password': 'test123456',
                   'confirm_password': 'test123456', 'email': 'perf@test.com',
                   'verification_code': '123456', 'register_type': 'email'},
             need_auth=False),
    Endpoint('user_login',          'POST', '/users/login/',
             data={'login_type': 'email', 'identifier': 'perf@test.com',
                   'password': 'test123456'},
             need_auth=False),
    Endpoint('send_code',           'POST', '/users/send-code/',
             data={'target': 'perf@test.com', 'send_type': 'email'},
             need_auth=False),

    # ===== 受保护端点（需有效 Token） =====
    Endpoint('position_list',       'GET',  '/positions/', need_auth=True),
    Endpoint('user_profile',        'GET',  '/users/profile/'),
    Endpoint('interview_list',      'GET',  '/v1/interviews/'),
    Endpoint('difficulty_configs',  'GET',  '/evaluations/difficulty-configs/'),
    Endpoint('recommendations',     'GET',  '/recommendations/expression-ability-overview/'),
]

# ============================================================
# 数据模型
# ============================================================

@dataclass
class RequestResult:
    """单次请求结果"""
    endpoint: str
    status_code: int
    elapsed_ms: float
    error: Optional[str] = None
    success: bool = True


@dataclass
class EndpointReport:
    """单端点汇总报告"""
    name: str
    method: str
    path: str
    total: int = 0
    success: int = 0
    failure: int = 0
    times_ms: list = field(default_factory=list)
    status_codes: dict = field(default_factory=dict)

    @property
    def error_rate(self) -> float:
        return self.failure / self.total if self.total > 0 else 0

    @property
    def p50(self) -> float:
        return _percentile(self.times_ms, 50)

    @property
    def p90(self) -> float:
        return _percentile(self.times_ms, 90)

    @property
    def p95(self) -> float:
        return _percentile(self.times_ms, 95)

    @property
    def p99(self) -> float:
        return _percentile(self.times_ms, 99)

    @property
    def avg(self) -> float:
        return statistics.mean(self.times_ms) if self.times_ms else 0

    @property
    def min_time(self) -> float:
        return min(self.times_ms) if self.times_ms else 0

    @property
    def max_time(self) -> float:
        return max(self.times_ms) if self.times_ms else 0


# ============================================================
# 工具函数
# ============================================================

def _percentile(data: list, p: float) -> float:
    """计算第 p 百分位数 (线性插值)"""
    if not data:
        return 0
    if len(data) == 1:
        return data[0]
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100.0
    f = int(k)
    c = k - f
    if f + 1 < len(sorted_data):
        return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])
    return sorted_data[f]


def get_auth_headers() -> dict:
    """获取认证头"""
    if not TOKEN:
        return {'Content-Type': 'application/json'}
    return {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json',
    }


def single_request(ep: Endpoint) -> RequestResult:
    """执行单次 HTTP 请求并返回结果"""
    url = f'{API_BASE_URL}{ep.path}'
    headers = get_auth_headers() if ep.need_auth else {'Content-Type': 'application/json'}

    start = time.perf_counter()
    try:
        if ep.method == 'GET':
            resp = requests.get(url, headers=headers, params=ep.query, timeout=REQUEST_TIMEOUT)
        else:
            resp = requests.post(
                url,
                data=json.dumps(ep.data or {}),
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        elapsed = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=ep.name,
            status_code=resp.status_code,
            elapsed_ms=elapsed,
        )
    except requests.exceptions.Timeout:
        elapsed = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=ep.name, status_code=0, elapsed_ms=elapsed,
            error='Timeout', success=False,
        )
    except requests.exceptions.ConnectionError as e:
        elapsed = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=ep.name, status_code=0, elapsed_ms=elapsed,
            error=f'ConnectionError: {e}', success=False,
        )
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=ep.name, status_code=0, elapsed_ms=elapsed,
            error=f'{type(e).__name__}: {e}', success=False,
        )


# ============================================================
# 核心测试逻辑
# ============================================================

def run_concurrent_test(ep: Endpoint, n_workers: int, total_requests: int) -> EndpointReport:
    """对单个端点执行并发测试"""
    report = EndpointReport(name=ep.name, method=ep.method, path=ep.path, total=total_requests)

    start_wall = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = [executor.submit(single_request, ep) for _ in range(total_requests)]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result.success:
                report.success += 1
            else:
                report.failure += 1
            report.times_ms.append(result.elapsed_ms)
            report.status_codes[result.status_code] = report.status_codes.get(result.status_code, 0) + 1
    wall_time = time.perf_counter() - start_wall

    report.throughput = report.total / wall_time if wall_time > 0 else 0
    report.wall_time_sec = wall_time
    return report


def run_all(n_workers: int, requests_per: int, filter_endpoint: Optional[str] = None):
    """运行全部性能测试"""
    targets = [e for e in ENDPOINTS if not filter_endpoint or filter_endpoint in e.name]

    if not TOKEN:
        print('⚠️  未配置 Token, 受保护端点将返回 401')
        print('   请先通过以下方式获取 Token:')
        print('   1. POST /api/users/register/  注册账号')
        print('   2. POST /api/users/login/     登录获取 Token')
        print('   3. 用 --token 参数传入\n')

    print('=' * 80)
    print('AI模拟面试平台 — 并发负载性能测试')
    print(f'基准URL:     {API_BASE_URL}')
    print(f'并发数:      {n_workers}')
    print(f'每端点请求:  {requests_per}')
    print(f'测试端点数:  {len(targets)}')
    print(f'Token配置:   {"已配置" if TOKEN else "未配置（受保护端点将返回 401）"}')
    print('=' * 80)

    all_reports: list[EndpointReport] = []

    for i, ep in enumerate(targets, 1):
        auth_label = '🔒' if ep.need_auth else '🌐'
        print(f'\n[{i}/{len(targets)}] {auth_label} [{ep.method}] /api{ep.path} ({ep.name})')
        print(f'  启动 {n_workers} 并发, {requests_per} 次请求...')

        report = run_concurrent_test(ep, n_workers, requests_per)
        all_reports.append(report)

        print(f'  成功: {report.success}/{report.total}  '
              f'失败: {report.failure}  '
              f'错误率: {report.error_rate*100:.1f}%')
        print(f'  耗时 — P50: {report.p50:.0f}ms  P90: {report.p90:.0f}ms  '
              f'P95: {report.p95:.0f}ms  P99: {report.p99:.0f}ms  '
              f'Avg: {report.avg:.0f}ms')
        print(f'  最小: {report.min_time:.0f}ms  最大: {report.max_time:.0f}ms  '
              f'吞吐: {report.throughput:.1f} req/s')
        if report.status_codes:
            codes_str = ', '.join(f'{k}: {v}' for k, v in sorted(report.status_codes.items()))
            print(f'  状态码分布: {codes_str}')

    # ---- 汇总 ----
    print('\n' + '=' * 80)
    print('汇总结果')
    print('=' * 80)

    all_times = []
    total_success = 0
    total_failure = 0
    for r in all_reports:
        all_times.extend(r.times_ms)
        total_success += r.success
        total_failure += r.failure
    total_all = total_success + total_failure

    if total_all:
        print(f'\n总请求: {total_all}  成功: {total_success}  失败: {total_failure}  '
              f'错误率: {total_failure/total_all*100:.1f}%')
    if all_times:
        print(f'全局延迟 — P50: {_percentile(all_times, 50):.0f}ms  '
              f'P90: {_percentile(all_times, 90):.0f}ms  '
              f'P95: {_percentile(all_times, 95):.0f}ms  '
              f'P99: {_percentile(all_times, 99):.0f}ms  '
              f'Avg: {statistics.mean(all_times):.0f}ms')

    # ---- 延迟排名 ----
    print('\n--- 端点延迟排名 (按 P95) ---')
    sorted_reports = sorted(all_reports, key=lambda r: r.p95, reverse=True)
    for i, r in enumerate(sorted_reports, 1):
        flag = ''
        if r.p95 > 500:
            flag = ' ⚠️  超过500ms'
        elif r.p95 > 200:
            flag = ' ⚡ 超过200ms'
        print(f'  {i}. {r.name:25s}  P50:{r.p50:6.0f}ms  P95:{r.p95:6.0f}ms  P99:{r.p99:6.0f}ms{flag}')

    # ---- 错误率排名 ----
    print('\n--- 错误率排名 ---')
    error_reports = sorted(all_reports, key=lambda r: r.error_rate, reverse=True)
    for i, r in enumerate(error_reports, 1):
        if r.error_rate > 0:
            flag = ' ❌' if r.error_rate > 0.5 else ' ⚠️'
            print(f'  {i}. {r.name:25s}  {r.error_rate*100:5.1f}%{flag}')

    # ---- 标准 ----
    print('\n--- 性能建议标准 ---')
    print('  ✅ 公开端点 P95 < 200ms')
    print('  ✅ 受保护端点 P95 < 500ms')
    print('  ✅ 错误率 < 1%')
    print('  ✅ 并发数 × 2 时吞吐量应接近线性增长')
    print('=' * 80)

    critical_failures = any(r.error_rate > 0.5 for r in all_reports)
    if critical_failures:
        print('\n⚠️  存在错误率超过 50% 的端点，请检查服务是否正常运行。')
    return 1 if critical_failures else 0


# ============================================================
# CLI
# ============================================================

def main():
    global API_BASE_URL, TOKEN

    parser = argparse.ArgumentParser(
        description='AI模拟面试平台 — 并发负载性能测试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python tests/performance/load_test.py
  python tests/performance/load_test.py --concurrent 20 --requests 50
  python tests/performance/load_test.py --endpoint position_list
  python tests/performance/load_test.py --base-url http://localhost:8000/api
  python tests/performance/load_test.py --token "your-jwt-token"
        ''',
    )
    parser.add_argument('--concurrent', '-c', type=int, default=DEFAULT_CONCURRENT,
                        help=f'并发线程数 (默认: {DEFAULT_CONCURRENT})')
    parser.add_argument('--requests', '-n', type=int, default=DEFAULT_REQUESTS_PER_ENDPOINT,
                        help=f'每个端点的请求总数 (默认: {DEFAULT_REQUESTS_PER_ENDPOINT})')
    parser.add_argument('--endpoint', '-e', type=str, default=None,
                        help='仅测试指定端点 (按名称模糊匹配)')
    parser.add_argument('--base-url', type=str, default=API_BASE_URL,
                        help=f'API 基准 URL (默认: {API_BASE_URL})')
    parser.add_argument('--token', '-t', type=str, default=TOKEN,
                        help='Bearer Token (先通过登录接口获取)')

    args = parser.parse_args()

    API_BASE_URL = args.base_url
    TOKEN = args.token

    sys.exit(run_all(args.concurrent, args.requests, args.endpoint))


if __name__ == '__main__':
    main()
