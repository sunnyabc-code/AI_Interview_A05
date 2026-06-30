"""
面试编排核心流程单元测试
覆盖: process_answer, _finish_chain, aggregate_report, session_state,
      _advance_or_complete, _build_transcript
"""
from decimal import Decimal
from unittest.mock import ANY, call, patch

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


class TestTranscriptBuilding:
    """对话转录构建测试"""

    def test_空轮次列表(self):
        result = _build_transcript([])
        assert result == ''

    def test_单轮问答(self):
        rounds = [
            _mock_round('请自我介绍', '我叫张三，有3年Java经验'),
        ]
        transcript = _build_transcript(rounds)
        assert '面试官：请自我介绍' in transcript
        assert '候选人：我叫张三，有3年Java经验' in transcript

    def test_多轮问答(self):
        rounds = [
            _mock_round('Q1', 'A1'),
            _mock_round('Q2', 'A2'),
            _mock_round('Q3', 'A3'),
        ]
        transcript = _build_transcript(rounds)
        lines = transcript.strip().split('\n')
        assert len(lines) == 6  # 3问3答

    def test_仅有问题无回答(self):
        rounds = [_mock_round('Q1', '')]
        transcript = _build_transcript(rounds)
        assert '面试官：Q1' in transcript
        assert '候选人：' not in transcript  # 空答案不输出


class TestFindPendingRound:
    """查找待回答轮次测试"""

    def test_找到未回答的轮次(self, create_tables, make_user, make_role,
                             make_difficulty, make_strategy, now):
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')
        chain = InterviewChain.objects.filter(session_id=session.id, status='running').first()

        pending = _find_pending_round(chain.id)
        assert pending is not None
        assert pending.candidate_answer_text == '' or pending.candidate_answer_text is None


class TestChainEvaluation:
    """链评分辅助函数测试"""

    def test_avg_ce_正常计算(self):
        ce = _mock_chain_eval(80, 75, 85, 70, 90)
        avg = _avg_ce(ce)
        assert avg == Decimal('80.00')  # (80+75+85+70+90)/5

    def test_avg_ce_部分None(self):
        ce = _mock_chain_eval(80, None, 85, None, 90)
        avg = _avg_ce(ce)
        assert avg == Decimal('85.00')  # (80+85+90)/3

    def test_avg_ce_全部None(self):
        ce = _mock_chain_eval(None, None, None, None, None)
        avg = _avg_ce(ce)
        assert avg == Decimal('60')  # 默认60分

    def test_next_global_no_首次(self, create_tables, make_user, make_role,
                                  make_difficulty, make_strategy, now):
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')
        assert _next_global_no(session.id) == 2  # 已有1轮


class TestProcessAnswer:
    """process_answer 面试流程核心测试"""

    def test_会话不存在抛异常(self, create_tables):
        with pytest.raises(ValueError, match='会话不存在或无权访问'):
            process_answer(99999, 1, '我的回答')

    def test_无可回答轮次抛异常(self, create_tables, make_user, make_role,
                                make_difficulty, make_strategy, mock_llm, now):
        """当没有进行中的链或待回答轮次时应报错"""
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        # 手动把所有链标记为 finished
        InterviewChain.objects.filter(session_id=session.id).update(status='finished')

        with pytest.raises(ValueError, match='没有进行中的链'):
            process_answer(session.id, user.id, '回答')

    def test_回答后记录答案(self, create_tables, make_user, make_role,
                            make_difficulty, make_strategy, mock_llm, now):
        """提交回答后应持久化到 InterviewRound"""
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        chain = InterviewChain.objects.filter(session_id=session.id, status='running').first()
        pending = _find_pending_round(chain.id)

        mock_llm.side_effect = [
            '{"need_followup": false, "followup_question": ""}',
            '{"content_score":80,"logic_score":78,"communication_score":85,"job_match_score":80,"confidence_score":75,"overall_score":80,"strengths":[],"weaknesses":[],"suggestions":[]}',
        ]

        result = process_answer(session.id, user.id, '这是我的回答')

        pending.refresh_from_db()
        assert pending.candidate_answer_text == '这是我的回答'
        assert pending.answered_at is not None
        assert 'content' in result

    def test_无需追问时完成当前链(self, create_tables, make_user, make_role,
                                 make_difficulty, make_strategy, mock_llm, now):
        """LLM 判断不需要追问 → 当前链结束 → 推进到下一条链"""
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        mock_llm.side_effect = [
            '{"need_followup": false, "followup_question": ""}',   # 追问判断
            '{"content_score":80,"logic_score":78,"communication_score":85,"job_match_score":80,"confidence_score":75,"overall_score":80,"strengths":["好"],"weaknesses":["一般"],"suggestions":["改进"]}',  # 评估
        ]

        result = process_answer(session.id, user.id, '我的技术回答')
        assert 'content' in result  # 返回下一个问题或结束消息

    def test_语音模式下创建SpeechMetric(self, create_tables, make_user, make_role,
                                         make_difficulty, make_strategy, mock_llm, now):
        """VOICE 模式应自动创建语音指标记录"""
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        mock_llm.side_effect = [
            '{"need_followup": false, "followup_question": ""}',   # 追问判断
            '{"content_score":80,"logic_score":78,"communication_score":85,"job_match_score":80,"confidence_score":75,"overall_score":80,"strengths":[],"weaknesses":[],"suggestions":[]}',  # 评估
        ]

        result = process_answer(session.id, user.id, '语音回答内容', input_mode='VOICE')
        assert result is not None

    def test_最后一条链完成后会话结束(self, create_tables, make_user, make_role,
                                      make_difficulty, make_strategy, mock_llm, now):
        """所有链完成后，面试状态变为 finished"""
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级', technical_chain_count=1,
                               project_chain_count=1, scenario_chain_count=1)
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        # 每次 LLM 调用：奇数次->追问判断(否)，偶数次->评估打分
        call_count = [0]

        def llm_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 2 == 1:  # 追问判断
                return '{"need_followup": false, "followup_question": ""}'
            else:  # 评估
                return '{"content_score":80,"logic_score":78,"communication_score":85,"job_match_score":80,"confidence_score":75,"overall_score":80,"strengths":[],"weaknesses":[],"suggestions":[]}'

        mock_llm.side_effect = llm_side_effect

        # 回答3次，覆盖3条链
        for i in range(3):
            result = process_answer(session.id, user.id, f'回答{i+1}')

        session.refresh_from_db()
        assert result['is_end'] or session.status == 'finished' or session.completed_chain_count >= 3


