@echo off
chcp 65001 >nul
echo ============================================================
echo    6. 性能测试 — P50/P95/P99 响应时间 + 并发负载
echo ============================================================
echo.
echo ⚠️  此测试需要后端服务运行在 http://127.0.0.1:8000
echo    请先用以下命令启动后端:
echo    cd backend ^&^& python manage.py runserver 0.0.0.0:8000
echo.
echo    获取 Token:
echo    curl -X POST http://127.0.0.1:8000/api/users/login/ ^
echo      -H "Content-Type: application/json" ^
echo      -d "{\"login_type\":\"email\",\"identifier\":\"YOUR_EMAIL\",\"password\":\"YOUR_PASS\"}"
echo.
echo 按任意键继续（确保服务已启动且已获取 Token）...
pause >nul
echo.

echo 6.1 并发负载测试（10并发 x 20次/端点，9个端点）...
echo ------------------------------------------------------------
cd /d "%~dp0..\.."
python tests/performance/load_test.py --concurrent 10 --requests 20
echo.

echo 6.2 API 响应时间基准（P50/P95/P99，5次重复）...
echo ------------------------------------------------------------
python test_response_time.py
echo.

echo ============================================================
echo    性能测试完成！
echo    性能标准:
echo      普通接口 P95 ^< 150ms
echo      LLM 接口 P95 ^< 30s
echo      错误率 ^< 1%%
echo ============================================================
pause
