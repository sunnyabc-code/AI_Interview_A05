@echo off
chcp 65001 >nul
echo ============================================================
echo    2. 单元测试详情
echo ============================================================
echo.
echo 4.1 LLM服务测试（22 项）...
cd /d "%~dp0..\..\backend"
python -m pytest interview_md/services/test_llm.py -v --tb=short
echo.
echo 4.2 用户认证与JWT（18 项）...
python -m pytest interview_md/test_authentication.py -v --tb=short
echo.
echo 4.3 面试评估逻辑（20 项）...
python -m pytest interview_md/services/test_orchestrator.py interview_md/services/test_session_service.py -v --tb=short
echo.
echo 4.6 语音异常分支（8 项）...
python -m pytest evaluations/tests.py -v --tb=short
echo.
echo 4.7 学习路径完成状态（8 项）...
python -m pytest learning/tests.py -v --tb=short
echo.
echo 4.8 统一响应封装 + API视图（36 项）...
python -m pytest interview_md/test_views.py -v --tb=short
echo.
echo 4.4 前端单元测试（16 项）...
cd /d "%~dp0..\..\frontend"
call npx vitest run --reporter=verbose
echo.
echo ============================================================
echo    单元测试全部完成（128 项）！
echo ============================================================
pause
