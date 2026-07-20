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
::
::  NOTA TECNICA: este script evita a proposito los bloques "if (...)"
::  de varias lineas cuando involucran rutas, porque si la carpeta
::  donde se guarda el .bat tiene un parentesis en el nombre (algo que
::  Windows genera solo, ej. "Descargas (1)" o "Nueva carpeta (2)"),
::  ese ")" cierra el bloque antes de tiempo y todo falla con errores
::  raros de "ruta no encontrada". Por eso se usan comparaciones de una
::  sola linea con goto.
:: ======================================================================

set "REPO_URL=https://github.com/AtraccionDeTalento/RUBRICA.git"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo ========================================================
echo   EVALUACION DOCENTE USIL - ACTUALIZACION AUTOMATICA
echo ========================================================
echo.
echo Carpeta de este script: %SCRIPT_DIR%
echo.

:: --- 1) Verificar que Git este instalado -------------------------------
git --version >nul 2>&1
if not errorlevel 1 goto :git_ok
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

:git_ok
:: --- 2) Detectar si ya estamos DENTRO del proyecto clonado -------------
if not exist "%SCRIPT_DIR%\.git" goto :buscar_subcarpeta
if not exist "%SCRIPT_DIR%\bot_evaluacion_docente\app_web.py" goto :buscar_subcarpeta
set "PROJECT_DIR=%SCRIPT_DIR%"
goto :actualizar

:buscar_subcarpeta
:: --- 3) Si no, buscar/crear una subcarpeta "RUBRICA" junto a este .bat -
set "PROJECT_DIR=%SCRIPT_DIR%\RUBRICA"

if exist "%PROJECT_DIR%\.git" goto :actualizar

if not exist "%PROJECT_DIR%" goto :clonar

:: Existe una carpeta "RUBRICA" pero no es un repositorio Git valido (por
:: ejemplo, restos de una prueba anterior). Si esta vacia, clonamos ahi
:: directo. Si tiene contenido, la RENOMBRAMOS (no la borramos, por si
:: tiene algo util) y clonamos una copia limpia, para que este .bat
:: funcione solo en cualquier PC sin necesitar intervencion manual.
set "IS_EMPTY=1"
for /f %%x in ('dir /b "%PROJECT_DIR%" 2^>nul') do set "IS_EMPTY=0"
if "%IS_EMPTY%"=="1" goto :clonar

set "BACKUP_NAME=RUBRICA_backup_%RANDOM%"
echo [AVISO] Encontre una carpeta "RUBRICA" que no es un repositorio Git valido.
echo Ruta: %PROJECT_DIR%
echo La voy a renombrar a "%BACKUP_NAME%" (por si tiene algo util) y descargar una copia nueva.
echo.

ren "%PROJECT_DIR%" "%BACKUP_NAME%"
if not errorlevel 1 goto :clonar
color 0C
echo [ERROR] No se pudo renombrar la carpeta "RUBRICA" existente.
echo Cierra cualquier programa que la este usando (Explorador, la app abierta, etc.) e intenta de nuevo.
pause
exit /b 1

:clonar
echo Primera vez en esta PC: descargando el proyecto completo...
echo   Origen: %REPO_URL%
echo   Destino: %PROJECT_DIR%
echo.

git clone "%REPO_URL%" "%PROJECT_DIR%"
if not errorlevel 1 goto :clon_ok
color 0C
echo [ERROR] No se pudo descargar el proyecto. Revisa tu conexion a internet.
pause
exit /b 1

:clon_ok
echo.
echo [OK] Proyecto descargado correctamente.
echo.
goto :mostrar_version

:actualizar
echo Proyecto encontrado en: %PROJECT_DIR%
echo Forzando sincronizacion con GitHub...
echo.
cd /d "%PROJECT_DIR%"

:: IMPORTANTE: no confiar en la salida de "git fetch" en silencio. Si
:: internet falla, un firewall bloquea github.com, o hay cualquier otro
:: problema, ESTO DEBE DETENER el proceso con un error visible en vez de
:: seguir como si ya estuviera actualizado (bug de una version anterior).
git fetch origin main
if not errorlevel 1 goto :fetch_ok
color 0C
echo.
echo [ERROR] No se pudo conectar con GitHub para revisar actualizaciones.
echo Verifica tu conexion a internet e intenta de nuevo.
cd /d "%SCRIPT_DIR%"
pause
exit /b 1

:fetch_ok
:: Forzar que la carpeta local quede EXACTAMENTE igual a GitHub,
:: descartando cualquier archivo modificado localmente. Esto evita que
:: un "git pull" normal se quede a medias por conflictos y el usuario
:: termine viendo una version vieja sin darse cuenta.
git reset --hard origin/main
if not errorlevel 1 goto :reset_ok
color 0C
echo [ERROR] No se pudo sincronizar con la version de GitHub.
cd /d "%SCRIPT_DIR%"
pause
exit /b 1

:reset_ok
git clean -fd >nul 2>&1
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
if exist "node_modules\electron" goto :abrir_app
echo Instalando motor grafico (Electron) por primera vez, esto puede tardar unos minutos...
call npm install
if not errorlevel 1 goto :abrir_app
color 0C
echo [ERROR] Fallo la instalacion de dependencias. Verifica que tengas Node.js instalado:
echo   https://nodejs.org/
pause
exit /b 1

:abrir_app
:: --- 5) Abrir la aplicacion ---------------------------------------------
echo.
echo Abriendo Evaluacion Docente USIL...
call npm start

echo.
echo La aplicacion se cerro.
pause
