@echo off
:: Forward to Build.bat preserving all arguments
call "%~dp0Build.bat" %*
exit /b %ERRORLEVEL%