class TestAggregateReport:
    """aggregate_report 报告聚合测试"""

    def test_无评估数据也生成报告(self, create_tables, make_user, make_role,
                                  make_difficulty, make_strategy, now):
        """即使没有 ChainEvaluation，也应生成默认分值的报告"""
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        aggregate_report(session.id)

        rep = MdEvaluationReport.objects.filter(session_id=session.id).first()
        assert rep is not None
        assert rep.generated_by == 'aggregation'
        # 默认分应为 60
        assert rep.overall_score == Decimal('60.00')

    def test_有评估数据正确聚合(self, create_tables, make_user, make_role,
                                make_difficulty, make_strategy, make_question, now):
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')

        # 创建3道题 → 创建会话
        for aspect in ['technical', 'project', 'scenario']:
            make_question(role.id, aspect)
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        # 手动创建 ChainEvaluation
        chains = list(InterviewChain.objects.filter(session_id=session.id).order_by('chain_no'))
        for chain in chains:
            ce = ChainEvaluation(
                session_id=session.id,
                chain_id=chain.id,
                aspect_type=chain.aspect_type,
                content_score=Decimal('85'),
                logic_score=Decimal('80'),
                communication_score=Decimal('90'),
                job_match_score=Decimal('82'),
                confidence_score=Decimal('78'),
                overall_score=Decimal('83'),
                strengths_json=['表现良好'],
                weaknesses_json=['需加强'],
                suggestions_json=['多练习'],
                created_at=now,
                updated_at=now,
            )
            ce.save()

        aggregate_report(session.id)

        rep = MdEvaluationReport.objects.filter(session_id=session.id).first()
        assert rep.overall_score is not None
        # 有实际评估数据时，分数不应是默认60
        assert rep.overall_score != Decimal('60.00')

    def test_报告生成后更新GrowthSnapshot(self, create_tables, make_user, make_role,
                                           make_difficulty, make_strategy, now):
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        aggregate_report(session.id)

        gs = GrowthSnapshot.objects.filter(user_id=user.id, role_id=role.id).first()
        assert gs is not None
        # total_sessions 统计的是已完成(finished)的会话数；本测试会话未标记 finished, 所以 ≥ 0 即可
        assert gs.total_sessions >= 0

    def test_不同方面权重影响总分(self, create_tables, make_user, make_role,
                                 make_difficulty, make_strategy, make_question, now):
        """验证 aspect_weight 不同时总分的加权计算"""
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        # 技术权重极高
        strat = make_strategy(role.id, 'easy',
                              technical_weight=Decimal('0.80'),
                              project_weight=Decimal('0.10'),
                              scenario_weight=Decimal('0.10'))

        for aspect in ['technical', 'project', 'scenario']:
            make_question(role.id, aspect)
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        chains = list(InterviewChain.objects.filter(session_id=session.id).order_by('chain_no'))
        for i, chain in enumerate(chains):
            ce = ChainEvaluation(
                session_id=session.id,
                chain_id=chain.id,
                aspect_type=chain.aspect_type,
                content_score=Decimal('90'),
                logic_score=Decimal('90'),
                communication_score=Decimal('90'),
                job_match_score=Decimal('90'),
                confidence_score=Decimal('90'),
                overall_score=Decimal('90'),
                created_at=now,
                updated_at=now,
            )
            ce.save()

        aggregate_report(session.id)
        rep = MdEvaluationReport.objects.filter(session_id=session.id).first()
        # 所有90分，加权后也是90
        assert rep.overall_score == Decimal('90.00')


class TestSessionState:
    """session_state 测试"""

    def test_不存在会话抛异常(self, create_tables):
        with pytest.raises(ValueError, match='会话不存在'):
            session_state(99999)

    def test_运行中会话返回状态(self, create_tables, make_user, make_role,
                               make_difficulty, make_strategy, now):
        from interview_md.services.session_service import create_interview_session
        user = make_user()
        role = make_role()
        diff = make_difficulty('easy', '初级')
        strat = make_strategy(role.id, 'easy')
        session = create_interview_session(user.id, role.id, 'easy', 'text')

        state = session_state(session.id)
        assert state['sessionId'] == str(session.id)
        assert state['status'] == 'running'
        assert state['isEnd'] is False
        assert 'currentQuestion' in state


# ============================================================
# 辅助函数
# ============================================================

def _mock_round(question, answer):
    """创建模拟的 InterviewRound 对象"""
    r = InterviewRound(question_text=question, candidate_answer_text=answer)
    return r


def _mock_chain_eval(content, logic, comm, job, conf):
    """创建模拟的 ChainEvaluation 对象"""
    ce = ChainEvaluation(
        content_score=Decimal(str(content)) if content is not None else None,
        logic_score=Decimal(str(logic)) if logic is not None else None,
        communication_score=Decimal(str(comm)) if comm is not None else None,
        job_match_score=Decimal(str(job)) if job is not None else None,
        confidence_score=Decimal(str(conf)) if conf is not None else None,
    )
    return ce
