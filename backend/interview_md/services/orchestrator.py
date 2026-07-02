import json
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from interview_md.models import (
    ChainEvaluation,
    GrowthSnapshot,
    InterviewChain,
    InterviewRound,
    InterviewSession,
    JobRole,
    MdEvaluationReport,
    QuestionBank,
    SessionAspect,
    SpeechMetric,
)
from interview_md.services import llm

ASPECT_LABEL = {'technical': '技术知识', 'project': '项目经历深挖', 'scenario': '场景题'}


def _nz(v, d):
    return d if v is None else v


def _build_transcript(rounds):
    lines = []
    for r in rounds:
        if r.question_text:
            lines.append(f'面试官：{r.question_text}')
        if r.candidate_answer_text:
            lines.append(f'候选人：{r.candidate_answer_text}')
    return '\n'.join(lines)


def _find_pending_round(chain_id):
    for r in InterviewRound.objects.filter(chain_id=chain_id).order_by('global_round_no'):
        if not (r.candidate_answer_text or '').strip():
            return r
    return None


def _next_global_no(session_id: int) -> int:
    last = InterviewRound.objects.filter(session_id=session_id).order_by('-global_round_no').first()
    return 1 if not last else last.global_round_no + 1


def _default_main_question(aspect: str) -> str:
    return {
        'technical': '请介绍你熟悉的一项核心技术，并说明你在项目中的实践。',
        'project': '请详细描述一个你主导或深度参与的项目。',
        'scenario': '请描述一次线上故障或棘手问题，你是如何定位与解决的。',
    }.get(aspect, '请继续作答。')


