from django.urls import path

from pathway import views

urlpatterns = [
    path("health/", views.PathwayHealthView.as_view(), name="pathway_health"),
    path("plan/generate/", views.PathwayGenerateView.as_view(), name="pathway_plan_generate"),
    path("plan/generate-async/", views.PathwayGenerateAsyncView.as_view(), name="pathway_plan_generate_async"),
    path("plan/generation-status/<int:job_id>/", views.PathwayGenerationStatusView.as_view(), name="pathway_plan_generation_status"),
    path("plan/generation-latest/", views.PathwayLatestGenerationJobView.as_view(), name="pathway_plan_generation_latest"),
    path("plan/current/", views.PathwayCurrentPlanView.as_view(), name="pathway_plan_current"),
    path("tasks/<int:task_id>/complete/", views.PathwayTaskCompleteView.as_view(), name="pathway_task_complete"),
    path("effect/", views.PathwayEffectView.as_view(), name="pathway_effect"),
]
