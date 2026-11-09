Set WshShell = CreateObject("WScript.Shell")
pythonExe = "C:\Users\aaaaa\AppData\Local\Programs\Python\Python311\python.exe"
rootDir = "C:\Users\aaaaa\.gemini\antigravity\scratch\local-ai-suite"

' Run bot_assistant in hidden background (0 = hide window)
WshShell.Run """" & pythonExe & """ """ & rootDir & "\bot_assistant\bot.py""", 0, False

' Run bot_trader in hidden background (0 = hide window)
WshShell.Run """" & pythonExe & """ """ & rootDir & "\bot_trader\bot.py""", 0, False
