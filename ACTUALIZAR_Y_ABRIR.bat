@echo off
setlocal EnableDelayedExpansion
title Evaluacion Docente USIL - Actualizar y Abrir
color 0B

:: ======================================================================
::  ACTUALIZAR_Y_ABRIR.bat
::  Un solo archivo para cualquier PC:
::   - Si es la PRIMERA vez (no existe el proyecto todavia): lo descarga
::     completo desde GitHub.
::   - Si YA existe: fuerza que quede IDENTICO a GitHub (descarta
::     cualquier diferencia local) antes de abrir la app.
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
goto :mostrar_version

:actualizar
echo Proyecto encontrado en: %PROJECT_DIR%
echo Forzando sincronizacion con GitHub...
echo.
pushd "%PROJECT_DIR%"

:: IMPORTANTE: no confiar en la salida de "git fetch" en silencio. Si
:: internet falla, un firewall bloquea github.com, o hay cualquier otro
:: problema, ESTO DEBE DETENER el proceso con un error visible en vez de
:: seguir como si ya estuviera actualizado (ese era el bug anterior).
git fetch origin main
if !errorlevel! neq 0 (
    color 0C
    echo.
    echo [ERROR] No se pudo conectar con GitHub para revisar actualizaciones.
    echo Verifica tu conexion a internet e intenta de nuevo.
    popd
    pause
    exit /b 1
)

:: Forzar que la carpeta local quede EXACTAMENTE igual a GitHub,
:: descartando cualquier archivo modificado localmente. Esto evita que
:: un "git pull" normal se quede a medias por conflictos y el usuario
:: termine viendo una version vieja sin darse cuenta.
git reset --hard origin/main
if !errorlevel! neq 0 (
    color 0C
    echo [ERROR] No se pudo sincronizar con la version de GitHub.
    popd
    pause
    exit /b 1
)
git clean -fd >nul 2>&1

popd
echo.
echo [OK] Proyecto sincronizado con GitHub.
echo.

:mostrar_version
cd /d "%PROJECT_DIR%"

:: --- Mostrar version instalada, para poder confirmar a simple vista ---
echo --------------------------------------------------------------
for /f "delims=" %%i in ('git log -1 --date^=format:"%%Y-%%m-%%d %%H:%%M" --pretty^=format:"%%h  %%ad  %%s"') do echo   Version instalada: %%i
echo --------------------------------------------------------------
echo.

:: --- 4) Verificar dependencias de Electron (solo la 1ra vez o si faltan) -
if not exist "node_modules\electron" (
    echo Instalando motor grafico ^(Electron^) por primera vez, esto puede tardar unos minutos...
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
