@echo off
chcp 65001 >nul
cd /d "%~dp0"
python analysis\tqqq_score.py >> tqqq_run.log 2>&1
