from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone

from core.response import APIResponse
from core.llm_client import LLMClient, LLMClientError
from interviews.models import Interview, InterviewRound
from interviews.serializers import (
    InterviewCreateSerializer,
    InterviewSerializer,
    InterviewUpdateSerializer,
    NextQuestionRequestSerializer,
    InterviewRoundSerializer,
    InterviewRoundAnswerRequestSerializer,
    InterviewRoundAnswerResponseSerializer,
    InterviewRoundListSerializer,
)
from questions.models import Question, QuestionCategory


class InterviewListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='创建面试',
        operation_description='创建面试并支持难度配置和题型选择开关',
        request_body=InterviewCreateSerializer,
        security=[{'Bearer': []}],
        responses={
            201: openapi.Response('创建成功', InterviewSerializer),
            400: openapi.Response('参数错误'),
            401: openapi.Response('未登录'),
        }
    )
    def post(self, request):
        serializer = InterviewCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(message='创建失败', code=400, errors=serializer.errors)

        validated_data = serializer.validated_data
        interview = Interview.objects.create(
            user=request.user,
            position=validated_data['position'],
            name=validated_data.get('name', ''),
            mode=validated_data.get('mode', 'text'),
            total_rounds=validated_data.get('total_rounds', 0),
            notes=validated_data.get('notes', ''),
            difficulty_config=validated_data.get('difficulty_config'),
            enable_technical_questions=validated_data.get('enable_technical_questions', True),
            enable_project_questions=validated_data.get('enable_project_questions', True),
            enable_scenario_questions=validated_data.get('enable_scenario_questions', True),
        )

        return APIResponse.success(data=InterviewSerializer(interview).data, message='创建成功', code=201)

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='面试列表',
        operation_description='获取当前用户的面试列表',
        security=[{'Bearer': []}],
        responses={200: openapi.Response('获取成功')}
    )
    def get(self, request):
        interviews = Interview.objects.filter(user=request.user).select_related('position', 'difficulty_config').order_by('-created_at')
        data = InterviewSerializer(interviews, many=True).data
        return APIResponse.success(data=data, message='获取成功', code=200)


class InterviewDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user_interview(self, user, interview_id):
        return Interview.objects.filter(id=interview_id, user=user).select_related('position', 'difficulty_config').first()

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='面试详情',
        operation_description='获取当前登录用户自己的面试详情',
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('获取成功', InterviewSerializer),
            401: openapi.Response('未登录'),
            404: openapi.Response('面试记录不存在'),
        }
    )
    def get(self, request, interview_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message='面试记录不存在', code=404)

        return APIResponse.success(data=InterviewSerializer(interview).data, message='获取成功', code=200)

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='更新面试记录',
        operation_description='更新当前登录用户自己的面试记录（支持部分更新）',
        request_body=InterviewUpdateSerializer,
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('更新成功', InterviewSerializer),
            400: openapi.Response('参数错误'),
            401: openapi.Response('未登录'),
            404: openapi.Response('面试记录不存在'),
        }
    )
    def patch(self, request, interview_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message='面试记录不存在', code=404)

        serializer = InterviewUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return APIResponse.error(message='更新失败', code=400, errors=serializer.errors)

        for field, value in serializer.validated_data.items():
            setattr(interview, field, value)
        interview.save()

        return APIResponse.success(data=InterviewSerializer(interview).data, message='更新成功', code=200)

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='删除面试记录',
        operation_description='删除当前登录用户自己的面试记录',
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('删除成功'),
            401: openapi.Response('未登录'),
            404: openapi.Response('面试记录不存在'),
        }
    )
    def delete(self, request, interview_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message='面试记录不存在', code=404)

        interview.delete()
        return APIResponse.success(data=None, message='删除成功', code=200)


