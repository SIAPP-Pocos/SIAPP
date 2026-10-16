@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title SIAPP

rem ============================================================================
rem  O SIAPP roda num ambiente Python isolado (.venv) dentro desta pasta.
rem
rem  Licoes das versoes anteriores (ver nota "SIAPP - Decisoes e Armadilhas"):
rem   - Neste computador, "python" no PATH aponta para a copia incompleta do
rem     MySQL Shell. Por isso NUNCA chamamos "python" puro nem activate.bat:
rem     sempre o caminho completo do executavel.
rem   - Em julho funcionou com o Python 3.13 da Microsoft Store (via "py").
rem   - Em agosto quebrou porque a pasta foi movida e o ambiente antigo ficou
rem     apontando para o caminho velho. Aqui, se o ambiente nao roda, e recriado.
rem ============================================================================

rem Protege contra variaveis que fazem qualquer Python procurar a biblioteca
rem no lugar errado (causa da mensagem "platform independent libraries").
set "PYTHONHOME="
set "PYTHONPATH="

set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PY%" goto criar_venv
"%VENV_PY%" -c "import sys" >nul 2>&1
if not errorlevel 1 goto rodar
echo  O ambiente .venv existente nao funciona mais (pasta movida?). Recriando...
rmdir /s /q "%VENV_DIR%"

:criar_venv
echo.
echo  Preparando o ambiente do SIAPP (so na primeira vez).
echo  Procurando um Python que funcione:
set "BASE_PY="

rem 1) Python Launcher (foi o caminho que funcionou em julho)
for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do call :testar "%%P"
rem 2) Instalacao do python.org para o usuario atual (ex.: Python312)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :testar "%%~fD\python.exe"
rem 3) Python da Microsoft Store (executavel real, nao o atalho)
for /d %%D in ("%LOCALAPPDATA%\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3*") do call :testar "%%~fD\python.exe"
rem 4) Qualquer outro python no PATH
for /f "delims=" %%P in ('where python 2^>nul') do call :testar "%%P"

if not defined BASE_PY goto sem_python

echo.
echo  Usando: %BASE_PY%
echo  Criando ambiente isolado em .venv ...
"%BASE_PY%" -m venv "%VENV_DIR%"
if errorlevel 1 goto falha_venv
if not exist "%VENV_PY%" goto falha_venv

:rodar
echo  Verificando dependencias...
"%VENV_PY%" -m pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 goto falha_pip

echo  Abrindo o SIAPP...
"%VENV_PY%" siapp.py %*
if errorlevel 1 pause
exit /b 0


rem ---------------------------------------------------------------------------
:testar
if defined BASE_PY exit /b 0
if not exist "%~1" exit /b 0
echo "%~1" | find /i "MySQL" >nul
if not errorlevel 1 goto testar_ignorado
rem atalho da Store que so abre a loja (fica direto em WindowsApps\)
if /i "%~dp1"=="%LOCALAPPDATA%\Microsoft\WindowsApps\" exit /b 0
"%~1" -c "import sys, venv, ensurepip; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 goto testar_falhou
echo    ok        %~1
set "BASE_PY=%~1"
exit /b 0
:testar_ignorado
echo    ignorado  %~1
exit /b 0
:testar_falhou
echo    falhou    %~1
exit /b 0

:sem_python
echo.
echo  [ERRO] Nenhum Python 3.9+ funcional foi encontrado.
echo  Copie a lista acima e envie para analise.
pause
exit /b 1

:falha_venv
echo.
echo  [ERRO] Nao foi possivel criar o ambiente .venv com:
echo         %BASE_PY%
echo  Copie as mensagens acima e envie para analise.
pause
exit /b 1

:falha_pip
echo.
echo  [ERRO] Falha ao instalar as dependencias.
echo  Se o erro mencionar "pythonnet", informe a versao do Python acima.
echo  Para recomecar do zero, apague a pasta .venv e rode de novo.
pause
exit /b 1
