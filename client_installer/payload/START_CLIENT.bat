@echo off
cd /d "%~dp0"
start "FULL MYSQL v7" .venv\Scripts\pythonw.exe dashboard.py
