import logging
import random
import time

from django.contrib.auth.hashers import check_password, make_password
from django.db import DatabaseError, IntegrityError
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

from interview_md.authentication import UserAccountJWTAuthentication, issue_jwt
from interview_md.models import JobRole, MdEvaluationReport, UserAccount
from interview_md.services import orchestrator
from interview_md.services.session_service import create_interview_session


def ok(data=None, msg='ok'):
    return Response({'code': 1, 'msg': msg, 'data': data})


def err(msg, code=0):
    return Response({'code': code, 'msg': msg, 'data': None})


def normalize_difficulty(d: str) -> str:
    if not d:
        return 'easy'
    d = d.strip()
    m = {'L1': 'easy', 'L2': 'medium', 'L3': 'hard'}
    return m.get(d, d.lower())


# 验证码（仿真）：与 origin/users 行为一致，单进程开发环境有效
_CODE_TTL_SEC = 300
_CODE_STORE = {}


def _purge_expired_codes():
    now = time.time()
    dead = [k for k, (_, exp) in _CODE_STORE.items() if exp < now]
    for k in dead:
        del _CODE_STORE[k]


def _normalize_identifier(send_type: str, raw: str) -> str:
    raw = (raw or '').strip()
    if send_type == 'email':
        # 全角 ＠（常见于输入法）转为半角 @，便于与库中邮箱比对
        s = raw.replace('＠', '@')
        return s.lower()
    return ''.join(c for c in raw if c.isdigit())


def _code_key(send_type: str, raw: str) -> tuple:
    st = (send_type or 'email').lower()
    return (st, _normalize_identifier(st, raw))


class RegisterMdView(APIView):
    # 避免全局 SimpleJWT 校验 localStorage 里的旧/无效 Bearer，导致未进入视图就 401
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        email = request.data.get('email') or ''
        if not username or len(password) < 6:
            return err('用户名必填且密码至少6位', 400)
        if UserAccount.objects.filter(username=username).exists():
            return err('用户名已存在', 400)
        now = timezone.now()
        try:
            ua = UserAccount(
                username=username,
                email=email or None,
                phone=request.data.get('phone') or None,
                password_hash=make_password(password),
                role='student',
                status=1,
                created_at=now,
                updated_at=now,
            )
            ua.save()
            return ok({'userId': ua.id})
        except IntegrityError:
            logger.warning('register duplicate username=%s', username)
            return err('用户名已存在', 400)
        except DatabaseError as e:
            logger.exception('register database error')
            return err(
                '数据库写入失败，请确认已按「数据库表.md」建表且 user_account 字段一致；'
                f'详情：{e}',
                0,
            )
        except Exception as e:
            logger.exception('register failed')
            return err(f'注册失败：{e}', 0)


class LoginMdView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        ua = UserAccount.objects.filter(username=username).first()
        # 登录：对本次输入的明文做校验（与存库的哈希比对），不能也不应“解密”哈希
        if not ua or not check_password(password, ua.password_hash):
            return err('用户名或密码错误', 401)
        token = issue_jwt(ua.id)
        return ok({'userId': ua.id, 'nickname': ua.username, 'token': token, 'expiresIn': 86400})


