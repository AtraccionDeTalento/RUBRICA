@echo off
setlocal EnableDelayedExpansion
title Evaluacion Docente USIL - Actualizar y Abrir
color 0B

:: ======================================================================
::  ACTUALIZAR_Y_ABRIR.bat
::  Un solo archivo para cualquier PC, SIN necesitar Git instalado:
::   - Si es la PRIMERA vez (no existe el proyecto todavia): lo descarga
::     completo desde GitHub (como .zip, via PowerShell).
::   - Si YA existe: revisa si hay una version nueva y la descarga antes
::     de abrir la app.
::  Puedes copiar este .bat solo (sin el resto del proyecto) a una PC
::  nueva, ejecutarlo, y el se encarga de traer todo. Solo necesita
::  Windows 10/11 (con PowerShell, que ya viene instalado) y Node.js
::  para el motor grafico (Electron).
::
::  NOTA TECNICA: se evitan a proposito los bloques "if (...)" de varias
::  lineas cuando involucran rutas, porque si la carpeta donde se guarda
::  el .bat tiene un parentesis en el nombre (Windows los genera solo,
::  ej. "Descargas (1)"), ese ")" cierra el bloque antes de tiempo y todo
::  falla con errores raros de "ruta no encontrada". Por eso se usan
::  comparaciones de una sola linea con goto.
:: ======================================================================

set "REPO_SLUG=AtraccionDeTalento/RUBRICA"
set "REPO_BRANCH=main"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo ========================================================
echo   EVALUACION DOCENTE USIL - ACTUALIZACION AUTOMATICA
echo ========================================================
echo.
echo Carpeta de este script: %SCRIPT_DIR%
echo.

:: --- 1) Verificar que PowerShell este disponible (viene con Windows) ---
powershell -NoProfile -Command "exit 0" >nul 2>&1
if not errorlevel 1 goto :ps_ok
color 0C
echo [ERROR] No se encontro PowerShell en esta PC. Es necesario para
echo descargar la actualizacion desde GitHub.
pause
exit /b 1

:ps_ok
:: --- 2) Detectar si ya estamos DENTRO del proyecto ----------------------
if not exist "%SCRIPT_DIR%\bot_evaluacion_docente\app_web.py" goto :buscar_subcarpeta_rubrica
set "PROJECT_DIR=%SCRIPT_DIR%"
goto :actualizar

:buscar_subcarpeta_rubrica

:: --- 3) Si no, buscar/crear una subcarpeta "RUBRICA" junto a este .bat -
set "PROJECT_DIR=%SCRIPT_DIR%\RUBRICA"

if exist "%PROJECT_DIR%\bot_evaluacion_docente\app_web.py" goto :actualizar

:: --- 3bis) Preguntar si ya existe una instalacion en OTRA carpeta ------
:: No se puede asumir que el sistema siempre vive junto a este .bat o en
:: una subcarpeta "RUBRICA" -- por ejemplo, la version empaquetada de
:: Electron puede estar en una ruta como
:: "...\dist_electron\win-unpacked\" con un nombre y ubicacion distintos
:: en cada PC. Si no se encontro automaticamente, se pregunta antes de
:: asumir que hay que instalar una copia nueva (para no terminar con
:: instalaciones duplicadas sin querer).
echo No encontre el sistema instalado automaticamente en esta carpeta.
echo.
set "RUTA_EXISTENTE="
set /p "RUTA_EXISTENTE=¿Ya tienes el sistema instalado en OTRA carpeta de esta PC? Si es asi, pega aqui la ruta completa a esa carpeta y presiona Enter (o solo Enter para instalarlo aqui de cero): "

if "%RUTA_EXISTENTE%"=="" goto :verificar_rubrica_vacia

:: Quitar comillas si el usuario pego la ruta con comillas (comun al copiar desde el Explorador)
set "RUTA_EXISTENTE=%RUTA_EXISTENTE:"=%"