class InterviewRoundListView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user_interview(self, user, interview_id):
        return Interview.objects.filter(id=interview_id, user=user).first()

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='获取面试轮次列表',
        operation_description='获取指定面试的所有轮次记录',
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('获取成功', InterviewRoundListSerializer(many=True)),
            401: openapi.Response('未登录'),
            404: openapi.Response('面试记录不存在'),
        }
    )
    def get(self, request, interview_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message='面试记录不存在', code=404)

        rounds = InterviewRound.objects.filter(interview=interview).select_related('category', 'question').order_by('round_number')
        data = InterviewRoundListSerializer(rounds, many=True).data
        return APIResponse.success(data=data, message='获取成功', code=200)



class InterviewNextQuestionView(APIView):
    permission_classes = [IsAuthenticated]

    difficulty_map = {
        'easy': 1,
        'medium': 2,
        'hard': 3,
    }

    def _get_user_interview(self, user, interview_id):
        return Interview.objects.filter(id=interview_id, user=user).select_related('position', 'difficulty_config').first()

    def _enabled_categories(self, interview):
        # 固定顺序：技术 -> 项目 -> 场景，避免前端参数影响面试编排。
        categories = []
        if interview.enable_technical_questions:
            categories.append('technical')
        if interview.enable_project_questions:
            categories.append('project')
        if interview.enable_scenario_questions:
            categories.append('scenario')
        return categories

    def _target_chain_count(self, interview, category_code):
        if not interview.difficulty_config:
            return 1

        config = interview.difficulty_config
        if category_code == 'technical':
            return max(getattr(config, 'technical_chain_count', 1), 0)
        if category_code == 'project':
            return max(getattr(config, 'project_chain_count', 1), 0)
        if category_code == 'scenario':
            return max(getattr(config, 'scenario_chain_count', 1), 0)
        return 0

    def _pick_question_from_category(self, interview, category_code, used_question_ids):
        base_qs = Question.objects.filter(
            position=interview.position,
            category__code=category_code,
            is_active=True,
        )

        difficulty_value = None
        if interview.difficulty_config and interview.difficulty_config.difficulty_code:
            difficulty_value = self.difficulty_map.get(interview.difficulty_config.difficulty_code.lower())

        # 优先同难度且未使用题目，避免重复。
        if difficulty_value is not None:
            exact_qs = base_qs.filter(difficulty=difficulty_value).exclude(id__in=used_question_ids).order_by('usage_count', 'id')
            question = exact_qs.first()
            if question:
                return question

        # 其次允许任意难度但不重复。
        non_repeat_qs = base_qs.exclude(id__in=used_question_ids).order_by('usage_count', 'id')
        question = non_repeat_qs.first()
        if question:
            return question

        # 最后允许重复题，保证流程能继续。
        if difficulty_value is not None:
            fallback_qs = base_qs.filter(difficulty=difficulty_value).order_by('usage_count', 'id')
            question = fallback_qs.first()
            if question:
                return question

        return base_qs.order_by('usage_count', 'id').first()

    def _max_questions_per_chain(self, interview, category_code):
        if not interview.difficulty_config:
            return 1

        config = interview.difficulty_config
        if category_code == 'technical':
            return max(getattr(config, 'technical_max_followup_depth', 1), 1)
        if category_code == 'project':
            return max(getattr(config, 'project_max_followup_depth', 1), 1)
        if category_code == 'scenario':
            return max(getattr(config, 'scenario_max_followup_depth', 1), 1)
        return 1

    def _compute_chain_state(self, interview, category_code):
        category_rounds = InterviewRound.objects.filter(
            interview=interview,
            category__code=category_code,
        )
        last_round = category_rounds.order_by('-round_number').first()
        max_questions_per_chain = self._max_questions_per_chain(interview, category_code)
        max_followup_index = max_questions_per_chain - 1

        # followup_depth: 0=主问题，1开始为追问；当达到 max_followup_index 后开启下一条链。
        if last_round and last_round.followup_depth < max_followup_index:
            return last_round.chain_index, last_round.followup_depth + 1

        max_chain_index = category_rounds.aggregate(max_value=Max('chain_index')).get('max_value') or 0
        return max_chain_index + 1, 0

    def _determine_next_slot(self, interview):
        """
        根据 difficulty_config 自动计算下一题的题型与链路位置。
        返回: (category_code, chain_index, followup_depth) 或 None(全部完成)
        """
        enabled_categories = self._enabled_categories(interview)
        for category_code in enabled_categories:
            target_chains = self._target_chain_count(interview, category_code)
            if target_chains <= 0:
                continue

            category_rounds = InterviewRound.objects.filter(
                interview=interview,
                category__code=category_code,
            ).order_by('-round_number')
            last_round = category_rounds.first()

            if not last_round:
                return category_code, 1, 0

            max_questions_per_chain = self._max_questions_per_chain(interview, category_code)
            max_followup_index = max_questions_per_chain - 1

            # 优先继续当前链直到达到该链最大提问数。
            if last_round.followup_depth < max_followup_index:
                return category_code, last_round.chain_index, last_round.followup_depth + 1

            # 当前链完成后，若仍有链数量配额，开启下一链。
            if last_round.chain_index < target_chains:
                return category_code, last_round.chain_index + 1, 0

            # 否则该题型已完成，继续检查下一个题型。
            continue

        return None

    def _build_llm_fallback_prompt(self, interview, category_code, chain_index, followup_depth):
        difficulty_code = interview.difficulty_config.difficulty_code if interview.difficulty_config else 'medium'
        answer_time_seconds = interview.difficulty_config.answer_time_seconds if interview.difficulty_config else 120

        category_label_map = {
            'technical': '技术知识题',
            'project': '项目经历题',
            'scenario': '场景题',
        }
        category_label = category_label_map.get(category_code, category_code)
        question_role = '主问题' if followup_depth == 0 else f'第{followup_depth}次追问'

        return (
            '你是一名严谨的技术面试官。请基于以下约束仅输出一个中文面试问题，不要输出答案。\n'
            f'- 岗位：{interview.position.name}\n'
            f'- 难度：{difficulty_code}\n'
            f'- 题型：{category_label}\n'
            f'- 提问链编号：{chain_index}\n'
            f'- 当前类型：{question_role}\n'
            f'- 预估答题时长：{answer_time_seconds}秒\n'
            '- 要求：问题清晰、可回答、不过度宽泛；如果是追问，要基于上一轮回答继续深挖细节。\n'
            '- 输出格式：只输出问题文本本身，不要带编号、解释、答案或额外说明。'
        )

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='获取下一题',
        operation_description='按面试题型开关和难度配置获取下一题，并创建一条轮次记录',
        request_body=NextQuestionRequestSerializer,
        security=[{'Bearer': []}],
        responses={
            201: openapi.Response('创建成功', InterviewRoundSerializer),
            400: openapi.Response('参数错误'),
            401: openapi.Response('未登录'),
            404: openapi.Response('面试记录不存在'),
            502: openapi.Response('题库未命中且LLM调用失败'),
        }
    )
    @transaction.atomic
    def post(self, request, interview_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message='面试记录不存在', code=404)

        if interview.status in ['completed', 'cancelled']:
            return APIResponse.error(message='当前面试状态不允许继续提问', code=400)

        request_serializer = NextQuestionRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return APIResponse.error(message='参数错误', code=400, errors=request_serializer.errors)

        enabled_categories = self._enabled_categories(interview)
        if not enabled_categories:
            return APIResponse.error(message='未启用任何题型，无法生成下一题', code=400)

        force_category = request_serializer.validated_data.get('force_category')
        if force_category:
            return APIResponse.error(message='题型由系统按难度配置自动编排，不支持外部指定', code=400)

        rounds_qs = InterviewRound.objects.filter(interview=interview).select_related('category', 'question')
        unfinished_round = rounds_qs.filter(end_time__isnull=True).order_by('-round_number').first()
        if unfinished_round and not (unfinished_round.user_answer or '').strip():
            return APIResponse.error(message='请先完成上一轮作答后再获取下一题', code=400)

        used_question_ids = list(rounds_qs.exclude(question__isnull=True).values_list('question_id', flat=True))
        next_round_number = (rounds_qs.order_by('-round_number').values_list('round_number', flat=True).first() or 0) + 1

        next_slot = self._determine_next_slot(interview)
        if not next_slot:
            end_time = timezone.now()
            actual_rounds = rounds_qs.count()
            duration_seconds = interview.duration_seconds
            if interview.start_time:
                duration_seconds = max(int((end_time - interview.start_time).total_seconds()), 0)

            interview.status = 'completed'
            interview.end_time = end_time
            interview.total_rounds = actual_rounds
            interview.duration_seconds = duration_seconds
            interview.save(update_fields=['status', 'end_time', 'total_rounds', 'duration_seconds'])

            return APIResponse.success(
                data={
                    'interview_id': interview.id,
                    'status': interview.status,
                    'end_time': interview.end_time,
                    'total_rounds': interview.total_rounds,
                    'duration_seconds': interview.duration_seconds,
                },
                message='当前面试已结束',
                code=200,
            )

        selected_category_code, chain_index, followup_depth = next_slot

        selected_question = None
        selected_question = self._pick_question_from_category(interview, selected_category_code, used_question_ids)

        category_name_map = {
            'technical': '技术知识',
            'project': '项目经历',
            'scenario': '场景题',
        }
        category, _ = QuestionCategory.objects.get_or_create(
            code=selected_category_code,
            defaults={'name': category_name_map.get(selected_category_code, selected_category_code)},
        )

        if not selected_question:
            llm_prompt = self._build_llm_fallback_prompt(interview, selected_category_code, chain_index, followup_depth)
            client = LLMClient.from_settings()
            try:
                generated_question = client.generate_question_from_prompt(prompt=llm_prompt)
            except LLMClientError as exc:
                return APIResponse.error(
                    message='题库未命中且LLM调用失败',
                    code=502,
                    errors={
                        'llm_error': str(exc),
                        'llm_prompt': llm_prompt,
                    },
                )

            interview_round = InterviewRound.objects.create(
                interview=interview,
                round_number=next_round_number,
                chain_index=chain_index,
                followup_depth=followup_depth,
                category=category,
                question=None,
                question_content=generated_question,
            )

            update_fields = []
            if interview.status == 'pending':
                interview.status = 'in_progress'
                update_fields.append('status')
            if not interview.start_time:
                interview.start_time = timezone.now()
                update_fields.append('start_time')
            if update_fields:
                interview.save(update_fields=update_fields)

            response_data = {
                'round_id': interview_round.id,
                'interview_id': interview.id,
                'round_number': interview_round.round_number,
                'chain_index': interview_round.chain_index,
                'followup_depth': interview_round.followup_depth,
                'category': category.code,
                'category_name': category.name,
                'question_id': None,
                'question_content': interview_round.question_content,
                'answer_time_seconds': interview.difficulty_config.answer_time_seconds if interview.difficulty_config else None,
                'start_time': interview_round.start_time,
                'need_llm_generation': False,
                'question_source': 'llm_auto',
                'llm_prompt': llm_prompt,
            }
            return APIResponse.success(data=response_data, message='题库未命中，已自动调用LLM生成题目', code=201)

        interview_round = InterviewRound.objects.create(
            interview=interview,
            round_number=next_round_number,
            chain_index=chain_index,
            followup_depth=followup_depth,
            category=category,
            question=selected_question,
            question_content=selected_question.content,
        )

        Question.objects.filter(id=selected_question.id).update(usage_count=F('usage_count') + 1)

        update_fields = []
        if interview.status == 'pending':
            interview.status = 'in_progress'
            update_fields.append('status')
        if not interview.start_time:
            interview.start_time = timezone.now()
            update_fields.append('start_time')
        if update_fields:
            interview.save(update_fields=update_fields)

        response_data = {
            'round_id': interview_round.id,
            'interview_id': interview.id,
            'round_number': interview_round.round_number,
            'chain_index': interview_round.chain_index,
            'followup_depth': interview_round.followup_depth,
            'category': category.code if category else None,
            'category_name': category.name if category else None,
            'question_id': selected_question.id,
            'question_content': interview_round.question_content,
            'answer_time_seconds': interview.difficulty_config.answer_time_seconds if interview.difficulty_config else None,
            'start_time': interview_round.start_time,
            'need_llm_generation': False,
            'question_source': 'question_bank',
            'llm_prompt': None,
        }
        return APIResponse.success(data=response_data, message='获取下一题成功', code=201)


class InterviewRoundAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user_interview(self, user, interview_id):
        return Interview.objects.filter(id=interview_id, user=user).first()

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='提交本轮回答',
        operation_description='提交指定轮次回答并写入结束时间，重复提交将返回已提交状态',
        request_body=InterviewRoundAnswerRequestSerializer,
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('提交成功', InterviewRoundAnswerResponseSerializer),
            400: openapi.Response('参数错误或状态不允许'),
            401: openapi.Response('未登录'),
            404: openapi.Response('面试或轮次不存在'),
        }
    )
    @transaction.atomic
    def post(self, request, interview_id, round_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message='面试记录不存在', code=404)

        if interview.status in ['completed', 'cancelled']:
            return APIResponse.error(message='当前面试状态不允许提交回答', code=400)

        serializer = InterviewRoundAnswerRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(message='参数错误', code=400, errors=serializer.errors)

        round_obj = InterviewRound.objects.filter(id=round_id, interview=interview).select_related('category', 'question').first()
        if not round_obj:
            return APIResponse.error(message='轮次不存在', code=404)

        answer_text = serializer.validated_data['user_answer'].strip()
        if not answer_text:
            return APIResponse.error(message='回答内容不能为空', code=400)

        # 检查是否已回答
        already_answered = bool((round_obj.user_answer or '').strip()) and round_obj.end_time is not None
        
        # 如果之前回答是 "1"（占位符），允许覆盖
        should_update = not already_answered or (round_obj.user_answer == '1')
        
        if should_update:
            round_obj.user_answer = answer_text
            round_obj.end_time = timezone.now()
            round_obj.save(update_fields=['user_answer', 'end_time'])

        if interview.status == 'pending':
            interview.status = 'in_progress'
            interview.save(update_fields=['status'])

        response_data = {
            'interview_id': interview.id,
            'round_id': round_obj.id,
            'round_number': round_obj.round_number,
            'chain_index': round_obj.chain_index,
            'followup_depth': round_obj.followup_depth,
            'category': round_obj.category.code if round_obj.category else None,
            'category_name': round_obj.category.name if round_obj.category else None,
            'question_id': round_obj.question.id if round_obj.question else None,
            'question_content': round_obj.question_content,
            'user_answer': round_obj.user_answer,
            'end_time': round_obj.end_time,
            'already_answered': already_answered,
            'interview_status': interview.status,
        }
        message = '该轮已提交，返回已保存结果' if already_answered else '提交回答成功'
        return APIResponse.success(data=response_data, message=message, code=200)


