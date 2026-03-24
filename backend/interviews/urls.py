from django.urls import path
from interviews import views

urlpatterns = [
    path('', views.InterviewListCreateView.as_view(), name='interview_list_create'),
    path('<int:interview_id>/', views.InterviewDetailView.as_view(), name='interview_detail'),
    path('<int:interview_id>/rounds/', views.InterviewRoundListView.as_view(), name='interview_round_list'),
    path('<int:interview_id>/next-question/', views.InterviewNextQuestionView.as_view(), name='interview_next_question'),
    path('<int:interview_id>/rounds/<int:round_id>/answer/', views.InterviewRoundAnswerView.as_view(), name='interview_round_answer'),
    path('<int:interview_id>/start/', views.InterviewStartView.as_view(), name='interview_start'),
    path('<int:interview_id>/pause/', views.InterviewPauseView.as_view(), name='interview_pause'),
    path('<int:interview_id>/resume/', views.InterviewResumeView.as_view(), name='interview_resume'),
    path('<int:interview_id>/end/', views.InterviewEndView.as_view(), name='interview_end'),
]
