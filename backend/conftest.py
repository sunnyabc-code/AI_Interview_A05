"""
测试根目录 conftest —— 提供全局 fixture 和测试数据库配置。

由于项目使用 managed=False（表由 DBA 预建），测试需要在 SQLite
内存库中手动建表，保证单元测试不依赖外部 MySQL。

LLM 调用在单元测试中通过 monkeypatch 或 responses 库 mock，
避免依赖真实 API Key。如需真实调用，使用 --run-llm 标记。
"""

import os
from unittest.mock import patch
from decimal import Decimal

import pytest
from django.conf import settings
from django.db import connection
from django.utils import timezone

# ============================================================
# LLM 标记：默认跳过需要真实 API 的测试
# ============================================================

def pytest_addoption(parser):
    parser.addoption(
        '--run-llm', action='store_true', default=False,
        help='运行需要真实 LLM API 的测试（需要 .env 中配置 API Key）',
    )


def pytest_configure(config):
    config.addinivalue_line('markers', 'llm: 需要 LLM API Key 的测试（默认跳过，用 --run-llm 启用）')


def pytest_collection_modifyitems(config, items):
    if config.getoption('--run-llm'):
        return
    skip_llm = pytest.mark.skip(reason='需要 --run-llm 选项且配置 API Key')
    for item in items:
        if item.get_closest_marker('llm'):
            item.add_marker(skip_llm)

# ============================================================
# 建表 fixture —— 为 managed=False 的模型手动建表
# ============================================================

CREATE_INTERVIEW_MD_TABLES = """..."""  # Will be set below


@pytest.fixture(scope='function')
def create_tables(db):
    """在每个测试函数执行前建表"""
    with connection.cursor() as cursor:
        for stmt in _get_create_sql().split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                cursor.execute(stmt)
    yield


