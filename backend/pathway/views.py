from concurrent.futures import ThreadPoolExecutor

from django.db import DatabaseError, transaction
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.response import APIResponse
from pathway.models import PathwayEvent, PathwayGenerationJob, PathwayPlan, PathwayProfile, PathwayTask
from pathway.services.diagnosis_service import DiagnosisService
from pathway.services.llm_pathway_service import LlmPathwayService
from pathway.services.recall_service import RecallService
from pathway.services.resource_recommendation_service import ResourceRecommendationService
from pathway.settings import llm_ready


_GENERATOR_POOL = ThreadPoolExecutor(max_workers=2)


def _serialize_plan(plan: PathwayPlan):
    tasks = list(
        plan.tasks.all()
        .order_by("day_index", "priority", "id")
    )
    profile = getattr(plan, "profile", None)
    generation_meta = getattr(plan, "generation_meta", None) or {}
    if not generation_meta:
        event = (
            PathwayEvent.objects.filter(plan=plan, event_type="generated")
            .order_by("-id")
            .first()
        )
        payload = event.payload_json if event else {}
        generation_meta = payload.get("generation_meta") if isinstance(payload, dict) else {}

    task_dicts = [
        {
            "id": t.id,
            "dayIndex": t.day_index,
            "taskType": t.task_type,
            "title": t.title,
            "reason": t.reason,
            "estimatedMinutes": t.estimated_minutes,
            "status": t.status,
            "priority": t.priority,
        }
        for t in tasks
    ]

    recommendations = ResourceRecommendationService().recommend_for_tasks(task_dicts, per_task=3)
    for item in task_dicts:
                item["recommendedLinks"] = recommendations.get(str(item.get("id") or ""), [])

    return {
        "planId": plan.id,
        "cycleDays": plan.cycle_days,
        "goalSummary": plan.goal_summary,
        "expectedGain": plan.expected_gain_json or {},
        "status": plan.status,
        "generationMeta": generation_meta or {},
        "profile": {
            "technicalScore": float(profile.technical_score) if profile and profile.technical_score is not None else None,
            "expressionScore": float(profile.expression_score) if profile and profile.expression_score is not None else None,
            "dimensions": profile.dimensions_json if profile else {},
            "weaknesses": profile.weaknesses_json if profile else [],
            "strengths": profile.strengths_json if profile else [],
            "confidenceLevel": float(profile.confidence_level) if profile and profile.confidence_level is not None else 0,
            "snapshotTime": profile.snapshot_time.isoformat() if profile and profile.snapshot_time else None,
        },
        "tasks": task_dicts,
    }


def _is_legacy_template_plan(plan: PathwayPlan) -> bool:
    event = (
        PathwayEvent.objects.filter(plan=plan, event_type="generated")
        .order_by("-id")
        .first()
    )
    payload = event.payload_json if event else {}
    generation_meta = payload.get("generation_meta") if isinstance(payload, dict) else None
    if generation_meta:
        return False

    legacy_titles = {
        "2分钟结构化复述训练",
        "单短板高强度题目训练",
        "语音自信表达演练",
        "当日复盘与总结",
    }
    titles = set(
        plan.tasks.all().values_list("title", flat=True)
    )
    return any(title in legacy_titles for title in titles)


def _serialize_job(job: PathwayGenerationJob):
    return {
        "jobId": job.id,
        "status": job.status,
        "cycleDays": job.cycle_days,
        "currentDay": job.current_day,
        "totalDays": job.total_days,
        "progressPercent": job.progress_percent,
        "message": job.message,
        "errorMessage": job.error_message,
        "planId": job.plan_id,
        "meta": job.meta_json or {},
        "createdAt": job.created_at,
        "updatedAt": job.updated_at,
    }


def _check_active_plan_constraint(user):
    active_plan = (
        PathwayPlan.objects.filter(user=user, status="active")
        .prefetch_related("tasks")
        .order_by("-id")
        .first()
    )
    if not active_plan:
        return None

    pending_count = active_plan.tasks.filter(status="pending").count()
    if pending_count <= 0:
        return None

    if _is_legacy_template_plan(active_plan):
        active_plan.status = "paused"
        active_plan.save(update_fields=["status", "updated_at"])
        return None

    return f"当前 7 天计划仍有 {pending_count} 项待处理，请先全部完成或跳过后再生成下一期。"


