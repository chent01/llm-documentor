@echo off
REM Medical Software Analysis Tool launcher for Windows

SETLOCAL

REM Set the Python executable path
SET PYTHON_EXE=python

REM Check if Python is available
%PYTHON_EXE% --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not available in the system PATH.
    echo Please install Python 3.8 or later and try again.
    pause
    exit /b 1
)

REM Get the directory where this batch file is located
SET SCRIPT_DIR=%~dp0

REM Launch the application
echo Launching Medical Software Analysis Tool...
%PYTHON_EXE% -m medical_analyzer %*

IF %ERRORLEVEL% NEQ 0 (
    echo Application exited with error code %ERRORLEVEL%
    pause
)

ENDLOCAL