def _get_create_sql():
    """返回建表 SQL（避免 cluttering the conftest namespace）"""
    return """
CREATE TABLE IF NOT EXISTS user_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(64) NOT NULL,
    email VARCHAR(128), phone VARCHAR(32), password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) DEFAULT 'student', status SMALLINT DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS job_role (
    id INTEGER PRIMARY KEY AUTOINCREMENT, code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(64) NOT NULL, description TEXT, is_active SMALLINT DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS difficulty_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT, difficulty_code VARCHAR(16) UNIQUE NOT NULL,
    difficulty_name VARCHAR(32) NOT NULL, answer_time_seconds INTEGER DEFAULT 120,
    technical_chain_count INTEGER DEFAULT 1, project_chain_count INTEGER DEFAULT 1,
    scenario_chain_count INTEGER DEFAULT 1, technical_max_followup_depth INTEGER DEFAULT 2,
    project_max_followup_depth INTEGER DEFAULT 2, scenario_max_followup_depth INTEGER DEFAULT 2,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS role_interview_strategy (
    id INTEGER PRIMARY KEY AUTOINCREMENT, role_id BIGINT NOT NULL REFERENCES job_role(id),
    difficulty_code VARCHAR(16) NOT NULL, technical_weight DECIMAL(6,4) DEFAULT 0.34,
    project_weight DECIMAL(6,4) DEFAULT 0.33, scenario_weight DECIMAL(6,4) DEFAULT 0.33,
    technical_chain_strategy_json TEXT, project_chain_strategy_json TEXT,
    scenario_chain_strategy_json TEXT, rubric_version VARCHAR(32), prompt_version VARCHAR(32),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS question_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT, role_id BIGINT NOT NULL REFERENCES job_role(id),
    aspect_type VARCHAR(16) NOT NULL, chain_anchor_type VARCHAR(32) NOT NULL,
    chain_anchor_code VARCHAR(64), topic VARCHAR(128), subtopic VARCHAR(128),
    difficulty VARCHAR(16), question_text TEXT NOT NULL, key_points_json TEXT,
    ideal_answer TEXT, followup_hints_json TEXT, source_type VARCHAR(32),
    is_active SMALLINT DEFAULT 1, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL);
CREATE TABLE IF NOT EXISTS interview_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id BIGINT NOT NULL REFERENCES user_account(id),
    role_id BIGINT NOT NULL REFERENCES job_role(id), resume_id BIGINT,
    difficulty VARCHAR(16) NOT NULL, difficulty_config_id BIGINT NOT NULL REFERENCES difficulty_config(id),
    mode VARCHAR(16) DEFAULT 'text', session_prompt_snapshot TEXT, context_snapshot TEXT,
    strategy_snapshot_json TEXT, status VARCHAR(16) NOT NULL, total_chain_count INTEGER DEFAULT 0,
    completed_chain_count INTEGER DEFAULT 0, started_at DATETIME, finished_at DATETIME,
    overall_score DECIMAL(5,2), summary TEXT, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL);
CREATE TABLE IF NOT EXISTS session_aspect (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id BIGINT NOT NULL REFERENCES interview_session(id),
    aspect_type VARCHAR(16) NOT NULL, aspect_name VARCHAR(64) NOT NULL,
    aspect_weight DECIMAL(6,4) NOT NULL, planned_chain_count INTEGER NOT NULL,
    completed_chain_count INTEGER DEFAULT 0, aspect_score DECIMAL(5,2),
    dimension_scores_json TEXT, status VARCHAR(16) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS interview_chain (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id BIGINT NOT NULL REFERENCES interview_session(id),
    session_aspect_id BIGINT NOT NULL REFERENCES session_aspect(id), chain_no INTEGER NOT NULL,
    chain_no_in_aspect INTEGER NOT NULL, aspect_type VARCHAR(16) NOT NULL,
    anchor_type VARCHAR(32) NOT NULL, anchor_id BIGINT, anchor_code VARCHAR(64),
    anchor_title VARCHAR(255), project_name VARCHAR(255), topic VARCHAR(128),
    subtopic VARCHAR(128), max_followup_depth INTEGER NOT NULL,
    current_followup_depth INTEGER DEFAULT 0, round_count INTEGER DEFAULT 0,
    chain_weight DECIMAL(6,4) DEFAULT 1, status VARCHAR(16) NOT NULL,
    started_at DATETIME, finished_at DATETIME, chain_score DECIMAL(5,2),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS interview_round (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id BIGINT NOT NULL REFERENCES interview_session(id),
    chain_id BIGINT NOT NULL REFERENCES interview_chain(id), global_round_no INTEGER NOT NULL,
    round_no_in_chain INTEGER NOT NULL, parent_round_id BIGINT REFERENCES interview_round(id),
    is_followup SMALLINT DEFAULT 0, question_text TEXT NOT NULL,
    question_source VARCHAR(32), candidate_answer_text TEXT, answer_audio_url VARCHAR(255),
    asr_text TEXT, answer_time_limit_seconds INTEGER, record_start_at DATETIME,
    record_end_at DATETIME, record_end_reason VARCHAR(32), uncovered_points_json TEXT,
    followup_needed SMALLINT, followup_reason TEXT, decision_json TEXT,
    asked_at DATETIME, answered_at DATETIME, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL);
CREATE TABLE IF NOT EXISTS chain_evaluation (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id BIGINT NOT NULL REFERENCES interview_session(id),
    chain_id BIGINT NOT NULL REFERENCES interview_chain(id), aspect_type VARCHAR(16) NOT NULL,
    rubric_id BIGINT, evaluation_mode VARCHAR(32) DEFAULT 'llm_only',
    grounding_status VARCHAR(32) DEFAULT 'not_used', retrieval_hit_count INTEGER DEFAULT 0,
    content_score DECIMAL(5,2), logic_score DECIMAL(5,2), communication_score DECIMAL(5,2),
    job_match_score DECIMAL(5,2), confidence_score DECIMAL(5,2), overall_score DECIMAL(5,2),
    strengths_json TEXT, weaknesses_json TEXT, suggestions_json TEXT, llm_result_json TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS evaluation_report (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id BIGINT NOT NULL REFERENCES interview_session(id),
    generated_by VARCHAR(32) NOT NULL, overall_score DECIMAL(5,2), technical_score DECIMAL(5,2),
    project_score DECIMAL(5,2), scenario_score DECIMAL(5,2), content_score DECIMAL(5,2),
    logic_score DECIMAL(5,2), communication_score DECIMAL(5,2), job_match_score DECIMAL(5,2),
    confidence_score DECIMAL(5,2), aspect_scores_json TEXT, dimension_scores_json TEXT,
    strengths_json TEXT, weaknesses_json TEXT, improvement_suggestions_json TEXT,
    next_step_plan_json TEXT, report_markdown TEXT, report_json TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS growth_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id BIGINT NOT NULL REFERENCES user_account(id),
    role_id BIGINT NOT NULL REFERENCES job_role(id), stat_date DATE NOT NULL,
    total_sessions INTEGER DEFAULT 0, avg_overall_score DECIMAL(5,2),
    avg_technical_score DECIMAL(5,2), avg_project_score DECIMAL(5,2),
    avg_scenario_score DECIMAL(5,2), avg_content_score DECIMAL(5,2),
    avg_logic_score DECIMAL(5,2), avg_communication_score DECIMAL(5,2),
    avg_job_match_score DECIMAL(5,2), avg_confidence_score DECIMAL(5,2),
    latest_summary TEXT, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL);
CREATE TABLE IF NOT EXISTS speech_metric (
    id INTEGER PRIMARY KEY AUTOINCREMENT, round_id BIGINT NOT NULL REFERENCES interview_round(id),
    audio_duration_ms INTEGER, speaking_rate_wpm DECIMAL(8,2), pause_count INTEGER,
    avg_pause_ms INTEGER, clarity_score DECIMAL(5,2), confidence_score DECIMAL(5,2),
    emotion_label VARCHAR(32), raw_features TEXT, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL);
CREATE TABLE IF NOT EXISTS student_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id BIGINT NOT NULL REFERENCES user_account(id),
    school VARCHAR(128), major VARCHAR(128), grade VARCHAR(32), target_role_code VARCHAR(64),
    self_intro TEXT, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL);
"""

