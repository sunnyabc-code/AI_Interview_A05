from django.urls import path

from interview_md import views

urlpatterns = [
    path('chain/auth/register/', views.RegisterMdView.as_view()),
    path('chain/auth/login/', views.LoginMdView.as_view()),
    path('chain/auth/send-code/', views.SendCodeMdView.as_view()),
    path('chain/auth/reset-password/', views.ResetPasswordMdView.as_view()),
    path('scenario/list/', views.ScenarioListView.as_view()),
    path('session/create/', views.SessionCreateView.as_view()),
    path('session/<int:session_id>/state/', views.SessionStateView.as_view()),
    path('dialogue/next/', views.DialogueNextView.as_view()),
    path('evaluation/submit/', views.EvaluationSubmitView.as_view()),
    path('report/detail/', views.ReportDetailView.as_view()),
    path('profile/trend/', views.ProfileTrendView.as_view()),
    path('profile/history/', views.ProfileHistoryView.as_view()),
]
