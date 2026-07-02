"""
面试会话服务层单元测试（8 项）
覆盖: create_interview_session 核心流程及辅助函数
"""
from decimal import Decimal

import pytest
from django.utils import timezone

from interview_md.models import InterviewChain, InterviewRound, InterviewSession, SessionAspect
from interview_md.services.session_service import (
    _anchor_type,
    _default_q,
    _max_depth,
    _pick_question,
    create_interview_session,
)


class TestHelperFunctions:
    def test_锚点类型与默认题目(self):
        assert _anchor_type('technical') == 'knowledge_point'
        assert _anchor_type('project') == 'project_probe'
        assert _anchor_type('scenario') == 'scenario_case'
        assert '技术栈' in _default_q('technical')
        assert '项目' in _default_q('project')
        assert '请继续作答' in _default_q('unknown_type')

    def test_追问深度配置与默认值(self, create_tables, make_difficulty, now):
        diff = make_difficulty(technical_max_followup_depth=3, project_max_followup_depth=4, scenario_max_followup_depth=5)
        assert _max_depth(diff, 'technical') == 3
        assert _max_depth(diff, 'project') == 4
        assert _max_depth(diff, 'scenario') == 5
        # None/0 使用默认值 2
        diff2 = make_difficulty('medium', '中级', technical_max_followup_depth=0)
        assert _max_depth(diff2, 'technical') == 2

    def test_选题循环与空题库(self, create_tables, make_role, make_question, now):
        role = make_role()
        q1 = make_question(role.id, 'technical', topic='第一题')
        q2 = make_question(role.id, 'technical', topic='第二题')
        assert _pick_question(role.id, 'technical', 1).id == q1.id
        assert _pick_question(role.id, 'technical', 2).id == q2.id
        assert _pick_question(role.id, 'scenario', 1) is None


class TestCreateInterviewSession:
    def test_基本会话创建与事务完整性(self, create_tables, make_user, make_role,
                                       make_difficulty, make_strategy, now):
        user, role = make_user(), make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        assert session.user_id == user.id and session.status == 'running'
        assert session.total_chain_count == 3
        assert SessionAspect.objects.filter(session_id=session.id).count() == 3
        assert InterviewChain.objects.filter(session_id=session.id).count() == 3
        assert InterviewRound.objects.filter(session_id=session.id).count() == 1

    def test_错误场景与边界(self, create_tables, make_user, make_role,
                             make_difficulty, make_strategy, now):
        user, role = make_user(), make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        with pytest.raises(ValueError, match='岗位不存在'):
            create_interview_session(1, 999, 'easy', 'text')
        with pytest.raises(ValueError, match='难度不存在'):
            create_interview_session(1, role.id, 'impossible', 'text')

    def test_不同难度链数与权重策略(self, create_tables, make_user, make_role,
                                     make_difficulty, make_strategy, now):
        user, role = make_user(), make_role()
        diff = make_difficulty('hard', '高级', technical_chain_count=3, project_chain_count=2, scenario_chain_count=2)
        strat = make_strategy(role.id, 'hard', technical_weight=Decimal('0.50'),
                              project_weight=Decimal('0.30'), scenario_weight=Decimal('0.20'))
        session = create_interview_session(user.id, role.id, 'hard', 'text')
        assert session.total_chain_count == 7

        ta = SessionAspect.objects.get(session_id=session.id, aspect_type='technical')
        assert ta.aspect_weight == Decimal('0.50')

        # 首链 running，其余 created
        chains = InterviewChain.objects.filter(session_id=session.id).order_by('chain_no')
        assert chains[0].status == 'running'
        assert all(c.status == 'created' for c in chains[1:])

    def test_无策略默认与语音模式(self, create_tables, make_user, make_role,
                                   make_difficulty, now):
        user, role = make_user(), make_role()
        diff = make_difficulty('easy', '初级')
        # 无策略 → 默认权重
        session = create_interview_session(user.id, role.id, 'easy', 'text')
        pa = SessionAspect.objects.get(session_id=session.id, aspect_type='project')
        assert pa.aspect_weight == Decimal('0.33')

        # 语音模式
        session2 = create_interview_session(user.id, role.id, 'easy', 'voice')
        assert session2.mode == 'voice'
        assert session2.status == 'running'

    def test_session_context记录岗位信息(self, create_tables, make_user, make_role,
                                          make_difficulty, make_strategy, now):
        user, role = make_user(), make_role(code='python_dev', name='Python开发')
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')
        assert session.context_snapshot['roleCode'] == 'python_dev'
        assert session.context_snapshot['roleName'] == 'Python开发'
