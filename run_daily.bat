@echo off
chcp 65001 >nul
cd /d "%~dp0"
py analysis\tqqq_score.py
py analysis\oklo_score.py
py analysis\ebay_score.py