def _build_and_persist_plan(user, cycle_days: int, job: PathwayGenerationJob = None):
    diagnosis_service = DiagnosisService()
    recall_service = RecallService()
    llm_pathway_service = LlmPathwayService()

    if job:
        job.status = "running"
        job.started_at = timezone.now()
        job.progress_percent = 5
        job.message = "正在分析你的历史面试能力数据..."
        job.save(update_fields=["status", "started_at", "progress_percent", "message", "updated_at"])

    snapshot = diagnosis_service.build_snapshot(user.id)
    generation_context = recall_service.build_generation_context(user.id)

    if job:
        job.progress_percent = 20
        job.message = "正在构建弱项画像并调用大模型生成 7 天学习路径..."
        job.save(update_fields=["progress_percent", "message", "updated_at"])

    plan = llm_pathway_service.generate_plan(snapshot, generation_context, cycle_days=cycle_days)

    with transaction.atomic():
        profile = PathwayProfile.objects.create(
            user=user,
            technical_score=snapshot.technical_score,
            expression_score=snapshot.expression_score,
            dimensions_json=snapshot.dimensions,
            weaknesses_json=[
                {
                    "key": w.key,
                    "weakness_type": w.weakness_type,
                    "severity": w.severity,
                    "trend": w.trend,
                    "evidence": w.evidence,
                }
                for w in snapshot.weaknesses
            ],
            strengths_json=snapshot.strengths,
            confidence_level=snapshot.confidence_level,
            snapshot_time=timezone.now(),
        )

        PathwayPlan.objects.filter(user=user, status="active").update(
            status="paused",
            updated_at=timezone.now(),
        )

        plan_obj = PathwayPlan.objects.create(
            user=user,
            profile=profile,
            status="active",
            cycle_days=plan.cycle_days,
            goal_summary=plan.goal_summary,
            expected_gain_json=plan.expected_gain,
        )

        total_days = max(1, plan.cycle_days)
        for idx, t in enumerate(plan.tasks, start=1):
            PathwayTask.objects.create(
                plan=plan_obj,
                day_index=t.day_index,
                task_type=t.task_type,
                source_type=t.source_type,
                source_id=t.source_id,
                title=t.title,
                reason=t.reason,
                estimated_minutes=t.estimated_minutes,
                priority=t.priority,
                status="pending",
            )
            if job and t.day_index > job.current_day:
                day = min(t.day_index, total_days)
                progress = min(95, int(day / total_days * 100))
                PathwayGenerationJob.objects.filter(id=job.id).update(
                    current_day=day,
                    total_days=total_days,
                    progress_percent=progress,
                    message=f"已生成第 {day} 天学习任务...",
                    updated_at=timezone.now(),
                )

        PathwayEvent.objects.create(
            user=user,
            plan=plan_obj,
            event_type="generated",
            payload_json={
                "cycle_days": plan.cycle_days,
                "generation_meta": plan.generation_meta,
                "context_summary": {
                    "lowest_knowledge_points": len(generation_context.get("technical", {}).get("lowest_knowledge_points", [])),
                    "scenario_directions": len(generation_context.get("scenario", {}).get("lowest_directions", [])),
                    "project_directions": len(generation_context.get("project", {}).get("lowest_directions", [])),
                    "expression_dimensions": len(generation_context.get("expression", {}).get("weak_dimensions", [])),
                },
                "llm_ready": llm_ready(),
            },
        )

    if job:
        PathwayGenerationJob.objects.filter(id=job.id).update(
            status="success",
            progress_percent=100,
            message="七日学习路径已生成完成",
            finished_at=timezone.now(),
            plan=plan_obj,
            meta_json=plan.generation_meta or {},
            updated_at=timezone.now(),
        )

    return plan_obj


def _run_generation_job(job_id: int):
    job = PathwayGenerationJob.objects.filter(id=job_id).select_related("user").first()
    if not job:
        return

    try:
        user = job.user
        block_message = _check_active_plan_constraint(user)
        if block_message:
            PathwayGenerationJob.objects.filter(id=job_id).update(
                status="failed",
                error_message=block_message,
                message="生成失败",
                finished_at=timezone.now(),
                updated_at=timezone.now(),
            )
            return

        _build_and_persist_plan(user=user, cycle_days=job.cycle_days, job=job)
    except Exception as exc:  # noqa: B902
        PathwayGenerationJob.objects.filter(id=job_id).update(
            status="failed",
            error_message=str(exc),
            message="生成失败",
            finished_at=timezone.now(),
            updated_at=timezone.now(),
        )


