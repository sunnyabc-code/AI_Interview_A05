@echo off
chcp 65001 >nul
echo ============================================================
echo    3. 集成测试 — 14 个核心 API 端点
echo ============================================================
echo.
echo ⚠️  此测试需要后端服务运行在 http://127.0.0.1:8000
echo.
echo 启动后端: cd backend ^&^& python manage.py runserver 0.0.0.0:8000
echo 获取 Token: POST http://127.0.0.1:8000/api/users/login/
echo   或 POST http://127.0.0.1:8000/api/chain/auth/login/
echo.
echo 按任意键继续（确保服务已启动且获得 Token）...
pause >nul
echo.
echo 执行 API 冒烟测试...
cd /d "%~dp0..\.."
python tests/api/test_api_smoke.py
echo.
echo ============================================================
echo    集成测试完成！
echo ============================================================
pause
