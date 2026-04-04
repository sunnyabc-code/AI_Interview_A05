from django.urls import path

from user_projects import views

urlpatterns = [
    path("", views.UserProjectListCreateView.as_view(), name="user_project_list_create"),
    path("<int:project_id>/", views.UserProjectDetailView.as_view(), name="user_project_detail"),
]
