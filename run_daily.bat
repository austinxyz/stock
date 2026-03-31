@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [%date% %time%] 开始每日分析... >> daily_run.log
python tqqq_score.py >> daily_run.log 2>&1
python oklo_score.py >> daily_run.log 2>&1
echo [%date% %time%] 完成 >> daily_run.log
