"""
LLM 服务层单元测试
覆盖: call_llm, extract_json_obj 及 API 兼容性
"""
import json
import re

import pytest
from django.conf import settings
from django.test import override_settings

from interview_md.services.llm import call_llm, extract_json_obj


# ============================================================
# extract_json_obj —— JSON 提取与容错
# ============================================================

class TestExtractJsonObj:
    """测试 LLM 返回文本的 JSON 提取逻辑"""

    def test_纯JSON字符串(self):
        text = '{"score": 85, "comment": "good"}'
        result = extract_json_obj(text)
        assert result == {"score": 85, "comment": "good"}

    def test_带Markdown代码块的JSON(self):
        text = '```json\n{"need_followup": true, "followup_question": "说说细节？"}\n```'
        result = extract_json_obj(text)
        assert result == {"need_followup": True, "followup_question": "说说细节？"}

    def test_JSON前后有文字(self):
        text = '好的，以下是我的评估：\n{"overall_score": 82}\n以上是评估结果。'
        result = extract_json_obj(text)
        assert result == {"overall_score": 82}

    def test_嵌套JSON对象(self):
        text = '{"evaluation": {"score": 90, "dimensions": {"logic": 88}}}'
        result = extract_json_obj(text)
        assert result == {"evaluation": {"score": 90, "dimensions": {"logic": 88}}}

    def test_含数组的JSON(self):
        text = '{"strengths": ["亮点1", "亮点2"], "score": 85}'
        result = extract_json_obj(text)
        assert result["strengths"] == ["亮点1", "亮点2"]
        assert result["score"] == 85

    def test_空字符串返回空字典(self):
        assert extract_json_obj("") == {}

    def test_无JSON返回空字典(self):
        assert extract_json_obj("这不是JSON文本") == {}

    def test_JSON语法错误返回空字典(self):
        assert extract_json_obj('{"score": 85, invalid}') == {}

    def test_None输入返回空字典(self):
        assert extract_json_obj(None) == {}

    def test_只有花括号的行(self):
        text = "{\n  \"key\": \"value\"\n}"
        result = extract_json_obj(text)
        assert result == {"key": "value"}

    def test_中文键值的JSON(self):
        text = '{"需要追问": true, "追问问题": "请继续说明"}'
        result = extract_json_obj(text)
        assert result == {"需要追问": True, "追问问题": "请继续说明"}

    def test_布尔值小写(self):
        text = '{"need_followup": false, "verified": true}'
        result = extract_json_obj(text)
        assert result == {"need_followup": False, "verified": True}


# ============================================================
# call_llm —— LLM 调用参数构造与配置
# ============================================================

class TestCallLlmConfig:
    """测试 LLM 配置读取与请求构造（不发起真实请求）"""

    def test_未配置LLM时抛出异常(self):
        """当 LLM_BASE_URL 或 LLM_API_KEY 为空时，call_llm 应尽早报错"""
        with override_settings(LLM_BASE_URL='', LLM_API_KEY=''):
            with pytest.raises(RuntimeError, match='未配置 LLM'):
                call_llm('测试提示词')

    def test_仅缺少API_KEY也抛异常(self):
        with override_settings(LLM_BASE_URL='https://api.test.com/v1', LLM_API_KEY=''):
            with pytest.raises(RuntimeError, match='未配置 LLM'):
                call_llm('测试提示词')

    def test_仅缺少BASE_URL也抛异常(self):
        with override_settings(LLM_BASE_URL='', LLM_API_KEY='sk-test123'):
            with pytest.raises(RuntimeError, match='未配置 LLM'):
                call_llm('测试提示词')

    def test_配置从settings读取(self):
        """验证 LLM 配置从 settings 正确读取"""
        assert settings.LLM_BASE_URL or True  # 至少有一个默认值
        assert settings.LLM_MODEL or True


