@echo off
SETLOCAL EnableDelayedExpansion

SET py=python
cd %~dp0

%py% -c "import venv"

if %errorlevel% EQU 1 (
    echo venv Python package needs to be installed...
    %py% -m pip install venv
)

if not exist .venv (
    echo Setting up Python Virtual Environment...
    %py% -m venv .venv
    call .venv\Scripts\activate.bat
    %py% -m pip install --upgrade pip
    %py% -m pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

if %errorlevel% EQU 0 (
    %py% qvoterapp\qvoter.py %*
)

pause >nul