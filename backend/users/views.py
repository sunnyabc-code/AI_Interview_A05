from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, get_user_model
from users.serializers import RegisterSerializer, LoginSerializer, UserSerializer, VerificationCodeSerializer, UpdateUserSerializer, ResetPasswordSerializer
import random
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['User'],
        operation_summary='用户注册',
        operation_description='支持邮箱注册和手机号注册',
        request_body=RegisterSerializer,
        responses={
            200: openapi.Response('注册成功', UserSerializer),
            400: openapi.Response('注册失败')
        }
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            # 创建用户
            # 检查邮箱是否已存在
            if data['register_type'] == 'email' and data.get('email'):
                existing_user = User.objects.filter(email=data['email']).first()
                if existing_user:
                    return Response({
                        'code': 400,
                        'message': '邮箱已注册'
                    })
            # 检查手机号是否已存在
            elif data['register_type'] == 'phone' and data.get('phone'):
                existing_user = User.objects.filter(phone=data['phone']).first()
                if existing_user:
                    return Response({
                        'code': 400,
                        'message': '手机号已注册'
                    })
            
            user = User.objects.create_user(
                username=data['username'],
                password=data['password'],
                email=data.get('email', ''),
                phone=data.get('phone', '')
            )
            
            return Response({
                'code': 200,
                'message': '注册成功',
                'data': UserSerializer(user).data
            })
        return Response({
            'code': 400,
            'message': '注册失败',
            'errors': serializer.errors
        })


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['User'],
        operation_summary='用户登录',
        operation_description='支持邮箱登录和手机号登录，返回JWT令牌',
        request_body=LoginSerializer,
        responses={
            200: openapi.Response('登录成功', UserSerializer),
            401: openapi.Response('账号或密码错误'),
            400: openapi.Response('登录失败')
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            # 验证用户
            if data['login_type'] == 'email':
                # 邮箱登录，先查找用户
                try:
                    user = User.objects.filter(email=data['identifier']).first()
                    if user:
                        user = authenticate(request, username=user.username, password=data['password'])
                    else:
                        user = None
                except Exception:
                    user = None
            else:
                # 手机号登录，先查找用户
                try:
                    user = User.objects.filter(phone=data['identifier']).first()
                    if user:
                        user = authenticate(request, username=user.username, password=data['password'])
                    else:
                        user = None
                except Exception:
                    user = None
            
            if user:
                # 生成JWT令牌
                refresh = RefreshToken.for_user(user)
                return Response({
                    'code': 200,
                    'message': '登录成功',
                    'data': {
                        'user': UserSerializer(user).data,
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                })
            return Response({
                'code': 401,
                'message': '账号或密码错误'
            })
        return Response({
            'code': 400,
            'message': '登录失败',
            'errors': serializer.errors
        })


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['User'],
        operation_summary='退出登录',
        operation_description='退出当前登录状态（客户端需要删除本地存储的JWT令牌）',
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('退出登录成功')
        }
    )
    def post(self, request):
        user = request.user
        # JWT是无状态的，不需要服务器端操作
        # 客户端需要删除本地存储的token
        return Response({
            'code': 200,
            'message': f'用户 {user.username} 退出登录成功',
            'data': {
                'username': user.username,
                'user_id': user.id
            }
        })


@method_decorator(csrf_exempt, name='dispatch')
class SendVerificationCodeView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['User'],
        operation_summary='发送验证码',
        operation_description='发送注册验证码（仿真）',
        request_body=VerificationCodeSerializer,
        responses={
            200: openapi.Response('验证码发送成功'),
            400: openapi.Response('发送失败')
        }
    )
    def post(self, request):
        serializer = VerificationCodeSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            # 生成验证码（仿真）
            code = str(random.randint(100000, 999999))
            
            # 这里应该调用发送短信/邮件的API，现在只是仿真
            print(f"验证码: {code} 发送到 {data['target']}")
            
            return Response({
                'code': 200,
                'message': '验证码发送成功',
                'data': {
                    'verification_code': code  # 实际环境中不应该返回验证码
                }
            })
        return Response({
            'code': 400,
            'message': '发送失败',
            'errors': serializer.errors
        })


@method_decorator(csrf_exempt, name='dispatch')
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['User'],
        operation_summary='获取用户信息',
        operation_description='获取当前登录用户的详细信息',
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('获取成功', UserSerializer),
            401: openapi.Response('未登录')
        }
    )
    def get(self, request):
        user = request.user
        return Response({
            'code': 200,
            'message': '获取成功',
            'data': UserSerializer(user).data
        })


@method_decorator(csrf_exempt, name='dispatch')
class UpdateUserView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['User'],
        operation_summary='修改用户属性',
        operation_description='修改当前登录用户的个人信息',
        request_body=UpdateUserSerializer,
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response('更新成功', UserSerializer),
            400: openapi.Response('更新失败'),
            401: openapi.Response('未登录')
        }
    )
    def put(self, request):
        user = request.user
        
        serializer = UpdateUserSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            # 更新用户信息
            if 'username' in data:
                user.username = data['username']
            if 'email' in data:
                user.email = data['email']
            if 'phone' in data:
                user.phone = data['phone']
            if 'avatar' in data:
                user.avatar = data['avatar']
            if 'target_positions' in data:
                # 验证岗位ID是否存在
                from positions.models import JobPosition
                position_ids = data['target_positions']
                valid_positions = JobPosition.objects.filter(id__in=position_ids)
                if valid_positions.count() != len(position_ids):
                    return Response({
                        'code': 400,
                        'message': '部分岗位ID不存在'
                    })
                user.target_positions.set(valid_positions)
            
            user.save()
            
            return Response({
                'code': 200,
                'message': '更新成功',
                'data': UserSerializer(user).data
            })
        return Response({
            'code': 400,
            'message': '更新失败',
            'errors': serializer.errors
        })


@method_decorator(csrf_exempt, name='dispatch')
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['User'],
        operation_summary='重置密码',
        operation_description='通过邮箱或手机号重置密码',
        request_body=ResetPasswordSerializer,
        responses={
            200: openapi.Response('密码重置成功'),
            400: openapi.Response('重置失败')
        }
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            # 查找用户
            if data['reset_type'] == 'email':
                user = User.objects.get(email=data['identifier'])
            else:
                user = User.objects.get(phone=data['identifier'])
            
            # 更新密码
            user.set_password(data['new_password'])
            user.save()
            
            return Response({
                'code': 200,
                'message': '密码重置成功'
            })
        return Response({
            'code': 400,
            'message': '重置失败',
            'errors': serializer.errors
        })


@method_decorator(csrf_exempt, name='dispatch')
class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['User'],
        operation_summary='刷新JWT令牌',
        operation_description='使用刷新令牌获取新的访问令牌',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'refresh': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='刷新令牌'
                )
            },
            required=['refresh']
        ),
        responses={
            200: openapi.Response('令牌刷新成功'),
            400: openapi.Response('刷新失败')
        }
    )
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'code': 400,
                'message': '刷新令牌不能为空'
            })
        
        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            return Response({
                'code': 200,
                'message': '令牌刷新成功',
                'data': {
                    'access': access_token,
                    'refresh': str(refresh)
                }
            })
        except Exception as e:
            return Response({
                'code': 400,
                'message': '刷新失败',
                'errors': str(e)
            })