# ============================================================
# 常用数据 fixture
# ============================================================

@pytest.fixture
def now():
    return timezone.now()


@pytest.fixture
def make_user(create_tables, now):
    """创建测试用户的工厂函数"""
    from interview_md.models import UserAccount
    from django.contrib.auth.hashers import make_password

    def _make(username='testuser', password='testpass123', **kwargs):
        u = UserAccount(
            username=username,
            password_hash=make_password(password),
            email=kwargs.get('email', 'test@example.com'),
            phone=kwargs.get('phone', ''),
            role=kwargs.get('role', 'student'),
            status=kwargs.get('status', 1),
            created_at=now, updated_at=now,
        )
        u.save()
        return u
    return _make


@pytest.fixture
def make_role(create_tables, now):
    """创建测试岗位的工厂函数"""
    from interview_md.models import JobRole

    def _make(code='java_backend', name='Java后端工程师', **kwargs):
        r = JobRole(
            code=code, name=name,
            description=kwargs.get('description', ''),
            is_active=kwargs.get('is_active', 1),
            created_at=now, updated_at=now,
        )
        r.save()
        return r
    return _make


@pytest.fixture
def make_difficulty(create_tables, now):
    """创建测试难度配置的工厂函数"""
    from interview_md.models import DifficultyConfig

    def _make(code='easy', name='初级', **kwargs):
        d = DifficultyConfig(
            difficulty_code=code, difficulty_name=name,
            answer_time_seconds=kwargs.get('answer_time_seconds', 120),
            technical_chain_count=kwargs.get('technical_chain_count', 1),
            project_chain_count=kwargs.get('project_chain_count', 1),
            scenario_chain_count=kwargs.get('scenario_chain_count', 1),
            technical_max_followup_depth=kwargs.get('technical_max_followup_depth', 2),
            project_max_followup_depth=kwargs.get('project_max_followup_depth', 2),
            scenario_max_followup_depth=kwargs.get('scenario_max_followup_depth', 2),
            created_at=now, updated_at=now,
        )
        d.save()
        return d
    return _make


@pytest.fixture
def make_strategy(create_tables, now):
    """创建测试面试策略的工厂函数"""
    from interview_md.models import RoleInterviewStrategy

    def _make(role_id, difficulty_code='easy', **kwargs):
        s = RoleInterviewStrategy(
            role_id=role_id, difficulty_code=difficulty_code,
            technical_weight=kwargs.get('technical_weight', Decimal('0.34')),
            project_weight=kwargs.get('project_weight', Decimal('0.33')),
            scenario_weight=kwargs.get('scenario_weight', Decimal('0.33')),
            created_at=now, updated_at=now,
        )
        s.save()
        return s
    return _make


@pytest.fixture
def make_question(create_tables, now):
    """创建测试题目的工厂函数"""
    from interview_md.models import QuestionBank

    def _make(role_id, aspect='technical', **kwargs):
        q = QuestionBank(
            role_id=role_id, aspect_type=aspect,
            chain_anchor_type=kwargs.get('chain_anchor_type', 'knowledge_point'),
            chain_anchor_code=kwargs.get('chain_anchor_code', f'{aspect}_1'),
            topic=kwargs.get('topic', '测试题目'),
            subtopic=kwargs.get('subtopic', ''),
            difficulty=kwargs.get('difficulty', 'easy'),
            question_text=kwargs.get('question_text', '请描述你在项目中使用的技术栈？'),
            key_points_json=kwargs.get('key_points_json', None),
            ideal_answer=kwargs.get('ideal_answer', ''),
            followup_hints_json=kwargs.get('followup_hints_json', None),
            source_type=kwargs.get('source_type', 'seed'),
            is_active=kwargs.get('is_active', 1),
            created_at=now, updated_at=now,
        )
        q.save()
        return q
    return _make


# ============================================================
# Mock LLM fixture
# ============================================================

@pytest.fixture
def mock_llm():
    with patch('interview_md.services.llm.call_llm') as mock:
        yield mock

@pytest.fixture
def mock_llm_no_followup(mock_llm):
    mock_llm.return_value = '{"need_followup": false, "followup_question": ""}'
    return mock_llm

@pytest.fixture
def mock_llm_followup(mock_llm):
    mock_llm.return_value = '{"need_followup": true, "followup_question": "请详细说明你在这个项目中遇到的最大技术难点是什么？"}'
    return mock_llm

@pytest.fixture
def mock_llm_evaluation(mock_llm):
    mock_llm.return_value = '''{"content_score":82,"logic_score":78,"communication_score":85,"job_match_score":80,"confidence_score":75,"overall_score":80,"strengths":["回答结构清晰"],"weaknesses":["细节不足"],"suggestions":["用STAR法则"]}'''
    return mock_llm
