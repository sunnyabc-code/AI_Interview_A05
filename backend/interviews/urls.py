from django.urls import path
from interviews import views

urlpatterns = [
    path('', views.InterviewListCreateView.as_view(), name='interview_list_create'),
    path('<int:interview_id>/', views.InterviewDetailView.as_view(), name='interview_detail'),
]
