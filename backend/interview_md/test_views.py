"""
API 视图层集成测试
覆盖: 注册/登录/场景列表/会话创建/对话/报告/趋势等全部端点
"""
import json

import pytest
from django.test import Client
from django.utils import timezone

from interview_md.authentication import issue_jwt


# ============================================================
# 认证相关 API
# ============================================================

class TestRegisterApi:
    """POST /api/chain/auth/register/"""

    def test_注册成功(self, create_tables, now):
        client = Client()
        resp = client.post(
            '/api/chain/auth/register/',
            data=json.dumps({
                'username': 'newuser',
                'password': 'test123456',
                'email': 'new@test.com',
            }),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 1
        assert data['data']['userId'] is not None

    def test_用户名已存在(self, create_tables, make_user, now):
        make_user(username='existing')
        client = Client()
        resp = client.post(
            '/api/chain/auth/register/',
            data=json.dumps({'username': 'existing', 'password': 'test123456'}),
            content_type='application/json',
        )
        assert resp.json()['code'] != 1

    def test_密码过短拒绝(self, create_tables):
        client = Client()
        resp = client.post(
            '/api/chain/auth/register/',
            data=json.dumps({'username': 'newuser', 'password': '12345'}),
            content_type='application/json',
        )
        assert resp.json()['code'] == 400

    def test_用户名为空拒绝(self, create_tables):
        client = Client()
        resp = client.post(
            '/api/chain/auth/register/',
            data=json.dumps({'username': '', 'password': '123456'}),
            content_type='application/json',
        )
        assert resp.json()['code'] == 400


class TestLoginApi:
    """POST /api/chain/auth/login/"""

    def test_正确密码登录成功(self, create_tables, make_user, now):
        from django.contrib.auth.hashers import make_password
        from interview_md.models import UserAccount
        # 直接用 make_user 创建的密码是哈希过的
        user = make_user(username='logintest', password='correct123')

        client = Client()
        resp = client.post(
            '/api/chain/auth/login/',
            data=json.dumps({'username': 'logintest', 'password': 'correct123'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 1
        assert 'token' in data['data']

    def test_错误密码登录失败(self, create_tables, make_user, now):
        user = make_user(username='logintest2', password='right')

        client = Client()
        resp = client.post(
            '/api/chain/auth/login/',
            data=json.dumps({'username': 'logintest2', 'password': 'wrong123'}),
            content_type='application/json',
        )
        assert resp.json()['code'] == 401

    def test_不存在用户登录失败(self, create_tables):
        client = Client()
        resp = client.post(
            '/api/chain/auth/login/',
            data=json.dumps({'username': 'nobody', 'password': 'anything'}),
            content_type='application/json',
        )
        assert resp.json()['code'] == 401


class TestSendCodeApi:
    """POST /api/chain/auth/send-code/"""

    def test_邮箱发送验证码(self, create_tables, make_user, now):
        user = make_user(username='codetest', email='code@test.com')

        client = Client()
        resp = client.post(
            '/api/chain/auth/send-code/',
            data=json.dumps({
                'target': 'code@test.com',
                'send_type': 'email',
                'purpose': 'reset',
            }),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['code'] == 1
        assert len(data['data']['verificationCode']) == 6

    def test_未注册邮箱重置密码拒绝(self, create_tables):
        client = Client()
        resp = client.post(
            '/api/chain/auth/send-code/',
            data=json.dumps({
                'target': 'unknown@test.com',
                'send_type': 'email',
                'purpose': 'reset',
            }),
            content_type='application/json',
        )
        assert resp.json()['code'] == 400

    def test_邮箱格式不正确(self, create_tables):
        client = Client()
        resp = client.post(
            '/api/chain/auth/send-code/',
            data=json.dumps({
                'target': 'not-an-email',
                'send_type': 'email',
                'purpose': 'register',
            }),
            content_type='application/json',
        )
        assert resp.json()['code'] == 400

    def test_fullwidth_at_sign_conversion(self, create_tables, make_user, now):
        """全角 ＠ 应自动转换为半角 @"""
        user = make_user(username='fullwidth', email='full@test.com')

        client = Client()
        resp = client.post(
            '/api/chain/auth/send-code/',
            data=json.dumps({
                'target': 'full＠test.com',  # 全角 @
                'send_type': 'email',
                'purpose': 'reset',
            }),
            content_type='application/json',
        )
        assert resp.json()['code'] == 1  # 应该识别为已注册邮箱


class TestResetPasswordApi:
    """POST /api/chain/auth/reset-password/"""

    def test_完整重置流程(self, create_tables, make_user, now):
        from interview_md.models import UserAccount
        user = make_user(username='resetme', email='reset@test.com', password='oldpass12')

        client = Client()
        # 1. 发送验证码
        resp1 = client.post(
            '/api/chain/auth/send-code/',
            data=json.dumps({'target': 'reset@test.com', 'send_type': 'email', 'purpose': 'reset'}),
            content_type='application/json',
        )
        code = resp1.json()['data']['verificationCode']

        # 2. 重置密码
        resp2 = client.post(
            '/api/chain/auth/reset-password/',
            data=json.dumps({
                'identifier': 'reset@test.com',
                'verification_code': code,
                'new_password': 'newpass456',
                'confirm_password': 'newpass456',
                'reset_type': 'email',
            }),
            content_type='application/json',
        )
        assert resp2.json()['code'] == 1

        # 3. 用新密码登录
        resp3 = client.post(
            '/api/chain/auth/login/',
            data=json.dumps({'username': 'resetme', 'password': 'newpass456'}),
            content_type='application/json',
        )
        assert resp3.json()['code'] == 1

    def test_验证码错误拒绝(self, create_tables, make_user, now):
        user = make_user(username='wrongcode', email='wrongcode@test.com')

        client = Client()
        resp1 = client.post(
            '/api/chain/auth/send-code/',
            data=json.dumps({'target': 'wrongcode@test.com', 'send_type': 'email', 'purpose': 'reset'}),
            content_type='application/json',
        )

        resp2 = client.post(
            '/api/chain/auth/reset-password/',
            data=json.dumps({
                'identifier': 'wrongcode@test.com',
                'verification_code': '000000',  # 错误的验证码
                'new_password': 'newpass456',
                'confirm_password': 'newpass456',
                'reset_type': 'email',
            }),
            content_type='application/json',
        )
        assert resp2.json()['code'] == 400

    def test_两次密码不一致(self, create_tables, make_user, now):
        user = make_user(username='mismatch', email='mis@test.com')

        client = Client()
        resp1 = client.post(
            '/api/chain/auth/send-code/',
            data=json.dumps({'target': 'mis@test.com', 'send_type': 'email', 'purpose': 'reset'}),
            content_type='application/json',
        )
        code = resp1.json()['data']['verificationCode']

        resp2 = client.post(
            '/api/chain/auth/reset-password/',
            data=json.dumps({
                'identifier': 'mis@test.com',
                'verification_code': code,
                'new_password': 'pass1',
                'confirm_password': 'pass2',
                'reset_type': 'email',
            }),
            content_type='application/json',
        )
        assert resp2.json()['code'] == 400


# ============================================================
# 业务 API（需要认证）
# ============================================================

def _auth_header(user_id):
    """生成 Bearer token header"""
    token = issue_jwt(user_id)
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


class TestScenarioListApi:
    """GET /api/scenario/list/"""

    def test_获取岗位列表(self, create_tables, make_role, now):
        make_role(code='java', name='Java后端')
        make_role(code='frontend', name='前端开发')

        client = Client()
        resp = client.get('/api/scenario/list/')
        data = resp.json()
        assert data['code'] == 1
        assert len(data['data']) >= 2

    def test_仅返回激活状态的岗位(self, create_tables, make_role, now):
        make_role(code='active', is_active=1)
        make_role(code='inactive', is_active=0)

        client = Client()
        resp = client.get('/api/scenario/list/')
        data = resp.json()
        codes = [r['category'] for r in data['data']]
        assert 'active' in codes
        assert 'inactive' not in codes


class TestSessionCreateApi:
    """POST /api/session/create/"""

    def test_创建会话成功(self, create_tables, make_user, make_role,
                          make_difficulty, make_strategy, make_question, now):
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        for a in ['technical', 'project', 'scenario']:
            make_question(role.id, a)

        client = Client()
        resp = client.post(
            '/api/session/create/',
            data=json.dumps({'roleId': role.id, 'difficulty': 'easy', 'mode': 'text'}),
            content_type='application/json',
            **_auth_header(user.id),
        )
        data = resp.json()
        assert data['code'] == 1
        assert data['data']['sessionId'] is not None
        assert data['data']['status'] == 'running'

    def test_未认证无法创建(self, create_tables):
        client = Client()
        resp = client.post(
            '/api/session/create/',
            data=json.dumps({'roleId': 1}),
            content_type='application/json',
        )
        # DRF IsAuthenticated 返回 403，body 不含 code 字段
        assert resp.status_code in (401, 403)


class TestDialogueApi:
    """POST /api/dialogue/next/"""

    def test_提交回答并获取下题(self, create_tables, make_user, make_role,
                               make_difficulty, make_strategy, make_question,
                               mock_llm, now):
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        for a in ['technical', 'project', 'scenario']:
            make_question(role.id, a)
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        # LLM 调用：第1次->追问判断(否)，第2次->评估打分
        mock_llm.side_effect = [
            '{"need_followup": false, "followup_question": ""}',
            '{"content_score":80,"logic_score":78,"communication_score":85,"job_match_score":80,"confidence_score":75,"overall_score":80,"strengths":[],"weaknesses":[],"suggestions":[]}',
            '{"need_followup": false, "followup_question": ""}',
            '{"content_score":80,"logic_score":78,"communication_score":85,"job_match_score":80,"confidence_score":75,"overall_score":80,"strengths":[],"weaknesses":[],"suggestions":[]}',
            '{"need_followup": false, "followup_question": ""}',
            '{"content_score":80,"logic_score":78,"communication_score":85,"job_match_score":80,"confidence_score":75,"overall_score":80,"strengths":[],"weaknesses":[],"suggestions":[]}',
        ]

        client = Client()
        resp = client.post(
            '/api/dialogue/next/',
            data=json.dumps({'sessionId': str(session.id), 'content': '我的回答'}),
            content_type='application/json',
            **_auth_header(user.id),
        )
        data = resp.json()
        assert data['code'] == 1
        # 应有回复（无论是否结束）
        assert 'content' in data['data']


class TestReportApi:
    """GET /api/report/detail/"""

    def test_获取报告(self, create_tables, make_user, make_role,
                     make_difficulty, make_strategy, make_question, now):
        from interview_md.services.session_service import create_interview_session
        from interview_md.services.orchestrator import aggregate_report
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        for a in ['technical', 'project', 'scenario']:
            make_question(role.id, a)
        session = create_interview_session(user.id, role.id, 'easy', 'text')
        aggregate_report(session.id)

        client = Client()
        resp = client.get(
            '/api/report/detail/',
            {'sessionId': str(session.id)},
            **_auth_header(user.id),
        )
        data = resp.json()
        assert data['code'] == 1
        assert 'totalScore' in data['data']

    def test_不存在的会话返回404(self, create_tables, make_user, now):
        user = make_user()
        client = Client()
        resp = client.get(
            '/api/report/detail/',
            {'sessionId': '99999'},
            **_auth_header(user.id),
        )
        assert resp.json()['code'] == 404


class TestProfileApi:
    """GET /api/profile/trend/ 和 /api/profile/history/"""

    def test_趋势API(self, create_tables, make_user, make_role,
                    make_difficulty, make_strategy, now):
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')

        client = Client()
        resp = client.get(
            '/api/profile/trend/',
            {'userId': user.id, 'days': 7},
            **_auth_header(user.id),
        )
        data = resp.json()
        assert data['code'] == 1
        assert 'labels' in data['data']
        assert 'scores' in data['data']

    def test_历史API(self, create_tables, make_user, make_role,
                    make_difficulty, make_strategy, now):
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')

        client = Client()
        resp = client.get(
            '/api/profile/history/',
            {'userId': user.id, 'page': 1, 'size': 10},
            **_auth_header(user.id),
        )
        data = resp.json()
        assert data['code'] == 1
        assert 'records' in data['data']


class TestNormalizeDifficulty:
    """normalize_difficulty 工具函数测试"""

    def test_L1转easy(self):
        from interview_md.views import normalize_difficulty
        assert normalize_difficulty('L1') == 'easy'

    def test_L2转medium(self):
        from interview_md.views import normalize_difficulty
        assert normalize_difficulty('L2') == 'medium'

    def test_L3转hard(self):
        from interview_md.views import normalize_difficulty
        assert normalize_difficulty('L3') == 'hard'

    def test_空字符串默认easy(self):
        from interview_md.views import normalize_difficulty
        assert normalize_difficulty('') == 'easy'

    def test_已知值直接通过(self):
        from interview_md.views import normalize_difficulty
        assert normalize_difficulty('medium') == 'medium'