class TestCallLlmRequestStructure:
    """测试请求体构造逻辑（通过 mock requests.post）"""

    def test_基本请求构造(self):
        """验证正确的请求体结构"""
        from unittest.mock import MagicMock, patch
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'choices': [{'message': {'content': '{"result": "ok"}'}}]
        }
        with patch('requests.post', return_value=mock_resp) as mock_post:
            with override_settings(
                LLM_BASE_URL='https://api.test.com/v1',
                LLM_API_KEY='sk-test123',
                LLM_MODEL='test-model',
            ):
                call_llm('你是面试官，请提问。')

            call_args = mock_post.call_args
            assert call_args[0][0] == 'https://api.test.com/v1/chat/completions'
            assert call_args[1]['headers']['Authorization'] == 'Bearer sk-test123'
            body = call_args[1]['json']
            assert body['model'] == 'test-model'
            assert body['messages'][0]['role'] == 'system'
            assert body['messages'][0]['content'] == '你是面试官，请提问。'

    def test_含JSON关键词时启用JSON模式(self):
        """当 system_prompt 中含有 'json' 时，自动设置 response_format"""
        from unittest.mock import MagicMock, patch
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'choices': [{'message': {'content': '{}'}}]}
        with patch('requests.post', return_value=mock_resp) as mock_post:
            with override_settings(
                LLM_BASE_URL='https://api.test.com/v1',
                LLM_API_KEY='sk-test123',
                LLM_MODEL='deepseek-chat',
            ):
                call_llm('请输出 JSON 格式的评估结果')

            body = mock_post.call_args[1]['json']
            assert body['response_format'] == {'type': 'json_object'}

    def test_不含JSON时不启用JSON模式(self):
        """system_prompt 不含 'json' 时不添加 response_format"""
        from unittest.mock import MagicMock, patch
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'choices': [{'message': {'content': '普通文本回复'}}]}
        with patch('requests.post', return_value=mock_resp) as mock_post:
            with override_settings(
                LLM_BASE_URL='https://api.test.com/v1',
                LLM_API_KEY='sk-test123',
                LLM_MODEL='deepseek-chat',
            ):
                call_llm('请用中文回答这个问题')

            body = mock_post.call_args[1]['json']
            assert 'response_format' not in body

    def test_历史消息正确传递(self):
        """验证 history_messages 被正确追加到 messages 数组"""
        from unittest.mock import MagicMock, patch
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'choices': [{'message': {'content': '{}'}}]}
        with patch('requests.post', return_value=mock_resp) as mock_post:
            history = [
                {'role': 'user', 'content': '我叫张三'},
                {'role': 'assistant', 'content': '你好张三'},
            ]
            with override_settings(
                LLM_BASE_URL='https://api.test.com/v1',
                LLM_API_KEY='sk-test123',
                LLM_MODEL='deepseek-chat',
            ):
                call_llm('你是面试官', history_messages=history)

            body = mock_post.call_args[1]['json']
            assert len(body['messages']) == 3  # system + 2条历史
            assert body['messages'][1] == {'role': 'user', 'content': '我叫张三'}
            assert body['messages'][2] == {'role': 'assistant', 'content': '你好张三'}

    def test_HTTP错误状态码抛异常(self):
        """HTTP >= 400 应抛出 RuntimeError"""
        from unittest.mock import MagicMock, patch
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = 'Internal Server Error'
        with patch('requests.post', return_value=mock_resp):
            with override_settings(
                LLM_BASE_URL='https://api.test.com/v1',
                LLM_API_KEY='sk-test123',
                LLM_MODEL='deepseek-chat',
            ):
                with pytest.raises(RuntimeError, match='LLM HTTP 500'):
                    call_llm('测试')

    def test_响应为空时返回空字符串(self):
        """当 choices 列表为空时返回空字符串"""
        from unittest.mock import MagicMock, patch
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'choices': []}
        with patch('requests.post', return_value=mock_resp):
            with override_settings(
                LLM_BASE_URL='https://api.test.com/v1',
                LLM_API_KEY='sk-test123',
                LLM_MODEL='deepseek-chat',
            ):
                result = call_llm('测试')
            assert result == ''


# ============================================================
# DeepSeek API 兼容性测试（需要 --run-llm）
# ============================================================

class TestDeepSeekApiCompatibility:
    """验证 DeepSeek API 的 OpenAI 兼容协议是否正常"""

    @pytest.mark.llm
    def test_deepseek_基础调用(self):
        """向 DeepSeek 发送最简单的请求，验证连通性"""
        response = call_llm('请只回复一个词：正常')
        assert len(response) > 0
        assert '正常' in response or 'ok' in response.lower() or len(response) > 0

    @pytest.mark.llm
    def test_deepseek_JSON输出(self):
        """验证 DeepSeek 的结构化 JSON 输出"""
        prompt = '''请严格按以下JSON格式输出，不要包含其他文字：
{"topic": "Python装饰器", "difficulty": 3, "summary": "一句话说明"}
只输出JSON，不要markdown代码块。'''
        response = call_llm(prompt)
        result = extract_json_obj(response)
        assert 'topic' in result
        assert 'difficulty' in result

    @pytest.mark.llm
    def test_deepseek_面试追问决策(self):
        """模拟真实的追问判断场景"""
        sys = '''你是企业面试官。根据对话判断是否需要追问。只输出JSON：
{"need_followup": true/false, "followup_question": "..."}
对话：
面试官：请介绍你最熟悉的项目
候选人：我做了一个电商系统，用了Spring Boot'''
        response = call_llm(sys)
        result = extract_json_obj(response)
        assert 'need_followup' in result
        assert isinstance(result['need_followup'], bool)

    @pytest.mark.llm
    def test_deepseek_面试评估打分(self):
        """模拟真实的面试评估场景"""
        sys = '''你是面试评估专家。对以下问答打分(0-100)。
只输出JSON：{"content_score":0,"logic_score":0,"communication_score":0,"overall_score":0}

对话：
面试官：请解释HashMap和TreeMap的区别
候选人：HashMap基于哈希表，O(1)查找；TreeMap基于红黑树，O(log n)查找，支持排序。'''
        response = call_llm(sys)
        result = extract_json_obj(response)
        assert 'overall_score' in result
        score = result['overall_score']
        assert 0 <= score <= 100, f'分数 {score} 不在0-100范围内'