class SendCodeMdView(APIView):
    """发送验证码（仿真），对齐 origin `users/send-code/`。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        _purge_expired_codes()
        target = (request.data.get('target') or '').strip()
        send_type = (request.data.get('send_type') or 'email').lower()
        purpose = (request.data.get('purpose') or 'reset').lower()
        if not target:
            return err('请输入邮箱或手机号', 400)
        if send_type not in ('email', 'phone'):
            return err('send_type 须为 email 或 phone', 400)
        if send_type == 'email':
            target = _normalize_identifier('email', target)
            if '@' not in target:
                return err(
                    '邮箱格式不正确：需包含 @（如 name@qq.com）。若只用手机号注册，请点「手机号」',
                    400,
                )
        else:
            target = _normalize_identifier('phone', target)
            if len(target) < 11:
                return err('手机号格式不正确', 400)

        if purpose == 'reset':
            if send_type == 'email':
                if not UserAccount.objects.filter(email__iexact=target).exists():
                    return err('该邮箱未注册', 400)
            elif not UserAccount.objects.filter(phone=target).exists():
                return err('该手机号未注册', 400)
        elif purpose == 'register':
            if send_type == 'email':
                if UserAccount.objects.filter(email__iexact=target).exists():
                    return err('该邮箱已注册', 400)
            elif UserAccount.objects.filter(phone=target).exists():
                return err('该手机号已注册', 400)

        code = f'{random.randint(100000, 999999)}'
        key = _code_key(send_type, target)
        _CODE_STORE[key] = (code, time.time() + _CODE_TTL_SEC)
        logger.info('send-code simulation: %s -> %s', key, code)
        return ok(
            {
                'verificationCode': code,
                'expiresIn': _CODE_TTL_SEC,
            }
        )


class ResetPasswordMdView(APIView):
    """通过邮箱或手机号重置密码，对齐 origin `users/reset-password/`。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        _purge_expired_codes()
        identifier = (request.data.get('identifier') or '').strip()
        verification_code = (request.data.get('verification_code') or '').strip()
        new_password = request.data.get('new_password') or ''
        confirm_password = request.data.get('confirm_password') or ''
        reset_type = (request.data.get('reset_type') or 'email').lower()
        if not identifier:
            return err('请输入邮箱或手机号', 400)
        if new_password != confirm_password:
            return err('两次密码输入不一致', 400)
        if len(new_password) < 6:
            return err('密码至少6位', 400)
        if not verification_code.isdigit() or len(verification_code) != 6:
            return err('验证码格式错误', 400)
        if reset_type == 'email':
            identifier = _normalize_identifier('email', identifier)
            if '@' not in identifier:
                return err(
                    '邮箱格式不正确：需包含 @。若只用手机号注册，请选「手机号」',
                    400,
                )
            ua = UserAccount.objects.filter(email__iexact=identifier).first()
        else:
            digits = _normalize_identifier('phone', identifier)
            ua = UserAccount.objects.filter(phone=digits).first()
        if not ua:
            return err('账号不存在', 400)
        key = _code_key(reset_type, identifier)
        slot = _CODE_STORE.get(key)
        if not slot or slot[1] < time.time():
            return err('验证码已过期，请重新获取', 400)
        if slot[0] != verification_code:
            return err('验证码错误', 400)
        now = timezone.now()
        ua.password_hash = make_password(new_password)
        ua.updated_at = now
        ua.save(update_fields=['password_hash', 'updated_at'])
        del _CODE_STORE[key]
        return ok(msg='密码重置成功')


class ScenarioListView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        rows = JobRole.objects.filter(is_active=1).order_by('id')
        data = []
        for r in rows:
            data.append(
                {
                    'roleId': r.id,
                    'templateId': r.id,
                    'title': r.name,
                    'category': r.code,
                    'rolePersona': f'{r.name} 方向面试官',
                    'difficulty': 'medium',
                    'description': r.description or '岗位化题库与差异化评估权重。',
                }
            )
        return ok(data)