class PathwayHealthView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Pathway"],
        operation_summary="Pathway 健康检查",
        operation_description="检查个性化提升路径模块是否可用，以及 LLM 配置状态。",
        security=[{"Bearer": []}],
        responses={200: openapi.Response("检查成功")},
    )
    def get(self, request):
        return APIResponse.success(
            data={
                "module": "pathway",
                "enabled": True,
                "llm_ready": llm_ready(),
            },
            message="pathway 模块可用",
            code=200,
        )


class PathwayGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Pathway"],
        operation_summary="生成个性化提升路径",
        operation_description="基于用户真实弱项（技术知识点/场景/项目/表达）调用可配置 LLM 生成 7 日路径，失败时自动回退确定性策略。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "cycle_days": openapi.Schema(type=openapi.TYPE_INTEGER, default=7),
            },
        ),
        security=[{"Bearer": []}],
        responses={200: openapi.Response("生成成功")},
    )
    def post(self, request):
        cycle_days = int(request.data.get("cycle_days") or 7)
        cycle_days = max(3, min(30, cycle_days))

        block_message = _check_active_plan_constraint(request.user)
        if block_message:
            return APIResponse.error(message=block_message, code=400)

        plan_obj = _build_and_persist_plan(user=request.user, cycle_days=cycle_days)
        plan_data = _serialize_plan(plan_obj)

        return APIResponse.success(
            data={"plan": plan_data},
            message="个性化提升路径生成成功",
            code=200,
        )


class PathwayGenerateAsyncView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Pathway"],
        operation_summary="异步生成个性化提升路径",
        operation_description="提交生成任务并返回 job_id，前端可轮询进度；刷新或跳转后生成不中断。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "cycle_days": openapi.Schema(type=openapi.TYPE_INTEGER, default=7),
            },
        ),
        security=[{"Bearer": []}],
        responses={200: openapi.Response("提交成功")},
    )
    def post(self, request):
        cycle_days = int(request.data.get("cycle_days") or 7)
        cycle_days = max(7, min(30, cycle_days))

        try:
            running_job = (
                PathwayGenerationJob.objects.filter(user=request.user, status__in=["pending", "running"])
                .order_by("-id")
                .first()
            )
        except DatabaseError:
            return APIResponse.error(message="生成任务表不可用，请先执行迁移。", code=503)
        if running_job:
            return APIResponse.success(
                data={"job": _serialize_job(running_job)},
                message="已有进行中的生成任务",
                code=200,
            )

        block_message = _check_active_plan_constraint(request.user)
        if block_message:
            return APIResponse.error(message=block_message, code=400)

        try:
            job = PathwayGenerationJob.objects.create(
                user=request.user,
                status="pending",
                cycle_days=cycle_days,
                total_days=cycle_days,
                progress_percent=0,
                message="任务已提交，等待开始生成...",
            )
        except DatabaseError:
            return APIResponse.error(message="生成任务表不可用，请先执行迁移。", code=503)

        _GENERATOR_POOL.submit(_run_generation_job, job.id)

        return APIResponse.success(
            data={"job": _serialize_job(job)},
            message="生成任务已启动",
            code=200,
        )


class PathwayGenerationStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Pathway"],
        operation_summary="获取生成任务状态",
        operation_description="轮询指定生成任务状态与进度。",
        security=[{"Bearer": []}],
        responses={200: openapi.Response("获取成功")},
    )
    def get(self, request, job_id):
        try:
            job = PathwayGenerationJob.objects.filter(id=job_id, user=request.user).first()
        except DatabaseError:
            return APIResponse.error(message="生成任务表不可用，请先执行迁移。", code=503)
        if not job:
            return APIResponse.error(message="生成任务不存在", code=404)

        payload = {"job": _serialize_job(job)}
        if job.status == "success" and job.plan_id:
            plan = (
                PathwayPlan.objects.filter(id=job.plan_id)
                .select_related("profile")
                .prefetch_related("tasks")
                .first()
            )
            if plan:
                payload["plan"] = _serialize_plan(plan)

        return APIResponse.success(data=payload, message="获取成功", code=200)


class PathwayLatestGenerationJobView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Pathway"],
        operation_summary="获取最近生成任务",
        operation_description="用于刷新/跳转后恢复进度显示。",
        security=[{"Bearer": []}],
        responses={200: openapi.Response("获取成功")},
    )
    def get(self, request):
        try:
            job = (
                PathwayGenerationJob.objects.filter(user=request.user)
                .order_by("-id")
                .first()
            )
        except DatabaseError:
            return APIResponse.error(message="生成任务表不可用，请先执行迁移。", code=503)
        if not job:
            return APIResponse.success(data={"job": None}, message="暂无生成任务", code=200)

        payload = {"job": _serialize_job(job)}
        if job.status == "success" and job.plan_id:
            plan = (
                PathwayPlan.objects.filter(id=job.plan_id)
                .select_related("profile")
                .prefetch_related("tasks")
                .first()
            )
            if plan:
                payload["plan"] = _serialize_plan(plan)

        return APIResponse.success(data=payload, message="获取成功", code=200)


