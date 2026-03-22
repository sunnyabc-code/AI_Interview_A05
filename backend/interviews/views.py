from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.response import APIResponse
from interviews.models import Interview
from interviews.serializers import InterviewCreateSerializer, InterviewSerializer, InterviewUpdateSerializer


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
