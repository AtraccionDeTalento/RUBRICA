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
::  PLANES DE CONTINGENCIA incluidos (para que "descargar y funcionar"
::  tenga la mayor cantidad de caminos posibles en PCs viejas/raras):
::   1. Descarga: Invoke-WebRequest (3 intentos) -> WebClient -> curl.exe
::   2. Extraccion: Expand-Archive -> tar.exe (incluido desde Win10 1803)
::   3. TLS 1.2 forzado (PCs viejas a veces traen TLS 1.0 por defecto y
::      GitHub ya no lo acepta, lo que se ve como fallos raros de red)
::   4. Copia archivo por archivo: si UNO falla (bloqueado, antivirus,
::      etc.) se avisa cual y se sigue con el resto, no se aborta todo
::   5. Si el .zip no se puede ni descargar/extraer/copiar de ninguna
::      forma, y hay Git instalado en la PC, se intenta "git clone/pull"
::      como ultimo recurso (Git no es requisito, pero si esta, se usa)
::   6. Aviso temprano si "Acceso a carpetas controlado" de Windows
::      Defender esta activo (causa mas comun de "Acceso denegado")
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
:: --- 1bis) Aviso temprano si "Acceso a carpetas controlado" esta activo -
:: Es la causa mas comun de "Acceso denegado" al actualizar. Se avisa
:: ANTES de intentar nada, para que si falla mas adelante ya se sepa por
:: donde empezar a mirar (no bloquea la ejecucion, es solo informativo).
for /f "delims=" %%c in ('powershell -NoProfile -Command "try { if ((Get-MpPreference -ErrorAction Stop).EnableControlledFolderAccess -eq 1) { 'ACTIVO' } else { 'INACTIVO' } } catch { 'DESCONOCIDO' }" 2^>nul') do set "CFA_ESTADO=%%c"
if "%CFA_ESTADO%"=="ACTIVO" (
    echo [AVISO] "Acceso a carpetas controlado" de Windows Defender esta ACTIVO en esta PC.
    echo Si la actualizacion falla con "Acceso denegado", esta es la causa mas probable.
    echo Mas abajo, si algo falla, te doy el comando exacto para arreglarlo.
    echo.
)

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
if not errorlevel 1 goto :descarga_inicial_ok

:: Plan de contingencia final: si el .zip fallo por completo y esta PC
:: tiene Git instalado, se intenta clonar por ese medio antes de rendirse.
call :intentar_git_fallback "%PROJECT_DIR%" "clone"
if not errorlevel 1 goto :descarga_inicial_ok

color 0C
echo [ERROR] No se pudo descargar el proyecto por ningun metodo disponible.
echo Revisa tu conexion a internet, o si el antivirus esta bloqueando la descarga.
pause
exit /b 1

