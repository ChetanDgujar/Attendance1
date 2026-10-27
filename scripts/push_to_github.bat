@echo off
title Push to GitHub - Attendance1
echo ==============================================================================
echo Pushing Multimodal Attendance & Engagement Agent to GitHub:
echo https://github.com/ChetanDgujar/Attendance1
echo ==============================================================================
cd /d "%~dp0\.."
git push -u origin main
echo ==============================================================================
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Successfully pushed to https://github.com/ChetanDgujar/Attendance1
) else (
    echo [NOTICE] If prompted above, complete the GitHub sign-in in your browser.
)
echo ==============================================================================
pause
