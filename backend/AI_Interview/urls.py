"""
URL configuration for AI_Interview project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# JWT Bearer Token认证配置
from drf_yasg.generators import OpenAPISchemaGenerator

class JWTSchemaGenerator(OpenAPISchemaGenerator):
    def get_security_definitions(self):
        security_definitions = super().get_security_definitions()
        security_definitions['Bearer'] = {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': '请输入: Bearer <JWT令牌>'
        }
        return security_definitions

schema_view = get_schema_view(
    openapi.Info(
        title="AI模拟面试平台 API",
        default_version='v1',
        description="AI模拟面试与能力提升平台API文档\n\nJWT认证方式: 在Authorize中输入 `Bearer <your_token>`",
    ),
    public=True,
    authentication_classes=[],
    permission_classes=[],
    generator_class=JWTSchemaGenerator,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # 其他路由...
    path('api/users/', include('users.urls')),
    path('api/positions/', include('positions.urls')),
    path('api/user-projects/', include('user_projects.urls')),
    path('api/evaluations/', include('evaluations.urls')),
    path('api/recommendations/', include('recommendations.urls')),
    path('api/pathway/', include('pathway.urls')),
    path('api/v1/interviews/', include('interviews.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
