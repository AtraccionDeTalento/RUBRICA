const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const https = require('https');
const crypto = require('crypto');
const fs = require('fs');

let mainWindow;
let pythonProcess;
let bootAttempt = 0;

// Cargar la imagen del icono en Base64 para mostrar en la pantalla de carga
let iconBase64 = '';
try {
  const iconPath = path.join(__dirname, 'icon.png');
  if (fs.existsSync(iconPath)) {
    iconBase64 = 'data:image/png;base64,' + fs.readFileSync(iconPath).toString('base64');
  }
} catch (e) {
  console.error('Error al cargar icon.png:', e);
}

// ─── Pantalla de carga con estado ────────────────────────────────────────────
function loadingPage(mensaje, subMensaje = '', esError = false) {
  const color  = esError ? '#fef2f2' : '#f8fafc';
  const titCol = esError ? '#b91c1c' : '#0f172a';
  const subCol = esError ? '#dc2626' : '#475569';
  
  const iconHtml = esError ? '<div class="icon">⚠️</div>' : 
                   (iconBase64 ? `<img src="${iconBase64}" style="width: 160px; height: 160px; object-fit: contain; margin-bottom: 8px;" />` : 
                   '<div class="icon">🎓</div>');

  const buttonHtml = `
    <div id="restart-container" style="display: ${esError ? 'flex' : 'none'}; flex-direction: column; align-items: center; gap: 8px; margin-top: 15px;">
      ${!esError ? '<p style="font-size: 12px; color: #64748b;">¿Está demorando demasiado?</p>' : ''}
      <button onclick="try { window.electronAPI.reiniciarApp(); } catch(e) { window.location.reload(); }" style="
        padding: 10px 20px;
        background-color: ${esError ? '#ef4444' : '#f1f5f9'};
        color: ${esError ? '#ffffff' : '#334155'};
        border: 1px solid ${esError ? '#dc2626' : '#cbd5e1'};
        border-radius: 6px;
        font-family: inherit;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
      " onmouseover="this.style.backgroundColor='${esError ? '#dc2626' : '#e2e8f0'}'" onmouseout="this.style.backgroundColor='${esError ? '#ef4444' : '#f1f5f9'}'">
        ${esError ? 'Reintentar / Iniciar de nuevo' : 'Forzar Reinicio del Servidor'}
      </button>
    </div>
    ${!esError ? `
    <script>
      setTimeout(() => {
        const container = document.getElementById('restart-container');
        if (container) container.style.display = 'flex';
      }, 7000);
    </script>
    ` : ''}
  `;

  const html = `<!DOCTYPE html><html><head><meta charset="UTF-8">
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{display:flex;flex-direction:column;justify-content:center;align-items:center;
         height:100vh;font-family:'Segoe UI',sans-serif;background:${color};gap:18px}
    .icon{font-size:56px}
    h2{color:${titCol};font-size:20px;font-weight:700;text-align:center;max-width:480px;line-height:1.4}
    p{color:${subCol};font-size:14px;text-align:center;max-width:480px;line-height:1.6}
    .bar{width:320px;height:6px;background:#e2e8f0;border-radius:99px;overflow:hidden}
    .fill{height:100%;background:${esError ? '#ef4444' : '#1e3a8a'};border-radius:99px;
          ${esError ? '' : 'animation:slide 1.4s ease-in-out infinite'};width:${esError ? '100%' : '40%'}}
    @keyframes slide{0%{transform:translateX(-100%)}100%{transform:translateX(900%)}}
  </style></head><body>
  ${iconHtml}
  <h2>${mensaje}</h2>
  ${subMensaje ? `<p>${subMensaje}</p>` : ''}
  ${!esError ? '<div class="bar"><div class="fill"></div></div>' : ''}
  ${buttonHtml}
  </body></html>`;
  
  try {
    const { pathToFileURL } = require('url');
    const tempPath = path.join(app.getPath('userData'), 'loading.html');
    fs.writeFileSync(tempPath, html, 'utf8');
    return pathToFileURL(tempPath).href;
  } catch (e) {
    console.error('Error writing loading.html, falling back to data URL:', e);
    return 'data:text/html;base64,' + Buffer.from(html).toString('base64');
  }
}

