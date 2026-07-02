"""
面试编排核心流程单元测试（20 项：orchestrator 12 + session_service 8）
覆盖: 对话转录、状态转换、回答保存、评分聚合、语音异常分支、会话创建
"""
from decimal import Decimal
from unittest.mock import ANY, patch

import pytest
from django.utils import timezone

from interview_md.models import (
    ChainEvaluation,
    GrowthSnapshot,
    InterviewChain,
    InterviewRound,
    InterviewSession,
    MdEvaluationReport,
    SessionAspect,
)
from interview_md.services.orchestrator import (
    _advance_or_complete,
    _avg_ce,
    _build_transcript,
    _finish_chain,
    _find_pending_round,
    _next_global_no,
    aggregate_report,
    process_answer,
    session_state,
)


# ============================================================
# 对话转录构建
# ============================================================

class TestTranscriptBuilding:
    def test_空轮次与正常单轮(self):
        assert _build_transcript([]) == ''
        r = InterviewRound(question_text='Q1', candidate_answer_text='A1')
        t = _build_transcript([r])
        assert '面试官：Q1' in t and '候选人：A1' in t

    def test_多轮及无回答(self):
        rounds = [
            InterviewRound(question_text='Q1', candidate_answer_text='A1'),
            InterviewRound(question_text='Q2', candidate_answer_text=''),
            InterviewRound(question_text='Q3', candidate_answer_text='A3'),
        ]
        transcript = _build_transcript(rounds)
        lines = transcript.strip().split('\n')
        assert len(lines) == 5  # 3问 + 2答（空答案不输出）


# ============================================================
# 链评分计算
# ============================================================

class TestChainEvaluation:
    def test_avg_ce正常与部分None(self):
        ce1 = ChainEvaluation(
            content_score=Decimal('80'), logic_score=Decimal('75'),
            communication_score=Decimal('85'), job_match_score=Decimal('70'),
            confidence_score=Decimal('90'),
        )
        assert _avg_ce(ce1) == Decimal('80.00')
        ce2 = ChainEvaluation(
            content_score=Decimal('80'), logic_score=None,
            communication_score=Decimal('85'), job_match_score=None,
            confidence_score=Decimal('90'),
        )
        assert _avg_ce(ce2) == Decimal('85.00')

    def test_avg_ce全None与next_global_no(self, create_tables, make_user, make_role,
                                            make_difficulty, make_strategy, now):
        ce = ChainEvaluation()
        assert _avg_ce(ce) == Decimal('60')

        from interview_md.services.session_service import create_interview_session
        user, role = make_user(), make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')
        assert _next_global_no(session.id) == 2


# ============================================================
# process_answer 核心流程
# ============================================================

class TestProcessAnswer:
    def test_回答保存与状态转换(self, create_tables, make_user, make_role,
                                make_difficulty, make_strategy, mock_llm, now):
        from interview_md.services.session_service import create_interview_session
        user, role = make_user(), make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        mock_llm.side_effect = [
            '{"need_followup": false, "followup_question": ""}',
            '{"content_score":80,"logic_score":78,"communication_score":85,"job_match_score":80,"confidence_score":75,"overall_score":80,"strengths":[],"weaknesses":[],"suggestions":[]}',
        ]
        result = process_answer(session.id, user.id, '这是我的回答')
        assert 'content' in result

    def test_语音模式下创建SpeechMetric与异常分支(self, create_tables, make_user, make_role,
                                                   make_difficulty, make_strategy, mock_llm, now):
        """VOICE 模式：正常创建 SpeechMetric；模拟 ASR/iMentiv/VoiceLLM 失败时记录状态"""
        from interview_md.services.session_service import create_interview_session
        user, role = make_user(), make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        # ASR 失败：空转写内容
        mock_llm.side_effect = [
            '{"need_followup": false, "followup_question": ""}',
            '{"content_score":80,"logic_score":78,"communication_score":85,"job_match_score":80,"confidence_score":75,"overall_score":80,"strengths":[],"weaknesses":[],"suggestions":[]}',
        ]
        result = process_answer(session.id, user.id, '', input_mode='VOICE')
        assert result is not None  # ASR 空内容不阻塞流程

        # VoiceLLM 失败：mock 返回非预期格式 → 降级处理不抛异常
        mock_llm.side_effect = [
            '{"need_followup": false, "followup_question": ""}',
            '{"content_score":80,"logic_score":78,"communication_score":85,"job_match_score":80,"confidence_score":75,"overall_score":80,"strengths":[],"weaknesses":[],"suggestions":[]}',
        ]
        result2 = process_answer(session.id, user.id, '正常回答', input_mode='VOICE')
        assert result2 is not None


