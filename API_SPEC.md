# AI模拟面试平台 - API规范文档

## 一、API设计原则

### 1.1 RESTful规范
- 使用HTTP动词表示操作类型（GET/POST/PUT/DELETE）
- 使用名词表示资源
- 使用复数形式表示资源集合
- 使用版本号管理API（如 `/api/v1/`）

### 1.2 统一响应格式

#### 成功响应
```json
{
    "code": 200,
    "message": "success",
    "data": {}
}
```

#### 错误响应
```json
{
    "code": 400,
    "message": "错误信息",
    "errors": {}
}
```

#### 列表响应（带分页）
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "items": [],
        "pagination": {
            "total": 100,
            "page": 1,
            "page_size": 20,
            "total_pages": 5
        }
    }
}
```

### 1.3 HTTP状态码规范
- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `204 No Content`: 删除成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证
- `403 Forbidden`: 无权限
- `404 Not Found`: 资源不存在
- `422 Unprocessable Entity`: 业务逻辑错误
- `500 Internal Server Error`: 服务器错误

---

## 二、API端点规划

### 2.1 用户模块 (Users)

| 方法 | 路径 | 描述 | 权限 |
|-----|------|------|------|
| POST | `/api/v1/users/register/` | 用户注册 | 公开 |
| POST | `/api/v1/users/login/` | 用户登录 | 公开 |
| GET | `/api/v1/users/profile/` | 获取个人信息 | 认证 |
| PUT | `/api/v1/users/profile/` | 更新个人信息 | 认证 |
| GET | `/api/v1/users/progress/` | 获取用户进度 | 认证 |

### 2.2 岗位模块 (Positions)

| 方法 | 路径 | 描述 | 权限 |
|-----|------|------|------|
| GET | `/api/v1/positions/` | 获取岗位列表 | 公开 |
| GET | `/api/v1/positions/{id}/` | 获取岗位详情 | 公开 |
| GET | `/api/v1/positions/{id}/dimensions/` | 获取岗位评估维度 | 公开 |

### 2.3 题库模块 (Questions)

| 方法 | 路径 | 描述 | 权限 |
|-----|------|------|------|
| GET | `/api/v1/questions/categories/` | 获取题目分类 | 公开 |
| GET | `/api/v1/questions/knowledge-points/` | 获取知识点列表 | 公开 |
| GET | `/api/v1/questions/` | 获取题目列表 | 公开 |
| GET | `/api/v1/questions/{id}/` | 获取题目详情 | 公开 |

### 2.4 面试模块 (Interviews)

| 方法 | 路径 | 描述 | 权限 |
|-----|------|------|------|
| POST | `/api/v1/interviews/` | 创建面试 | 认证 |
| GET | `/api/v1/interviews/` | 获取面试列表 | 认证 |
| GET | `/api/v1/interviews/{id}/` | 获取面试详情 | 认证 |
| POST | `/api/v1/interviews/{id}/start/` | 开始面试 | 认证 |
| POST | `/api/v1/interviews/{id}/message/` | 发送消息 | 认证 |
| POST | `/api/v1/interviews/{id}/end/` | 结束面试 | 认证 |

### 2.5 评估模块 (Evaluations)

| 方法 | 路径 | 描述 | 权限 |
|-----|------|------|------|
| GET | `/api/v1/evaluations/{interview_id}/` | 获取评估结果 | 认证 |
| GET | `/api/v1/evaluations/{interview_id}/dimensions/` | 获取维度评分 | 认证 |

### 2.6 报告模块 (Reports)

| 方法 | 路径 | 描述 | 权限 |
|-----|------|------|------|
| GET | `/api/v1/reports/{interview_id}/` | 获取评估报告 | 认证 |
| GET | `/api/v1/reports/{interview_id}/download/` | 下载PDF报告 | 认证 |

### 2.7 推荐模块 (Recommendations)

| 方法 | 路径 | 描述 | 权限 |
|-----|------|------|------|
| GET | `/api/v1/recommendations/` | 获取推荐列表 | 认证 |
| PUT | `/api/v1/recommendations/{id}/complete/` | 标记推荐完成 | 认证 |

### 2.8 学习模块 (Learning)

| 方法 | 路径 | 描述 | 权限 |
|-----|------|------|------|
| GET | `/api/v1/learning/resources/` | 获取学习资源 | 认证 |
| GET | `/api/v1/learning/paths/` | 获取学习路径 | 认证 |
| PUT | `/api/v1/learning/paths/{id}/progress/` | 更新学习进度 | 认证 |

---

## 三、API实现规范

### 3.1 使用Django REST Framework

#### 安装依赖
```bash
pip install djangorestframework django-cors-headers
```

#### 配置settings.py
```python
INSTALLED_APPS = [
    ...
    'rest_framework',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    ...
]

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}
```

### 3.2 统一响应封装

#### 创建响应工具类
```python
# core/response.py
from rest_framework.response import Response