class PathwayCurrentPlanView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Pathway"],
        operation_summary="获取当前路径计划",
        operation_description="获取当前用户的 active 计划，若无则回退最近一次历史计划。",
        security=[{"Bearer": []}],
        responses={200: openapi.Response("获取成功")},
    )
    def get(self, request):
        plan = (
            PathwayPlan.objects.filter(user=request.user, status="active")
            .select_related("profile")
            .prefetch_related("tasks")
            .order_by("-id")
            .first()
        )
        if not plan:
            plan = (
                PathwayPlan.objects.filter(user=request.user)
                .select_related("profile")
                .prefetch_related("tasks")
                .order_by("-id")
                .first()
            )

        if not plan:
            return APIResponse.success(
                data={"plan": None},
                message="当前暂无路径计划",
                code=200,
            )

        return APIResponse.success(
            data={"plan": _serialize_plan(plan)},
            message="获取成功",
            code=200,
        )


class PathwayTaskCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Pathway"],
        operation_summary="更新任务完成状态",
        operation_description="将路径任务标记为 done/skipped，并记录完成备注。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "status": openapi.Schema(type=openapi.TYPE_STRING, default="done"),
                "completion_note": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        security=[{"Bearer": []}],
        responses={200: openapi.Response("更新成功")},
    )
    def post(self, request, task_id):
        task = (
            PathwayTask.objects.select_related("plan")
            .filter(id=task_id, plan__user=request.user)
            .first()
        )
        if not task:
            return APIResponse.error(message="任务不存在或无权限", code=404)

        status = str(request.data.get("status") or "done").lower().strip()
        if status not in {"done", "skipped", "pending"}:
            return APIResponse.error(message="status 参数不合法", code=400)

        task.status = status
        task.completion_note = str(request.data.get("completion_note") or "").strip()
        task.done_at = timezone.now() if status == "done" else None
        task.save(update_fields=["status", "completion_note", "done_at", "updated_at"])

        # 当前计划任务都处理完成后，自动标记为 completed。
        if task.plan.status == "active":
            remaining = task.plan.tasks.filter(status="pending").count()
            if remaining == 0:
                task.plan.status = "completed"
                task.plan.save(update_fields=["status", "updated_at"])

        PathwayEvent.objects.create(
            user=request.user,
            plan=task.plan,
            event_type="task_done",
            payload_json={
                "task_id": task.id,
                "status": task.status,
                "completion_note": task.completion_note,
            },
        )

        return APIResponse.success(
            data={
                "taskId": task.id,
                "status": task.status,
                "doneAt": task.done_at,
            },
            message="任务状态更新成功",
            code=200,
        )


class PathwayEffectView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Pathway"],
        operation_summary="路径效果概览",
        operation_description="返回路径完成度与最近两次画像变化，用于前端效果展示。",
        security=[{"Bearer": []}],
        responses={200: openapi.Response("获取成功")},
    )
    def get(self, request):
        plan = (
            PathwayPlan.objects.filter(user=request.user)
            .prefetch_related("tasks")
            .order_by("-id")
            .first()
        )
        if not plan:
            return APIResponse.success(
                data={
                    "completionRate": 0,
                    "doneTasks": 0,
                    "totalTasks": 0,
                    "deltas": {},
                },
                message="暂无路径计划",
                code=200,
            )

        tasks = list(plan.tasks.all())
        total = len(tasks)
        done = len([t for t in tasks if t.status == "done"])
        completion_rate = round((done / total) * 100, 2) if total else 0

        profiles = list(
            PathwayProfile.objects.filter(user=request.user)
            .order_by("-snapshot_time", "-id")[:2]
        )
        deltas = {}
        if len(profiles) >= 2:
            latest, previous = profiles[0], profiles[1]
            for key in ["technical_score", "expression_score"]:
                a = getattr(latest, key)
                b = getattr(previous, key)
                if a is not None and b is not None:
                    deltas[key] = round(float(a) - float(b), 2)

        return APIResponse.success(
            data={
                "planId": plan.id,
                "status": plan.status,
                "completionRate": completion_rate,
                "doneTasks": done,
                "totalTasks": total,
                "deltas": deltas,
            },
            message="获取成功",
            code=200,
        )
