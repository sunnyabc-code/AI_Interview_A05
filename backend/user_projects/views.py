from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.response import APIResponse
from user_projects.models import UserProject
from user_projects.serializers import (
    UserProjectCreateUpdateSerializer,
    UserProjectSerializer,
)


class UserProjectListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["UserProject"],
        operation_summary="用户项目列表",
        operation_description="获取当前用户的项目列表",
        security=[{"Bearer": []}],
        responses={200: openapi.Response("获取成功")},
    )
    def get(self, request):
        queryset = UserProject.objects.filter(user=request.user).select_related("position")
        data = UserProjectSerializer(queryset, many=True).data
        return APIResponse.success(data=data, message="获取成功", code=200)

    @swagger_auto_schema(
        tags=["UserProject"],
        operation_summary="创建用户项目",
        operation_description="为当前用户创建项目记录",
        request_body=UserProjectCreateUpdateSerializer,
        security=[{"Bearer": []}],
        responses={201: openapi.Response("创建成功")},
    )
    def post(self, request):
        serializer = UserProjectCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(message="参数错误", code=400, errors=serializer.errors)

        project = serializer.save(user=request.user)
        data = UserProjectSerializer(project).data
        return APIResponse.success(data=data, message="创建成功", code=201)


class UserProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_project(self, user, project_id):
        return UserProject.objects.filter(project_id=project_id, user=user).select_related("position").first()

    @swagger_auto_schema(
        tags=["UserProject"],
        operation_summary="更新用户项目",
        operation_description="更新当前用户指定项目",
        request_body=UserProjectCreateUpdateSerializer,
        security=[{"Bearer": []}],
        responses={200: openapi.Response("更新成功"), 404: openapi.Response("项目不存在")},
    )
    def patch(self, request, project_id):
        project = self._get_project(request.user, project_id)
        if not project:
            return APIResponse.error(message="项目不存在", code=404)

        serializer = UserProjectCreateUpdateSerializer(project, data=request.data, partial=True)
        if not serializer.is_valid():
            return APIResponse.error(message="参数错误", code=400, errors=serializer.errors)

        project = serializer.save()
        data = UserProjectSerializer(project).data
        return APIResponse.success(data=data, message="更新成功", code=200)

    @swagger_auto_schema(
        tags=["UserProject"],
        operation_summary="删除用户项目",
        operation_description="删除当前用户指定项目",
        security=[{"Bearer": []}],
        responses={200: openapi.Response("删除成功"), 404: openapi.Response("项目不存在")},
    )
    def delete(self, request, project_id):
        project = self._get_project(request.user, project_id)
        if not project:
            return APIResponse.error(message="项目不存在", code=404)

        project.delete()
        return APIResponse.success(data=None, message="删除成功", code=200)
