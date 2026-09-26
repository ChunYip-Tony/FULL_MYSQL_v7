@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -c "from api_client import test_api; import json; print(json.dumps(test_api(),indent=2,default=str))"
pause
