from django.urls import path
from positions import views

urlpatterns = [
    path('', views.JobPositionListView.as_view(), name='position_list'),
]
