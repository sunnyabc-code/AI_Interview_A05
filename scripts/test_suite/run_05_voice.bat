@echo off
chcp 65001 >nul
echo ============================================================
echo    5. 语音链路测试（3 正常 + 2 异常 = 5 项）
echo ============================================================
echo.
echo 5.1 TTS 语音合成测试...
echo ------------------------------------------------------------
cd /d "%~dp0..\..\backend"
python scripts/test_tts_and_asr.py
echo.

echo 5.2 语音异常分支单元测试（ASR/iMentiv/VoiceLLM 失败）...
echo ------------------------------------------------------------
cd /d "%~dp0..\..\backend"
python -m pytest evaluations/tests.py -v --tb=short
echo.

echo 5.3 语音分析集成测试（需后端服务运行）...
echo ------------------------------------------------------------
echo ⚠️  此步骤需后端服务运行 + 准备测试音频文件。
echo    请手动执行以下 API 调用（或用 Postman）:
echo.
echo    # 上传测试音频
echo    curl -X POST http://127.0.0.1:8000/api/evaluations/trigger-voice-analysis/ ^
echo      -H "Authorization: Bearer %%TOKEN%%" ^
echo      -H "Content-Type: application/json" ^
echo      -d "{\"audio_id\": 1, \"transcript\": \"测试转写文本\"}"
echo.
echo    # 触发 iMentiv 分析
echo    curl -X POST http://127.0.0.1:8000/api/evaluations/trigger-imentiv-analysis/ ^
echo      -H "Authorization: Bearer %%TOKEN%%" ^
echo      -H "Content-Type: application/json" ^
echo      -d "{\"audio_id\": 1}"
echo.
echo    # 查询分析结果
echo    curl http://127.0.0.1:8000/api/evaluations/imentiv-analysis/1/ ^
echo      -H "Authorization: Bearer %%TOKEN%%"
echo.

echo ============================================================
echo    语音链路测试完成！
echo ============================================================
pause
