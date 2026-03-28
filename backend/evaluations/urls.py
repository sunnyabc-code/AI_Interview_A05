from django.urls import path
from evaluations import views

urlpatterns = [
    path(
        "difficulty-configs/",
        views.DifficultyConfigListView.as_view(),
        name="difficulty_config_list",
    ),
    path(
        "voice-analysis/run/",
        views.VoiceAnalysisRunView.as_view(),
        name="voice_analysis_run",
    ),
    path(
        "imentiv-analysis/run/",
        views.ImentivAnalysisRunView.as_view(),
        name="imentiv_analysis_run",
    ),
    path(
        "imentiv-analysis/<int:audio_id>/status/",
        views.ImentivAnalysisStatusView.as_view(),
        name="imentiv_analysis_status",
    ),
]
