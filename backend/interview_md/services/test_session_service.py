"""
面试会话服务层单元测试
覆盖: create_interview_session 及辅助函数
"""
from decimal import Decimal

import pytest
from django.db import transaction
from django.utils import timezone

from interview_md.models import (
    InterviewChain,
    InterviewRound,
    InterviewSession,
    SessionAspect,
)
from interview_md.services.session_service import (
    _anchor_type,
    _default_q,
    _max_depth,
    _pick_question,
    create_interview_session,
)


class TestHelperFunctions:
    """辅助函数单元测试"""

    def test_anchor_type_technical(self):
        assert _anchor_type('technical') == 'knowledge_point'

    def test_anchor_type_project(self):
        assert _anchor_type('project') == 'project_probe'

    def test_anchor_type_scenario(self):
        assert _anchor_type('scenario') == 'scenario_case'

    def test_default_q_technical(self):
        q = _default_q('technical')
        assert '技术栈' in q

    def test_default_q_project(self):
        q = _default_q('project')
        assert '项目' in q

    def test_default_q_scenario(self):
        q = _default_q('scenario')
        assert '延迟' in q or '排查' in q or '线上' in q

    def test_default_q_unknown_aspect(self):
        q = _default_q('unknown_type')
        assert '请继续作答' in q

    def test_max_depth_technical(self, create_tables, make_difficulty, now):
        diff = make_difficulty(technical_max_followup_depth=3)
        assert _max_depth(diff, 'technical') == 3

    def test_max_depth_project(self, create_tables, make_difficulty, now):
        diff = make_difficulty(project_max_followup_depth=4)
        assert _max_depth(diff, 'project') == 4

    def test_max_depth_scenario(self, create_tables, make_difficulty, now):
        diff = make_difficulty(scenario_max_followup_depth=5)
        assert _max_depth(diff, 'scenario') == 5

    def test_max_depth_默认值(self, create_tables, make_difficulty, now):
        """当配置为 None 或 0 时使用默认值 2"""
        diff = make_difficulty(technical_max_followup_depth=0)
        assert _max_depth(diff, 'technical') == 2

    def test_pick_question_循环选题(self, create_tables, make_role, make_question, now):
        """相同 chain_idx 应选到不同的题（轮询）"""
        role = make_role()
        q1 = make_question(role.id, 'technical', topic='第一题')
        q2 = make_question(role.id, 'technical', topic='第二题')

        result1 = _pick_question(role.id, 'technical', 1)
        result2 = _pick_question(role.id, 'technical', 2)
        assert result1.id == q1.id
        assert result2.id == q2.id

    def test_pick_question_无题目返回None(self, create_tables, make_role):
        role = make_role()
        result = _pick_question(role.id, 'technical', 1)
        assert result is None


class TestCreateInterviewSession:
    """create_interview_session 核心流程测试"""

    def test_基本会话创建成功(self, create_tables, make_user, make_role,
                                make_difficulty, make_strategy, now):
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')

        session = create_interview_session(user.id, role.id, 'easy', 'text')

        assert session is not None
        assert session.user_id == user.id
        assert session.role_id == role.id
        assert session.status == 'running'
        assert session.total_chain_count == 3  # 默认 tech/proj/scen 各1

    def test_岗位不存在抛异常(self, create_tables):
        with pytest.raises(ValueError, match='岗位不存在或未启用'):
            create_interview_session(1, 999, 'easy', 'text')

    def test_难度不存在抛异常(self, create_tables, make_role, now):
        role = make_role()
        with pytest.raises(ValueError, match='难度不存在'):
            create_interview_session(1, role.id, 'impossible', 'text')

    def test_会话创建在事务中完成(self, create_tables, make_user, make_role,
                                   make_difficulty, make_strategy, now):
        """事务原子性：要么全部成功，要么全部回滚"""
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')

        session = create_interview_session(user.id, role.id, 'easy', 'text')

        # 验证所有关联记录都已创建
        aspects = SessionAspect.objects.filter(session_id=session.id)
        assert aspects.count() == 3  # tech/proj/scen

        chains = InterviewChain.objects.filter(session_id=session.id)
        assert chains.count() == 3

        rounds = InterviewRound.objects.filter(session_id=session.id)
        assert rounds.count() == 1  # 首轮问题已创建

    def test_不同难度影响链数(self, create_tables, make_user, make_role,
                               make_difficulty, make_strategy, now):
        """难度配置不同应产生不同数量的面试链"""
        user = make_user()
        role = make_role()
        diff = make_difficulty('hard', '高级',
                               technical_chain_count=3,
                               project_chain_count=2,
                               scenario_chain_count=2)
        strat = make_strategy(role.id, 'hard')

        session = create_interview_session(user.id, role.id, 'hard', 'text')
        assert session.total_chain_count == 7  # 3+2+2

    def test_首条链状态为running(self, create_tables, make_user, make_role,
                                  make_difficulty, make_strategy, now):
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')

        session = create_interview_session(user.id, role.id, 'easy', 'text')
        first_chain = InterviewChain.objects.filter(session_id=session.id).order_by('chain_no').first()
        assert first_chain.status == 'running'

    def test_其余链状态为created(self, create_tables, make_user, make_role,
                                   make_difficulty, make_strategy, now):
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')

        session = create_interview_session(user.id, role.id, 'easy', 'text')
        other_chains = InterviewChain.objects.filter(
            session_id=session.id, status='created'
        )
        assert other_chains.count() == 2  # 除第一条外都是 created

    def test_Aspect权重来自策略(self, create_tables, make_user, make_role,
                                 make_difficulty, make_strategy, now):
        """SessionAspect 的权重应从 RoleInterviewStrategy 读取"""
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy',
                              technical_weight=Decimal('0.50'),
                              project_weight=Decimal('0.30'),
                              scenario_weight=Decimal('0.20'))

        session = create_interview_session(user.id, role.id, 'easy', 'text')
        ta = SessionAspect.objects.get(session_id=session.id, aspect_type='technical')
        assert ta.aspect_weight == Decimal('0.50')

    def test_无策略时使用默认权重(self, create_tables, make_user, make_role,
                                   make_difficulty, now):
        """没有 RoleInterviewStrategy 时应有合理默认值"""
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        # 不创建 strategy

        session = create_interview_session(user.id, role.id, 'easy', 'text')
        pa = SessionAspect.objects.get(session_id=session.id, aspect_type='project')
        assert pa.aspect_weight == Decimal('0.33')

    def test_session_context_snapshot记录岗位信息(self, create_tables, make_user,
                                                    make_role, make_difficulty,
                                                    make_strategy, now):
        user = make_user()
        role = make_role(code='python_dev', name='Python开发')
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')

        session = create_interview_session(user.id, role.id, 'easy', 'text')
        assert session.context_snapshot['roleCode'] == 'python_dev'
        assert session.context_snapshot['roleName'] == 'Python开发'

    def test_语音模式会话创建(self, create_tables, make_user, make_role,
                               make_difficulty, make_strategy, now):
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')

        session = create_interview_session(user.id, role.id, 'easy', 'voice')
        assert session.mode == 'voice'
        assert session.status == 'running'
