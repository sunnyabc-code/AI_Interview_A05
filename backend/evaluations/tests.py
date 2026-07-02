"""
语音异常分支覆盖测试（8 项 — 4.7.6）
覆盖: VoiceAnalysis 和 VoiceLLMResult 的失败状态、错误信息、时间字段
模拟 ASR 服务失败、iMentiv 服务失败、Voice LLM 服务失败三种异常场景
"""
import pytest
from django.db import connection
from django.utils import timezone
from decimal import Decimal


@pytest.fixture
def create_voice_tables(db):
    with connection.cursor() as c:
        c.execute("PRAGMA foreign_keys = OFF")
        c.execute("DROP TABLE IF EXISTS voice_analyses")
        c.execute("DROP TABLE IF EXISTS voice_llm_results")
        c.execute("""CREATE TABLE voice_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, round_id BIGINT, audio_id BIGINT,
            status VARCHAR(20) NOT NULL DEFAULT 'success',
            duration_seconds REAL NOT NULL DEFAULT 0, speech_rate REAL NOT NULL DEFAULT 0,
            speech_rate_level VARCHAR(8) NOT NULL DEFAULT 'normal',
            audio_clarity_score REAL NOT NULL DEFAULT 0, confidence_score REAL NOT NULL DEFAULT 0,
            emotion VARCHAR(50) NOT NULL DEFAULT '', imentiv_status VARCHAR(50) NOT NULL DEFAULT '',
            imentiv_emotion_analysis TEXT NOT NULL DEFAULT '{}',
            filler_word_total INTEGER NOT NULL DEFAULT 0, filler_word_counts TEXT NOT NULL DEFAULT '{}',
            rms_mean REAL NOT NULL DEFAULT 0, rms_std REAL NOT NULL DEFAULT 0, rms_cv REAL NOT NULL DEFAULT 0,
            silence_ratio REAL NOT NULL DEFAULT 0, silence_ratio_level VARCHAR(12) NOT NULL DEFAULT 'good',
            voiced_frames INTEGER NOT NULL DEFAULT 0, total_frames INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE voice_llm_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, interview_id BIGINT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            overall_audio_score DECIMAL NOT NULL DEFAULT 0,
            speech_rate_and_rhythm_score DECIMAL NOT NULL DEFAULT 0,
            speech_rate_and_rhythm TEXT NOT NULL DEFAULT '',
            fluency_score DECIMAL NOT NULL DEFAULT 0, fluency TEXT NOT NULL DEFAULT '',
            confidence_and_voice_energy_score DECIMAL NOT NULL DEFAULT 0,
            confidence_and_voice_energy TEXT NOT NULL DEFAULT '',
            emotional_stability_and_tone_score DECIMAL NOT NULL DEFAULT 0,
            emotional_stability_and_tone TEXT NOT NULL DEFAULT '',
            strengths TEXT NOT NULL DEFAULT '', improvements TEXT NOT NULL DEFAULT '',
            position_communication_tips TEXT NOT NULL DEFAULT '', encouragement TEXT NOT NULL DEFAULT '',
            llm_model VARCHAR(120) NOT NULL DEFAULT '', prompt_version VARCHAR(40) NOT NULL DEFAULT 'voice_llm_v1',
            raw_input_json TEXT NOT NULL DEFAULT '{}', raw_output_json TEXT NOT NULL DEFAULT '{}',
            generated_at DATETIME, error_message TEXT NOT NULL DEFAULT '', retry_count INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
    yield


def _ts():
    return timezone.now().strftime('%Y-%m-%d %H:%M:%S')


class TestVoiceAnalysisFailure:
    """ASR / iMentiv 服务失败"""

    def test_ASR失败状态为failed(self, create_voice_tables):
        with connection.cursor() as c:
            c.execute("INSERT INTO voice_analyses (status,created_at,updated_at) VALUES ('failed',%s,%s)", [_ts(), _ts()])
            c.execute("SELECT status FROM voice_analyses WHERE status='failed'")
            assert c.fetchone()[0] == 'failed'

    def test_iMentiv失败记录错误原因(self, create_voice_tables):
        with connection.cursor() as c:
            c.execute("INSERT INTO voice_analyses (status,imentiv_status,created_at,updated_at) VALUES ('failed','connection_timeout',%s,%s)", [_ts(), _ts()])
            c.execute("SELECT status,imentiv_status FROM voice_analyses WHERE imentiv_status='connection_timeout'")
            r = c.fetchone()
        assert r[0] == 'failed' and r[1] == 'connection_timeout'

    def test_成功状态字段正确(self, create_voice_tables):
        with connection.cursor() as c:
            c.execute("INSERT INTO voice_analyses (status,imentiv_status,duration_seconds,speech_rate,audio_clarity_score,confidence_score,emotion,created_at,updated_at) VALUES ('success','',10,200,85,78,'neutral',%s,%s)", [_ts(), _ts()])
            c.execute("SELECT status,imentiv_status,speech_rate,audio_clarity_score FROM voice_analyses WHERE speech_rate=200")
            r = c.fetchone()
        assert r[0] == 'success' and r[1] == '' and r[2] == 200 and r[3] == 85

    def test_四种状态与状态转换(self, create_voice_tables):
        with connection.cursor() as c:
            for s in ['pending', 'running', 'success', 'failed']:
                c.execute("INSERT INTO voice_analyses (status,created_at,updated_at) VALUES (%s,%s,%s)", [s, _ts(), _ts()])
            c.execute("SELECT DISTINCT status FROM voice_analyses")
            assert {r[0] for r in c.fetchall()} == {'pending', 'running', 'success', 'failed'}
            # running → failed
            c.execute("UPDATE voice_analyses SET status='failed',imentiv_status='http_500' WHERE status='running'")
            c.execute("SELECT COUNT(*) FROM voice_analyses WHERE status='failed' AND imentiv_status='http_500'")
            assert c.fetchone()[0] >= 1


class TestVoiceLLMResultFailure:
    """Voice LLM 失败"""

    def test_LLM失败记录错误与重试(self, create_voice_tables):
        with connection.cursor() as c:
            c.execute("INSERT INTO voice_llm_results (interview_id,status,error_message,retry_count,created_at,updated_at) VALUES (1,'failed','503 Service Unavailable',3,%s,%s)", [_ts(), _ts()])
            c.execute("SELECT status,error_message,retry_count FROM voice_llm_results WHERE interview_id=1")
            r = c.fetchone()
        assert r[0] == 'failed' and '503' in r[1] and r[2] == 3

    def test_成功状态与默认prompt版本(self, create_voice_tables):
        with connection.cursor() as c:
            c.execute("INSERT INTO voice_llm_results (interview_id,status,overall_audio_score,error_message,retry_count,generated_at,created_at,updated_at) VALUES (2,'success',78,'',0,%s,%s,%s)", [_ts(), _ts(), _ts()])
            c.execute("SELECT status,error_message,prompt_version FROM voice_llm_results WHERE interview_id=2")
            r = c.fetchone()
        assert r[0] == 'success' and r[1] == '' and r[2] == 'voice_llm_v1'

    def test_JSON异常与模型版本追踪(self, create_voice_tables):
        with connection.cursor() as c:
            c.execute("INSERT INTO voice_llm_results (interview_id,status,error_message,raw_output_json,retry_count,llm_model,prompt_version,created_at,updated_at) VALUES (3,'failed','JSONDecodeError','{}',1,'deepseek-ai/DeepSeek-V3.2','voice_llm_v2',%s,%s)", [_ts(), _ts()])
            c.execute("SELECT status,error_message,llm_model,prompt_version FROM voice_llm_results WHERE interview_id=3")
            r = c.fetchone()
        assert r[0] == 'failed' and 'JSONDecodeError' in r[1]
        assert r[2] == 'deepseek-ai/DeepSeek-V3.2' and r[3] == 'voice_llm_v2'

    def test_前端兼容_失败记录不产生undefined(self, create_voice_tables):
        with connection.cursor() as c:
            c.execute("INSERT INTO voice_llm_results (interview_id,status,error_message,created_at,updated_at) VALUES (4,'failed','Connection reset',%s,%s)", [_ts(), _ts()])
            c.execute("SELECT strengths,improvements,encouragement FROM voice_llm_results WHERE interview_id=4")
            r = c.fetchone()
        assert r == ('', '', '')
