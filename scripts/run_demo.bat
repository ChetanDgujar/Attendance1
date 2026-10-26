@echo off
title Multimodal Attendance & Engagement Agent - Simulation Demo
echo ==============================================================================
echo Running Multimodal Attendance & Engagement Simulation...
echo ==============================================================================
cd /d "%~dp0\.."
python main.py demo --duration 30
pause
