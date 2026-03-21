from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from interview_md.models import (
    DifficultyConfig,
    InterviewChain,
    InterviewRound,
    InterviewSession,
    JobRole,
    QuestionBank,
    RoleInterviewStrategy,
    SessionAspect,
)

ASPECT_TYPES = ('technical', 'project', 'scenario')
ASPECT_NAMES = ('技术知识', '项目经历深挖', '场景题')


def _nz(v, d):
    return d if v is None or v < 1 else v


def _max_depth(diff: DifficultyConfig, aspect: str) -> int:
    if aspect == 'technical':
        return _nz(diff.technical_max_followup_depth, 2)
    if aspect == 'project':
        return _nz(diff.project_max_followup_depth, 2)
    return _nz(diff.scenario_max_followup_depth, 2)


def _anchor_type(aspect: str) -> str:
    if aspect == 'project':
        return 'project_probe'
    if aspect == 'scenario':
        return 'scenario_case'
    return 'knowledge_point'


def _pick_question(role_id: int, aspect: str, chain_idx: int):
    qs = list(
        QuestionBank.objects.filter(role_id=role_id, aspect_type=aspect, is_active=1).order_by('id')
    )
    if not qs:
        return None
    return qs[(chain_idx - 1) % len(qs)]


def _default_q(aspect: str) -> str:
    return {
        'technical': '请先简要介绍你最熟悉的一门技术栈，并说明你在项目中的使用方式。',
        'project': '请介绍一个你负责的核心项目：背景、你的职责、关键难点与结果。',
        'scenario': '如果线上接口延迟突然升高，你会如何排查与处理？',
    }.get(aspect, '请继续作答。')


@transaction.atomic
def create_interview_session(user_id: int, role_id: int, difficulty_code: str, mode: str = 'text'):
    role = JobRole.objects.filter(pk=role_id, is_active=1).first()
    if not role:
        raise ValueError('岗位不存在或未启用')

    diff = DifficultyConfig.objects.filter(difficulty_code=difficulty_code).first()
    if not diff:
        raise ValueError(f'难度不存在: {difficulty_code}')

    strat = RoleInterviewStrategy.objects.filter(role_id=role_id, difficulty_code=difficulty_code).first()
    w_t = strat.technical_weight if strat else Decimal('0.34')
    w_p = strat.project_weight if strat else Decimal('0.33')
    w_s = strat.scenario_weight if strat else Decimal('0.33')

    planned = [
        _nz(diff.technical_chain_count, 1),
        _nz(diff.project_chain_count, 1),
        _nz(diff.scenario_chain_count, 1),
    ]
    total_chains = sum(planned)
    now = timezone.now()

    session = InterviewSession(
        user_id=user_id,
        role_id=role_id,
        difficulty=difficulty_code,
        difficulty_config_id=diff.id,
        mode=mode or 'text',
        session_prompt_snapshot='',
        status='running',
        total_chain_count=total_chains,
        completed_chain_count=0,
        started_at=now,
        context_snapshot={'roleCode': role.code, 'roleName': role.name, 'difficulty': difficulty_code},
        strategy_snapshot_json={
            'technical_weight': float(w_t),
            'project_weight': float(w_p),
            'scenario_weight': float(w_s),
        },
        created_at=now,
        updated_at=now,
    )
    session.save()

    aspect_pks = {}
    weights = (w_t, w_p, w_s)
    for i, at in enumerate(ASPECT_TYPES):
        sa = SessionAspect(
            session_id=session.id,
            aspect_type=at,
            aspect_name=ASPECT_NAMES[i],
            aspect_weight=weights[i],
            planned_chain_count=planned[i],
            completed_chain_count=0,
            status='pending',
            created_at=now,
            updated_at=now,
        )
        sa.save()
        aspect_pks[at] = sa.id

    chains = []
    global_no = 0
    for ai, at in enumerate(ASPECT_TYPES):
        for c in range(1, planned[ai] + 1):
            global_no += 1
            qb = _pick_question(role_id, at, c)
            ch = InterviewChain(
                session_id=session.id,
                session_aspect_id=aspect_pks[at],
                chain_no=global_no,
                chain_no_in_aspect=c,
                aspect_type=at,
                anchor_type=_anchor_type(at),
                anchor_id=qb.id if qb else None,
                anchor_code=qb.chain_anchor_code if qb else f'{at}_{c}',
                anchor_title=(qb.topic if qb else ASPECT_NAMES[ai]),
                topic=qb.topic if qb else ASPECT_NAMES[ai],
                subtopic=qb.subtopic if qb else '',
                max_followup_depth=_max_depth(diff, at),
                current_followup_depth=0,
                round_count=0,
                chain_weight=Decimal('1'),
                status='running' if global_no == 1 else 'created',
                started_at=now if global_no == 1 else None,
                created_at=now,
                updated_at=now,
            )
            ch.save()
            chains.append(ch)

    first = chains[0]
    qb0 = _pick_question(role_id, first.aspect_type, first.chain_no_in_aspect)
    qtext = qb0.question_text if qb0 else _default_q(first.aspect_type)
    r = InterviewRound(
        session_id=session.id,
        chain_id=first.id,
        global_round_no=1,
        round_no_in_chain=1,
        is_followup=0,
        question_text=qtext,
        question_source='question_bank' if qb0 else 'llm_generated',
        asked_at=now,
        created_at=now,
        updated_at=now,
    )
    r.save()
    first.round_count = 1
    first.save(update_fields=['round_count'])

    sa0 = SessionAspect.objects.get(pk=first.session_aspect_id)
    sa0.status = 'running'
    sa0.save(update_fields=['status'])

    return session