// ─── Crear ventana principal ──────────────────────────────────────────────────
function createWindow() {
  const iconPath = path.join(__dirname, 'icon.png');
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.maximize();
  mainWindow.loadURL(loadingPage('Iniciando Sistema de Evaluación Docente...', 'Preparando el motor de inteligencia artificial...'));

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

// ─── Auto-actualizacion desde GitHub SIN depender de git ────────────────────
// El ejecutable no debe requerir que la PC tenga git instalado para
// funcionar ni para actualizarse -git solo lo usa ACTUALIZAR_Y_ABRIR.bat
// como atajo de instalacion para gente tecnica, nunca la app en si-.
// Por eso la app descarga cada archivo de codigo directo desde GitHub via
// HTTPS (API de GitHub + raw.githubusercontent.com) y verifica su hash
// contra el que reporta la propia API, sin necesitar git para nada. Esto se
// ejecuta automaticamente CADA VEZ que se abre la app -sin importar como se
// abra (exe, acceso directo, npm start)- y tambien se puede disparar a mano
// con el boton "Actualizar Sistema" (ver ipcMain.handle mas abajo).
const REPO_SLUG = 'AtraccionDeTalento/RUBRICA';
const REPO_BRANCH = 'main';

// Lista explicita (no automatica) de los archivos que este boton actualiza.
// Solo "codigo y datos de la app" -- nunca main.js/preload.js/package.json/
// node_modules ni los .dll de Electron: eso requiere un instalador nuevo, no
// un update de contenido (igual que ya se maneja para Sistema de Vacaciones).
const ARCHIVOS_ACTUALIZABLES = [
  'servidor.py',
  'bot_evaluacion_docente/actualizar_nombres_links.py',
  'bot_evaluacion_docente/analizador_experiencia.py',
  'bot_evaluacion_docente/analizador_rubrica.py',
  'bot_evaluacion_docente/analizar_links.py',
  'bot_evaluacion_docente/app_web.py',
  'bot_evaluacion_docente/buscador_web_cv.py',
  'bot_evaluacion_docente/clasificador_talento.py',
  'bot_evaluacion_docente/compilar.py',
  'bot_evaluacion_docente/config.py',
  'bot_evaluacion_docente/extractor_cvs.py',
  'bot_evaluacion_docente/extractor_web_cvs.py',
  'bot_evaluacion_docente/extraer_links_columna_k.py',
  'bot_evaluacion_docente/fix.py',
  'bot_evaluacion_docente/generador_decisiones.py',
  'bot_evaluacion_docente/generador_decisiones_mejorado.py',
  'bot_evaluacion_docente/generador_decisiones_nuevo.py',
  'bot_evaluacion_docente/generador_reportes.py',
  'bot_evaluacion_docente/launcher.py',
  'bot_evaluacion_docente/logger_error.py',
  'bot_evaluacion_docente/main.py',
  'bot_evaluacion_docente/motor_evaluacion.py',
  'bot_evaluacion_docente/procesar_cvs_web.py',
  'bot_evaluacion_docente/rubrica_loader.py',
  'bot_evaluacion_docente/run_server.py',
  'bot_evaluacion_docente/requirements.txt',
  'bot_evaluacion_docente/requerimientos_2026.json',
  'bot_evaluacion_docente/templates/index.html',
  'bot_evaluacion_docente/static/script.js',
  'bot_evaluacion_docente/static/styles.css',
  'Rubrica/Criterios 2025.json',
  'Rubrica/DTC DTINV.json',
  'Rubrica/PRACTITIONER DOCENTE CARRERA MH.json',
  'Rubrica/diccionario_c2_docencia.json',
  'Rubrica/diccionario_c3_profesional.json',
  'Rubrica/empresas_top500.json'
];

function enviarProgresoActualizacion(mensaje) {
  console.log('[ACTUALIZAR-SISTEMA] ' + mensaje);
  if (!mainWindow) return;
  // Si la app ya cargo la pantalla real (http://127.0.0.1:5000), este mensaje
  // es del boton manual "Actualizar Sistema": se manda por IPC a esa pantalla.
  // Si todavia esta en la pantalla de carga (arranque automatico), se
  // actualiza la pantalla de carga misma para que se vea el progreso.
  const urlActual = mainWindow.webContents.getURL();
  if (urlActual.startsWith('http://127.0.0.1:5000')) {
    mainWindow.webContents.send('actualizar-sistema-progreso', mensaje);
  } else {
    mainWindow.loadURL(loadingPage('Actualizando el sistema...', mensaje));
  }
}

function httpsGetJson(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'RUBRICA-auto-update', 'Accept': 'application/vnd.github+json' } }, (res) => {
      if (res.statusCode < 200 || res.statusCode >= 300) {
        res.resume();
        reject(new Error(`GitHub API respondio ${res.statusCode} para ${url}`));
        return;
      }
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
      });
    }).on('error', reject);
  });
}

