from django.urls import path

from recommendations import views

urlpatterns = [
    path(
        'knowledge-feedback/',
        views.KnowledgeFeedbackView.as_view(),
        name='knowledge_feedback',
    ),
    path(
        'knowledge-feedback/<int:knowledge_id>/detail/',
        views.KnowledgeFeedbackDetailView.as_view(),
        name='knowledge_feedback_detail',
    ),
]
