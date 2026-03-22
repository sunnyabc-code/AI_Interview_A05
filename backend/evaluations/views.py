from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.response import APIResponse
from evaluations.models import DifficultyConfig


class DifficultyConfigListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Evaluation'],
        operation_summary='难度配置列表',
        operation_description='获取所有难度配置列表',
        security=[{'Bearer': []}],
        responses={200: openapi.Response('获取成功')}
    )
    def get(self, request):
        configs = DifficultyConfig.objects.all().order_by('id')
        data = []
        for config in configs:
            data.append({
                'id': config.id,
                'difficulty_code': config.difficulty_code,
                'difficulty_name': config.difficulty_name,
                'answer_time_seconds': config.answer_time_seconds,
                'technical_chain_count': config.technical_chain_count,
                'project_chain_count': config.project_chain_count,
                'scenario_chain_count': config.scenario_chain_count,
                'technical_max_followup_depth': config.technical_max_followup_depth,
                'project_max_followup_depth': config.project_max_followup_depth,
                'scenario_max_followup_depth': config.scenario_max_followup_depth,
                'created_at': config.created_at,
                'updated_at': config.updated_at
            })
        return APIResponse.success(data=data, message='获取成功', code=200)
