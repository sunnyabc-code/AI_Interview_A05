"""
与 数据库表.md 对齐的只读/写入表映射（managed=False，表由 DBA 已建好）。
"""
from django.db import models


class UserAccount(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=64)
    email = models.CharField(max_length=128, blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=32, default='student')
    status = models.SmallIntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_account'

    @property
    def is_authenticated(self):
        return True


class StudentProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UserAccount, db_column='user_id', on_delete=models.DO_NOTHING)
    school = models.CharField(max_length=128, blank=True)
    major = models.CharField(max_length=128, blank=True)
    grade = models.CharField(max_length=32, blank=True)
    target_role_code = models.CharField(max_length=64, blank=True)
    self_intro = models.TextField(blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'student_profile'


class JobRole(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    is_active = models.SmallIntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'job_role'


class DifficultyConfig(models.Model):
    id = models.BigAutoField(primary_key=True)
    difficulty_code = models.CharField(max_length=16, unique=True)
    difficulty_name = models.CharField(max_length=32)
    answer_time_seconds = models.IntegerField(default=120)
    technical_chain_count = models.IntegerField(default=1)
    project_chain_count = models.IntegerField(default=1)
    scenario_chain_count = models.IntegerField(default=1)
    technical_max_followup_depth = models.IntegerField(default=2)
    project_max_followup_depth = models.IntegerField(default=2)
    scenario_max_followup_depth = models.IntegerField(default=2)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'difficulty_config'


class RoleInterviewStrategy(models.Model):
    id = models.BigAutoField(primary_key=True)
    role = models.ForeignKey(JobRole, db_column='role_id', on_delete=models.DO_NOTHING)
    difficulty_code = models.CharField(max_length=16)
    technical_weight = models.DecimalField(max_digits=6, decimal_places=4)
    project_weight = models.DecimalField(max_digits=6, decimal_places=4)
    scenario_weight = models.DecimalField(max_digits=6, decimal_places=4)
    technical_chain_strategy_json = models.JSONField(blank=True, null=True)
    project_chain_strategy_json = models.JSONField(blank=True, null=True)
    scenario_chain_strategy_json = models.JSONField(blank=True, null=True)
    rubric_version = models.CharField(max_length=32, blank=True, null=True)
    prompt_version = models.CharField(max_length=32, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'role_interview_strategy'


class QuestionBank(models.Model):
    id = models.BigAutoField(primary_key=True)
    role = models.ForeignKey(JobRole, db_column='role_id', on_delete=models.DO_NOTHING)
    aspect_type = models.CharField(max_length=16)
    chain_anchor_type = models.CharField(max_length=32)
    chain_anchor_code = models.CharField(max_length=64, blank=True)
    topic = models.CharField(max_length=128, blank=True)
    subtopic = models.CharField(max_length=128, blank=True)
    difficulty = models.CharField(max_length=16, blank=True)
    question_text = models.TextField()
    key_points_json = models.JSONField(blank=True, null=True)
    ideal_answer = models.TextField(blank=True)
    followup_hints_json = models.JSONField(blank=True, null=True)
    source_type = models.CharField(max_length=32, blank=True)
    is_active = models.SmallIntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'question_bank'


class InterviewSession(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UserAccount, db_column='user_id', on_delete=models.DO_NOTHING)
    role = models.ForeignKey(JobRole, db_column='role_id', on_delete=models.DO_NOTHING)
    resume_id = models.BigIntegerField(blank=True, null=True)
    difficulty = models.CharField(max_length=16)
    difficulty_config = models.ForeignKey(DifficultyConfig, db_column='difficulty_config_id', on_delete=models.DO_NOTHING)
    mode = models.CharField(max_length=16, default='text')
    session_prompt_snapshot = models.TextField(blank=True)
    context_snapshot = models.JSONField(blank=True, null=True)
    strategy_snapshot_json = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=16)
    total_chain_count = models.IntegerField(default=0)
    completed_chain_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'interview_session'


class SessionAspect(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(InterviewSession, db_column='session_id', on_delete=models.DO_NOTHING)
    aspect_type = models.CharField(max_length=16)
    aspect_name = models.CharField(max_length=64)
    aspect_weight = models.DecimalField(max_digits=6, decimal_places=4)
    planned_chain_count = models.IntegerField()
    completed_chain_count = models.IntegerField(default=0)
    aspect_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    dimension_scores_json = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=16)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'session_aspect'


class InterviewChain(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(InterviewSession, db_column='session_id', on_delete=models.DO_NOTHING)
    session_aspect = models.ForeignKey(SessionAspect, db_column='session_aspect_id', on_delete=models.DO_NOTHING)
    chain_no = models.IntegerField()
    chain_no_in_aspect = models.IntegerField()
    aspect_type = models.CharField(max_length=16)
    anchor_type = models.CharField(max_length=32)
    anchor_id = models.BigIntegerField(blank=True, null=True)
    anchor_code = models.CharField(max_length=64, blank=True)
    anchor_title = models.CharField(max_length=255, blank=True)
    project_name = models.CharField(max_length=255, blank=True)
    topic = models.CharField(max_length=128, blank=True)
    subtopic = models.CharField(max_length=128, blank=True)
    max_followup_depth = models.IntegerField()
    current_followup_depth = models.IntegerField(default=0)
    round_count = models.IntegerField(default=0)
    chain_weight = models.DecimalField(max_digits=6, decimal_places=4, default=1)
    status = models.CharField(max_length=16)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    chain_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'interview_chain'


class InterviewRound(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(InterviewSession, db_column='session_id', on_delete=models.DO_NOTHING)
    chain = models.ForeignKey(InterviewChain, db_column='chain_id', on_delete=models.DO_NOTHING)
    global_round_no = models.IntegerField()
    round_no_in_chain = models.IntegerField()
    parent_round = models.ForeignKey(
        'self', db_column='parent_round_id', on_delete=models.DO_NOTHING, blank=True, null=True, related_name='+'
    )
    is_followup = models.SmallIntegerField(default=0)
    question_text = models.TextField()
    question_source = models.CharField(max_length=32, blank=True)
    candidate_answer_text = models.TextField(blank=True)
    answer_audio_url = models.CharField(max_length=255, blank=True)
    asr_text = models.TextField(blank=True)
    answer_time_limit_seconds = models.IntegerField(blank=True, null=True)
    record_start_at = models.DateTimeField(blank=True, null=True)
    record_end_at = models.DateTimeField(blank=True, null=True)
    record_end_reason = models.CharField(max_length=32, blank=True)
    uncovered_points_json = models.JSONField(blank=True, null=True)
    followup_needed = models.SmallIntegerField(blank=True, null=True)
    followup_reason = models.TextField(blank=True)
    decision_json = models.JSONField(blank=True, null=True)
    asked_at = models.DateTimeField(blank=True, null=True)
    answered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'interview_round'


class SpeechMetric(models.Model):
    id = models.BigAutoField(primary_key=True)
    round = models.ForeignKey(InterviewRound, db_column='round_id', on_delete=models.DO_NOTHING)
    audio_duration_ms = models.IntegerField(blank=True, null=True)
    speaking_rate_wpm = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    pause_count = models.IntegerField(blank=True, null=True)
    avg_pause_ms = models.IntegerField(blank=True, null=True)
    clarity_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    emotion_label = models.CharField(max_length=32, blank=True)
    raw_features = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'speech_metric'


class ChainEvaluation(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(InterviewSession, db_column='session_id', on_delete=models.DO_NOTHING)
    chain = models.ForeignKey(InterviewChain, db_column='chain_id', on_delete=models.DO_NOTHING)
    aspect_type = models.CharField(max_length=16)
    rubric_id = models.BigIntegerField(blank=True, null=True)
    evaluation_mode = models.CharField(max_length=32, default='llm_only')
    grounding_status = models.CharField(max_length=32, default='not_used')
    retrieval_hit_count = models.IntegerField(default=0)
    content_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    logic_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    communication_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    job_match_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    strengths_json = models.JSONField(blank=True, null=True)
    weaknesses_json = models.JSONField(blank=True, null=True)
    suggestions_json = models.JSONField(blank=True, null=True)
    llm_result_json = models.TextField(blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'chain_evaluation'


class MdEvaluationReport(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(InterviewSession, db_column='session_id', on_delete=models.DO_NOTHING)
    generated_by = models.CharField(max_length=32)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    technical_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    project_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    scenario_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    content_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    logic_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    communication_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    job_match_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    aspect_scores_json = models.JSONField(blank=True, null=True)
    dimension_scores_json = models.JSONField(blank=True, null=True)
    strengths_json = models.JSONField(blank=True, null=True)
    weaknesses_json = models.JSONField(blank=True, null=True)
    improvement_suggestions_json = models.JSONField(blank=True, null=True)
    next_step_plan_json = models.JSONField(blank=True, null=True)
    report_markdown = models.TextField(blank=True)
    report_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'evaluation_report'


class GrowthSnapshot(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UserAccount, db_column='user_id', on_delete=models.DO_NOTHING)
    role = models.ForeignKey(JobRole, db_column='role_id', on_delete=models.DO_NOTHING)
    stat_date = models.DateField()
    total_sessions = models.IntegerField(default=0)
    avg_overall_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    avg_technical_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    avg_project_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    avg_scenario_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    avg_content_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    avg_logic_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    avg_communication_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    avg_job_match_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    avg_confidence_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    latest_summary = models.TextField(blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'growth_snapshot'
