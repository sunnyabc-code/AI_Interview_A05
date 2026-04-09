# Pathway Module (Scaffold)

This module is added as an isolated scaffold to avoid impacting existing backend behavior.

## Current status
- Not registered in Django URLs/apps yet
- No existing endpoints are changed
- No existing models are altered

## Components
- `contracts.py`: shared data structures
- `services/diagnosis_service.py`: build user profile snapshot
- `services/recall_service.py`: rule-based candidate recall
- `services/llm_rerank_service.py`: optional LLM ranking layer with fallback
- `services/planner_service.py`: build cycle plan tasks
- `settings.py`: LLM config loader from environment variables

## Planned API (next step)
- `POST /api/pathway/plan/generate/`
- `GET /api/pathway/plan/current/`
- `POST /api/pathway/tasks/{task_id}/complete/`
- `GET /api/pathway/effect/`

## Environment variables for LLM
- `PATHWAY_LLM_BASE_URL`
- `PATHWAY_LLM_API_KEY`
- `PATHWAY_LLM_MODEL`
- `PATHWAY_LLM_TIMEOUT_SECONDS`
- `PATHWAY_LLM_MAX_RETRIES`
