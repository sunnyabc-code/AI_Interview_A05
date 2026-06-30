#!/usr/bin/env python
"""
LLM 连通性诊断脚本
测试项目配置的 LLM 服务是否可用，输出详细的诊断信息。

用法:
    python scripts/test_llm_diagnostics.py
    python scripts/test_llm_diagnostics.py --prompt "请出一道Java面试题"
    python scripts/test_llm_diagnostics.py --benchmark  # 性能基准测试
"""
import argparse
import os
import sys
import statistics
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Interview.settings')
import django
django.setup()

from django.conf import settings


def print_config():
    """输出当前 LLM 配置（隐藏 Key 部分内容）"""
    base_url = getattr(settings, 'LLM_BASE_URL', '')
    api_key = getattr(settings, 'LLM_API_KEY', '')
    model = getattr(settings, 'LLM_MODEL', '')

    print('=== LLM 配置诊断 ===')
    print(f'LLM_BASE_URL : {base_url or "(未配置)"}')
    print(f'LLM_MODEL    : {model or "(未配置)"}')

    if api_key:
        masked = api_key[:7] + '*' * (len(api_key) - 11) + api_key[-4:] if len(api_key) > 11 else '****'
        print(f'LLM_API_KEY  : {masked}')
    else:
        print('LLM_API_KEY  : (未配置)')

    # 检测常见的配置错误
    issues = []
    if not base_url:
        issues.append('❌ LLM_BASE_URL 为空，LLM 调用将失败')
    elif not base_url.startswith('https://'):
        issues.append('⚠️  LLM_BASE_URL 建议使用 HTTPS')

    if not api_key:
        issues.append('❌ LLM_API_KEY 为空，LLM 调用将失败')

    if not model:
        issues.append('❌ LLM_MODEL 为空，LLM 调用将失败')

    # 检查常见提供商的 URL 是否正确
    known_providers = {
        'api.deepseek.com': 'DeepSeek',
        'dashscope.aliyuncs.com': '阿里云百炼 (DashScope)',
        'api.openai.com': 'OpenAI',
        'api.siliconflow.cn': '硅基流动 (SiliconFlow)',
        'open.bigmodel.cn': '智谱 GLM',
        'localhost': '本地服务 (Ollama/vLLM)',
    }
    for url_key, name in known_providers.items():
        if url_key in base_url:
            print(f'检测到提供商 : {name}')
            break

    if issues:
        print('\n发现配置问题:')
        for issue in issues:
            print(f'  {issue}')
    else:
        print('✅ 基础配置检查通过')

    return len([i for i in issues if i.startswith('❌')]) == 0


def test_connectivity() -> dict:
    """发送一个最小请求测试连通性，返回诊断信息"""
    from interview_md.services.llm import call_llm

    print('\n=== 连通性测试 ===')
    print('发送测试请求...')

    t0 = time.perf_counter()
    try:
        response = call_llm('请只回复一个词：正常')
        elapsed = time.perf_counter() - t0
        print(f'✅ 连通成功！耗时: {elapsed:.2f}s')
        print(f'   响应预览: {response[:100]}')
        return {'success': True, 'time': elapsed, 'response': response}
    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(f'❌ 连通失败 (耗时 {elapsed:.2f}s)')
        print(f'   错误信息: {e}')
        return {'success': False, 'time': elapsed, 'error': str(e)}


def test_json_output() -> dict:
    """测试结构化 JSON 输出能力"""
    from interview_md.services.llm import call_llm, extract_json_obj

    print('\n=== JSON 输出测试 ===')
    prompt = '请输出一个JSON对象，包含 name(你的名字) 和 version(版本号) 两个字段。只输出JSON。'
    print(f'Prompt: {prompt[:60]}...')

    t0 = time.perf_counter()
    try:
        response = call_llm(prompt)
        elapsed = time.perf_counter() - t0
        result = extract_json_obj(response)
        if result and isinstance(result, dict):
            print(f'✅ JSON 解析成功 (耗时 {elapsed:.2f}s)')
            print(f'   解析结果: {result}')
            return {'success': True, 'time': elapsed, 'json': result}
        else:
            print(f'⚠️  JSON 为空，但未报错。原始响应: {response[:200]}')
            return {'success': False, 'time': elapsed, 'raw': response}
    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(f'❌ 测试失败: {e}')
        return {'success': False, 'time': elapsed, 'error': str(e)}


def run_benchmark(rounds: int = 5):
    """性能基准测试：多次调用测量 P50/P95"""
    from interview_md.services.llm import call_llm

    print(f'\n=== 性能基准测试 ({rounds} 轮) ===')
    times = []
    for i in range(rounds):
        t0 = time.perf_counter()
        try:
            call_llm('回复一个字：好')
            elapsed = time.perf_counter() - t0
            times.append(elapsed)
            print(f'  第{i+1}轮: {elapsed:.2f}s')
        except Exception as e:
            print(f'  第{i+1}轮: 失败 ({e})')

    if times:
        print(f'\n  样本数: {len(times)}')
        print(f'  P50: {statistics.median(times):.2f}s')
        if len(times) >= 3:
            sorted_times = sorted(times)
            p95 = sorted_times[int(len(times) * 0.95 - 0.5)]
            print(f'  P95: {p95:.2f}s')
        print(f'  平均: {statistics.mean(times):.2f}s')
        print(f'  最快: {min(times):.2f}s  最慢: {max(times):.2f}s')


def main():
    parser = argparse.ArgumentParser(description='LLM 连通性诊断')
    parser.add_argument('--prompt', default=None, help='自定义测试 prompt')
    parser.add_argument('--benchmark', action='store_true', help='运行性能基准测试')
    parser.add_argument('--rounds', type=int, default=5, help='基准测试轮数')
    args = parser.parse_args()

    print('=' * 60)
    print('LLM 连通性诊断工具')
    print('=' * 60)

    if not print_config():
        print('\n请先修复配置问题后再运行诊断。')
        print('参考: 编辑 backend/.env 文件，或设置环境变量 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL')
        return 1

    result = test_connectivity()
    if not result['success']:
        print('\n连通性测试失败，跳过后续测试。')
        return 1

    test_json_output()

    if args.prompt:
        from interview_md.services.llm import call_llm
        print(f'\n=== 自定义 Prompt 测试 ===')
        print(f'Prompt: {args.prompt}')
        try:
            response = call_llm(args.prompt)
            print(f'响应:\n{response}')
        except Exception as e:
            print(f'失败: {e}')

    if args.benchmark:
        run_benchmark(args.rounds)

    print('\n' + '=' * 60)
    print('诊断完成。')
    print('=' * 60)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