class InterviewStartView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user_interview(self, user, interview_id):
        return Interview.objects.filter(id=interview_id, user=user).first()

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='开始面试',
        operation_description='将面试状态设置为进行中，记录开始时间',
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('面试开始成功'),
            400: openapi.Response('参数错误或状态不允许'),
            401: openapi.Response('未登录'),
            404: openapi.Response('面试记录不存在'),
        }
    )
    @transaction.atomic
    def post(self, request, interview_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message='面试记录不存在', code=404)
        
        if interview.status == 'in_progress':
            return APIResponse.error(message='面试已经开始', code=400)
        
        interview.status = 'in_progress'
        interview.start_time = timezone.now()
        interview.save(update_fields=['status', 'start_time'])
        
        return APIResponse.success(
            data={
                'interview_id': interview.id,
                'status': interview.status,
                'start_time': interview.start_time
            },
            message='面试已开始'
        )


class InterviewPauseView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user_interview(self, user, interview_id):
        return Interview.objects.filter(id=interview_id, user=user).first()

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='暂停面试',
        operation_description='将面试状态设置为暂停，记录暂停时间',
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('面试暂停成功'),
            400: openapi.Response('参数错误或状态不允许'),
            401: openapi.Response('未登录'),
            404: openapi.Response('面试记录不存在'),
        }
    )
    @transaction.atomic
    def post(self, request, interview_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message='面试记录不存在', code=404)
        
        if interview.status != 'in_progress':
            return APIResponse.error(message='面试未在进行中', code=400)
        
        interview.status = 'paused'
        interview.pause_time = timezone.now()
        interview.pause_count = (interview.pause_count or 0) + 1
        interview.save(update_fields=['status', 'pause_time', 'pause_count'])
        
        return APIResponse.success(
            data={
                'interview_id': interview.id,
                'status': interview.status,
                'pause_time': interview.pause_time
            },
            message='面试已暂停'
        )


