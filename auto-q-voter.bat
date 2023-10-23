@echo off
chdir c:\PATH_TO_THE_REPO\
if %errorlevel% EQU 1 (
    pause
) else (
    echo Settings file opened. Fill it and close when ready...
    notepad.exe plot.spec.json
    cls
    call q-voter.bat
    pause
)
