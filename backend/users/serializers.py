from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    target_positions = serializers.SerializerMethodField()
    
    def get_target_positions(self, obj):
        return [
            {
                'id': position.id,
                'name': position.name
            }
            for position in obj.target_positions.all()
        ]
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'avatar', 'target_positions', 'interview_count', 'created_at']


class UpdateUserSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, max_length=20, allow_blank=True)
    avatar = serializers.CharField(required=False, max_length=500, allow_blank=True)
    target_positions = serializers.ListField(required=False, child=serializers.IntegerField())


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(required=True, min_length=6, write_only=True)
    confirm_password = serializers.CharField(required=True, min_length=6, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, max_length=20, allow_blank=True)
    verification_code = serializers.CharField(required=True, write_only=True)
    register_type = serializers.ChoiceField(required=True, choices=['email', 'phone'])

    def validate(self, data):
        # 验证密码
        if data['password'] != data['confirm_password']:
            raise ValidationError('两次密码输入不一致')

        # 验证验证码（仿真）
        if not data['verification_code'].isdigit():
            raise ValidationError('验证码格式错误')

        # 验证用户名
        if User.objects.filter(username=data['username']).exists():
            raise ValidationError('用户名已存在')

        # 验证邮箱或手机号
        if data['register_type'] == 'email':
            if not data.get('email'):
                raise ValidationError('邮箱不能为空')
            if User.objects.filter(email=data['email']).exists():
                raise ValidationError('邮箱已注册')
        else:
            if not data.get('phone'):
                raise ValidationError('手机号不能为空')
            if User.objects.filter(phone=data['phone']).exists():
                raise ValidationError('手机号已注册')

        return data


class LoginSerializer(serializers.Serializer):
    login_type = serializers.ChoiceField(required=True, choices=['email', 'phone'])
    identifier = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        # 验证登录方式
        if data['login_type'] == 'email':
            if not data['identifier'].count('@'):
                raise ValidationError('邮箱格式错误')
        else:
            if not data['identifier'].isdigit():
                raise ValidationError('手机号格式错误')
        return data


class VerificationCodeSerializer(serializers.Serializer):
    target = serializers.CharField(required=True)
    send_type = serializers.ChoiceField(required=True, choices=['email', 'phone'])

    def validate(self, data):
        if data['send_type'] == 'email':
            if not data['target'].count('@'):
                raise ValidationError('邮箱格式错误')
        else:
            if not data['target'].isdigit():
                raise ValidationError('手机号格式错误')
        return data


class ResetPasswordSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True)
    verification_code = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6, write_only=True)
    confirm_password = serializers.CharField(required=True, min_length=6, write_only=True)
    reset_type = serializers.ChoiceField(required=True, choices=['email', 'phone'])

    def validate(self, data):
        # 验证密码
        if data['new_password'] != data['confirm_password']:
            raise ValidationError('两次密码输入不一致')

        # 验证验证码
        if not data['verification_code'].isdigit():
            raise ValidationError('验证码格式错误')

        # 验证用户存在
        if data['reset_type'] == 'email':
            if not User.objects.filter(email=data['identifier']).exists():
                raise ValidationError('邮箱未注册')
        else:
            if not User.objects.filter(phone=data['identifier']).exists():
                raise ValidationError('手机号未注册')

        return data