class InterviewResumeView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user_interview(self, user, interview_id):
        return Interview.objects.filter(id=interview_id, user=user).first()

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='恢复面试',
        operation_description='将面试状态设置为进行中，计算暂停时长',
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('面试恢复成功'),
            400: openapi.Response('参数错误或状态不允许'),
            401: openapi.Response('未登录'),
            404: openapi.Response('面试记录不存在'),
        }
    )
    @transaction.atomic
    def post(self, request, interview_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message='面试记录不存在', code=404)
        
        if interview.status != 'paused':
            return APIResponse.error(message='面试未暂停', code=400)
        
        # 计算暂停时长
        pause_duration = int((timezone.now() - interview.pause_time).total_seconds())
        interview.total_pause_duration = (interview.total_pause_duration or 0) + pause_duration
        
        interview.status = 'in_progress'
        interview.save(update_fields=['status', 'total_pause_duration'])
        
        return APIResponse.success(
            data={
                'interview_id': interview.id,
                'status': interview.status,
                'resume_time': timezone.now(),
                'pause_duration': pause_duration
            },
            message='面试已恢复'
        )


class InterviewEndView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user_interview(self, user, interview_id):
        return Interview.objects.filter(id=interview_id, user=user).first()

    @swagger_auto_schema(
        tags=['Interview'],
        operation_summary='结束面试',
        operation_description='将面试状态设置为已完成，计算总时长和实际面试时长',
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('面试结束成功'),
            400: openapi.Response('参数错误或状态不允许'),
            401: openapi.Response('未登录'),
            404: openapi.Response('面试记录不存在'),
        }
    )
    @transaction.atomic
    def post(self, request, interview_id):
        interview = self._get_user_interview(request.user, interview_id)
        if not interview:
            return APIResponse.error(message='面试记录不存在', code=404)
        
        if interview.status == 'completed':
            return APIResponse.error(message='面试已经结束', code=400)
        
        end_time = timezone.now()
        total_duration = int((end_time - interview.start_time).total_seconds())
        actual_duration = total_duration - (interview.total_pause_duration or 0)
        
        interview.status = 'completed'
        interview.end_time = end_time
        interview.duration_seconds = total_duration
        interview.actual_duration = actual_duration
        interview.save(update_fields=['status', 'end_time', 'duration_seconds', 'actual_duration'])
        
        return APIResponse.success(
            data={
                'interview_id': interview.id,
                'status': interview.status,
                'end_time': interview.end_time,
                'total_duration': total_duration,
                'actual_duration': actual_duration
            },
            message='面试已结束'
        )