@transaction.atomic
def process_answer(session_id: int, user_id: int, answer: str, input_mode: str = 'TEXT'):
    session = InterviewSession.objects.select_for_update().filter(pk=session_id, user_id=user_id).first()
    if not session:
        raise ValueError('会话不存在或无权访问')
    if session.status != 'running':
        raise ValueError('会话已结束')

    chain = InterviewChain.objects.filter(session_id=session_id, status='running').first()
    if not chain:
        raise ValueError('没有进行中的链')

    pending = _find_pending_round(chain.id)
    if not pending:
        raise ValueError('没有待回答的问题')

    now = timezone.now()
    pending.candidate_answer_text = answer
    pending.answered_at = now
    pending.updated_at = now
    pending.save()

    if input_mode.upper() == 'VOICE':
        sm = SpeechMetric(
            round_id=pending.id,
            audio_duration_ms=max(1000, len(answer) * 80),
            speaking_rate_wpm=Decimal(str(min(220, 120 + len(answer) // 8))),
            pause_count=0,
            avg_pause_ms=0,
            clarity_score=Decimal('75'),
            confidence_score=Decimal('70'),
            emotion_label='neutral',
            raw_features={'source': 'estimate'},
            created_at=now,
            updated_at=now,
        )
        sm.save()

    chain_rounds = list(InterviewRound.objects.filter(chain_id=chain.id).order_by('round_no_in_chain'))
    followups_used = max(0, len(chain_rounds) - 1)
    can_follow = followups_used < _nz(chain.max_followup_depth, 2)

    if can_follow:
        transcript = _build_transcript(chain_rounds)
        role = JobRole.objects.filter(pk=session.role_id).first()
        rn = role.name if role else '技术岗位'
        sys = f'''你是严谨的企业面试官，岗位方向：{rn}，当前环节：{ASPECT_LABEL.get(chain.aspect_type, "面试")}。
根据对话判断是否需要追问。只输出 JSON：{{"need_followup":true/false,"followup_question":"..."}}
【对话】
{transcript}'''
        raw = llm.call_llm(sys, None)
        fj = llm.extract_json_obj(raw)
        need = bool(fj.get('need_followup'))
        fq = (fj.get('followup_question') or '').strip()
        if need and fq:
            nr = InterviewRound(
                session_id=session.id,
                chain_id=chain.id,
                global_round_no=_next_global_no(session.id),
                round_no_in_chain=len(chain_rounds) + 1,
                parent_round_id=pending.id,
                is_followup=1,
                question_text=fq,
                question_source='llm_generated',
                asked_at=now,
                created_at=now,
                updated_at=now,
            )
            nr.save()
            chain.round_count = len(chain_rounds) + 1
            chain.current_followup_depth = followups_used + 1
            chain.updated_at = now
            chain.save()
            return {'content': fq, 'is_end': False, 'session': session}

    _finish_chain(session, chain, chain_rounds)
    session.refresh_from_db()
    return _advance_or_complete(InterviewSession.objects.get(pk=session.id), now)


def _avg_ce(ce: ChainEvaluation):
    s = Decimal('0')
    n = 0
    for f in (ce.content_score, ce.logic_score, ce.communication_score, ce.job_match_score, ce.confidence_score):
        if f is not None:
            s += f
            n += 1
    if n == 0:
        return Decimal('60')
    return (s / n).quantize(Decimal('0.01'))


def _finish_chain(session: InterviewSession, chain: InterviewChain, chain_rounds):
    transcript = _build_transcript(chain_rounds)
    role = JobRole.objects.filter(pk=session.role_id).first()
    rn = role.name if role else '工程师'
    sys = f'''你是面试评估专家。请根据「岗位：{rn}」与以下对话，对本轮问答打分（0-100）。
只输出 JSON：
{{"content_score":0,"logic_score":0,"communication_score":0,"job_match_score":0,"confidence_score":0,"overall_score":0,
"strengths":["亮点"],"weaknesses":["不足"],"suggestions":["建议"]}}
【对话】
{transcript}'''
    raw = llm.call_llm(sys, None)
    j = llm.extract_json_obj(raw)
    now = timezone.now()

    def _bd(k, default='65'):
        try:
            return Decimal(str(j.get(k, default)))
        except Exception:
            return Decimal(default)

    ce = ChainEvaluation(
        session_id=session.id,
        chain_id=chain.id,
        aspect_type=chain.aspect_type,
        rubric_id=None,
        evaluation_mode='llm_only',
        grounding_status='not_used',
        retrieval_hit_count=0,
        content_score=_bd('content_score'),
        logic_score=_bd('logic_score'),
        communication_score=_bd('communication_score'),
        job_match_score=_bd('job_match_score'),
        confidence_score=_bd('confidence_score'),
        overall_score=_bd('overall_score'),
        strengths_json=j.get('strengths') or [],
        weaknesses_json=j.get('weaknesses') or [],
        suggestions_json=j.get('suggestions') or [],
        llm_result_json=raw[:65000],
        created_at=now,
        updated_at=now,
    )
    ce.save()
    ov = ce.overall_score if ce.overall_score is not None else _avg_ce(ce)
    chain.chain_score = ov
    chain.status = 'finished'
    chain.finished_at = now
    chain.updated_at = now
    chain.save()

    sa = SessionAspect.objects.get(pk=chain.session_aspect_id)
    sa.completed_chain_count = _nz(sa.completed_chain_count, 0) + 1
    if sa.completed_chain_count >= _nz(sa.planned_chain_count, 1):
        sa.status = 'finished'
    sa.updated_at = now
    sa.save()

    session.completed_chain_count = _nz(session.completed_chain_count, 0) + 1
    session.updated_at = now
    session.save()


def _advance_or_complete(session: InterviewSession, now):
    session = InterviewSession.objects.get(pk=session.id)
    if _nz(session.completed_chain_count, 0) >= _nz(session.total_chain_count, 1):
        session.status = 'finished'
        session.finished_at = now
        session.save()
        aggregate_report(session.id)
        return {
            'content': '本场面试已结束，系统已生成结构化评估报告。',
            'is_end': True,
            'session': session,
        }

    nxt = InterviewChain.objects.filter(session_id=session.id, status='created').order_by('chain_no').first()
    if not nxt:
        session.status = 'finished'
        session.finished_at = now
        session.save()
        aggregate_report(session.id)
        return {'content': '面试结束。', 'is_end': True, 'session': session}

    nxt.status = 'running'
    nxt.started_at = now
    nxt.updated_at = now
    nxt.save()

    sa = SessionAspect.objects.get(pk=nxt.session_aspect_id)
    if sa.status == 'pending':
        sa.status = 'running'
        sa.updated_at = now
        sa.save()

    qb = QuestionBank.objects.filter(pk=nxt.anchor_id).first() if nxt.anchor_id else None
    qtext = qb.question_text if qb and qb.question_text else _default_main_question(nxt.aspect_type)
    label = ASPECT_LABEL.get(nxt.aspect_type, '环节')
    full_q = f'【{label}】\n{qtext}'

    nr = InterviewRound(
        session_id=session.id,
        chain_id=nxt.id,
        global_round_no=_next_global_no(session.id),
        round_no_in_chain=1,
        is_followup=0,
        question_text=full_q,
        question_source='question_bank' if qb else 'llm_generated',
        asked_at=now,
        created_at=now,
        updated_at=now,
    )
    nr.save()
    nxt.round_count = 1
    nxt.current_followup_depth = 0
    nxt.updated_at = now
    nxt.save()

    return {'content': full_q, 'is_end': False, 'session': session}


def aggregate_report(session_id: int):
    session = InterviewSession.objects.filter(pk=session_id).first()
    if not session:
        return

    evals = list(ChainEvaluation.objects.filter(session_id=session_id))
    by_aspect = {'technical': [], 'project': [], 'scenario': []}
    for ce in evals:
        if ce.overall_score is not None:
            by_aspect.setdefault(ce.aspect_type, []).append(ce.overall_score)

    def _avg(lst):
        if not lst:
            return Decimal('60')
        return (sum(lst, Decimal('0')) / len(lst)).quantize(Decimal('0.01'))

    tech = _avg(by_aspect['technical'])
    proj = _avg(by_aspect['project'])
    scen = _avg(by_aspect['scenario'])

    aspects = list(SessionAspect.objects.filter(session_id=session_id))
    w_t, w_p, w_s = Decimal('0.34'), Decimal('0.33'), Decimal('0.33')
    for sa in aspects:
        if sa.aspect_type == 'technical' and sa.aspect_weight:
            w_t = sa.aspect_weight
        if sa.aspect_type == 'project' and sa.aspect_weight:
            w_p = sa.aspect_weight
        if sa.aspect_type == 'scenario' and sa.aspect_weight:
            w_s = sa.aspect_weight

    overall = (tech * w_t + proj * w_p + scen * w_s).quantize(Decimal('0.01'))

    n = max(1, len(evals))
    c = sum((e.content_score or Decimal('0') for e in evals), Decimal('0')) / n
    l = sum((e.logic_score or Decimal('0') for e in evals), Decimal('0')) / n
    comm = sum((e.communication_score or Decimal('0') for e in evals), Decimal('0')) / n
    jm = sum((e.job_match_score or Decimal('0') for e in evals), Decimal('0')) / n
    cf = sum((e.confidence_score or Decimal('0') for e in evals), Decimal('0')) / n

    for sa in aspects:
        sc = _avg(by_aspect.get(sa.aspect_type, []))
        sa.aspect_score = sc
        sa.updated_at = timezone.now()
        sa.save(update_fields=['aspect_score', 'updated_at'])

    session.overall_score = overall
    session.summary = '技术/项目/场景三方面加权总分，详见报告。'
    session.updated_at = timezone.now()
    session.save(update_fields=['overall_score', 'summary', 'updated_at'])

    strengths, weaknesses, suggestions = [], [], []
    for ce in evals:
        if ce.strengths_json:
            strengths.extend(ce.strengths_json if isinstance(ce.strengths_json, list) else [])
        if ce.weaknesses_json:
            weaknesses.extend(ce.weaknesses_json if isinstance(ce.weaknesses_json, list) else [])
        if ce.suggestions_json:
            suggestions.extend(ce.suggestions_json if isinstance(ce.suggestions_json, list) else [])

    aspect_json = {'technical': float(tech), 'project': float(proj), 'scenario': float(scen)}
    dim_json = {
        'content': float(c.quantize(Decimal('0.01'))),
        'logic': float(l.quantize(Decimal('0.01'))),
        'communication': float(comm.quantize(Decimal('0.01'))),
        'job_match': float(jm.quantize(Decimal('0.01'))),
        'confidence': float(cf.quantize(Decimal('0.01'))),
    }
    plan = ['针对薄弱维度完成专项链式练习', '用 STAR 法则复盘本次问答']

    md_lines = ['# 模拟面试评估报告', '', f'## 综合得分：{overall}', '']
    md_lines.append('### 三方面得分')
    md_lines.append(f'- 技术知识：{tech}')
    md_lines.append(f'- 项目深挖：{proj}')
    md_lines.append(f'- 场景题：{scen}')

    now = timezone.now()
    rep_defaults = {
        'generated_by': 'aggregation',
        'overall_score': overall,
        'technical_score': tech,
        'project_score': proj,
        'scenario_score': scen,
        'content_score': c,
        'logic_score': l,
        'communication_score': comm,
        'job_match_score': jm,
        'confidence_score': cf,
        'aspect_scores_json': aspect_json,
        'dimension_scores_json': dim_json,
        'strengths_json': strengths,
        'weaknesses_json': weaknesses,
        'improvement_suggestions_json': suggestions,
        'next_step_plan_json': plan,
        'report_markdown': '\n'.join(md_lines),
        'report_json': {'overall_score': float(overall), 'aspect_scores': aspect_json, 'dimension_avg': dim_json},
        'created_at': now,
        'updated_at': now,
    }
    rep, created = MdEvaluationReport.objects.update_or_create(session_id=session_id, defaults=rep_defaults)
    if created:
        rep.created_at = now
        rep.save(update_fields=['created_at'])

    today = timezone.now().date()
    total_finished = InterviewSession.objects.filter(
        user_id=session.user_id, role_id=session.role_id, status='finished'
    ).count()
    gs_defaults = {
        'total_sessions': total_finished,
        'avg_overall_score': overall,
        'avg_technical_score': tech,
        'avg_project_score': proj,
        'avg_scenario_score': scen,
        'avg_content_score': c,
        'avg_logic_score': l,
        'avg_communication_score': comm,
        'avg_job_match_score': jm,
        'avg_confidence_score': cf,
        'latest_summary': '最近一次模拟面试已完成，请查看报告中的改进建议。',
        'created_at': now,
        'updated_at': now,
    }
    gs, gsc = GrowthSnapshot.objects.update_or_create(
        user_id=session.user_id, role_id=session.role_id, stat_date=today, defaults=gs_defaults
    )
    if gsc:
        gs.created_at = timezone.now()
        gs.save(update_fields=['created_at'])


def session_state(session_id: int):
    session = InterviewSession.objects.filter(pk=session_id).first()
    if not session:
        raise ValueError('会话不存在')
    chain = InterviewChain.objects.filter(session_id=session_id, status='running').first()
    pending = _find_pending_round(chain.id) if chain else None
    show = pending
    if not show and chain:
        show = InterviewRound.objects.filter(chain_id=chain.id).order_by('-global_round_no').first()
    data = {
        'sessionId': str(session_id),
        'status': session.status,
        'totalChains': session.total_chain_count,
        'completedChains': session.completed_chain_count,
        'isEnd': session.status == 'finished',
    }
    if chain:
        data['aspectType'] = chain.aspect_type
        data['aspectLabel'] = ASPECT_LABEL.get(chain.aspect_type, '')
        data['chainNo'] = chain.chain_no
    if show and show.question_text:
        data['openingQuestion'] = show.question_text
        data['currentQuestion'] = show.question_text
    return data
