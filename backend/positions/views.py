from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.response import APIResponse
from positions.models import JobPosition


class JobPositionListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Position'],
        operation_summary='岗位列表',
        operation_description='获取所有岗位列表',
        security=[{'Bearer': []}],
        responses={200: openapi.Response('获取成功')}
    )
    def get(self, request):
        positions = JobPosition.objects.all().order_by('id')
        data = []
        for position in positions:
            data.append({
                'id': position.id,
                'code': position.code,
                'name': position.name,
                'description': position.description,
                'tech_stack': position.tech_stack,
                'required_skills': position.required_skills,
                'created_at': position.created_at,
                'updated_at': position.updated_at
            })
        return APIResponse.success(data=data, message='获取成功', code=200)
