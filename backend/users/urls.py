from django.urls import path
from users import views

urlpatterns = [
    # 注册
    path('register/', views.RegisterView.as_view(), name='register'),
    # 登录
    path('login/', views.LoginView.as_view(), name='login'),
    # 退出登录
    path('logout/', views.LogoutView.as_view(), name='logout'),
    # 发送验证码
    path('send-code/', views.SendVerificationCodeView.as_view(), name='send_code'),
    # 获取用户信息（当前登录用户）
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    # 修改用户属性（当前登录用户）
    path('profile/update/', views.UpdateUserView.as_view(), name='update_profile'),
    # 重置密码
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset_password'),
    # 刷新令牌
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
]
