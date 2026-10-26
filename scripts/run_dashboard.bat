@echo off
title Multimodal Attendance & Engagement Agent - Dashboard
echo ==============================================================================
echo Launching Multimodal Attendance & Engagement Agent Dashboard...
echo ==============================================================================
cd /d "%~dp0\.."
python main.py dashboard --port 8080
pause