class APIResponse:
    @staticmethod
    def success(data=None, message="success", code=200):
        return Response({
            "code": code,
            "message": message,
            "data": data
        }, status=code)
    
    @staticmethod
    def error(message="error", code=400, errors=None):
        return Response({
            "code": code,
            "message": message,
            "errors": errors
        }, status=code)
```

### 3.3 分页规范
```python
# core/pagination.py
from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
```

### 3.4 过滤规范
```python
# core/filters.py
from django_filters import rest_framework as filters

class PositionFilter(filters.FilterSet):
    code = filters.CharFilter(lookup_expr='exact')
    name = filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = JobPosition
        fields = ['code', 'name']
```

### 3.5 序列化器规范
```python
# positions/serializers.py
from rest_framework import serializers
from .models import JobPosition

class JobPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosition
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
```

### 3.6 视图集规范
```python
# positions/views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from core.response import APIResponse
from .models import JobPosition
from .serializers import JobPositionSerializer

class JobPositionViewSet(viewsets.ModelViewSet):
    queryset = JobPosition.objects.all()
    serializer_class = JobPositionSerializer
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(data=serializer.data)
    
    @action(detail=True, methods=['get'])
    def dimensions(self, request, pk=None):
        position = self.get_object()
        dimensions = position.dimensions.all()
        return APIResponse.success(data=dimensions.values())
```

### 3.7 路由规范
```python
# positions/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JobPositionViewSet

router = DefaultRouter()
router.register(r'positions', JobPositionViewSet)

urlpatterns = [
    path('api/v1/', include(router.urls)),
]
```

---

## 四、认证与权限

### 4.1 认证方式
- JWT Token认证（推荐）
- Session认证（用于Admin）

### 4.2 权限级别
- `IsAuthenticated`: 需要登录
- `IsAdminUser`: 需要管理员权限
- `AllowAny`: 公开访问

### 4.3 认证配置
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

---

## 五、错误处理

### 5.1 自定义异常处理器
```python
# core/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'code': response.status_code,
            'message': str(exc),
            'errors': response.data
        }
        response.data = custom_response_data
    
    return response
```

---

## 六、API文档

### 6.1 使用Swagger UI
```bash
pip install drf-yasg
```

### 6.2 配置Swagger
```python
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="AI模拟面试平台 API",
        default_version='v1',
        description="AI模拟面试与能力提升平台API文档",
    ),
    public=True,
)

urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
```

---

## 七、开发规范

### 7.1 代码组织
```
apps/
├── users/
│   ├── serializers.py      # 序列化器
│   ├── views.py            # 视图
│   ├── urls.py             # 路由
│   ├── filters.py          # 过滤器
│   └── permissions.py      # 权限
```

### 7.2 命名规范
- 类名：大驼峰（PascalCase）
- 函数名：小写下划线（snake_case）
- 变量名：小写下划线（snake_case）
- 常量：大写下划线（UPPER_SNAKE_CASE）

### 7.3 注释规范
- 类和函数使用docstring
- 复杂逻辑添加行内注释
- API端点添加描述注释

---

## 八、测试规范

### 8.1 单元测试
```python
# positions/tests.py
from django.test import TestCase
from rest_framework.test import APITestCase
from .models import JobPosition

class JobPositionAPITest(APITestCase):
    def test_list_positions(self):
        response = self.client.get('/api/v1/positions/')
        self.assertEqual(response.status_code, 200)
```

### 8.2 API测试
```python
def test_create_interview(self):
    self.client.force_authenticate(user=self.user)
    response = self.client.post('/api/v1/interviews/', {
        'position': 1,
        'mode': 'text'
    })
    self.assertEqual(response.status_code, 201)
```
