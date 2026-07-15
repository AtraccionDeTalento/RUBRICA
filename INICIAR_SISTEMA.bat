@echo off
title Evaluacion Docente USIL - Servidor Activo

:: Fijar el directorio de trabajo donde este el script
cd /d "%~dp0"

echo ========================================================
echo   SISTEMA DE EVALUACION DOCENTE - PEOPLE ANALYTICS
echo ========================================================
echo.

:: Verificar que Python base exista
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] No tienes Python instalado en esta computadora o no esta en el PATH.
    pause
    exit /b 1
)

:: Definir cual Python usar
set PYTHON_EXE=python
if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=".venv\Scripts\python.exe"
) else if exist ".venv2\Scripts\python.exe" (
    set PYTHON_EXE=".venv2\Scripts\python.exe"
)

:: Validar si el entorno virtual esta roto (el error que te salio en la imagen)
%PYTHON_EXE% -c "print('OK')" >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR CRITICO] Tu entorno virtual actual esta roto. 
    echo Esto pasa cuando se actualiza o reinstala el Python de tu PC.
    echo.
    echo Para solucionarlo, CIERRA esta ventana y haz doble clic en:
    echo "INSTALAR_Y_REPARAR.bat"
    echo.
    pause
    exit /b 1
)

:: Moverse a la carpeta del bot para arrancar
if exist "bot_evaluacion_docente\app_web.py" (
    cd bot_evaluacion_docente
) else (
    color 0C
    echo [ERROR] No se encuentra la carpeta bot_evaluacion_docente.
    pause
    exit /b 1
)

echo Iniciando el motor de inteligencia artificial...
echo.
echo ======================================================================
echo   IMPORTANTE: NO CIERRES ESTA VENTANA NEGRA
echo   Si la cierras, el sistema web dejara de funcionar.
echo ======================================================================
echo.
echo Abriendo tu navegador web...

:: Abrir el navegador despues de 2 segundos
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

:: En Windows, como retrocedimos un nivel si el venv esta en la raiz, ajustamos:
if exist "..\.venv\Scripts\python.exe" (
    ..\.venv\Scripts\python.exe app_web.py
) else if exist "..\.venv2\Scripts\python.exe" (
    ..\.venv2\Scripts\python.exe app_web.py
) else (
    python app_web.py
)

echo.
echo El servidor se ha detenido.
pause
