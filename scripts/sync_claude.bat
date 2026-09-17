@echo off
setlocal
python "%~dp0sync_claude.py" %*
if errorlevel 1 (
    echo Sync failed. Please check Python environment and Claude Desktop installation.
    exit /b 1
)