function httpsGetBuffer(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'RUBRICA-auto-update' } }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        res.resume();
        httpsGetBuffer(res.headers.location).then(resolve, reject);
        return;
      }
      if (res.statusCode < 200 || res.statusCode >= 300) {
        res.resume();
        reject(new Error(`HTTP ${res.statusCode} descargando ${url}`));
        return;
      }
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => resolve(Buffer.concat(chunks)));
    }).on('error', reject);
  });
}

// El hash que usa git internamente para identificar un blob -- comparar contra
// esto verifica el archivo contra lo que GitHub realmente tiene registrado,
// no solo contra si mismo (mas fuerte que solo "se descargo sin cortarse").
function gitBlobSha1(buffer) {
  const header = Buffer.from(`blob ${buffer.length}\0`, 'utf8');
  return crypto.createHash('sha1').update(header).update(buffer).digest('hex');
}

function encodeRepoPath(relPath) {
  return relPath.split('/').map(encodeURIComponent).join('/');
}

async function obtenerArbolRemoto(commitSha) {
  const url = `https://api.github.com/repos/${REPO_SLUG}/git/trees/${commitSha}?recursive=1`;
  const arbol = await httpsGetJson(url);
  const mapa = new Map();
  for (const entrada of (arbol.tree || [])) {
    if (entrada.type === 'blob') mapa.set(entrada.path, entrada.sha);
  }
  return mapa;
}

