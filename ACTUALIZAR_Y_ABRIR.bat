@echo off
setlocal EnableDelayedExpansion
title Evaluacion Docente USIL - Actualizar y Abrir
color 0B

:: ======================================================================
::  ACTUALIZAR_Y_ABRIR.bat
::  Un solo archivo para cualquier PC:
::   - Si es la PRIMERA vez (no existe el proyecto todavia): lo descarga
::     completo desde GitHub.
::   - Si YA existe: baja automaticamente la ultima actualizacion antes
::     de abrir la app.
::  Puedes copiar este .bat solo (sin el resto del proyecto) a una PC
::  nueva, ejecutarlo, y el se encarga de traer todo.
:: ======================================================================

set "REPO_URL=https://github.com/AtraccionDeTalento/RUBRICA.git"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo ========================================================
echo   EVALUACION DOCENTE USIL - ACTUALIZACION AUTOMATICA
echo ========================================================
echo.

:: --- 1) Verificar que Git este instalado -------------------------------
git --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] No tienes Git instalado en esta computadora.
    echo.
    echo Para que la actualizacion automatica funcione, instala Git desde:
    echo   https://git-scm.com/download/win
    echo.
    echo Luego vuelve a ejecutar este mismo archivo .bat
    echo.
    pause
    exit /b 1
)

:: --- 2) Detectar si ya estamos DENTRO del proyecto clonado -------------
if exist "%SCRIPT_DIR%\.git" if exist "%SCRIPT_DIR%\bot_evaluacion_docente\app_web.py" (
    set "PROJECT_DIR=%SCRIPT_DIR%"
    goto :actualizar
)

:: --- 3) Si no, buscar/crear una subcarpeta "RUBRICA" junto a este .bat -
set "PROJECT_DIR=%SCRIPT_DIR%\RUBRICA"

if exist "%PROJECT_DIR%\.git" (
    goto :actualizar
)

echo Primera vez en esta PC: descargando el proyecto completo...
echo   Origen: %REPO_URL%
echo   Destino: %PROJECT_DIR%
echo.

if exist "%PROJECT_DIR%" (
    echo [ERROR] Ya existe una carpeta "RUBRICA" aqui pero no es un repositorio Git valido.
    echo Renombra o elimina esa carpeta y vuelve a intentar.
    pause
    exit /b 1
)

git clone "%REPO_URL%" "%PROJECT_DIR%"
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] No se pudo descargar el proyecto. Revisa tu conexion a internet.
    pause
    exit /b 1
)

echo.
echo [OK] Proyecto descargado correctamente.
echo.
goto :dependencias

:actualizar
echo Proyecto encontrado en: %PROJECT_DIR%
echo Buscando actualizaciones en GitHub...
echo.
pushd "%PROJECT_DIR%"

git fetch origin main >nul 2>&1

for /f %%i in ('git rev-parse HEAD') do set LOCAL_REV=%%i
for /f %%i in ('git rev-parse origin/main') do set REMOTE_REV=%%i

if "!LOCAL_REV!"=="!REMOTE_REV!" (
    echo [OK] Ya tienes la ultima version. No hay actualizaciones pendientes.
) else (
    echo Hay una actualizacion nueva. Descargando cambios...
    git pull origin main
    if !errorlevel! neq 0 (
        color 0C
        echo [ERROR] No se pudo actualizar. Puede que tengas cambios locales sin guardar.
        echo Contacta al administrador del proyecto antes de continuar.
        popd
        pause
        exit /b 1
    )
    echo [OK] Proyecto actualizado a la ultima version.
)
popd
echo.

:dependencias
cd /d "%PROJECT_DIR%"

:: --- 4) Verificar dependencias de Electron (solo la 1ra vez o si faltan) -
if not exist "node_modules\electron" (
    echo Instalando motor grafico (Electron) por primera vez, esto puede tardar unos minutos...
    call npm install
    if %errorlevel% neq 0 (
        color 0C
        echo [ERROR] Fallo la instalacion de dependencias. Verifica que tengas Node.js instalado:
        echo   https://nodejs.org/
        pause
        exit /b 1
    )
)

:: --- 5) Abrir la aplicacion ---------------------------------------------
echo.
echo Abriendo Evaluacion Docente USIL...
call npm start

echo.
echo La aplicacion se cerro.
pause
