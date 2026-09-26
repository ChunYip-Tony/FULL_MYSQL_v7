@echo off
cd /d "%~dp0"
if exist agent.pid for /f %%P in (agent.pid) do taskkill /PID %%P /T /F >nul 2>nul
del /q agent.pid >nul 2>nul