:: NOTA: comparaciones de una sola linea a proposito (sin bloques "if (...)"),
:: porque la ruta la escribe el usuario y podria traer parentesis (ej. una
:: carpeta "Nueva carpeta (2)"), lo que rompe los bloques de varias lineas.
if not exist "%RUTA_EXISTENTE%\bot_evaluacion_docente\app_web.py" goto :probar_carpeta_contenedora
set "PROJECT_DIR=%RUTA_EXISTENTE%"
echo.
echo [OK] Encontrado. Usare esta carpeta: %PROJECT_DIR%
echo.
goto :actualizar

:probar_carpeta_contenedora
:: Si nos dieron la ruta al .exe empaquetado en vez de la carpeta que lo
:: contiene (ej. "...\win-unpacked\Evaluacion Docente USIL.exe"), usar la
:: carpeta contenedora.
for %%F in ("%RUTA_EXISTENTE%") do set "RUTA_EXISTENTE_DIR=%%~dpF"
set "RUTA_EXISTENTE_DIR=%RUTA_EXISTENTE_DIR:~0,-1%"
if not exist "%RUTA_EXISTENTE_DIR%\bot_evaluacion_docente\app_web.py" goto :ruta_existente_invalida
set "PROJECT_DIR=%RUTA_EXISTENTE_DIR%"
echo.
echo [OK] Encontrado. Usare esta carpeta: %PROJECT_DIR%
echo.
goto :actualizar

:ruta_existente_invalida
color 0C
echo.
echo [ERROR] No encontre "bot_evaluacion_docente\app_web.py" en esa ruta:
echo   %RUTA_EXISTENTE%
echo Verifica la ruta (debe ser la carpeta que contiene "bot_evaluacion_docente",
echo no un acceso directo) y vuelve a ejecutar este archivo .bat.
pause
exit /b 1

:verificar_rubrica_vacia
if not exist "%PROJECT_DIR%" goto :descargar_primera_vez

:: Existe una carpeta "RUBRICA" pero no parece el proyecto (por ejemplo,
:: restos de una prueba anterior). La RENOMBRAMOS (no la borramos, por si
:: tiene algo util) y descargamos una copia limpia, para que este .bat
:: funcione solo en cualquier PC sin necesitar intervencion manual.
set "IS_EMPTY=1"
for /f %%x in ('dir /b "%PROJECT_DIR%" 2^>nul') do set "IS_EMPTY=0"
if "%IS_EMPTY%"=="1" goto :descargar_primera_vez

set "BACKUP_NAME=RUBRICA_backup_%RANDOM%"
echo [AVISO] Encontre una carpeta "RUBRICA" que no parece el proyecto valido.
echo Ruta: %PROJECT_DIR%
echo La voy a renombrar a "%BACKUP_NAME%" (por si tiene algo util) y descargar una copia nueva.
echo.

ren "%PROJECT_DIR%" "%BACKUP_NAME%"
if not errorlevel 1 goto :descargar_primera_vez
color 0C
echo [ERROR] No se pudo renombrar la carpeta "RUBRICA" existente.
echo Cierra cualquier programa que la este usando (Explorador, la app abierta, etc.) e intenta de nuevo.
pause
exit /b 1

