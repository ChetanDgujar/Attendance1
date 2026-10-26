@echo off
title Multimodal Attendance & Engagement Agent - Test Runner
echo ==============================================================================
echo Executing Verification Test Suite...
echo ==============================================================================
cd /d "%~dp0\.."
python main.py test
pause
