import requests
import time

# 配置信息
API_BASE_URL = 'http://localhost:8000/api/v1'
INTERVIEW_ID = 10  # 替换为你的面试ID
TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc0MjUyODI2LCJpYXQiOjE3NzQyNDkyMjYsImp0aSI6ImMyZjk5ZjQxMGMwYjQyMDZhNTMyZmFjMmY2M2Q4MDA3IiwidXNlcl9pZCI6IjMifQ.3LqUwGpqeQBqoIZmkdHA2SQzmkiUSBA1-hxKWCXcdCE'  # 替换为你的访问令牌

# 测试函数
def test_next_question_time():
    url = f'{API_BASE_URL}/interviews/{INTERVIEW_ID}/next-question/'
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {}
    
    # 记录开始时间
    start_time = time.time()
    
    # 发送请求
    response = requests.post(url, headers=headers, json=data)
    
    # 记录结束时间
    end_time = time.time()
    
    # 计算响应时间
    response_time = end_time - start_time
    
    # 输出结果
    print(f"响应时间: {response_time:.2f} 秒")
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {response.json()}")

if __name__ == "__main__":
    print("开始测试问题生成API响应时间...")
    test_next_question_time()
    print("测试完成")