class SessionCreateView(APIView):
    authentication_classes = [UserAccountJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        role_id = request.data.get('roleId') or request.data.get('templateId')
        cfg = request.data.get('config') or {}
        diff = normalize_difficulty(request.data.get('difficulty') or cfg.get('difficulty') or 'easy')
        mode = request.data.get('mode') or 'text'
        if not role_id:
            return err('请选择岗位 roleId', 400)
        try:
            session = create_interview_session(user.id, int(role_id), diff, mode)
            return ok({'sessionId': str(session.id), 'status': session.status, 'startedAt': session.started_at})
        except Exception as e:
            return err(str(e), 400)


class SessionStateView(APIView):
    authentication_classes = [UserAccountJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            st = orchestrator.session_state(int(session_id))
            return ok(st)
        except Exception as e:
            return err(str(e), 400)


class DialogueNextView(APIView):
    authentication_classes = [UserAccountJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sid = request.data.get('sessionId')
        content = request.data.get('content') or request.data.get('userAnswer') or ''
        user = request.user
        if not sid:
            return err('缺少 sessionId', 400)
        try:
            out = orchestrator.process_answer(int(sid), user.id, content, 'TEXT')
            sess = out.get('session')
            is_end = out.get('is_end') or (sess and sess.status == 'finished')
            data = {
                'question': out['content'],
                'content': out['content'],
                'round': None,
                'totalRounds': sess.total_chain_count if sess else 0,
                'completedChains': sess.completed_chain_count if sess else 0,
                'isEnd': bool(is_end),
                'hint': '请结合岗位与场景作答，表达尽量结构化。',
            }
            return ok(data)
        except Exception as e:
            return err(str(e), 400)


class EvaluationSubmitView(APIView):
    authentication_classes = [UserAccountJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from interview_md.models import InterviewSession

        sid = request.data.get('sessionId')
        if not sid:
            return err('缺少 sessionId', 400)
        try:
            orchestrator.aggregate_report(int(sid))
            now = timezone.now()
            s = InterviewSession.objects.filter(pk=int(sid), user_id=request.user.id).first()
            if s and s.status != 'finished':
                s.status = 'finished'
                s.finished_at = now
                s.updated_at = now
                s.save(update_fields=['status', 'finished_at', 'updated_at'])
            return ok()
        except Exception as e:
            return err(str(e), 400)


class ReportDetailView(APIView):
    authentication_classes = [UserAccountJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sid = request.query_params.get('sessionId')
        if not sid:
            return err('缺少 sessionId', 400)
        rep = MdEvaluationReport.objects.filter(session_id=int(sid)).first()
        if not rep:
            return err('报告不存在', 404)
        dim = rep.dimension_scores_json or {}
        ds = []
        mapping = [
            ('内容深度', 'content'),
            ('逻辑严谨', 'logic'),
            ('沟通表达', 'communication'),
            ('岗位匹配', 'job_match'),
            ('自信稳定', 'confidence'),
        ]
        for name, key in mapping:
            v = dim.get(key)
            if v is None:
                continue
            try:
                raw = float(v)
                sc = min(10, max(0, int(raw // 10)))
            except (TypeError, ValueError):
                sc = 5
            ds.append({'name': name, 'score': sc, 'comment': ''})
        strengths = rep.strengths_json if isinstance(rep.strengths_json, list) else []
        sugs = rep.improvement_suggestions_json if isinstance(rep.improvement_suggestions_json, list) else []
        suggestions = []
        for i, s in enumerate(sugs):
            suggestions.append(
                {'action': str(s), 'why': '结合链式面试表现归纳', 'how': '针对薄弱项完成专项练习'}
            )
        total = int(rep.overall_score) if rep.overall_score else 0
        return ok(
            {
                'sessionId': sid,
                'totalScore': total,
                'dimensionScores': ds,
                'strengths': [str(x) for x in strengths],
                'suggestions': suggestions,
                'generatedAt': rep.updated_at.isoformat() if rep.updated_at else None,
                'technicalScore': float(rep.technical_score) if rep.technical_score else None,
                'projectScore': float(rep.project_score) if rep.project_score else None,
                'scenarioScore': float(rep.scenario_score) if rep.scenario_score else None,
            }
        )


class ProfileTrendView(APIView):
    authentication_classes = [UserAccountJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from interview_md.models import InterviewSession

        uid = int(request.query_params.get('userId', request.user.id))
        days = int(request.query_params.get('days', 7))
        qs = (
            InterviewSession.objects.filter(user_id=uid, status='finished', overall_score__isnull=False)
            .order_by('finished_at')
            .values_list('finished_at', 'overall_score')[: max(days, 1)]
        )
        labels, scores = [], []
        for ft, sc in qs:
            labels.append(ft.date().isoformat() if ft else '')
            scores.append(int(sc) if sc else 0)
        if not labels:
            labels, scores = ['暂无'], [0]
        return ok({'labels': labels, 'scores': scores})


class ProfileHistoryView(APIView):
    authentication_classes = [UserAccountJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from interview_md.models import InterviewSession

        uid = int(request.query_params.get('userId', request.user.id))
        page = int(request.query_params.get('page', 1))
        size = int(request.query_params.get('size', 10))
        offset = max(0, (page - 1) * size)
        total = InterviewSession.objects.filter(user_id=uid).count()
        records = []
        for s in InterviewSession.objects.filter(user_id=uid).order_by('-created_at')[offset : offset + size]:
            jr = JobRole.objects.filter(pk=s.role_id).first()
            records.append(
                {
                    'sessionId': s.id,
                    'scenario': jr.name if jr else '模拟面试',
                    'score': int(s.overall_score) if s.overall_score else 0,
                    'completedAt': s.finished_at.isoformat() if s.finished_at else '',
                }
            )
        return ok({'records': records, 'total': total, 'page': page, 'size': size})
