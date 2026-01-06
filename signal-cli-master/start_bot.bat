@echo off
REM Signal Store Bot - Windows Batch Startup Script

echo Starting Signal Store Bot...

REM Set JAVA_HOME to Java 21
set "JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-21.0.9.10-hotspot"

REM Verify Java is accessible
java -version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Java not found. Please check JAVA_HOME.
    pause
    exit /b 1
)

echo JAVA_HOME set to: %JAVA_HOME%
echo.

REM Start the bot
python start_scheduled.py

pause



