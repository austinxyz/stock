@echo off
chcp 65001 >nul
cd /d "%~dp0"
py analysis\tqqq_score.py
timeout /t 5 /nobreak >nul
py analysis\oklo_score.py
timeout /t 5 /nobreak >nul
py analysis\ebay_score.py
timeout /t 5 /nobreak >nul
py analysis\kweb_score.py