async function descargarArchivoVerificado(relPath, shaEsperado, baseDir) {
  const destino = path.join(baseDir, ...relPath.split('/'));
  const url = `https://raw.githubusercontent.com/${REPO_SLUG}/${REPO_BRANCH}/${encodeRepoPath(relPath)}`;
  let ultimoError = null;
  for (let intento = 1; intento <= 3; intento++) {
    try {
      const contenido = await httpsGetBuffer(url);
      if (shaEsperado && gitBlobSha1(contenido) !== shaEsperado) {
        throw new Error('El archivo descargado no coincide con el hash reportado por GitHub');
      }
      fs.mkdirSync(path.dirname(destino), { recursive: true });
      const tmp = destino + '.tmp';
      fs.writeFileSync(tmp, contenido);
      fs.renameSync(tmp, destino);
      return true;
    } catch (e) {
      ultimoError = e;
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  console.warn(`[ACTUALIZAR-SISTEMA] Fallo descargando ${relPath}:`, ultimoError && ultimoError.message);
  return false;
}

async function actualizarSistemaSinGit() {
  const baseDir = app.isPackaged ? path.dirname(app.getPath('exe')) : __dirname;
  const marcadorVersion = path.join(baseDir, '.version_commit');

  try {
    enviarProgresoActualizacion('Buscando la ultima version en GitHub...');
    const commitInfo = await httpsGetJson(`https://api.github.com/repos/${REPO_SLUG}/commits/${REPO_BRANCH}`);
    const remoteSha = commitInfo.sha;

    let localSha = null;
    if (fs.existsSync(marcadorVersion)) {
      try { localSha = fs.readFileSync(marcadorVersion, 'utf8').trim(); } catch (e) {}
    }

    if (localSha && localSha === remoteSha) {
      return { ok: true, actualizado: false, mensaje: 'Ya tienes la ultima version del sistema.' };
    }

    enviarProgresoActualizacion('Descargando lista de archivos...');
    const arbol = await obtenerArbolRemoto(remoteSha);

    enviarProgresoActualizacion('Cerrando el servidor actual...');
    killPythonServer();
    await new Promise((r) => setTimeout(r, 1000));

    let ok = 0;
    const fallidos = [];
    for (const relPath of ARCHIVOS_ACTUALIZABLES) {
      enviarProgresoActualizacion(`Actualizando ${relPath}...`);
      const shaEsperado = arbol.get(relPath) || null;
      const exito = await descargarArchivoVerificado(relPath, shaEsperado, baseDir);
      if (exito) ok++; else fallidos.push(relPath);
    }

    if (fallidos.length === 0) {
      fs.writeFileSync(marcadorVersion, remoteSha, 'utf8');
    }

    enviarProgresoActualizacion('Reiniciando el servidor...');
    bootAttempt++;
    await setupAndStartServer();

    return {
      ok: true,
      actualizado: true,
      archivosActualizados: ok,
      archivosFallidos: fallidos,
      mensaje: fallidos.length === 0
        ? `Sistema actualizado correctamente (${ok} archivos).`
        : `Actualizado con avisos: ${ok} archivos bien, ${fallidos.length} fallaron (${fallidos.join(', ')}). Puedes intentar de nuevo.`
    };
  } catch (e) {
    console.error('[ACTUALIZAR-SISTEMA] Error:', e);
    return { ok: false, actualizado: false, mensaje: `No se pudo actualizar: ${e.message}` };
  }
}

ipcMain.handle('actualizar-sistema', async () => {
  return actualizarSistemaSinGit();
});

// ─── Ejecutar un comando Python y esperar a que termine ──────────────────────
function runPythonCmd(pythonExe, args, cwd) {
  return new Promise((resolve, reject) => {
    const currentDir = cwd || (app.isPackaged ? path.dirname(app.getPath('exe')) : __dirname);
    const proc = spawn(pythonExe, args, { cwd: currentDir, shell: false });
    let out = '';
    let err = '';
    proc.stdout.on('data', d => { out += d.toString(); });
    proc.stderr.on('data', d => { err += d.toString(); });
    proc.on('close', code => {
      if (code === 0) resolve(out);
      else reject(new Error(err || `Exit code ${code}`));
    });
    proc.on('error', reject);
  });
}

// ─── Buscar Python instalado en el sistema ───────────────────────────────────
async function detectarPython() {
  const candidatos = ['python', 'python3', 'py'];
  for (const py of candidatos) {
    try {
      await runPythonCmd(py, ['--version']);
      return py;
    } catch (e) {
      // siguiente candidato
    }
  }
  return null;
}

// ─── Setup + arranque del servidor ───────────────────────────────────────────
async function setupAndStartServer() {
  const currentAttempt = ++bootAttempt;

  const baseDir = app.isPackaged ? path.dirname(app.getPath('exe')) : __dirname;
  const venvDir = app.isPackaged ? path.join(app.getPath('userData'), '.venv') : path.join(baseDir, '.venv');
  const venvPython  = path.join(venvDir, 'Scripts', 'python.exe');
  const serverScript = path.join(baseDir, 'servidor.py');
  const requirements = path.join(baseDir, 'bot_evaluacion_docente', 'requirements.txt');

  // 1. ¿Ya tiene .venv? Arrancar directo.
  if (fs.existsSync(venvPython)) {
    console.log('[BOOT] .venv encontrado → arrancando servidor...');
    if (currentAttempt !== bootAttempt) return;
    startPythonServer(venvPython, serverScript, currentAttempt);
    return;
  }

  // 2. Buscar Python global.
  if (mainWindow) mainWindow.loadURL(loadingPage(
    'Primera vez en este equipo',
    'Buscando Python instalado en el sistema...'
  ));
  if (currentAttempt !== bootAttempt) return;

  const pythonGlobal = await detectarPython();
  if (currentAttempt !== bootAttempt) return;

  if (!pythonGlobal) {
    if (mainWindow) mainWindow.loadURL(loadingPage(
      'Python no encontrado',
      'Este sistema requiere Python 3.10+ instalado.<br>' +
      'Descárgalo desde <b>python.org</b>, instálalo marcando "Add to PATH" y vuelve a abrir la app.',
      true
    ));
    return;
  }

  // 3. Verificar si el Python global ya tiene las dependencias requeridas instaladas
  if (mainWindow) mainWindow.loadURL(loadingPage(
    'Verificando tecnologías',
    'Verificando si ya tienes las dependencias de Python necesarias instaladas...'
  ));
  if (currentAttempt !== bootAttempt) return;

  try {
    console.log('[BOOT] Probando si Python global ya tiene las librerías necesarias...');
    await runPythonCmd(pythonGlobal, ['-c', 'import flask, pandas, openpyxl, pdfplumber']);
    if (currentAttempt !== bootAttempt) return;
    console.log('[BOOT] ¡Librerías encontradas en Python global! Arrancando directamente...');
    
    if (mainWindow) mainWindow.loadURL(loadingPage(
      'Listo. Iniciando el sistema...',
      'Abriendo el Sistema de Evaluación Docente...'
    ));

    startPythonServer(pythonGlobal, serverScript, currentAttempt);
    return;
  } catch (e) {
    console.log('[BOOT] Falta alguna dependencia en Python global. Se procederá a crear un entorno virtual local...');
  }
  if (currentAttempt !== bootAttempt) return;

  // 4. Crear entorno virtual.
  if (mainWindow) mainWindow.loadURL(loadingPage(
    'Configurando entorno (primera vez)',
    'Creando entorno virtual Python...<br>Esto puede tardar 1-2 minutos la primera vez.'
  ));

  try {
    await runPythonCmd(pythonGlobal, ['-m', 'venv', venvDir]);
    if (currentAttempt !== bootAttempt) return;
    console.log('[BOOT] .venv creado OK en: ' + venvDir);
  } catch (e) {
    if (currentAttempt !== bootAttempt) return;
    if (mainWindow) mainWindow.loadURL(loadingPage(
      'Error al crear entorno',
      `No se pudo crear el entorno virtual: ${e.message}`,
      true
    ));
    return;
  }

  // 5. Instalar dependencias.
  if (mainWindow) mainWindow.loadURL(loadingPage(
    'Instalando dependencias',
    'Descargando e instalando dependencias (Flask, Pandas, OpenPyXL, pdfplumber)...<br>Solo ocurre la primera vez en este equipo.'
  ));
  if (currentAttempt !== bootAttempt) return;

  try {
    await runPythonCmd(venvPython, ['-m', 'pip', 'install', '--upgrade', 'pip', '--quiet']);
    if (currentAttempt !== bootAttempt) return;
    await runPythonCmd(venvPython, ['-m', 'pip', 'install', '-r', requirements, '--quiet']);
    if (currentAttempt !== bootAttempt) return;
    console.log('[BOOT] Dependencias instaladas OK');
  } catch (e) {
    if (currentAttempt !== bootAttempt) return;
    if (mainWindow) mainWindow.loadURL(loadingPage(
      'Error al instalar dependencias',
      `Problema instalando librerías: ${e.message}`,
      true
    ));
    return;
  }

  // 6. Todo listo → arrancar servidor.
  if (mainWindow) mainWindow.loadURL(loadingPage(
    'Listo. Iniciando el sistema...',
    'Abriendo el Sistema de Evaluación Docente...'
  ));
  if (currentAttempt !== bootAttempt) return;

  startPythonServer(venvPython, serverScript, currentAttempt);
}

// ─── Arrancar proceso Python (Flask) ─────────────────────────────────────────
function startPythonServer(pythonExe, serverScript, attempt) {
  if (attempt !== bootAttempt) return;

  const baseDir = app.isPackaged ? path.dirname(app.getPath('exe')) : __dirname;
  pythonProcess = spawn(pythonExe, [serverScript], {
    cwd: baseDir
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python] ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Python Err] ${data}`);
  });

  pythonProcess.on('error', (err) => {
    console.error('[Python] No se pudo iniciar:', err);
    if (attempt !== bootAttempt) return;
    if (mainWindow) mainWindow.loadURL(loadingPage(
      'Error iniciando el servidor',
      `Python no pudo arrancar: ${err.message}`,
      true
    ));
  });

  pythonProcess.on('close', (code) => {
    console.log(`[BOOT] El proceso Python terminó con código: ${code}`);
    if (attempt !== bootAttempt) return;

    if (mainWindow) {
      const currentURL = mainWindow.webContents.getURL();
      if (!currentURL.startsWith('http://127.0.0.1:5000')) {
        mainWindow.loadURL(loadingPage(
          'El servidor de Python se cerró inesperadamente',
          `Código de salida: ${code}. Esto puede ocurrir si el puerto 5000 está en uso o si hay un error en los scripts de Python.`,
          true
        ));
      }
    }
  });

  // Hacer "ping" al servidor hasta que responda en puerto 5000
  setTimeout(() => checkServerReady(attempt), 2000);
}

// ─── Esperar a que Flask responda ────────────────────────────────────────────
function checkServerReady(attempt) {
  if (attempt !== bootAttempt) {
    console.log(`[BOOT] Omitiendo checkServerReady obsoleto para intento ${attempt}`);
    return;
  }

  const req = http.request(
    { hostname: '127.0.0.1', port: 5000, path: '/', method: 'GET' },
    (res) => {
      if (attempt !== bootAttempt) return;
      if ([200, 302, 404].includes(res.statusCode)) {
        if (mainWindow) mainWindow.loadURL('http://127.0.0.1:5000');
      } else {
        setTimeout(() => checkServerReady(attempt), 1000);
      }
    }
  );
  req.on('error', () => {
    if (attempt !== bootAttempt) return;
    setTimeout(() => checkServerReady(attempt), 1000);
  });
  req.end();
}

// ─── Ciclo de vida de la app ──────────────────────────────────────────────────
app.on('ready', async () => {
  createWindow();

  // Revisar actualizaciones SIEMPRE al abrir la app, sin depender de git.
  // Si actualizarSistemaSinGit() aplico una actualizacion, ya arranco el
  // servidor por su cuenta (ver el final de esa funcion); si no habia nada
  // nuevo o la revision fallo (sin internet, etc.), arrancamos aqui como de
  // costumbre - nunca se bloquea el arranque de la app por esto.
  let resultado = { actualizado: false };
  try {
    resultado = await actualizarSistemaSinGit();
  } catch (e) {
    console.warn('[UPDATE] Error inesperado revisando actualizaciones:', e.message);
  }

  if (resultado.actualizado) return;

  setupAndStartServer().catch(err => {
    console.error('[BOOT] Error inesperado:', err);
    if (mainWindow) mainWindow.loadURL(loadingPage(
      'Error inesperado al iniciar',
      err.message,
      true
    ));
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('quit', () => {
  killPythonServer();
});

// ─── Control de reinicio de la aplicación ────────────────────────────────────
ipcMain.on('reiniciar-app', () => {
  console.log('[BOOT] Reinicio solicitado por el usuario...');
  reiniciarServidorYApp();
});

function killPythonServer() {
  if (pythonProcess && !pythonProcess.killed) {
    console.log(`[BOOT] Matando proceso Python existente (PID: ${pythonProcess.pid})...`);
    try {
      spawn('taskkill', ['/pid', String(pythonProcess.pid), '/f', '/t'], {
        detached: true, stdio: 'ignore'
      }).unref();
    } catch (e) {
      try { pythonProcess.kill('SIGKILL'); } catch (_) {}
    }
    pythonProcess = null;
  }
}

async function reiniciarServidorYApp() {
  // Incrementar intento para detener cualquier checkServerReady o setup previo
  bootAttempt++;
  
  // Matar el servidor Python actual si existe
  killPythonServer();
  
  // Mostrar pantalla de carga nuevamente
  if (mainWindow) {
    mainWindow.loadURL(loadingPage('Reiniciando servidor...', 'Espere por favor, estamos liberando el puerto y volviendo a levantar el proceso...'));
  }
  
  // Esperar un breve momento para asegurar la liberación del puerto
  setTimeout(() => {
    setupAndStartServer().catch(err => {
      console.error('[BOOT] Error inesperado en reinicio:', err);
      if (mainWindow) mainWindow.loadURL(loadingPage(
        'Error inesperado al reiniciar',
        err.message,
        true
      ));
    });
  }, 1000);
}
