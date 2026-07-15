@echo off
color 0A
title Instalador - People Analytics USIL

cd /d "%~dp0"

echo ========================================================
echo   INSTALADOR Y REPARADOR DE DEPENDENCIAS - USIL
echo ========================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo.
    echo Presiona cualquier tecla para abrir la pagina de descarga...
    pause >nul
    start https://www.python.org/downloads/
    exit /b 1
)

echo [OK] Python detectado.
echo.
echo Buscando entornos virtuales antiguos o corruptos...

:: Borrar entornos que puedan estar corruptos
if exist ".venv" (
    echo [Borrando] Eliminando entorno .venv antiguo...
    rmdir /s /q ".venv"
)
if exist "bot_evaluacion_docente\.venv" (
    echo [Borrando] Eliminando entorno de subcarpeta...
    rmdir /s /q "bot_evaluacion_docente\.venv"
)

echo.
echo Creando un nuevo entorno virtual fresco (.venv)...
python -m venv .venv

if not exist ".venv\Scripts\activate.bat" (
    color 0C
    echo [ERROR] No se pudo crear el entorno virtual.
    pause
    exit /b 1
)

echo.
echo Instalando las dependencias del proyecto...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul

if exist "bot_evaluacion_docente\requirements.txt" (
    pip install -r bot_evaluacion_docente\requirements.txt
) else (
    echo [ERROR] No se encontro requirements.txt
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   INSTALACION / REPARACION COMPLETADA CON EXITO
echo ========================================================
echo.
echo Ya puedes cerrar esta ventana y ejecutar "INICIAR_SISTEMA.bat".
pause
