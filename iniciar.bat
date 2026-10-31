@echo off
rem Abre o SIAPP sem janela de console (quem trabalha e o SIAPP.vbs).
rem Para ver o console e cada passo, use "SIAPP - diagnostico.bat".
start "" wscript.exe //nologo "%~dp0SIAPP.vbs"
exit /b 0