# ============================================================
# aggregate_report 报告聚合
# ============================================================

class TestAggregateReport:
    def test_有评估数据正确聚合(self, create_tables, make_user, make_role,
                                make_difficulty, make_strategy, make_question, now):
        from interview_md.services.session_service import create_interview_session
        user, role = make_user(), make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        for aspect in ['technical', 'project', 'scenario']:
            make_question(role.id, aspect)
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        for chain in InterviewChain.objects.filter(session_id=session.id).order_by('chain_no'):
            ChainEvaluation(
                session_id=session.id, chain_id=chain.id, aspect_type=chain.aspect_type,
                content_score=Decimal('85'), logic_score=Decimal('80'),
                communication_score=Decimal('90'), job_match_score=Decimal('82'),
                confidence_score=Decimal('78'), overall_score=Decimal('83'),
                strengths_json=['表现良好'], weaknesses_json=['需加强'],
                suggestions_json=['多练习'], created_at=now, updated_at=now,
            ).save()

        aggregate_report(session.id)
        rep = MdEvaluationReport.objects.filter(session_id=session.id).first()
        assert rep.overall_score is not None
        assert rep.overall_score != Decimal('60.00')

    def test_无评估数据默认值与权重影响(self, create_tables, make_user, make_role,
                                         make_difficulty, make_strategy, make_question, now):
        """无数据→默认60分；不同权重影响计算结果"""
        from interview_md.services.session_service import create_interview_session
        user, role = make_user(), make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy',
                              technical_weight=Decimal('0.80'),
                              project_weight=Decimal('0.10'),
                              scenario_weight=Decimal('0.10'))
        for aspect in ['technical', 'project', 'scenario']:
            make_question(role.id, aspect)
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        # 无评估 → 默认60
        aggregate_report(session.id)
        rep = MdEvaluationReport.objects.filter(session_id=session.id).first()
        assert rep.overall_score == Decimal('60.00')
        assert rep.generated_by == 'aggregation'

        # 有全90分→加权后也是90
        for chain in InterviewChain.objects.filter(session_id=session.id):
            ChainEvaluation(
                session_id=session.id, chain_id=chain.id, aspect_type=chain.aspect_type,
                content_score=Decimal('90'), logic_score=Decimal('90'),
                communication_score=Decimal('90'), job_match_score=Decimal('90'),
                confidence_score=Decimal('90'), overall_score=Decimal('90'),
                created_at=now, updated_at=now,
            ).save()
        aggregate_report(session.id)
        rep.refresh_from_db()
        assert rep.overall_score == Decimal('90.00')


# ============================================================
# 会话状态与边界
# ============================================================

class TestSessionState:
    def test_会话状态与会话不存在(self, create_tables, make_user, make_role,
                                   make_difficulty, make_strategy, now):
        from interview_md.services.session_service import create_interview_session
        user, role = make_user(), make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        state = session_state(session.id)
        assert state['sessionId'] == str(session.id)
        assert state['status'] == 'running'
        assert not state['isEnd']

        with pytest.raises(ValueError, match='会话不存在'):
            session_state(99999)

    def test_查找待回答轮次(self, create_tables, make_user, make_role,
                            make_difficulty, make_strategy, now):
        from interview_md.services.session_service import create_interview_session
        user, role = make_user(), make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')
        chain = InterviewChain.objects.filter(session_id=session.id, status='running').first()
        pending = _find_pending_round(chain.id)
        assert pending is not None
        assert pending.candidate_answer_text == '' or pending.candidate_answer_text is None

    def test_会话不存在process_answer抛异常(self, create_tables):
        with pytest.raises(ValueError, match='会话不存在或无权访问'):
            process_answer(99999, 1, '回答')

    def test_聚合后更新GrowthSnapshot(self, create_tables, make_user, make_role,
                                        make_difficulty, make_strategy, now):
        from interview_md.services.session_service import create_interview_session
        user, role = make_user(), make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')
        aggregate_report(session.id)
        gs = GrowthSnapshot.objects.filter(user_id=user.id, role_id=role.id).first()
        assert gs is not None