:descargar_primera_vez
echo Primera vez en esta PC: descargando el proyecto completo desde GitHub...
echo   Destino: %PROJECT_DIR%
echo.
mkdir "%PROJECT_DIR%" >nul 2>&1
call :descargar_y_extraer "%PROJECT_DIR%"
if errorlevel 1 (
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
echo Revisando si hay una version nueva en GitHub...
echo.

set "LOCAL_SHA="
if not exist "%PROJECT_DIR%\.version_commit" goto :leer_local_sha_fin
set /p LOCAL_SHA=<"%PROJECT_DIR%\.version_commit"
:leer_local_sha_fin

set "REMOTE_SHA="
for /f "delims=" %%s in ('powershell -NoProfile -Command "try { (Invoke-RestMethod -Uri 'https://api.github.com/repos/%REPO_SLUG%/commits/%REPO_BRANCH%' -Headers @{'User-Agent'='RUBRICA-updater'}).sha } catch { 'ERROR' }"') do set "REMOTE_SHA=%%s"

if not "%REMOTE_SHA%"=="ERROR" if not "%REMOTE_SHA%"=="" goto :sha_ok
color 0C
echo [ERROR] No se pudo conectar con GitHub para revisar actualizaciones.
echo Verifica tu conexion a internet e intenta de nuevo.
pause
exit /b 1

:sha_ok
if "%LOCAL_SHA%"=="%REMOTE_SHA%" (
    echo [OK] Ya tienes la ultima version instalada.
    goto :mostrar_version
)

echo Hay una version nueva. Descargando...
call :descargar_y_extraer "%PROJECT_DIR%"
if errorlevel 1 (
    color 0C
    echo [ERROR] No se pudo descargar la actualizacion. Revisa tu conexion a internet.
    pause
    exit /b 1
)
echo.
echo [OK] Proyecto actualizado a la ultima version.
echo.
goto :mostrar_version

:mostrar_version
cd /d "%PROJECT_DIR%"

echo --------------------------------------------------------------
if not exist "%PROJECT_DIR%\.version_commit" goto :mostrar_version_desconocida
set /p VERSION_MOSTRAR=<"%PROJECT_DIR%\.version_commit"
echo   Version instalada (commit^): !VERSION_MOSTRAR:~0,7!
goto :mostrar_version_fin
:mostrar_version_desconocida
echo   Version instalada: desconocida
:mostrar_version_fin
echo --------------------------------------------------------------
echo.

:: --- 4) Verificar que Electron este REALMENTE instalado (no solo la carpeta) -
:: "node_modules\electron" puede existir pero sin el .exe real adentro si la
:: descarga/extraccion se corto a la mitad (pasa mas seguido de lo que parece:
:: antivirus, conexion inestable, etc.). Revisar solo que la carpeta exista no
:: alcanza -- el .bat creeria que ya esta todo listo y "npm start" truena sin
:: ninguna explicacion util para quien lo esta usando.
if exist "node_modules\electron\dist\electron.exe" goto :abrir_app

if not exist "node_modules\electron" goto :instalar_electron
echo [AVISO] La instalacion de Electron parece incompleta (falta electron.exe).
echo Voy a reinstalarla...
echo.
rmdir /s /q "node_modules\electron" >nul 2>&1

:instalar_electron
echo Instalando motor grafico (Electron), esto puede tardar unos minutos...
call npm install
if errorlevel 1 goto :error_instalacion

if exist "node_modules\electron\dist\electron.exe" goto :abrir_app

:error_instalacion
color 0C
echo.
echo [ERROR] No se pudo dejar Electron correctamente instalado.
echo.
echo Causas mas comunes: el antivirus bloquea/borra electron.exe recien
echo extraido, la conexion se corta a medio descargar, o falta espacio en
echo disco. Prueba desactivar el antivirus un momento y vuelve a ejecutar
echo este mismo archivo .bat.
echo.
echo Tambien confirma que tengas Node.js instalado:
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
exit /b 0

:: ========================================================================
::  Descarga el .zip del repo (rama main) y lo extrae dentro de %1,
::  sobrescribiendo los archivos que ya existan. No usa Git para nada,
::  solo PowerShell (Invoke-WebRequest + Expand-Archive, ambos incluidos
::  en Windows). Guarda el commit descargado en ".version_commit" dentro
::  del proyecto para poder comparar versiones la proxima vez.
:: ========================================================================
:descargar_y_extraer
set "DEST_DIR=%~1"
set "PS1_TEMP=%TEMP%\rubrica_actualizar_%RANDOM%.ps1"

:: Se genera un archivo .ps1 aparte en vez de meter todo el script de
:: PowerShell en una sola linea "-Command" con muchos "^" -- un bloque tan
:: largo corrompe el buffer de lectura de cmd.exe para el resto del .bat
:: (se vieron errores raros como "etlocal no reconocido" en TODO el
:: archivo, no solo en esta parte). Escribir un .ps1 real y llamarlo con
:: -File evita ese problema por completo.
(
echo param^([string]$Dest, [string]$RepoSlug, [string]$Branch^)
echo $zipUrl = "https://github.com/$RepoSlug/archive/refs/heads/$Branch.zip"
echo $tmpZip = Join-Path $env:TEMP ^('rubrica_update_' + [guid]::NewGuid^(^).ToString^(^) + '.zip'^)
echo $tmpDir = Join-Path $env:TEMP ^('rubrica_extract_' + [guid]::NewGuid^(^).ToString^(^)^)
echo try {
echo   try {
echo     Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip -UseBasicParsing -ErrorAction Stop
echo     Expand-Archive -Path $tmpZip -DestinationPath $tmpDir -Force -ErrorAction Stop
echo   } catch {
echo     Write-Output ^('ERROR-DESCARGA: ' + $_.Exception.Message^)
echo     exit 1
echo   }
echo   $srcFolder = Get-ChildItem -Path $tmpDir -Directory ^| Select-Object -First 1
echo   $archivos = Get-ChildItem -Path $srcFolder.FullName -Recurse -File
echo   $fallidos = @^(^)
echo   foreach ^($f in $archivos^) {
echo     $rel = $f.FullName.Substring^($srcFolder.FullName.Length + 1^)
echo     $destino = Join-Path $Dest $rel
echo     try {
echo       New-Item -ItemType Directory -Path ^(Split-Path $destino^) -Force -ErrorAction Stop ^| Out-Null
echo       if ^((Test-Path $destino^) -and ^((Get-Item $destino^).Attributes -band [IO.FileAttributes]::ReadOnly^)^) {
echo         ^(Get-Item $destino^).Attributes = ^(Get-Item $destino^).Attributes -band ^(-bnot [IO.FileAttributes]::ReadOnly^)
echo       }
echo       Copy-Item -Path $f.FullName -Destination $destino -Force -ErrorAction Stop
echo     } catch {
echo       $fallidos += ^('{0} ^({1}^)' -f $rel, $_.Exception.Message^)
echo       Write-Output ^('AVISO: no se pudo actualizar ' + $rel + ' - ' + $_.Exception.Message^)
echo     }
echo   }
echo   try {
echo     $commitInfo = Invoke-RestMethod -Uri ^("https://api.github.com/repos/$RepoSlug/commits/$Branch"^) -Headers @{'User-Agent'='RUBRICA-updater'} -ErrorAction Stop
echo     Set-Content -Path ^(Join-Path $Dest '.version_commit'^) -Value $commitInfo.sha -NoNewline -ErrorAction Stop
echo   } catch {
echo     Write-Output ^('AVISO: no se pudo guardar el marcador de version - ' + $_.Exception.Message^)
echo   }
echo   if ^($fallidos.Count -gt 0^) {
echo     Write-Output ^('RESUMEN: ' + $fallidos.Count + ' de ' + $archivos.Count + ' archivo^(s^) no se pudieron actualizar.'^)
echo     Write-Output 'Si esto se repite, revisa Windows Security ^> Proteccion contra ransomware ^> Acceso a carpetas controlado, o el antivirus de esta PC.'
echo   } else {
echo     Write-Output ^('OK: ' + $archivos.Count + ' archivo^(s^) actualizados.'^)
echo   }
echo   exit 0
echo } finally {
echo   Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue
echo   Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
echo }
) > "%PS1_TEMP%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_TEMP%" -Dest "%DEST_DIR%" -RepoSlug "%REPO_SLUG%" -Branch "%REPO_BRANCH%"
set "PS1_EXIT=%errorlevel%"
del "%PS1_TEMP%" >nul 2>&1
exit /b %PS1_EXIT%
