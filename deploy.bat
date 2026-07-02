@echo off
chcp 65001 >nul
echo ============================================================
echo   AI模拟面试平台 — 一键部署到 122.9.42.110
echo ============================================================
echo.

REM === Step 1: Build Frontend ===
echo [1/3] 构建前端...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo 安装前端依赖...
    call npm install
)
call npm run build
if %ERRORLEVEL% neq 0 (
    echo 前端构建失败！
    pause
    exit /b 1
)
echo 前端构建完成 → dist/

REM === Step 2: Build & Start Docker ===
echo.
echo [2/3] 启动 Docker 容器...
cd /d "%~dp0"
docker-compose down
docker-compose up -d --build
if %ERRORLEVEL% neq 0 (
    echo Docker 启动失败！
    pause
    exit /b 1
)

REM === Step 3: Verify ===
echo.
echo [3/3] 验证部署...
timeout /t 5 /nobreak >nul
echo.
echo 后端健康检查:
curl -s http://122.9.42.110/api/positions/ 2>nul || echo   (请手动访问 http://122.9.42.110/api/positions/)
echo.
echo 前端页面:
curl -s -o NUL -w "%%{http_code}" http://122.9.42.110/ 2>nul || echo   (请手动访问 http://122.9.42.110/)
echo.

echo ============================================================
echo   部署完成！
echo   访问地址: http://122.9.42.110
echo   查看日志: docker-compose logs -f
echo ============================================================
pause
