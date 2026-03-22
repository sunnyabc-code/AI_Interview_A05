from django.urls import path
from evaluations import views

urlpatterns = [
    path('difficulty-configs/', views.DifficultyConfigListView.as_view(), name='difficulty_config_list'),
]
