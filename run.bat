@echo off
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% == 0 goto :endofscript
echo "Errors encountered during execution. Exited with status: %errorlevel%"
python email_errors.py %errorlevel%

:endofscript
echo "Finished the backup"
