@echo off
title Local AI Suite - Starting All Bots
cd /d "%~dp0"
echo Starting Bot 1: Personal Assistant...
start "Personal Assistant Bot" "C:\Users\aaaaa\AppData\Local\Programs\Python\Python311\python.exe" bot_assistant\bot.py
echo Starting Bot 2: Crypto & Smart Money Trader...
start "Trader Bot" "C:\Users\aaaaa\AppData\Local\Programs\Python\Python311\python.exe" bot_trader\bot.py
echo Both bots launched in background!
timeout /t 3
