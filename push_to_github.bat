@echo off
title Push Local AI Suite to GitHub
cd /d "%~dp0"
echo Pushing changes to https://github.com/AppMissia/local-ai-suite ...
"C:\Users\aaaaa\AppData\Local\Programs\Git\cmd\git.exe" push -u origin main
pause
