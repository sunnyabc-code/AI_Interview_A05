from rest_framework import viewsets, status
from rest_framework.decorators import action
from core.response import APIResponse
from core.pagination import StandardPagination
from core.exceptions import APIException


class BaseViewSet(viewsets.ModelViewSet):
    pagination_class = StandardPagination
    
    def get_queryset(self):
        return super().get_queryset()
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return APIResponse.paginated(
                    items=serializer.data,
                    pagination=self.paginator.get_paginated_response(None)['pagination']
                )
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success(data=serializer.data)
        except Exception as e:
            raise APIException(message=str(e))
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success(data=serializer.data)
        except Exception as e:
            raise APIException(message=str(e))
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return APIResponse.success(data=serializer.data, code=status.HTTP_201_CREATED)
        except Exception as e:
            raise APIException(message=str(e))
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return APIResponse.success(data=serializer.data)
        except Exception as e:
            raise APIException(message=str(e))
    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return APIResponse.success(message='Deleted successfully', code=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            raise APIException(message=str(e))
    
    @action(detail=False, methods=['get'])
    def options(self, request):
        return APIResponse.success(data={
            'actions': ['list', 'create', 'retrieve', 'update', 'destroy']
        })
