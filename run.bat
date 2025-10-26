START python %~dp0\main.py
if %ERRORLEVEL% == 0 goto :endofscript
echo "Errors encountered during execution.  Exited with status: %errorlevel%"
START python %~dp0\email_errors.py %errorlevel%

:endofscript
echo "Finished the backup"