:descarga_inicial_ok
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
for /f "delims=" %%s in ('powershell -NoProfile -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor 3072; (Invoke-RestMethod -Uri 'https://api.github.com/repos/%REPO_SLUG%/commits/%REPO_BRANCH%' -Headers @{'User-Agent'='RUBRICA-updater'}).sha } catch { 'ERROR' }"') do set "REMOTE_SHA=%%s"

if not "%REMOTE_SHA%"=="ERROR" if not "%REMOTE_SHA%"=="" goto :sha_ok
color 0C
echo [ERROR] No se pudo conectar con GitHub para revisar actualizaciones.
echo Verifica tu conexion a internet e intenta de nuevo.
echo Si esto se repite pero la app ya funciona, puedes omitir la actualizacion
echo cerrando esta ventana y abriendo la app directamente.
pause
exit /b 1

:sha_ok
if "%LOCAL_SHA%"=="%REMOTE_SHA%" (
    echo [OK] Ya tienes la ultima version instalada.
    goto :mostrar_version
)

echo Hay una version nueva. Descargando...
call :descargar_y_extraer "%PROJECT_DIR%"
if not errorlevel 1 goto :actualizacion_ok

:: Plan de contingencia final: intentar Git si esta disponible.
call :intentar_git_fallback "%PROJECT_DIR%" "pull"
if not errorlevel 1 goto :actualizacion_ok

color 0C
echo [ERROR] No se pudo descargar la actualizacion por ningun metodo disponible.
echo La app se abrira igual con la version que ya tenias instalada.
echo.
pause
goto :mostrar_version

:actualizacion_ok
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
echo Causas mas comunes y como resolverlas:
echo   1. El antivirus bloquea/borra electron.exe recien extraido.
echo      Prueba agregando esta carpeta como excepcion (como Administrador,
echo      en PowerShell^):
echo        Add-MpPreference -ExclusionPath "%PROJECT_DIR%"
echo   2. La conexion se corta a medio descargar. Vuelve a ejecutar este
echo      mismo archivo .bat (reintenta automaticamente^).
echo   3. Falta espacio en disco.
echo   4. No tienes Node.js instalado:
echo        https://nodejs.org/
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
::  Plan de contingencia final: si el metodo normal (.zip por HTTPS) fallo
::  por completo, y esta PC tiene Git instalado (no es requisito, pero si
::  esta, se aprovecha), se intenta clonar/actualizar por ese medio.
::  %1 = carpeta destino, %2 = "clone" o "pull"
:: ========================================================================
:intentar_git_fallback
set "GIT_DEST=%~1"
set "GIT_MODO=%~2"
git --version >nul 2>&1
if errorlevel 1 exit /b 1

echo.
echo [AVISO] La descarga normal fallo. Se detecto Git instalado en esta PC,
echo intentando por ese medio como ultimo recurso...
echo.

if /i not "%GIT_MODO%"=="clone" goto :git_pull_modo
rmdir /s /q "%GIT_DEST%" >nul 2>&1
git clone "https://github.com/%REPO_SLUG%.git" "%GIT_DEST%"
exit /b %errorlevel%

:git_pull_modo
pushd "%GIT_DEST%"
if not exist ".git" goto :git_pull_sin_git
git fetch origin %REPO_BRANCH%
if errorlevel 1 goto :git_pull_fallo
git reset --hard origin/%REPO_BRANCH%
set "GIT_RESULT=%errorlevel%"
goto :git_pull_fin
:git_pull_fallo
set "GIT_RESULT=1"
goto :git_pull_fin
:git_pull_sin_git
set "GIT_RESULT=1"
:git_pull_fin
popd
exit /b %GIT_RESULT%

:: ========================================================================
::  Descarga el .zip del repo (rama main) y lo extrae dentro de %1,
::  sobrescribiendo los archivos que ya existan. No requiere Git.
::  Genera un .ps1 temporal (en vez de una sola linea "-Command" con
::  muchos "^") porque un bloque tan largo corrompe el buffer de lectura
::  de cmd.exe para el resto del .bat.
:: ========================================================================
:descargar_y_extraer
set "DEST_DIR=%~1"
set "PS1_TEMP=%TEMP%\rubrica_actualizar_%RANDOM%.ps1"

echo param([string]$Dest, [string]$RepoSlug, [string]$Branch) > "%PS1_TEMP%"
echo try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor 3072 } catch {} >> "%PS1_TEMP%"
echo $zipUrl = "https://github.com/$RepoSlug/archive/refs/heads/$Branch.zip" >> "%PS1_TEMP%"
echo $tmpZip = Join-Path $env:TEMP ('rubrica_update_' + [guid]::NewGuid().ToString() + '.zip') >> "%PS1_TEMP%"
echo $tmpDir = Join-Path $env:TEMP ('rubrica_extract_' + [guid]::NewGuid().ToString()) >> "%PS1_TEMP%"
echo # --- Plan de contingencia 1: descarga por 3 metodos distintos --- >> "%PS1_TEMP%"
echo $descargaOk = $false >> "%PS1_TEMP%"
echo $erroresDescarga = @() >> "%PS1_TEMP%"
echo for ($intento = 1; $intento -le 3; $intento++) { >> "%PS1_TEMP%"
echo   try { >> "%PS1_TEMP%"
echo     Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip -UseBasicParsing -ErrorAction Stop >> "%PS1_TEMP%"
echo     if ((Test-Path $tmpZip) -and ((Get-Item $tmpZip).Length -gt 0)) { $descargaOk = $true; break } >> "%PS1_TEMP%"
echo   } catch { >> "%PS1_TEMP%"
echo     $erroresDescarga += ('Invoke-WebRequest intento ' + $intento + ': ' + $_.Exception.Message) >> "%PS1_TEMP%"
echo     Start-Sleep -Seconds 2 >> "%PS1_TEMP%"
echo   } >> "%PS1_TEMP%"
echo } >> "%PS1_TEMP%"
echo if (-not $descargaOk) { >> "%PS1_TEMP%"
echo   try { >> "%PS1_TEMP%"
echo     $wc = New-Object System.Net.WebClient >> "%PS1_TEMP%"
echo     $wc.DownloadFile($zipUrl, $tmpZip) >> "%PS1_TEMP%"
echo     if ((Test-Path $tmpZip) -and ((Get-Item $tmpZip).Length -gt 0)) { $descargaOk = $true } >> "%PS1_TEMP%"
echo   } catch { >> "%PS1_TEMP%"
echo     $erroresDescarga += ('WebClient: ' + $_.Exception.Message) >> "%PS1_TEMP%"
echo   } >> "%PS1_TEMP%"
echo } >> "%PS1_TEMP%"
echo if (-not $descargaOk -and (Get-Command curl.exe -ErrorAction SilentlyContinue)) { >> "%PS1_TEMP%"
echo   try { >> "%PS1_TEMP%"
echo     ^& curl.exe -L --fail -o $tmpZip $zipUrl --silent >> "%PS1_TEMP%"
echo     if (($LASTEXITCODE -eq 0) -and (Test-Path $tmpZip) -and ((Get-Item $tmpZip).Length -gt 0)) { $descargaOk = $true } >> "%PS1_TEMP%"
echo   } catch { >> "%PS1_TEMP%"
echo     $erroresDescarga += ('curl.exe: ' + $_.Exception.Message) >> "%PS1_TEMP%"
echo   } >> "%PS1_TEMP%"
echo } >> "%PS1_TEMP%"
echo if (-not $descargaOk) { >> "%PS1_TEMP%"
echo   Write-Output 'ERROR-DESCARGA: no se pudo bajar el .zip por ningun metodo (Invoke-WebRequest, WebClient, curl.exe).' >> "%PS1_TEMP%"
echo   foreach ($e in $erroresDescarga) { Write-Output ('  - ' + $e) } >> "%PS1_TEMP%"
echo   exit 1 >> "%PS1_TEMP%"
echo } >> "%PS1_TEMP%"
echo # --- Plan de contingencia 2: extraccion por 2 metodos distintos --- >> "%PS1_TEMP%"
echo $extraidoOk = $false >> "%PS1_TEMP%"
echo try { >> "%PS1_TEMP%"
echo   Expand-Archive -Path $tmpZip -DestinationPath $tmpDir -Force -ErrorAction Stop >> "%PS1_TEMP%"
echo   $extraidoOk = $true >> "%PS1_TEMP%"
echo } catch { >> "%PS1_TEMP%"
echo   Write-Output ('AVISO: Expand-Archive fallo (' + $_.Exception.Message + '), probando con tar...') >> "%PS1_TEMP%"
echo   if (Get-Command tar.exe -ErrorAction SilentlyContinue) { >> "%PS1_TEMP%"
echo     New-Item -ItemType Directory -Path $tmpDir -Force ^| Out-Null >> "%PS1_TEMP%"
echo     ^& tar.exe -xf $tmpZip -C $tmpDir >> "%PS1_TEMP%"
echo     if ($LASTEXITCODE -eq 0) { $extraidoOk = $true } >> "%PS1_TEMP%"
echo   } >> "%PS1_TEMP%"
echo } >> "%PS1_TEMP%"
echo if (-not $extraidoOk) { >> "%PS1_TEMP%"
echo   Write-Output 'ERROR-DESCARGA: no se pudo extraer el .zip (ni con Expand-Archive ni con tar).' >> "%PS1_TEMP%"
echo   Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue >> "%PS1_TEMP%"
echo   exit 1 >> "%PS1_TEMP%"
echo } >> "%PS1_TEMP%"
echo try { >> "%PS1_TEMP%"
echo   $srcFolder = Get-ChildItem -Path $tmpDir -Directory ^| Select-Object -First 1 >> "%PS1_TEMP%"
echo   $archivos = Get-ChildItem -Path $srcFolder.FullName -Recurse -File >> "%PS1_TEMP%"
echo   $fallidos = @() >> "%PS1_TEMP%"
echo   foreach ($f in $archivos) { >> "%PS1_TEMP%"
echo     $rel = $f.FullName.Substring($srcFolder.FullName.Length + 1) >> "%PS1_TEMP%"
echo     $destino = Join-Path $Dest $rel >> "%PS1_TEMP%"
echo     try { >> "%PS1_TEMP%"
echo       New-Item -ItemType Directory -Path (Split-Path $destino) -Force -ErrorAction Stop ^| Out-Null >> "%PS1_TEMP%"
echo       if ((Test-Path $destino) -and ((Get-Item $destino).Attributes -band [IO.FileAttributes]::ReadOnly)) { >> "%PS1_TEMP%"
echo         (Get-Item $destino).Attributes = (Get-Item $destino).Attributes -band (-bnot [IO.FileAttributes]::ReadOnly) >> "%PS1_TEMP%"
echo       } >> "%PS1_TEMP%"
echo       Copy-Item -Path $f.FullName -Destination $destino -Force -ErrorAction Stop >> "%PS1_TEMP%"
echo     } catch { >> "%PS1_TEMP%"
echo       $fallidos += ('{0} ({1})' -f $rel, $_.Exception.Message) >> "%PS1_TEMP%"
echo       Write-Output ('AVISO: no se pudo actualizar ' + $rel + ' - ' + $_.Exception.Message) >> "%PS1_TEMP%"
echo     } >> "%PS1_TEMP%"
echo   } >> "%PS1_TEMP%"
echo   try { >> "%PS1_TEMP%"
echo     $commitInfo = Invoke-RestMethod -Uri ("https://api.github.com/repos/$RepoSlug/commits/$Branch") -Headers @{'User-Agent'='RUBRICA-updater'} -ErrorAction Stop >> "%PS1_TEMP%"
echo     Set-Content -Path (Join-Path $Dest '.version_commit') -Value $commitInfo.sha -NoNewline -ErrorAction Stop >> "%PS1_TEMP%"
echo   } catch { >> "%PS1_TEMP%"
echo     Write-Output ('AVISO: no se pudo guardar el marcador de version - ' + $_.Exception.Message) >> "%PS1_TEMP%"
echo   } >> "%PS1_TEMP%"
echo   if ($fallidos.Count -gt 0) { >> "%PS1_TEMP%"
echo     Write-Output ('RESUMEN: ' + $fallidos.Count + ' de ' + $archivos.Count + ' archivo(s) no se pudieron actualizar.') >> "%PS1_TEMP%"
echo     Write-Output '' >> "%PS1_TEMP%"
echo     Write-Output 'Esto suele pasar por el antivirus o "Acceso a carpetas controlado" de Windows Defender.' >> "%PS1_TEMP%"
echo     Write-Output 'Para arreglarlo (como Administrador, en PowerShell), ejecuta:' >> "%PS1_TEMP%"
echo     Write-Output ('  Add-MpPreference -ExclusionPath "' + $Dest + '"') >> "%PS1_TEMP%"
echo   } else { >> "%PS1_TEMP%"
echo     Write-Output ('OK: ' + $archivos.Count + ' archivo(s) actualizados.') >> "%PS1_TEMP%"
echo   } >> "%PS1_TEMP%"
echo   exit 0 >> "%PS1_TEMP%"
echo } finally { >> "%PS1_TEMP%"
echo   Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue >> "%PS1_TEMP%"
echo   Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue >> "%PS1_TEMP%"
echo } >> "%PS1_TEMP%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_TEMP%" -Dest "%DEST_DIR%" -RepoSlug "%REPO_SLUG%" -Branch "%REPO_BRANCH%"
set "PS1_EXIT=%errorlevel%"
del "%PS1_TEMP%" >nul 2>&1
exit /b %PS1_EXIT%
