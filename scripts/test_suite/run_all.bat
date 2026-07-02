@echo off
chcp 65001 >nul
echo ============================================================
echo    AI模拟面试平台 — 测试执行总览
echo ============================================================
echo.
echo [1/7] 自动化单元测试（112 后端 + 16 前端 = 128 项）...
echo ------------------------------------------------------------
cd /d "%~dp0..\..\backend"
python -m pytest interview_md/ evaluations/tests.py learning/tests.py -v --tb=short
echo.

echo [2/7] 集成测试 — API 冒烟测试（需后端服务运行在 8000 端口）...
echo ------------------------------------------------------------
echo ⚠️  请先启动后端: cd backend ^&^& python manage.py runserver 0.0.0.0:8000
echo.
echo 按任意键继续（确保服务已启动）...
pause >nul
cd /d "%~dp0..\.."
python tests/api/test_api_smoke.py --token "YOUR_JWT_TOKEN"
echo.

echo [3/7] 系统测试 — 人工场景清单...
echo ------------------------------------------------------------
cd /d "%~dp0..\.."
python scripts/test_suite/run_03_system_test.py
echo.

echo [4/7] AI智能体测试 — LLM 连通性与诊断...
echo ------------------------------------------------------------
cd /d "%~dp0..\..\backend"
python scripts/test_llm_connection.py
echo.
python scripts/test_llm_diagnostics.py
echo.

echo [5/7] 语音链路测试...
echo ------------------------------------------------------------
cd /d "%~dp0..\..\backend"
python scripts/test_tts_and_asr.py
echo.
python -m pytest evaluations/tests.py -v --tb=short
echo.

echo [6/7] 性能测试（需后端服务运行在 8000 端口）...
echo ------------------------------------------------------------
echo ⚠️  请确保后端服务已启动！
echo.
pause >nul
cd /d "%~dp0..\.."
python tests/performance/load_test.py --concurrent 10 --requests 20
echo.
python test_response_time.py
echo.

echo [7/7] 前端单元测试...
echo ------------------------------------------------------------
cd /d "%~dp0..\..\frontend"
call npx vitest run --reporter=verbose
echo.

echo ============================================================
echo    全部测试执行完成！
echo ============================================================
pause
