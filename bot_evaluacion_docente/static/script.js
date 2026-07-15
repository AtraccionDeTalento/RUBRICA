// Script principal para la aplicación web
let intervalId = null;
let archivoSeleccionado = null;
let archivosExcelSeleccionados = [];
let carpetaPdfsSeleccionada = null;
window.registrosConError = []; // Para almacenar registros con error
window.ordenActual = 'excel'; // Por defecto: orden del Excel

// Safety timeout: restaura el botón "Iniciar" automáticamente si se queda pegado
let btnSafetyTimeout = null;
function armBtnSafety() {
    clearTimeout(btnSafetyTimeout);
    btnSafetyTimeout = setTimeout(() => {
        const btn = document.getElementById('btn-lanzar-analisis');
        // Solo restaurar si el botón sigue deshabilitado Y no hay polling activo
        if (btn && btn.disabled && !intervalId) {
            console.warn('[SAFETY] Botón "Iniciar" restaurado automáticamente tras 15s sin polling.');
            btn.disabled = false;
            btn.textContent = '🚀 Iniciar Análisis de Talento';
        }
    }, 15000);
}
function disarmBtnSafety() {
    clearTimeout(btnSafetyTimeout);
}

let stuckTimeout = null;

function startStuckDetection() {
    clearTimeout(stuckTimeout);
    stuckTimeout = setTimeout(() => {
        const btnReiniciar = document.getElementById('btn-reiniciar');
        const btnReiniciarProc = document.getElementById('btn-reiniciar-procesando');
        if (btnReiniciar) btnReiniciar.style.display = 'inline-flex';
        if (btnReiniciarProc) btnReiniciarProc.style.display = 'block';
    }, 12000); // Mostrar botón después de 12 segundos atascado
}

function clearStuckDetection() {
    clearTimeout(stuckTimeout);
    const btnReiniciar = document.getElementById('btn-reiniciar');
    const btnReiniciarProc = document.getElementById('btn-reiniciar-procesando');
    if (btnReiniciar) btnReiniciar.style.display = 'none';
    if (btnReiniciarProc) btnReiniciarProc.style.display = 'none';
}

async function forzarReinicio() {
    const overlay = document.getElementById('reiniciando-overlay');
    if (overlay) overlay.style.display = 'flex';
    
    // Si estamos en Electron, usamos el API nativo para reiniciar de verdad (mata servidor, libera puerto y reinicia app)
    if (window.electronAPI && typeof window.electronAPI.reiniciarApp === 'function') {
        try {
            window.electronAPI.reiniciarApp();
            return;
        } catch (err) {
            console.error("Error llamando a reiniciarApp de Electron:", err);
        }
    }
    
    // Fallback para navegador web puro (llama al endpoint de la API y recarga la página)
    try {
        await fetch('/hard-reset', { method: 'POST' });
    } catch(e) {
        console.error("Error al forzar reinicio via API web:", e);
    }
    setTimeout(() => {
        window.location.reload();
    }, 1500);
}


// Función para re-analizar un registro individual
async function reanalizarRegistro(url, dni, nombre, facultad, carrera) {
    if (!url) {
        alert('⚠️ No hay URL disponible para re-analizar este registro');
        return;
    }
    
    // Crear modal de re-análisis
    const modal = document.createElement('div');
    modal.className = 'modal-reanalisis';
    modal.id = 'modal-reanalisis';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>🔄 Re-analizando Registro</h3>
                <button class="modal-close" onclick="cerrarModalReanalisis()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="reanalisis-info">
                    <p><strong>Candidato:</strong> ${nombre || 'Sin nombre'}</p>
                    <p><strong>DNI:</strong> ${dni || 'N/A'}</p>
                    <p><strong>Facultad:</strong> ${facultad || 'N/A'}</p>
                    <p><strong>URL:</strong> <a href="${url}" target="_blank">${url.substring(0, 50)}...</a></p>
                </div>
                <div class="reanalisis-estado">
                    <div class="loader-mini"></div>
                    <p id="reanalisis-mensaje">Conectando con CTI Vitae...</p>
                    <p class="reanalisis-aviso">⏱️ Este proceso puede demorar hasta 5 minutos en perfiles sobrecargados</p>
                </div>
                <div class="reanalisis-resultado" id="reanalisis-resultado" style="display: none;">
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    try {
        // Timeout de 5 minutos (300000 ms) para perfiles sobrecargados
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000);
        
        const response = await fetch('/api/reanalizar-registro', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url, dni, nombre, facultad, carrera }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        const resultado = await response.json();
        
        const estadoDiv = modal.querySelector('.reanalisis-estado');
        const resultadoDiv = modal.querySelector('#reanalisis-resultado');
        
        estadoDiv.style.display = 'none';
        resultadoDiv.style.display = 'block';
        
        if (resultado.exito) {
            const cv = resultado.cv_data;
            const eval_data = resultado.evaluacion || {};
            const puntajes = eval_data.puntajes || {};
            const total = eval_data.total || 0;
            const pct = eval_data.porcentaje || 0;
            const maxPts = eval_data.maximo || 200;
            const clsRaw = eval_data.clasificacion || '';
            const clsKey = clsRaw.split(' ')[0].split('(')[0];
            const clsColor = PERFIL_COLOR[clsKey] || '#34495e';

            // ── Actualizar la fila en la tabla principal ──────────────────────
            const filaExistente = dni
                ? document.querySelector(`#tabla-clasificacion-tbody tr[data-dni="${dni}"]`)
                : null;

            if (filaExistente) {
                // Perfil badge
                const tdPerfil = filaExistente.querySelector('.td-perfil');
                if (tdPerfil) {
                    tdPerfil.innerHTML = `<span class="badge-perfil" style="background-color:${clsColor}">${clsRaw || 'SIN CLASIFICAR'}</span>`;
                }
                // Tipo perfil badge
                const tdTipoPerfil = filaExistente.querySelector('.td-tipo-perfil');
                if (tdTipoPerfil && eval_data.tipo_perfil) {
                    tdTipoPerfil.innerHTML = _badgeTipoPerfil(eval_data.tipo_perfil);
                }
                // Puntaje total
                const tdPuntaje = filaExistente.querySelector('.td-puntaje');
                if (tdPuntaje) {
                    tdPuntaje.innerHTML = `<strong>${total}/${maxPts}</strong> (${pct}%)`;
                }
                // Justificación
                const tdJustif = filaExistente.querySelector('.td-justif');
                if (tdJustif && eval_data.justificacion_decision) {
                    tdJustif.textContent = eval_data.justificacion_decision;
                }
                // C1-C5 (columnas 6-10)
                const maxCriterios = [
                    eval_data.detalles?.formacion_academica?.maximo || 50,
                    eval_data.detalles?.experiencia_docente?.maximo || 40,
                    eval_data.detalles?.experiencia_profesional?.maximo || 40,
                    eval_data.detalles?.centro_labores?.maximo || 20,
                    eval_data.detalles?.produccion_academica?.maximo || 50,
                ];
                ['C1','C2','C3','C4','C5'].forEach((key, i) => {
                    const tds = filaExistente.querySelectorAll('td');
                    const td = tds[6 + i];
                    if (td) {
                        td.innerHTML = `<div style="font-weight:600">${puntajes[key] || 0}/${maxCriterios[i]}</div>`;
                    }
                });
                // Marcar visualmente como re-analizado
                filaExistente.style.outline = '2px solid #22c55e';
                filaExistente.style.outlineOffset = '-2px';
            }

            resultadoDiv.innerHTML = `
                <div class="resultado-exito">
                    <h4>✅ Re-análisis Exitoso${filaExistente ? ' — Tabla actualizada' : ''}</h4>
                    <div class="diagnostico">
                        <h5>📊 Datos Extraídos:</h5>
                        <ul>
                            <li><strong>Nombre:</strong> ${cv.nombre || 'N/A'}</li>
                            <li><strong>Educación:</strong> ${cv.educacion?.doctorado ? 'Doctorado' : cv.educacion?.maestria ? 'Maestría' : 'Licenciatura'}</li>
                            <li><strong>Experiencia:</strong> ${cv.anos_experiencia || 0} años</li>
                            <li><strong>Exp. Docente:</strong> ${cv.experiencia_docente || 0} años</li>
                            <li><strong>Publicaciones:</strong> ${cv.publicaciones || 0}</li>
                        </ul>
                        ${resultado.diagnostico ? `
                        <h5>🔍 Diagnóstico:</h5>
                        <ul>
                            <li>URL accesible: ${resultado.diagnostico.url_accesible ? '✅' : '❌'}</li>
                            <li>Datos encontrados: ${resultado.diagnostico.datos_encontrados?.join(', ') || 'Ninguno'}</li>
                            ${resultado.diagnostico.datos_faltantes?.length > 0 ? `<li>Datos faltantes: ${resultado.diagnostico.datos_faltantes.join(', ')}</li>` : ''}
                            ${resultado.diagnostico.warnings?.length > 0 ? `<li class="warning">⚠️ ${resultado.diagnostico.warnings.join(', ')}</li>` : ''}
                        </ul>
                        ` : ''}
                        ${eval_data.clasificacion ? `
                        <h5>📋 Nueva Evaluación:</h5>
                        <ul>
                            <li><strong>Perfil:</strong> ${eval_data.clasificacion}</li>
                            <li><strong>Puntaje:</strong> ${total}/${maxPts} (${pct}%)</li>
                            <li><strong>C1:</strong> ${puntajes.C1||0} | <strong>C2:</strong> ${puntajes.C2||0} | <strong>C3:</strong> ${puntajes.C3||0} | <strong>C4:</strong> ${puntajes.C4||0} | <strong>C5:</strong> ${puntajes.C5||0}</li>
                            <li><strong>Elegible:</strong> ${eval_data.es_elegible ? '✅ Sí' : '❌ No'}</li>
                        </ul>
                        ` : ''}
                    </div>
                </div>
            `;
        } else {
            resultadoDiv.innerHTML = `
                <div class="resultado-error">
                    <h4>❌ Error en Re-análisis</h4>
                    <div class="diagnostico">
                        <h5>🔍 Diagnóstico del Problema:</h5>
                        <ul>
                            <li>URL accesible: ${resultado.diagnostico?.url_accesible ? '✅' : '❌'}</li>
                            ${resultado.diagnostico?.errores?.map(e => `<li class="error">❌ ${e}</li>`).join('') || ''}
                        </ul>
                        <p class="sugerencia">
                            <strong>💡 Sugerencia:</strong> Verifica que la URL del CTI Vitae sea correcta y 
                            que el perfil esté accesible públicamente.
                        </p>
                    </div>
                </div>
            `;
        }
        
    } catch (error) {
        const estadoDiv = modal.querySelector('.reanalisis-estado');
        const resultadoDiv = modal.querySelector('#reanalisis-resultado');
        
        estadoDiv.style.display = 'none';
        resultadoDiv.style.display = 'block';
        resultadoDiv.innerHTML = `
            <div class="resultado-error">
                <h4>❌ Error de Conexión</h4>
                <p>No se pudo conectar con el servidor: ${error.message}</p>
            </div>
        `;
    }
}

function cerrarModalReanalisis() {
    const modal = document.getElementById('modal-reanalisis');
    if (modal) {
        modal.remove();
    }
}

// ─── BÚSQUEDA EN LEGAJOS (CV FÍSICO) ────────────────────────────────────────

async function buscarCVEnLegajos(dni, nombre, facultad, carrera) {
    // Crear el modal de búsqueda en legajos
    const modalExistente = document.getElementById('modal-legajos');
    if (modalExistente) modalExistente.remove();

    const modal = document.createElement('div');
    modal.id = 'modal-legajos';
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content" style="max-width:680px">
            <div class="modal-header">
                <h3>📂 Buscar CV en Legajos</h3>
                <button class="modal-close" onclick="cerrarModalLegajos()">✕</button>
            </div>
            <div class="modal-body">
                <div class="reanalisis-estado" style="text-align:center;padding:30px">
                    <div class="spinner" style="margin:0 auto 16px"></div>
                    <p>Buscando CV de <strong>${nombre || dni}</strong> en el kit de contratación...</p>
                    <small style="color:#888">Esto puede tardar unos segundos mientras se analiza el PDF</small>
                </div>
                <div id="legajos-resultado" style="display:none"></div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    try {
        const response = await fetch('/api/buscar-cv-legajo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dni, nombre, facultad, carrera })
        });
        const resultado = await response.json();

        const estadoDiv = modal.querySelector('.reanalisis-estado');
        const resultadoDiv = modal.querySelector('#legajos-resultado');
        estadoDiv.style.display = 'none';
        resultadoDiv.style.display = 'block';

        if (!resultado.exito) {
            resultadoDiv.innerHTML = `
                <div class="resultado-error">
                    <h4>❌ Error al buscar en legajos</h4>
                    <p>${resultado.mensaje || 'Error desconocido en el servidor.'}</p>
                </div>
            `;
            return;
        }

        if (!resultado.encontrado) {
            // No se encontró → mostrar candidatos similares si hay
            let similaresHTML = '';
            if (resultado.candidatos_similares && resultado.candidatos_similares.length > 0) {
                similaresHTML = `
                    <h5>🔍 Carpetas similares encontradas:</h5>
                    <ul>
                        ${resultado.candidatos_similares.map(c =>
                            `<li><code>${c.nombre}</code> — puntaje similitud: ${c.score}</li>`
                        ).join('')}
                    </ul>
                    <p style="color:#888;font-size:0.85em">Ninguna superó el umbral mínimo de coincidencia. Verifica el nombre o DNI del candidato.</p>
                `;
            }
            resultadoDiv.innerHTML = `
                <div class="resultado-error">
                    <h4>📂 CV no encontrado en legajos</h4>
                    <p>${resultado.mensaje}</p>
                    ${similaresHTML}
                </div>
            `;
            return;
        }

        // ─── Encontrado con éxito ────────────────────────────
        const cv = resultado.cv_data || {};
        const evalData = resultado.evaluacion || {};

        const educStr = cv.educacion
            ? (cv.educacion.doctorado ? '🎓 Doctorado'
               : cv.educacion.maestria ? '🎓 Maestría'
               : cv.educacion.licenciatura ? '🎓 Licenciatura'
               : '—')
            : '—';

        const perfilStr = evalData.clasificacion
            ? `<li><strong>Perfil:</strong> ${evalData.clasificacion}</li>
               <li><strong>Puntaje:</strong> ${evalData.total || 0}/200 (${evalData.porcentaje || 0}%)</li>
               <li><strong>Elegible:</strong> ${evalData.es_elegible ? '✅ Sí' : '❌ No'}</li>
               ${(evalData.puntajes || {}).C1 !== undefined ? `
               <li><strong>Criterios:</strong> C1=${evalData.puntajes.C1}/50 | C2=${evalData.puntajes.C2}/40 | C3=${evalData.puntajes.C3}/40 | C4=${evalData.puntajes.C4}/20 | C5=${evalData.puntajes.C5}/50</li>` : ''}`
            : '<li>No se pudo evaluar con la rúbrica</li>';

        resultadoDiv.innerHTML = `
            <div class="resultado-exito">
                <h4>✅ CV encontrado en legajos</h4>
                <div class="diagnostico">
                    <h5>📁 Ubicación:</h5>
                    <ul>
                        <li><strong>Carpeta:</strong> <code>${resultado.nombre_carpeta}</code></li>
                        <li><strong>Archivo:</strong> <code>${resultado.archivo_cv}</code></li>
                    </ul>
                    <h5>📊 Datos extraídos del CV físico:</h5>
                    <ul>
                        <li><strong>Nombre detectado:</strong> ${cv.nombre || '(no detectado)'}</li>
                        <li><strong>Educación:</strong> ${educStr}</li>
                        <li><strong>Experiencia total:</strong> ${cv.anos_experiencia || 0} años</li>
                        <li><strong>Exp. docente:</strong> ${cv.experiencia_docente || 0} años</li>
                        <li><strong>Publicaciones:</strong> ${cv.publicaciones || 0}</li>
                        <li><strong>Idiomas:</strong> ${(cv.idiomas || []).join(', ') || '—'}</li>
                    </ul>
                    <h5>📋 Evaluación basada en CV físico:</h5>
                    <ul>
                        ${perfilStr}
                    </ul>
                </div>
            </div>
        `;

    } catch (error) {
        const estadoDiv = modal.querySelector('.reanalisis-estado');
        const resultadoDiv = modal.querySelector('#legajos-resultado');
        estadoDiv.style.display = 'none';
        resultadoDiv.style.display = 'block';
        resultadoDiv.innerHTML = `
            <div class="resultado-error">
                <h4>❌ Error de conexión</h4>
                <p>No se pudo conectar con el servidor: ${error.message}</p>
            </div>
        `;
    }
}

function cerrarModalLegajos() {
    const modal = document.getElementById('modal-legajos');
    if (modal) modal.remove();
}

// Mapa de colores por clasificación de perfil (compartido entre funciones)
const PERFIL_COLOR = {
    DOCENTE_INVESTIGADOR_HORAS:   '#1e3a8a',
    DOCENTE_INVESTIGADOR:          '#2563eb',
    DTC:                           '#0d9488',
    DTC_POTENCIAL:                 '#14b8a6',
    DTP:                           '#0891b2',
    DTP_POTENCIAL:                 '#22d3ee',
    PRACTITIONER:                  '#7c3aed',
    PROFESIONAL_POTENCIAL:         '#d97706',
    ACADEMICO_FORMACION:           '#f59e0b',
    ACEPTABLE:                     '#16a34a',
    EN_DESARROLLO:                 '#6b7280',
    NO_CALIFICA:                   '#dc2626',
    NO_ELEGIBLE:                   '#374151',
};

// Helper global: badge visual para tipo de perfil (accessible desde cualquier función)
function _badgeTipoPerfil(tipo) {
    const cfg = {
        clinico:      { icon: '🏥', label: 'Clínico',      color: '#dc2626' },
        investigador: { icon: '🔬', label: 'Investigador', color: '#2563eb' },
        industrial:   { icon: '🏭', label: 'Industrial',   color: '#b45309' },
        docente:      { icon: '📚', label: 'Docente',      color: '#0d9488' },
        general:      { icon: '👤', label: 'General',      color: '#6b7280' }
    };
    const c = cfg[tipo] || cfg.general;
    return `<span class="badge-tipo-perfil" style="background:${c.color};color:#fff;padding:2px 7px;border-radius:10px;font-size:0.75em;white-space:nowrap">${c.icon} ${c.label}</span>`;
}

// ─── INVESTIGAR PENDIENTE desde tabla de candidatos sin CTI ──────────────────────
async function investigarPendiente(btnEl) {
    const dni       = btnEl.dataset.dni;
    const nombre    = btnEl.dataset.nombre;
    const facultad  = btnEl.dataset.facultad;
    const carrera   = btnEl.dataset.carrera;
    const rowEl     = btnEl.closest('tr');

    const mostrarToast = (msg, tipo = 'info') => {
        const colores = { ok: '#22c55e', error: '#ef4444', info: '#6366f1', warn: '#f59e0b' };
        const t = document.createElement('div');
        t.style.cssText = `position:fixed;bottom:28px;right:28px;z-index:9999;
            background:${colores[tipo]||colores.info};color:#fff;
            padding:12px 20px;border-radius:10px;font-weight:600;
            box-shadow:0 4px 20px rgba(0,0,0,.3);font-size:0.95em;
            animation:fadeInUp .3s ease;max-width:400px;line-height:1.4;`;
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 6000);
    };

    btnEl.disabled = true;
    btnEl.classList.add('btn-investigando');
    btnEl.innerHTML = '🔄 Investigando y procesando...';

    try {
        const response = await fetch('/api/buscar-cv-web', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dni, nombre, facultad, carrera })
        });
        const resultado = await response.json();

        if (!resultado.encontrado || resultado.error) {
            btnEl.disabled = false;
            btnEl.classList.remove('btn-investigando');
            btnEl.innerHTML = '🔬 Investigar';
            mostrarToast(`Sin datos en internet para “${nombre}”`, 'warn');
            return;
        }

        const ev    = resultado.evaluacion || {};
        const conf  = resultado.score_confianza || 0;
        const total = ev.total || 0;
        const pct   = ev.porcentaje || 0;
        const clsRaw = ev.clasificacion || 'SIN CLASIFICAR';
        const clsKey  = clsRaw.split(' ')[0].split('(')[0];
        const clsColor = PERFIL_COLOR[clsKey] || '#34495e';
        const confColor = conf >= 60 ? '#22c55e' : conf >= 30 ? '#f59e0b' : '#ef4444';
        const numCell = rowEl.querySelector('.td-num')?.textContent || '';

        rowEl.classList.add('fila-recreada');
        rowEl.innerHTML = `
            <td class="td-num">${numCell}</td>
            <td class="td-nombre">
                <strong>${nombre}</strong>
                <span class="badge-recreado">❆ RECREADO</span>
            </td>
            <td class="td-dni">${dni || 'N/A'}</td>
            <td class="td-facultad">${facultad || 'N/A'}</td>
            <td class="td-motivo" style="background:none;border:none">
                <strong style="color:#1e40af;font-size:1em">${total}/200</strong>
                <small style="color:#6b7280"> (${pct}%)</small>
            </td>
            <td class="td-accion">
                <span style="display:inline-block;background:${clsColor};color:#fff;padding:4px 10px;border-radius:8px;font-size:0.78em;font-weight:700">${clsRaw}</span><br>
                <span style="display:inline-block;margin-top:4px;background:${confColor};color:#fff;padding:2px 8px;border-radius:8px;font-size:0.75em">Conf. ${conf}%</span>
            </td>
        `;

        mostrarToast(`❆ RECREADO · ${nombre} → ${clsRaw} (${total}/200)`, 'ok');

    } catch (err) {
        btnEl.disabled = false;
        btnEl.classList.remove('btn-investigando');
        btnEl.innerHTML = '🔬 Investigar';
        mostrarToast(`Error de conexión: ${err.message}`, 'error');
    }
}

// ─── BÚSQUEDA WEB EXPERIMENTAL (CV reconstruido desde internet) ──────────────

async function buscarCVEnWeb(dni, nombre, facultad, carrera, btnEl) {

    // ── Estado: botón en carga ───────────────────────────────────────────────
    const btnOrig = btnEl ? btnEl.textContent : '';
    if (btnEl) {
        btnEl.disabled = true;
        btnEl.textContent = '⏳';
        btnEl.title = 'Buscando en internet...';
    }

    // Encontrar la fila por DNI (tabla principal)
    const rowEl = btnEl ? btnEl.closest('tr') : document.querySelector(`tr[data-dni="${dni}"]`);

    // Toast si no hay fila
    const mostrarToast = (msg, tipo = 'info') => {
        const colores = { ok: '#22c55e', error: '#ef4444', info: '#6366f1', warn: '#f59e0b' };
        const t = document.createElement('div');
        t.style.cssText = `
            position:fixed;bottom:28px;right:28px;z-index:9999;
            background:${colores[tipo]||colores.info};color:#fff;
            padding:12px 20px;border-radius:10px;font-weight:600;
            box-shadow:0 4px 20px rgba(0,0,0,.3);font-size:0.95em;
            animation:fadeInUp .3s ease;max-width:400px;line-height:1.4;
        `;
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 6000);
    };

    try {
        const response = await fetch('/api/buscar-cv-web', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dni, nombre, facultad, carrera })
        });
        const resultado = await response.json();

        if (btnEl) { btnEl.disabled = false; btnEl.textContent = btnOrig; }

        // ── Error de servidor ────────────────────────────────────────────────
        if (resultado.error && !resultado.encontrado) {
            mostrarToast(`❌ Sin datos web: ${resultado.error || resultado.mensaje}`, 'error');
            return;
        }

        if (!resultado.encontrado) {
            mostrarToast(`🌐 Sin resultados en internet para "${nombre}"`, 'warn');
            return;
        }

        // ── ENCONTRADO — actualizar fila en-lugar ────────────────────────────
        const ev  = resultado.evaluacion || {};
        const cv  = resultado.cv_data    || {};
        const conf = resultado.score_confianza || 0;

        const puntajes   = ev.puntajes   || { C1:0, C2:0, C3:0, C4:0, C5:0, C6:0, C7:0 };
        const tipoPerfil = ev.tipo_perfil || 'general';
        const total      = ev.total       || 0;
        const pct        = ev.porcentaje  || 0;

        // Colores de perfil (mapa global)
        const clsRaw  = ev.clasificacion || '';
        const clsKey  = clsRaw.split(' ')[0].split('(')[0];
        const clsColor = PERFIL_COLOR[clsKey] || '#34495e';

        const confColor = conf >= 60 ? '#22c55e' : conf >= 30 ? '#f59e0b' : '#ef4444';
        const confLabel = conf >= 60 ? 'Alta' : conf >= 30 ? 'Media' : 'Baja';

        const fuentesHTML = (resultado.fuentes_urls || []).slice(0, 4)
            .map(u => `<a href="${u}" target="_blank" style="color:#818cf8;font-size:0.78em;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:300px">${u}</a>`)
            .join('') || '—';

        const elegibleBadge = ev.es_elegible
            ? '<span class="badge-elegible">✅ ELEGIBLE</span>'
            : '<span class="badge-no-elegible">❌ NO ELEGIBLE</span>';

        const dniTexto = dni ? `<small class="dni-text">DNI: ${dni}</small><br>` : '';

        if (rowEl) {
            // Reemplazar celdas en la fila existente (mantiene posición)
            const posNum = rowEl.querySelector('.ranking-num')?.textContent || '';
            const escapedDniRec    = (dni    || '').replace(/'/g, "\\'");
            const escapedNombreRec = (nombre || '').replace(/'/g, "\\'");
            const escapedFacRec    = (facultad || '').replace(/'/g, "\\'");
            const escapedCarRec    = (carrera  || '').replace(/'/g, "\\'");
            const maxPts = ev.maximo || 200;

            // Justificación para la columna td-justif
            const justifTextoRec = ev.justificacion_decision
                || (ev.clasificacion ? (ev.clasificacion.match(/\(([^)]+)\)/)?.[1] || '—') : '—');

            // Botón para volver a buscar desde web (re-run)
            const btnRewebRec = `<button class="btn-web-exp" onclick="buscarCVEnWeb('${escapedDniRec}','${escapedNombreRec}','${escapedFacRec}','${escapedCarRec}',this)" title="Volver a buscar en internet">🌐 Web</button>`;

            // Función auxiliar para renderizar la evidencia en la tabla
            const renderEvi = (det) => {
                if (!det) return '';
                const arr = Array.isArray(det.evidencias) ? det.evidencias : (Array.isArray(det.evidencia) ? det.evidencia : []);
                const valid = arr.filter(Boolean);
                if (!valid.length) return '';
                const items = valid.slice(0, 2).map(e => `• ${String(e).trim().substring(0, 60)}`).join('<br>');
                const plus = valid.length > 2 ? `<br><small style="color:#9ca3af">+${valid.length - 2} más</small>` : '';
                return `<div style="font-size:0.7em;color:#4b5563;margin-top:4px;line-height:1.2;text-align:left;max-width:180px;white-space:normal;word-break:break-word;">${items}${plus}</div>`;
            };

            rowEl.classList.add('fila-recreada');
            rowEl.innerHTML = `
                <td class="ranking-num">${posNum}</td>
                <td>
                    <strong>${nombre}</strong>
                    <span class="badge-recreado">✦ RECREADO</span><br>
                    ${dniTexto}
                    <span class="source-badge" style="background:#6366f1;color:#fff">WEB</span>
                    ${elegibleBadge}
                    ${btnRewebRec}
                    <div class="recreado-fuentes" style="margin-top:6px">${fuentesHTML}</div>
                    <div style="margin-top:4px">
                        <span style="background:${confColor};color:#fff;padding:2px 8px;border-radius:12px;font-size:0.75em;font-weight:600">
                            Conf. ${conf}%
                        </span>
                    </div>
                </td>
                <td class="td-tipo-perfil">${_badgeTipoPerfil(tipoPerfil)}</td>
                <td class="td-perfil">
                    <span class="badge-perfil" style="background:${clsColor}">${clsRaw || 'SIN CLASIFICAR'}</span>
                </td>
                <td class="td-puntaje"><strong>${total}/${maxPts}</strong> (${pct}%)</td>
                <td class="td-justif" style="font-size:0.82em;color:#374151;max-width:220px;word-wrap:break-word;white-space:normal">${justifTextoRec}</td>
                <td style="vertical-align:top">
                    <div style="font-weight:600">${puntajes.C1||0}/${ev.detalles?.formacion_academica?.maximo || 50}</div>
                    ${renderEvi(ev.detalles?.formacion_academica)}
                </td>
                <td style="vertical-align:top">
                    <div style="font-weight:600">${puntajes.C2||0}/${ev.detalles?.experiencia_docente?.maximo || 40}</div>
                    ${renderEvi(ev.detalles?.experiencia_docente)}
                </td>
                <td style="vertical-align:top">
                    <div style="font-weight:600">${puntajes.C3||0}/${ev.detalles?.experiencia_profesional?.maximo || 40}</div>
                    ${renderEvi(ev.detalles?.experiencia_profesional)}
                </td>
                <td style="vertical-align:top">
                    <div style="font-weight:600">${puntajes.C4||0}/${ev.detalles?.centro_labores?.maximo || 20}</div>
                    ${renderEvi(ev.detalles?.centro_labores)}
                </td>
                <td style="vertical-align:top">
                    <div style="font-weight:600">${puntajes.C5||0}/${ev.detalles?.produccion_academica?.maximo || 50}</div>
                    ${renderEvi(ev.detalles?.produccion_academica)}
                </td>
            `;
        }

        // Toast de éxito
        mostrarToast(
            `✦ RECREADO ✦  ${nombre}\n→ ${clsRaw || 'SIN CLASIFICAR'}  (${total}/200) · Confianza web: ${conf}%`,
            'ok'
        );

    } catch (err) {
        if (btnEl) { btnEl.disabled = false; btnEl.textContent = btnOrig; }
        mostrarToast(`❌ Error de conexión: ${err.message}`, 'error');
    }
}

function cerrarModalWebCV() {
    const modal = document.getElementById('modal-web-cv');
    if (modal) modal.remove();
}


const inicioScreen = document.getElementById('inicio-screen');
const procesandoScreen = document.getElementById('procesando-screen');
const resultadosScreen = document.getElementById('resultados-screen');
const errorScreen = document.getElementById('error-screen');

const btnIniciar = document.getElementById('btn-lanzar-analisis');
const btnNuevaEvaluacion = document.getElementById('btn-nueva-evaluacion');
const btnReintentar = document.getElementById('btn-reintentar');

// ── Modo nombres (búsqueda masiva por texto) ────────────────────────────────
let modoNombres = false;
let listaNombresParsed = [];

// ── Modo links (CTI Vitae agregados manualmente) ────────────────────────────
let modoLinks = false;
let listaLinksManual = [];

function seleccionarModo(modo) {
    modoNombres = (modo === 'nombres');
    modoLinks   = (modo === 'links');
    const panelArchivos = document.getElementById('panel-archivos');
    const panelNombres  = document.getElementById('panel-nombres');
    const panelLinks    = document.getElementById('panel-links');
    const tabArchivos   = document.getElementById('tab-archivos');
    const tabNombres    = document.getElementById('tab-nombres');
    const tabLinks      = document.getElementById('tab-links');
    if (panelArchivos) panelArchivos.style.display = (modoNombres || modoLinks) ? 'none' : 'block';
    if (panelNombres)  panelNombres.style.display  = modoNombres ? 'block' : 'none';
    if (panelLinks)    panelLinks.style.display    = modoLinks   ? 'block' : 'none';
    if (tabArchivos)   tabArchivos.classList.toggle('active', !modoNombres && !modoLinks);
    if (tabNombres)    tabNombres.classList.toggle('active',   modoNombres);
    if (tabLinks)      tabLinks.classList.toggle('active',     modoLinks);
}

function agregarLinkManual() {
    const input = document.getElementById('input-link-cti');
    if (!input) return;
    const url = input.value.trim();
    if (!url) return;
    try {
        new URL(url);
    } catch (e) {
        alert('⚠️ Ingresa un link válido (debe empezar con http:// o https://)');
        return;
    }
    if (listaLinksManual.includes(url)) {
        alert('⚠️ Ese link ya fue agregado');
        input.value = '';
        return;
    }
    listaLinksManual.push(url);
    input.value = '';
    input.focus();
    renderLinksManual();
}

function eliminarLinkManual(index) {
    listaLinksManual.splice(index, 1);
    renderLinksManual();
}

function limpiarLinksManuales() {
    listaLinksManual = [];
    renderLinksManual();
}

function renderLinksManual() {
    const countEl   = document.getElementById('links-count');
    const previewEl = document.getElementById('links-preview');
    if (countEl) {
        countEl.textContent = `${listaLinksManual.length} link${listaLinksManual.length !== 1 ? 's' : ''} agregado${listaLinksManual.length !== 1 ? 's' : ''}`;
    }
    if (previewEl) {
        if (listaLinksManual.length > 0) {
            previewEl.style.display = 'flex';
            previewEl.innerHTML = listaLinksManual.map((url, i) => `
                <span class="link-badge">
                    <span class="link-badge-url" title="${url}">${url}</span>
                    <button type="button" class="link-badge-quitar" onclick="eliminarLinkManual(${i})">✕</button>
                </span>
            `).join('');
        } else {
            previewEl.style.display = 'none';
            previewEl.innerHTML = '';
        }
    }
}

function parsearNombres() {
    const ta = document.getElementById('textarea-nombres');
    if (!ta) return;
    const lineas = ta.value.split('\n').map(l => l.trim()).filter(l => l.length > 1);
    listaNombresParsed = lineas;
    const countEl   = document.getElementById('nombres-count');
    const previewEl = document.getElementById('nombres-preview');
    if (countEl) countEl.textContent = `${lineas.length} nombre${lineas.length !== 1 ? 's' : ''} detectado${lineas.length !== 1 ? 's' : ''}`;
    if (previewEl) {
        if (lineas.length > 0) {
            previewEl.style.display = 'block';
            previewEl.innerHTML = lineas.slice(0, 10)
                .map((n, i) => `<span class="nombre-badge">${i+1}. ${n}</span>`)
                .join('') + (lineas.length > 10 ? `<span class="nombre-badge mas">+${lineas.length - 10} más</span>` : '');
        } else {
            previewEl.style.display = 'none';
            previewEl.innerHTML = '';
        }
    }
}

function limpiarNombres() {
    const ta = document.getElementById('textarea-nombres');
    if (ta) ta.value = '';
    listaNombresParsed = [];
    const countEl   = document.getElementById('nombres-count');
    const previewEl = document.getElementById('nombres-preview');
    if (countEl)   countEl.textContent = '0 nombres detectados';
    if (previewEl) { previewEl.style.display = 'none'; previewEl.innerHTML = ''; }
}

// Elementos de carga de archivo Excel
const uploadArea = document.getElementById('upload-area');
const archivoInput = document.getElementById('archivo-excel');
const btnSeleccionarArchivo = document.getElementById('btn-seleccionar-archivo');
const archivoSeleccionadoDiv = document.getElementById('archivo-seleccionado');
const nombreArchivoSpan = document.getElementById('nombre-archivo');
const btnQuitarArchivo = document.getElementById('btn-quitar-archivo');
const archivoInfoDiv = document.getElementById('archivo-info');
const archivoStatsP = document.getElementById('archivo-stats');

// Elementos de carga de carpeta PDFs
const uploadAreaPdfs = document.getElementById('upload-area-pdfs');
const archivosInput = document.getElementById('archivos-pdfs');
const btnSeleccionarCarpeta = document.getElementById('btn-seleccionar-carpeta');
const carpetaSeleccionadaDiv = document.getElementById('carpeta-seleccionada');
const nombreCarpetaSpan = document.getElementById('nombre-carpeta');
const btnQuitarCarpeta = document.getElementById('btn-quitar-carpeta');
const carpetaInfoDiv = document.getElementById('carpeta-info');
const carpetaStatsP = document.getElementById('carpeta-stats');

// Event Listeners
btnIniciar.addEventListener('click', iniciarEvaluacion);
btnNuevaEvaluacion.addEventListener('click', reiniciarApp);
btnReintentar.addEventListener('click', iniciarEvaluacion);

// Event Listeners para carga de archivo
if (btnSeleccionarArchivo) {
    btnSeleccionarArchivo.addEventListener('click', () => archivoInput.click());
}

if (uploadArea) {
    uploadArea.addEventListener('click', (e) => {
        if (e.target !== btnSeleccionarArchivo) {
            archivoInput.click();
        }
    });
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            procesarArchivosExcelSeleccionados(files);
        }
    });
}

if (archivoInput) {
    archivoInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            procesarArchivosExcelSeleccionados(e.target.files);
        }
    });
}

if (btnQuitarArchivo) {
    btnQuitarArchivo.addEventListener('click', quitarArchivo);
}

// Event Listeners para carga de carpeta PDFs
if (btnSeleccionarCarpeta) {
    btnSeleccionarCarpeta.addEventListener('click', () => archivosInput.click());
}

if (uploadAreaPdfs) {
    uploadAreaPdfs.addEventListener('click', (e) => {
        if (e.target !== btnSeleccionarCarpeta) {
            archivosInput.click();
        }
    });

    uploadAreaPdfs.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadAreaPdfs.classList.add('dragover');
    });

    uploadAreaPdfs.addEventListener('dragleave', () => {
        uploadAreaPdfs.classList.remove('dragover');
    });

    uploadAreaPdfs.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadAreaPdfs.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            procesarArchivosSeleccionados(files);
        }
    });
}

if (archivosInput) {
    archivosInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            procesarArchivosSeleccionados(e.target.files);
        }
    });
}

if (btnQuitarCarpeta) {
    btnQuitarCarpeta.addEventListener('click', quitarCarpeta);
}

async function procesarArchivosSeleccionados(files) {
    // Filtrar solo archivos PDF
    const archivosPdf = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
    
    if (archivosPdf.length === 0) {
        alert('⚠️ No se seleccionaron archivos PDF');
        return;
    }
    
    carpetaPdfsSeleccionada = archivosPdf;
    
    // Mostrar los archivos seleccionados
    uploadAreaPdfs.style.display = 'none';
    carpetaSeleccionadaDiv.style.display = 'flex';
    nombreCarpetaSpan.textContent = `${archivosPdf.length} archivos PDF seleccionados`;
    
    // Subir los archivos PDF al servidor
    await subirArchivosPdfs(archivosPdf);
}

async function procesarArchivosExcelSeleccionados(files) {
    const excels = Array.from(files).filter(f => {
        const ext = f.name.split('.').pop().toLowerCase();
        return ['xlsx', 'xls'].includes(ext);
    });

    if (excels.length === 0) {
        alert('⚠️ No se detectaron archivos Excel válidos (.xlsx/.xls)');
        return;
    }

    archivosExcelSeleccionados = excels;
    // Se procesa el primer archivo como principal para mantener compatibilidad backend.
    await procesarArchivoSeleccionado(excels[0], excels.length);
}

async function subirArchivosPdfs(archivos) {
    const formData = new FormData();
    formData.append('nombre_carpeta', 'PDFs_seleccionados');
    
    archivos.forEach((archivo, index) => {
        formData.append('archivos_pdf', archivo);
    });
    
    // Mostrar estado de carga
    carpetaInfoDiv.style.display = 'block';
    carpetaStatsP.innerHTML = `<span class="upload-loading"><span class="mini-loader"></span> Subiendo ${archivos.length} archivos PDF...</span>`;
    
    try {
        const response = await fetch('/subir-carpeta-pdfs', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            carpetaStatsP.innerHTML = `✅ ${data.mensaje}`;
            carpetaStatsP.style.color = '#2e7d32';
        } else {
            carpetaStatsP.innerHTML = `⚠️ ${data.error}`;
            carpetaStatsP.style.color = '#c62828';
        }
    } catch (error) {
        carpetaStatsP.innerHTML = `❌ Error al subir archivos: ${error.message}`;
        carpetaStatsP.style.color = '#c62828';
    }
}

function quitarCarpeta() {
    carpetaPdfsSeleccionada = null;
    archivosInput.value = '';
    uploadAreaPdfs.style.display = 'block';
    carpetaSeleccionadaDiv.style.display = 'none';
    carpetaInfoDiv.style.display = 'none';
    
    // Notificar al servidor que se quitó la carpeta
    fetch('/quitar-carpeta-pdfs', { method: 'POST' });
}

async function procesarArchivoSeleccionado(file, totalSeleccionados = 1) {
    // Validar extensión
    const extension = file.name.split('.').pop().toLowerCase();
    if (!['xlsx', 'xls'].includes(extension)) {
        alert('⚠️ Por favor selecciona un archivo Excel (.xlsx o .xls)');
        return;
    }
    
    archivoSeleccionado = file;
    
    // Mostrar el archivo seleccionado
    uploadArea.style.display = 'none';
    archivoSeleccionadoDiv.style.display = 'flex';
    nombreArchivoSpan.textContent = totalSeleccionados > 1
        ? `${file.name} (+${totalSeleccionados - 1} más)`
        : file.name;
    
    // Subir el archivo al servidor para validarlo
    await subirArchivo(file, totalSeleccionados);
}

async function subirArchivo(file, totalSeleccionados = 1) {
    const formData = new FormData();
    formData.append('archivo', file);
    
    // Mostrar estado de carga
    archivoInfoDiv.style.display = 'block';
    archivoStatsP.innerHTML = '<span class="upload-loading"><span class="mini-loader"></span> Analizando archivo...</span>';
    
    try {
        const response = await fetch('/subir-archivo', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            archivoStatsP.innerHTML = totalSeleccionados > 1
                ? `✅ ${data.mensaje} (seleccionados ${totalSeleccionados})`
                : `✅ ${data.mensaje}`;
            archivoStatsP.style.color = '#2e7d32';
        } else {
            archivoStatsP.innerHTML = `⚠️ ${data.error}`;
            archivoStatsP.style.color = '#c62828';
        }
    } catch (error) {
        archivoStatsP.innerHTML = `❌ Error al subir archivo: ${error.message}`;
        archivoStatsP.style.color = '#c62828';
    }
}

function quitarArchivo() {
    archivoSeleccionado = null;
    archivosExcelSeleccionados = [];
    archivoInput.value = '';
    uploadArea.style.display = 'block';
    archivoSeleccionadoDiv.style.display = 'none';
    archivoInfoDiv.style.display = 'none';
    
    // Notificar al servidor que se quitó el archivo
    fetch('/quitar-archivo', { method: 'POST' });
}

function mostrarPantalla(pantalla) {
    if (!pantalla) {
        console.error("mostrarPantalla: pantalla is null or undefined");
        return;
    }
    const screens = [inicioScreen, procesandoScreen, resultadosScreen, errorScreen];
    screens.forEach(s => {
        if (s && s.classList) {
            s.classList.remove('active');
        }
    });
    if (pantalla.classList) {
        pantalla.classList.add('active');
    } else {
        console.error("mostrarPantalla: screen is missing classList", pantalla);
    }
}

async function iniciarEvaluacion() {
    try {
        // Si estamos en modo nombres → búsqueda masiva web
        if (modoNombres) {
            await iniciarBusquedaMasivaNombres();
            return;
        }

        // Modo links → evaluar directamente los links de CTI Vitae pegados
        if (modoLinks && listaLinksManual.length === 0) {
            alert('⚠️ Agrega al menos un link de CTI Vitae');
            return;
        }

        // Nada seleccionado (ni Excel, ni carpeta de PDFs, ni links) — no tiene sentido
        // arrancar el análisis, evita el bucle de "Iniciando..." sin datos.
        if (!modoLinks && !archivoSeleccionado && !carpetaPdfsSeleccionada) {
            seleccionarModo('archivos');
            mostrarPantalla(inicioScreen);
            alert('⚠️ Antes de iniciar, selecciona un Excel o una carpeta de CVs (PDFs).');
            return;
        }

        // Feedback inmediato — deshabilitar botón antes de la petición
        if (btnIniciar) {
            btnIniciar.disabled = true;
            btnIniciar.textContent = '⏳ Iniciando...';
        }
        armBtnSafety(); // Safety: restaurar botón automáticamente si se queda pegado
        mostrarPantalla(procesandoScreen);
        
        // Configurar timeout de 10 segundos para la petición
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        try {
            console.log('='.repeat(60));
            console.log('🚀 INICIANDO EVALUACIÓN COMPLETA');
            console.log('📄 Procesando todos los PDFs de la carpeta Cvs/');
            console.log('🌐 Procesando todas las URLs del Excel');
            console.log('='.repeat(60));
            
            const requestBody = {
                usar_excel: true
            };

            // Si hay PDFs seleccionados PERO no hay un Excel seleccionado explícitamente en esta sesión
            if (carpetaPdfsSeleccionada && !archivoSeleccionado) {
                requestBody.usar_excel = false;
            }

            // Modo links: se agregan al flujo normal de evaluación (junto a Excel/PDFs si los hay)
            if (modoLinks && listaLinksManual.length > 0) {
                requestBody.links_manuales = listaLinksManual;
                if (!archivoSeleccionado && !carpetaPdfsSeleccionada) {
                    requestBody.usar_excel = false;
                }
            }

            // Iniciar el proceso (sin enviar URLs, se leen automáticamente del Excel)
            const response = await fetch('/iniciar-evaluacion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            const data = await response.json();
            
            if (data.status === 'iniciado') {
                // Comenzar a consultar el estado
                intervalId = setInterval(consultarEstado, 2000);  // 2 s en vez de 500 ms para no saturar logs
                disarmBtnSafety(); // Polling activo, ya no necesitamos el safety
                startStuckDetection();
            } else {
                // Restaurar botón si el estado devuelto no es iniciado
                if (btnIniciar) {
                    btnIniciar.disabled = false;
                    btnIniciar.textContent = '🚀 Iniciar Análisis de Talento';
                }
                mostrarError('Error al iniciar la evaluación: ' + (data.error || 'Respuesta inesperada del servidor.'));
            }
        } catch (error) {
            clearTimeout(timeoutId);
            // Restaurar botón en caso de error
            if (btnIniciar) {
                btnIniciar.disabled = false;
                btnIniciar.textContent = '🚀 Iniciar Análisis de Talento';
            }
            let mensajeError = error.message;
            if (error.name === 'AbortError') {
                mensajeError = 'El servidor tardó demasiado en responder (Timeout).';
            }
            mostrarError('Error al iniciar la evaluación: ' + mensajeError);
        }
    } catch (e) {
        console.error('Critical crash in iniciarEvaluacion:', e);
        if (btnIniciar) {
            btnIniciar.disabled = false;
            btnIniciar.textContent = '🚀 Iniciar Análisis de Talento';
        }
        mostrarError('Error crítico: ' + e.message);
    }
}

async function iniciarBusquedaMasivaNombres() {
    try {
        if (listaNombresParsed.length === 0) {
            alert('⚠️ Pega al menos un nombre en el área de texto');
            return;
        }
        if (btnIniciar) {
            btnIniciar.disabled = true;
            btnIniciar.textContent = '⏳ Iniciando...';
        }
        armBtnSafety(); // Safety: restaurar botón automáticamente si se queda pegado
        mostrarPantalla(procesandoScreen);
        
        // Configurar timeout de 10 segundos para la petición
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        try {
            const response = await fetch('/api/buscar-masivo-nombres', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nombres: listaNombresParsed }),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            const data = await response.json();
            if (data.status === 'iniciado') {
                intervalId = setInterval(consultarEstado, 2000);
                disarmBtnSafety(); // Polling activo, ya no necesitamos el safety
                startStuckDetection();
            } else {
                if (btnIniciar) { btnIniciar.disabled = false; btnIniciar.textContent = '🚀 Iniciar Análisis de Talento'; }
                mostrarError(data.error || 'Error al iniciar búsqueda masiva');
            }
        } catch (error) {
            clearTimeout(timeoutId);
            if (btnIniciar) { btnIniciar.disabled = false; btnIniciar.textContent = '🚀 Iniciar Análisis de Talento'; }
            let mensajeError = error.message;
            if (error.name === 'AbortError') {
                mensajeError = 'El servidor tardó demasiado en responder (Timeout).';
            }
            mostrarError('Error al iniciar búsqueda masiva: ' + mensajeError);
        }
    } catch (e) {
        console.error('Critical crash in iniciarBusquedaMasivaNombres:', e);
        if (btnIniciar) {
            btnIniciar.disabled = false;
            btnIniciar.textContent = '🚀 Iniciar Análisis de Talento';
        }
        mostrarError('Error crítico: ' + e.message);
    }
}

async function consultarEstado() {
    try {
        const response = await fetch('/estado?_t=' + new Date().getTime());
        const estado = await response.json();
        
        // Actualizar UI
        actualizarProgreso(estado);
        
        // Si ya avanzó, quitamos el botón de reiniciar por si acaso
        if (estado.paso_actual > 0 || estado.porcentaje > 5) {
            clearStuckDetection();
        }
        
        // Si terminó (con éxito o error)
        if (estado.completado) {
            clearInterval(intervalId);
            
            if (estado.error) {
                mostrarError(estado.error);
            } else if (estado.resultado) {
                mostrarResultados(estado.resultado);
            }
        }
    } catch (error) {
        clearInterval(intervalId);
        mostrarError('Error al consultar estado: ' + error.message);
    }
}

function actualizarProgreso(estado) {
    // Actualizar mensaje
    document.getElementById('mensaje-estado').textContent = estado.mensaje;
    
    // Actualizar barra de progreso
    document.getElementById('progress-fill').style.width = estado.porcentaje + '%';
    document.getElementById('porcentaje').textContent = estado.porcentaje;
    
    // Actualizar estadísticas en tiempo real
    const statsContainer = document.getElementById('stats-realtime');
    if (estado.cvs_total > 0) {
        statsContainer.style.display = 'grid';
        
        // Tiempo restante
        const tiempoRestante = document.getElementById('tiempo-restante');
        if (estado.tiempo_estimado_restante !== null && estado.tiempo_estimado_restante > 0) {
            if (estado.tiempo_estimado_restante < 60) {
                tiempoRestante.textContent = `${Math.round(estado.tiempo_estimado_restante)}s`;
            } else {
                const mins = Math.floor(estado.tiempo_estimado_restante / 60);
                const segs = Math.round(estado.tiempo_estimado_restante % 60);
                tiempoRestante.textContent = `${mins}m ${segs}s`;
            }
        } else if (estado.cvs_total > 0 && estado.cvs_procesados >= estado.cvs_total) {
            // Solo mostrar "¡Completado!" si realmente había CVs que procesar y ya terminaron
            tiempoRestante.textContent = '¡Completado!';
        } else if (estado.completado) {
            tiempoRestante.textContent = '¡Completado!';
        } else {
            tiempoRestante.textContent = 'Calculando...';
        }
        
        // CVs procesados
        document.getElementById('cvs-procesados').textContent = 
            `${estado.cvs_procesados || 0} / ${estado.cvs_total}`;
        
        // Exitosos y errores
        document.getElementById('cvs-exitosos').textContent = estado.cvs_exitosos || 0;
        document.getElementById('cvs-errores').textContent = estado.cvs_con_error || 0;
        
        // Velocidad
        const velocidad = estado.velocidad_cvs_por_segundo || 0;
        document.getElementById('velocidad-cvs').textContent = `${velocidad.toFixed(1)} CVs/seg`;
    } else {
        statsContainer.style.display = 'none';
    }
    
    // Actualizar pasos
    for (let i = 1; i <= 5; i++) {
        const pasoElement = document.getElementById(`paso-${i}`);
        const icono = pasoElement.querySelector('.icono');
        
        if (i < estado.paso_actual) {
            pasoElement.classList.add('completado');
            pasoElement.classList.remove('activo');
            icono.textContent = '✅';
        } else if (i === estado.paso_actual) {
            pasoElement.classList.add('activo');
            pasoElement.classList.remove('completado');
            icono.textContent = '⏳';
        } else {
            pasoElement.classList.remove('completado', 'activo');
            icono.textContent = '⏳';
        }
    }
    
    // Guardar registros con error globalmente para acceso posterior
    if (estado.registros_con_error && estado.registros_con_error.length > 0) {
        window.registrosConError = estado.registros_con_error;
        // Mostrar panel de registros con error con botón de enfoque
        mostrarPanelRegistrosConError(estado.registros_con_error);
    }
}

/**
 * Muestra el panel de registros con error, cada uno con un botón para enfocarse en él
 */
function mostrarPanelRegistrosConError(registros) {
    const panel = document.getElementById('panel-errores-individual');
    const lista = document.getElementById('lista-registros-error');
    const contador = document.getElementById('contador-errores-panel');
    
    if (!panel || !registros || registros.length === 0) {
        if (panel) panel.style.display = 'none';
        return;
    }
    
    // Mostrar panel y actualizar contador
    panel.style.display = 'block';
    contador.textContent = registros.length;
    
    // Limpiar lista anterior
    lista.innerHTML = '';
    
    // Agregar cada registro con su botón de enfoque
    registros.forEach((registro, index) => {
        const registroDiv = document.createElement('div');
        registroDiv.className = 'registro-error-item';
        registroDiv.id = `registro-error-${index}`;
        
        const nombreDisplay = registro.nombre || 'Sin nombre';
        const dniDisplay = registro.dni || 'N/A';
        const errorDisplay = registro.error || 'Error desconocido';
        const urlDisplay = registro.url || '';
        const facultadDisplay = registro.facultad || '';
        const carreraDisplay = registro.carrera || '';
        
        registroDiv.innerHTML = `
            <div class="registro-error-info">
                <div class="registro-error-numero">#${registro.indice || index + 1}</div>
                <div class="registro-error-datos">
                    <span class="registro-error-nombre">${nombreDisplay}</span>
                    <span class="registro-error-dni">DNI: ${dniDisplay}</span>
                    <span class="registro-error-mensaje">${errorDisplay.substring(0, 60)}${errorDisplay.length > 60 ? '...' : ''}</span>
                </div>
            </div>
            <button class="btn-enfocar-registro" onclick="enfocarRegistro('${urlDisplay}', '${dniDisplay}', '${nombreDisplay.replace(/'/g, "\\'")}', '${facultadDisplay.replace(/'/g, "\\'")}', '${carreraDisplay.replace(/'/g, "\\'")}', ${index})">
                🔍 ENFOCAR
            </button>
        `;
        
        lista.appendChild(registroDiv);
    });
}

/**
 * Enfoca en un registro específico para analizarlo a detalle
 */
function enfocarRegistro(url, dni, nombre, facultad, carrera, index) {
    // Resaltar el registro seleccionado
    document.querySelectorAll('.registro-error-item').forEach(item => {
        item.classList.remove('enfocado');
    });
    const registroItem = document.getElementById(`registro-error-${index}`);
    if (registroItem) {
        registroItem.classList.add('enfocado');
    }
    
    // Llamar a la función existente de re-análisis con modal detallado
    reanalizarRegistro(url, dni, nombre, facultad, carrera);
}

function mostrarResultados(resultado) {
        async function verHistorialPersona(dni, nombre) {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:760px">
                    <div class="modal-header">
                        <h3>🕘 Historial de análisis</h3>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
                    </div>
                    <div class="modal-body">
                        <p><strong>Persona:</strong> ${nombre || 'Sin nombre'} ${dni ? `(DNI ${dni})` : ''}</p>
                        <div id="historial-cuerpo">Cargando historial...</div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            try {
                const q = new URLSearchParams({ dni: dni || '', nombre: nombre || '' }).toString();
                const resp = await fetch(`/api/historial-persona?${q}`);
                const data = await resp.json();
                const body = modal.querySelector('#historial-cuerpo');

                if (!resp.ok) {
                    body.innerHTML = `<p style="color:#dc2626">${data.error || 'No se pudo consultar historial'}</p>`;
                    return;
                }

                const hist = data.historial || [];
                if (!hist.length) {
                    body.innerHTML = '<p>No hay historial registrado para esta persona.</p>';
                    return;
                }

                body.innerHTML = `
                    <div class="historial-lista">
                        ${hist.slice().reverse().map(h => `
                            <div class="historial-item">
                                <div><strong>${h.fecha || ''}</strong> · ${h.clasificacion || 'SIN CLASIFICAR'}</div>
                                <div>Puntaje: ${h.total || 0} (${h.porcentaje || 0}%) · ${h.es_elegible ? 'Elegible' : 'No elegible'}</div>
                                <div style="color:#64748b">Fuente: ${h.fuente_datos || 'N/A'} · ${h.facultad || 'N/A'} / ${h.carrera || 'N/A'}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
            } catch (e) {
                const body = modal.querySelector('#historial-cuerpo');
                body.innerHTML = `<p style="color:#dc2626">Error consultando historial: ${e.message}</p>`;
            }
        }

        window.verHistorialPersona = verHistorialPersona;

    mostrarPantalla(resultadosScreen);
    
    // Mapeo de nombres y estilos para visualización - PERFILES COMPLETOS
    const perfilesConfig = {
        // Investigadores (azules)
        'DOCENTE_INVESTIGADOR_HORAS (Elite investigador)': { nombre: '🔬 INVESTIGADOR ELITE', color: '#1e3a8a', orden: 1 },
        'DOCENTE_INVESTIGADOR (Investigador activo)': { nombre: '🔬 INVESTIGADOR', color: '#2563eb', orden: 2 },
        // DTC (verdes/teal)
        'DTC (Docente Tiempo Completo)': { nombre: '📚 DTC', color: '#0d9488', orden: 3 },
        'DTC_POTENCIAL (Requiere más experiencia)': { nombre: '📗 DTC POTENCIAL', color: '#14b8a6', orden: 4 },
        // DTP (cyan)
        'DTP (Docente Tiempo Parcial)': { nombre: '📖 DTP', color: '#0891b2', orden: 5 },
        'DTP_POTENCIAL (En desarrollo)': { nombre: '📘 DTP POTENCIAL', color: '#22d3ee', orden: 6 },
        // Practitioner (púrpura / rosa médico)
        'PRACTITIONER MÉDICO (Evaluación Especializada)': { nombre: '⚕️ PRACTITIONER MÉDICO', color: '#be185d', orden: 7 },
        'PRACTITIONER (Profesional docente)': { nombre: '💼 PRACTITIONER', color: '#7c3aed', orden: 8 },
        // Potenciales (naranja)
        'PROFESIONAL_POTENCIAL (Puede desarrollar perfil docente)': { nombre: '🌱 PROFESIONAL POTENCIAL', color: '#ea580c', orden: 9 },
        'ACADEMICO_FORMACION (Fortalecer experiencia)': { nombre: '🎓 ACADÉMICO FORMACIÓN', color: '#f97316', orden: 10 },
        // Aceptables (amarillo)
        'ACEPTABLE (Cumple mínimos básicos)': { nombre: '✓ ACEPTABLE', color: '#ca8a04', orden: 11 },
        // No elegibles (rojo/gris)
        'EN_DESARROLLO (Insuficiente para docencia)': { nombre: '⚠️ EN DESARROLLO', color: '#dc2626', orden: 12 },
        'NO_CALIFICA (Puntaje insuficiente)': { nombre: '❌ NO CALIFICA', color: '#991b1b', orden: 13 },
        'NO_ELEGIBLE (Sin formación ni producción)': { nombre: '⛔ NO ELEGIBLE', color: '#64748b', orden: 14 },
        'NO_ELEGIBLE (No alcanza puntaje mínimo Practitioner: 90 pts)': { nombre: '⛔ NO ELEGIBLE', color: '#64748b', orden: 14 }
    };
    
    // Función auxiliar para obtener config basándose en match parcial robusto
    function getPerfilConfig(clasificacion) {
        if (!clasificacion) return { nombre: 'Desconocido', color: '#475569', orden: 99 };
        const upperClasif = clasificacion.toUpperCase();
        
        // Mapeo flexible de palabras clave a la config de color y nombre
        if ((upperClasif.includes('DOCENTE INVESTIGADOR') || upperClasif.includes('DOCENTE_INVESTIGADOR')) && upperClasif.includes('HORAS')) return perfilesConfig['DOCENTE_INVESTIGADOR_HORAS (Elite investigador)'];
        if (upperClasif.includes('DOCENTE INVESTIGADOR') || upperClasif.includes('DOCENTE_INVESTIGADOR')) return perfilesConfig['DOCENTE_INVESTIGADOR (Investigador activo)'];
        if (upperClasif.includes('DTC_POTENCIAL') || upperClasif.includes('DTC POTENCIAL')) return perfilesConfig['DTC_POTENCIAL (Requiere más experiencia)'];
        if (upperClasif.includes('DTP_POTENCIAL') || upperClasif.includes('DTP POTENCIAL')) return perfilesConfig['DTP_POTENCIAL (En desarrollo)'];
        if (upperClasif.includes('DTC')) return perfilesConfig['DTC (Docente Tiempo Completo)'];
        if (upperClasif.includes('DTP')) return perfilesConfig['DTP (Docente Tiempo Parcial)'];
        if (upperClasif.includes('PRACTITIONER') && upperClasif.includes('MÉDICO')) return perfilesConfig['PRACTITIONER MÉDICO (Evaluación Especializada)'];
        if (upperClasif.includes('PRACTITIONER')) return perfilesConfig['PRACTITIONER (Profesional docente)'];
        if (upperClasif.includes('PROFESIONAL POTENCIAL')) return perfilesConfig['PROFESIONAL_POTENCIAL (Puede desarrollar perfil docente)'];
        if (upperClasif.includes('ACADEMICO') || upperClasif.includes('FORMACION')) return perfilesConfig['ACADEMICO_FORMACION (Fortalecer experiencia)'];
        if (upperClasif.includes('ACEPTABLE')) return perfilesConfig['ACEPTABLE (Cumple mínimos básicos)'];
        if (upperClasif.includes('EN DESARROLLO')) return perfilesConfig['EN_DESARROLLO (Insuficiente para docencia)'];
        if (upperClasif.includes('NO_CALIFICA') || upperClasif.includes('NO CALIFICA')) return perfilesConfig['NO_CALIFICA (Puntaje insuficiente)'];
        if (upperClasif.includes('NO_ELEGIBLE') || upperClasif.includes('NO ELEGIBLE')) return perfilesConfig['NO_ELEGIBLE (Sin formación ni producción)'];
        
        // Fallback si nada coincide
        return { nombre: clasificacion.split(' (')[0], color: '#475569', orden: 99 };
    }
    
    // Mostrar resumen por perfil
    const resumenContainer = document.getElementById('resumen-perfiles');
    resumenContainer.innerHTML = '';
    
    // Contar candidatos por perfil real
    const perfilesCuenta = {};
    resultado.evaluaciones.forEach(evaluacion => {
        const perfil = evaluacion.clasificacion;
        perfilesCuenta[perfil] = (perfilesCuenta[perfil] || 0) + 1;
    });
    
    // Ordenar perfiles por orden definido
    const perfilesOrdenados = Object.entries(perfilesCuenta).sort((a, b) => {
        const configA = getPerfilConfig(a[0]);
        const configB = getPerfilConfig(b[0]);
        return (configA.orden || 99) - (configB.orden || 99);
    });
    
    for (const [perfil, cantidad] of perfilesOrdenados) {
        const config = getPerfilConfig(perfil);
        const perfilCard = document.createElement('div');
        perfilCard.className = 'perfil-card';
        // Quitamos el borde directo y usamos la variable CSS para el pseudoelemento ::before
        perfilCard.style.setProperty('--kpi-color', config.color);
        
        // Limpiamos los emojis iniciales del nombre para que se vea más limpio
        const tituloLimpio = (config.nombre.replace(/^[\u2700-\u27BF\u1F000-\u1F9FF\u2600-\u26FF\s]+/, '').trim()) || config.nombre;
        
        perfilCard.innerHTML = `
            <div class="perfil-card-content">
                <h4>${tituloLimpio}</h4>
                <div class="kpi-row">
                    <div class="cantidad" style="color: ${config.color}">${cantidad}</div>
                    <small>candidato(s)</small>
                </div>
            </div>
        `;
        resumenContainer.appendChild(perfilCard);
    }
    
    // =============================================
    // ORDENAMIENTO: CONTROLES Y LÓGICA
    // =============================================
    
    // Verificar si ordenContainer ya existe y eliminarlo para recrearlo
    let ordenContainer = document.getElementById('orden-controles');
    if (ordenContainer) {
        ordenContainer.remove();
    }
    
    // Crear nuevo contenedor de controles
    ordenContainer = document.createElement('div');
    ordenContainer.id = 'orden-controles';
    ordenContainer.className = 'orden-controles';
    ordenContainer.innerHTML = `
        <span class="orden-label">Ordenar por:</span>
        <button id="btn-orden-excel" class="btn-orden active" title="Orden del archivo Excel">
            📋 Orden Excel
        </button>
        <button id="btn-orden-puntaje" class="btn-orden" title="Mayor puntaje primero">
            🏆 Por Puntaje
        </button>
        <button id="btn-orden-perfil" class="btn-orden" title="Agrupar por tipo de perfil">
            📊 Por Perfil
        </button>
    `;
    
    // Insertar después del buscador y antes de tabla-scroll
    const tablaSection = document.querySelector('.tabla-clasificacion-section');
    const buscadorContainer = tablaSection ? tablaSection.querySelector('.buscador-container') : null;
    const tablaScroll = tablaSection ? tablaSection.querySelector('.tabla-scroll') : null;
    
    if (tablaSection) {
        if (buscadorContainer && buscadorContainer.nextElementSibling) {
            // Insertar después del buscador
            buscadorContainer.after(ordenContainer);
        } else if (tablaScroll) {
            // Insertar antes del scroll de tabla
            tablaScroll.before(ordenContainer);
        } else {
            // Como última opción, agregar al final de la sección
            tablaSection.appendChild(ordenContainer);
        }
    }
    
    // Estado de orden actual (por defecto: orden del Excel)
    let ordenActual = window.ordenActual || 'excel';
    
    // Función para ordenar evaluaciones
    function ordenarEvaluaciones(evaluaciones, criterio) {
        const copia = [...evaluaciones];
        switch(criterio) {
            case 'excel':
                // Ordenar por índice original del Excel
                return copia.sort((a, b) => (a.indice_original || 0) - (b.indice_original || 0));
            case 'puntaje':
                // Ordenar por puntaje descendente
                return copia.sort((a, b) => (b.total || 0) - (a.total || 0));
            case 'perfil':
                // Agrupar por perfil (investigadores primero, luego DTC, etc.)
                const ordenPerfil = {
                    'DOCENTE_INVESTIGADOR_HORAS': 1,
                    'DOCENTE_INVESTIGADOR': 2,
                    'DTC': 3,
                    'DTC_POTENCIAL': 4,
                    'DTP': 5,
                    'DTP_POTENCIAL': 6,
                    'PRACTITIONER_MEDICO': 7,
                    'PRACTITIONER': 8,
                    'PRACTITIONER_JUNIOR': 9,
                    'PROFESIONAL_POTENCIAL': 10,
                    'ACADEMICO_FORMACION': 11,
                    'ACEPTABLE': 11,
                    'EN_DESARROLLO': 12,
                    'NO_CALIFICA': 13,
                    'NO_ELEGIBLE': 99
                };
                return copia.sort((a, b) => {
                    const prefA = (a.clasificacion || '').split(' ')[0].split('(')[0];
                    const prefB = (b.clasificacion || '').split(' ')[0].split('(')[0];
                    const ordenA = ordenPerfil[prefA] || 50;
                    const ordenB = ordenPerfil[prefB] || 50;
                    if (ordenA !== ordenB) return ordenA - ordenB;
                    return (b.total || 0) - (a.total || 0); // Dentro del mismo perfil, por puntaje
                });
            default:
                return copia;
        }
    }
    
    // Función para actualizar la tabla
    function actualizarTabla(evaluaciones) {
        const tbody = document.getElementById('tabla-clasificacion-tbody');
        tbody.innerHTML = '';
        renderizarFilas(evaluaciones, tbody);
        aplicarFiltros();
    }
    
    // Event listeners para botones de orden
    document.getElementById('btn-orden-excel').onclick = () => {
        window.ordenActual = 'excel';
        document.querySelectorAll('.btn-orden').forEach(b => b.classList.remove('active'));
        document.getElementById('btn-orden-excel').classList.add('active');
        actualizarTabla(ordenarEvaluaciones(resultado.evaluaciones, 'excel'));
    };
    
    document.getElementById('btn-orden-puntaje').onclick = () => {
        window.ordenActual = 'puntaje';
        document.querySelectorAll('.btn-orden').forEach(b => b.classList.remove('active'));
        document.getElementById('btn-orden-puntaje').classList.add('active');
        actualizarTabla(ordenarEvaluaciones(resultado.evaluaciones, 'puntaje'));
    };
    
    document.getElementById('btn-orden-perfil').onclick = () => {
        window.ordenActual = 'perfil';
        document.querySelectorAll('.btn-orden').forEach(b => b.classList.remove('active'));
        document.getElementById('btn-orden-perfil').classList.add('active');
        actualizarTabla(ordenarEvaluaciones(resultado.evaluaciones, 'perfil'));
    };
    
    // Ordenar según criterio actual (por defecto: Excel)
    const evaluacionesOrdenadas = ordenarEvaluaciones(resultado.evaluaciones, ordenActual);
    
    // Mostrar tabla de ranking completo
    const tbody = document.getElementById('tabla-clasificacion-tbody');
    tbody.innerHTML = '';
    
    // NUEVO: Recopilar opciones únicas para los filtros
    const opcionesUnicas = {
        facultad: new Set(),
        tipoCandidato: new Set(),
        puesto: new Set(),
        catPractitioner: new Set(),
        perfil: new Set()
    };

    resultado.evaluaciones.forEach(ev => {
        if (ev.facultad) opcionesUnicas.facultad.add(ev.facultad.toUpperCase().trim());
        if (ev.tipo_candidato) opcionesUnicas.tipoCandidato.add(ev.tipo_candidato.toUpperCase().trim());
        if (ev.puesto) opcionesUnicas.puesto.add(ev.puesto.toUpperCase().trim());
        if (ev.categoria_practitioner) opcionesUnicas.catPractitioner.add(ev.categoria_practitioner.toUpperCase().trim());
        if (ev.clasificacion) opcionesUnicas.perfil.add(getPerfilConfig(ev.clasificacion).nombre);
    });

    // Función auxiliar para poblar los selects
    const poblarSelect = (id, setValores) => {
        const select = document.getElementById(id);
        if (!select) return;
        // Limpiar opciones previas (excepto la primera)
        while (select.options.length > 1) select.remove(1);
        Array.from(setValores).sort().forEach(val => {
            if (!val) return;
            const option = document.createElement('option');
            option.value = val;
            option.textContent = val;
            select.appendChild(option);
        });
    };

    poblarSelect('filtro-facultad', opcionesUnicas.facultad);
    poblarSelect('filtro-tipo-candidato', opcionesUnicas.tipoCandidato);
    poblarSelect('filtro-puesto', opcionesUnicas.puesto);
    poblarSelect('filtro-cat-practitioner', opcionesUnicas.catPractitioner);
    poblarSelect('filtro-perfil', opcionesUnicas.perfil);

    // Si el Excel no traía datos para un filtro, deshabilitarlo y explicar por qué
    // (antes quedaba un select "mudo" que parecía roto)
    ['filtro-facultad', 'filtro-tipo-candidato', 'filtro-puesto', 'filtro-cat-practitioner'].forEach(id => {
        const sel = document.getElementById(id);
        if (!sel) return;
        const sinDatos = sel.options.length <= 1 ||
            (id === 'filtro-facultad' && sel.options.length === 2 && sel.options[1].value === 'ARCHIVO SUBIDO');
        sel.disabled = sinDatos;
        sel.title = sinDatos
            ? 'Sin datos: el archivo cargado no incluía esta columna (FACULTAD / TIPO DE CANDIDATO / PUESTO / CAT. PRACTITIONER)'
            : '';
        sel.style.opacity = sinDatos ? '0.5' : '1';
    });
    
    // Función para renderizar filas (reutilizable)
    function renderizarFilas(evaluaciones, tbody) {
    evaluaciones.forEach((evaluacion, index) => {
        const row = document.createElement('tr');
        
        // NUEVO: Detectar si tiene información incompleta
        const tieneProblemas = evaluacion.info_incompleta || 
                               evaluacion.perfil_desactualizado || 
                               evaluacion.perfil_vacio;
        
        if (tieneProblemas) {
            row.classList.add('fila-problema');
        }
        
        // Determinar emoji de posición (mostrar índice Excel si está disponible)
        const indiceExcel = evaluacion.indice_original || (index + 1);
        let posEmoji = `${indiceExcel}`;
        // Solo mostrar medallas si está ordenado por puntaje
        if (window.ordenActual === 'puntaje') {
            if (index === 0) posEmoji = '🥇';
            else if (index === 1) posEmoji = '🥈';
            else if (index === 2) posEmoji = '🥉';
        }
        
        // Determinar fuente (PDF, Web o Combinado)
        const esPDF = evaluacion.archivo && evaluacion.archivo.toLowerCase().endsWith('.pdf');
        const esCombinado = evaluacion.fuente_datos === 'COMBINADO';
        let fuenteTexto = '';
        
        const url_link = evaluacion.url || evaluacion.link_cti || '';
        const link_html = url_link ? `<a href="${url_link}" target="_blank" class="source-badge link" style="text-decoration: none; cursor: pointer;">LINK</a>` : `<span class="source-badge link">LINK</span>`;
        
        if (esCombinado) {
            fuenteTexto = `<span class="source-badge combinado" title="Datos de PDF + CTI Vitae">📋+🌐</span> ${link_html}`;
        } else if (esPDF) {
            fuenteTexto = `<span class="source-badge cv">CV</span>`;
        } else {
            fuenteTexto = link_html;
        }
        
        // NUEVO: Indicador de problemas del perfil con botón de re-análisis
        let warningBadge = '';
        let btnReanalizar = '';
        
        // Detectar si el nombre indica error
        const nombreEsError = evaluacion.nombre === 'Error al extraer' || 
                              evaluacion.nombre === 'Nombre no encontrado' ||
                              !evaluacion.nombre;
        
        // Determinar si tiene problemas que requieren re-análisis
        const tieneError = evaluacion.error_extraccion || nombreEsError;
        const tieneProblemasVacio = evaluacion.perfil_vacio;
        const tieneProblemasDesactualizado = evaluacion.perfil_desactualizado;
        
        // URL para re-análisis - usar cualquier URL disponible
        const urlParaReanalisis = evaluacion.url || evaluacion.link_cti || '';
        const escapedNombre = (evaluacion.nombre || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const escapedDni = (evaluacion.dni || '').replace(/'/g, "\\'");
        const escapedFacultad = (evaluacion.facultad || '').replace(/'/g, "\\'");
        const escapedCarrera = (evaluacion.carrera || '').replace(/'/g, "\\'");
        
        // Siempre generar botón de re-análisis si hay problemas
        const generarBotonReanalizar = (texto = '🔄 Re-analizar') => {
            // Siempre mostrar el botón, incluso sin URL (para mostrar diagnóstico)
            return `<button class="btn-reanalizar" onclick="reanalizarRegistro('${urlParaReanalisis}', '${escapedDni}', '${escapedNombre}', '${escapedFacultad}', '${escapedCarrera}')" title="Re-analizar este registro">${texto}</button>`;
        };
        
        if (tieneError) {
            warningBadge = `<span class="badge-warning error" title="Error al extraer datos">❌ ERROR</span>`;
            btnReanalizar = generarBotonReanalizar('🔄 Re-analizar');
        } else if (tieneProblemasDesactualizado) {
            const meses = evaluacion.meses_sin_actualizar || '?';
            warningBadge = `<span class="badge-warning" title="Perfil desactualizado hace ${meses} meses">⚠️ ${meses}m</span>`;
            btnReanalizar = generarBotonReanalizar('🔄 Re-analizar');
        } else if (tieneProblemasVacio) {
            warningBadge = `<span class="badge-warning vacio" title="Perfil CTI vacío o en construcción">📭 VACÍO</span>`;
            btnReanalizar = generarBotonReanalizar('🔄 Re-analizar');
        }
        
        // Botón para buscar CV físico en legajos/kit de contratación
        const btnLegajos = `<button class="btn-legajo" onclick="buscarCVEnLegajos('${escapedDni}', '${escapedNombre}', '${escapedFacultad}', '${escapedCarrera}')" title="Buscar CV físico en el kit de contratación">📂 Legajos</button>`;
        const btnHistorial = '';
        
        // Badge del perfil con color
        // CONFIGURACIÓN DE COLORES POR PERFIL (actualizada con todos los perfiles)
        const perfilesConfig = {
            // INVESTIGADORES - Tonos azules
            'DOCENTE_INVESTIGADOR_HORAS (Elite investigador)': { nombre: '🔬 INVESTIGADOR ELITE', color: '#1e3a8a' },
            'DOCENTE_INVESTIGADOR (Investigador activo)': { nombre: '🔬 INVESTIGADOR', color: '#2563eb' },
            
            // DTC - Tonos verde azulado
            'DTC (Docente Tiempo Completo)': { nombre: '📚 DTC', color: '#0d9488' },
            'DTC_POTENCIAL (Requiere más experiencia)': { nombre: '📗 DTC POTENCIAL', color: '#14b8a6' },
            'DTC/DTP (Docente Tiempo Completo/Parcial)': { nombre: '📚 DTC/DTP', color: '#0d9488' },
            
            // DTP - Tonos cyan
            'DTP (Docente Tiempo Parcial)': { nombre: '📖 DTP', color: '#0891b2' },
            'DTP_POTENCIAL (En desarrollo)': { nombre: '📘 DTP POTENCIAL', color: '#22d3ee' },
            
            // PRACTITIONER - Tonos púrpura/violeta/rosa
            'PRACTITIONER MÉDICO (Evaluación Especializada)': { nombre: '⚕️ PRACTITIONER MÉDICO', color: '#be185d' },
            'PRACTITIONER (Profesional docente)': { nombre: '💼 PRACTITIONER', color: '#7c3aed' },
            
            // POTENCIALES - Tonos naranja/ámbar
            'PROFESIONAL_POTENCIAL (Puede desarrollar perfil docente)': { nombre: '🌟 POTENCIAL PRO', color: '#d97706' },
            'ACADEMICO_FORMACION (Fortalecer experiencia)': { nombre: '🎓 EN FORMACIÓN', color: '#f59e0b' },
            
            // ACEPTABLES - Verde
            'ACEPTABLE (Cumple mínimos básicos)': { nombre: '✅ ACEPTABLE', color: '#16a34a' },
            
            // EN DESARROLLO - Gris
            'EN_DESARROLLO (Insuficiente para docencia)': { nombre: '⏳ EN DESARROLLO', color: '#6b7280' },
            
            // NO CALIFICA - Rojo/Gris oscuro
            'NO_CALIFICA (Puntaje insuficiente)': { nombre: '❌ NO CALIFICA', color: '#dc2626' },
            'NO_ELEGIBLE (Sin formación ni producción)': { nombre: '⛔ NO ELEGIBLE', color: '#374151' },
            'NO_ELEGIBLE_PERFIL_DOCENTE': { nombre: '⛔ NO ELEGIBLE', color: '#374151' },
            
            // LEGADOS (para compatibilidad)
            'CON_HORAS_INVESTIGACION': { nombre: '🔬 INVESTIGADOR+', color: '#1e3a8a' },
            'DOCENTE_INVESTIGADOR': { nombre: '🔬 INVESTIGADOR', color: '#2563eb' },
            'DTC': { nombre: '📚 DTC', color: '#0d9488' },
            'DTP': { nombre: '📖 DTP', color: '#0891b2' },
            'PRACTITIONER MÉDICO': { nombre: '⚕️ PRACTITIONER MÉDICO', color: '#be185d' },
            'PRACTITIONER': { nombre: '💼 PRACTITIONER', color: '#7c3aed' },
            'NO_CALIFICA': { nombre: '❌ NO CALIFICA', color: '#dc2626' }
        };
        const configPerfil = getPerfilConfig(evaluacion.clasificacion);
        const perfilBadge = `<span class="badge-perfil" style="background-color: ${configPerfil.color}">${configPerfil.nombre}</span>`;
        
        // Badge de elegibilidad
        const elegibleBadge = evaluacion.es_elegible 
            ? '<span class="badge-elegible">✅ ELEGIBLE</span>' 
            : '<span class="badge-no-elegible">❌ NO ELEGIBLE</span>';
        
        // Mostrar DNI si existe
        const dniTexto = evaluacion.dni ? `<small class="dni-text">DNI: ${evaluacion.dni}</small><br>` : '';
        
        // Agregar data-search para búsqueda mejorada
        const dataSearch = [
            evaluacion.nombre || '',
            evaluacion.dni || '',
            evaluacion.facultad || '',
            evaluacion.carrera || '',
            evaluacion.clasificacion || '',
            configPerfil.nombre || '',
            evaluacion.tipo_perfil || '',
            evaluacion.es_elegible ? 'elegible' : 'no elegible'
        ].join(' ');
        
        row.setAttribute('data-search', dataSearch);
        row.setAttribute('data-dni', evaluacion.dni || '');
        row.setAttribute('data-facultad', (evaluacion.facultad || '').toUpperCase().trim());
        row.setAttribute('data-tipo-candidato', (evaluacion.tipo_candidato || '').toUpperCase().trim());
        row.setAttribute('data-puesto', (evaluacion.puesto || '').toUpperCase().trim());
        row.setAttribute('data-cat-practitioner', (evaluacion.categoria_practitioner || '').toUpperCase().trim());
        row.setAttribute('data-perfil', configPerfil.nombre || '');
        row.setAttribute('data-elegible', evaluacion.es_elegible ? '1' : '0');
        row.setAttribute('data-porcentaje', String(parseFloat(evaluacion.porcentaje) || 0));
        row.setAttribute('data-anos-docencia', String(parseFloat(evaluacion.detalles?.experiencia_docente?.anos_detectados) || 0));

        // Botón Web experimental — solo para candidatos con ERROR
        const btnWebExp = tieneError
            ? `<button class="btn-web-exp" onclick="buscarCVEnWeb('${escapedDni}', '${escapedNombre}', '${escapedFacultad}', '${escapedCarrera}', this)" title="Reconstruir CV desde internet y reclasificar">🌐 Web</button>`
            : '';

        // Badge RECREADO si ya fue procesado desde web
        const badgeRecreado = evaluacion.reconstruido_web
            ? `<span class="badge-recreado">✦ RECREADO</span>`
            : '';

        // Justificación: usar justificacion_decision (AI) o extraer texto entre paréntesis del perfil
        const justifTexto = evaluacion.justificacion_decision
            || (evaluacion.clasificacion ? (evaluacion.clasificacion.match(/\(([^)]+)\)/)?.[1] || '—') : '—');

        // Función auxiliar para renderizar la evidencia en la tabla
        const renderEvi = (det) => {
            if (!det) return '';
            const arr = Array.isArray(det.evidencias) ? det.evidencias : (Array.isArray(det.evidencia) ? det.evidencia : []);
            const valid = arr.filter(Boolean);
            if (!valid.length) return '';
            const items = valid.slice(0, 2).map(e => `• ${String(e).trim().substring(0, 60)}`).join('<br>');
            const plus = valid.length > 2 ? `<br><small style="color:#9ca3af">+${valid.length - 2} más</small>` : '';
            return `<div style="font-size:0.7em;color:#4b5563;margin-top:4px;line-height:1.2;text-align:left;max-width:180px;white-space:normal;word-break:break-word;">${items}${plus}</div>`;
        };

        row.innerHTML = `
            <td class="ranking-num">${posEmoji}</td>
            <td>
                <strong>${evaluacion.nombre}</strong> ${badgeRecreado} ${warningBadge} ${btnReanalizar} ${btnWebExp} ${btnLegajos} ${btnHistorial}<br>
                ${dniTexto}${fuenteTexto} ${elegibleBadge}
            </td>
            <td class="td-tipo-perfil">${_badgeTipoPerfil(evaluacion.tipo_perfil)}</td>
            <td class="td-perfil">${perfilBadge}</td>
            <td class="td-puntaje"><strong>${evaluacion.total}/${evaluacion.maximo || 200}</strong> (${evaluacion.porcentaje}%)</td>
            <td class="td-justif" style="font-size:0.82em;color:#374151;max-width:220px;word-wrap:break-word;white-space:normal">${justifTexto}</td>
            <td style="vertical-align:top">
                <div style="font-weight:600">${evaluacion.puntajes.C1}/${evaluacion.detalles?.formacion_academica?.maximo || 50}</div>
                ${renderEvi(evaluacion.detalles?.formacion_academica)}
            </td>
            <td style="vertical-align:top">
                <div style="font-weight:600">${evaluacion.puntajes.C2}/${evaluacion.detalles?.experiencia_docente?.maximo || 40}</div>
                ${renderEvi(evaluacion.detalles?.experiencia_docente)}
            </td>
            <td style="vertical-align:top">
                <div style="font-weight:600">${evaluacion.puntajes.C3}/${evaluacion.detalles?.experiencia_profesional?.maximo || 40}</div>
                ${renderEvi(evaluacion.detalles?.experiencia_profesional)}
            </td>
            <td style="vertical-align:top">
                <div style="font-weight:600">${evaluacion.puntajes.C4}/${evaluacion.detalles?.centro_labores?.maximo || 20}</div>
                ${renderEvi(evaluacion.detalles?.centro_labores)}
            </td>
            <td style="vertical-align:top">
                <div style="font-weight:600">${evaluacion.puntajes.C5}/${evaluacion.detalles?.produccion_academica?.maximo || 50}</div>
                ${renderEvi(evaluacion.detalles?.produccion_academica)}
            </td>
        `;
        tbody.appendChild(row);
    });
    } // Fin de renderizarFilas
    
    // Llamar a renderizarFilas con las evaluaciones ordenadas
    renderizarFilas(evaluacionesOrdenadas, tbody);
    
    // Configurar filtros y buscador.
    // Antes había DOS implementaciones de filtrado en paralelo (esta con
    // style.display y filtrarTablaRanking con la clase hidden-row), que
    // podían dejar filas ocultas de forma inconsistente. Ahora hay UNA sola:
    // filtrarTablaRanking (global), y esta función solo delega.
    function aplicarFiltros() {
        filtrarTablaRanking();
    }
    // Los listeners de los filtros se registran una sola vez en
    // inicializarBuscadorRanking() (DOMContentLoaded); no se duplican aquí.

    const btnLimpiar = document.getElementById('btn-limpiar-busqueda');
    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', () => {
            const buscador = document.getElementById('buscador-ranking');
            if (buscador) buscador.value = '';
            aplicarFiltros();
            btnLimpiar.style.display = 'none';
        });
        const buscador = document.getElementById('buscador-ranking');
        if (buscador) {
            buscador.addEventListener('input', (e) => {
                btnLimpiar.style.display = e.target.value ? 'block' : 'none';
            });
        }
    }
    
    // Mostrar detalles expandidos de cada candidato
    const detallesContainer = document.getElementById('detalles-candidatos');
    detallesContainer.innerHTML = '<h3>📝 Detalles por Candidato</h3>';
    
    resultado.evaluaciones.forEach((evaluacion) => {
        const detalleDiv = document.createElement('div');
        detalleDiv.className = 'candidato-detalle';
        
        let criteriosHTML = '';
        
        // Validar que existan detalles antes de acceder
        const detalles = evaluacion.detalles || {};
        const puntajes = evaluacion.puntajes || {};

        // Helper: construye el bloque visual de un criterio con justificación + evidencia + auditoria
        function _criterioHTML(label, pts, max, det) {
            const justif = det?.justificacion || 'Sin información para este criterio';
            const arrayEvidencias = Array.isArray(det?.evidencias) ? det.evidencias : (Array.isArray(det?.evidencia) ? det.evidencia : []);
            const rawEvi = arrayEvidencias.filter(Boolean);
            const eviItems = rawEvi.map(e => `<span class="evidencia-item">✅ ${String(e).trim().substring(0, 150)}</span>`).join('');
            const eviHTML = eviItems ? `<div class="evidencia-list">${eviItems}</div>` : '';
            return `<div class="criterio-detalle"><span class="nombre">${label}</span><span class="puntaje">${pts} / ${max}</span><small class="justif-text">💬 ${justif}</small>${eviHTML}</div>`;
        }

        criteriosHTML += _criterioHTML('C1 – Formación Académica',   puntajes.C1 || 0, detalles.formacion_academica?.maximo || 50, detalles.formacion_academica || detalles.C1);
        criteriosHTML += _criterioHTML('C2 – Experiencia Docente',    puntajes.C2 || 0, detalles.experiencia_docente?.maximo || 40, detalles.experiencia_docente || detalles.C2);
        criteriosHTML += _criterioHTML('C3 – Experiencia Profesional',puntajes.C3 || 0, detalles.experiencia_profesional?.maximo || 40, detalles.experiencia_profesional || detalles.C3);
        criteriosHTML += _criterioHTML('C4 – Centro de Labores',      puntajes.C4 || 0, detalles.centro_labores?.maximo || 20, detalles.centro_labores || detalles.C4);
        criteriosHTML += _criterioHTML('C5 – Producción Académica',   puntajes.C5 || 0, detalles.produccion_academica?.maximo || 50, detalles.produccion_academica || detalles.C5);
        
        // Mostrar información faltante si existe
        let infoFaltanteHTML = '';
        if (evaluacion.info_faltante) {
            const info = evaluacion.info_faltante;
            
            // Criterios sin información (críticos)
            if (info.criterios_faltantes && info.criterios_faltantes.length > 0) {
                infoFaltanteHTML += '<div class="info-faltante critica">';
                infoFaltanteHTML += '<strong>⚠️ Información Faltante (Crítico):</strong><ul>';
                info.criterios_faltantes.forEach(c => {
                    infoFaltanteHTML += `<li><strong>${c.nombre || 'Criterio'}</strong>: ${c.justificacion || 'Sin detalles'}</li>`;
                });
                infoFaltanteHTML += '</ul></div>';
            }
            
            // Criterios con información baja
            if (info.criterios_bajos && info.criterios_bajos.length > 0) {
                infoFaltanteHTML += '<div class="info-faltante baja">';
                infoFaltanteHTML += '<strong>📝 Información Incompleta:</strong><ul>';
                info.criterios_bajos.forEach(c => {
                    infoFaltanteHTML += `<li><strong>${c.nombre || 'Criterio'}</strong>: ${c.puntaje || 0}/${c.maximo || 0} pts (${c.porcentaje || 0}%)</li>`;
                });
                infoFaltanteHTML += '</ul></div>';
            }
            
            // Recomendaciones
            if (info.recomendaciones && info.recomendaciones.length > 0) {
                infoFaltanteHTML += '<div class="recomendaciones">';
                infoFaltanteHTML += '<strong>💡 Recomendaciones para mejorar el perfil:</strong><ul>';
                info.recomendaciones.forEach(rec => {
                    infoFaltanteHTML += `<li>${rec}</li>`;
                });
                infoFaltanteHTML += '</ul></div>';
            }
            
            // Brecha para perfil más cercano
            if (info.perfil_mas_cercano && info.perfil_mas_cercano.brecha > 0) {
                infoFaltanteHTML += `<div class="brecha-perfil">`;
                infoFaltanteHTML += `<strong>🎯 Para alcanzar ${info.perfil_mas_cercano.nombre}:</strong> `;
                infoFaltanteHTML += `Necesita ${info.perfil_mas_cercano.brecha} puntos adicionales`;
                infoFaltanteHTML += `</div>`;
            }
            
            // Completitud del CV
            infoFaltanteHTML += `<div class="completitud-cv">`;
            infoFaltanteHTML += `<strong>📊 Completitud del CV:</strong> ${info.completitud_cv}%`;
            if (info.total_criterios_sin_info > 0) {
                infoFaltanteHTML += ` (${info.total_criterios_sin_info} criterio(s) sin información)`;
            }
            infoFaltanteHTML += `</div>`;
        }
        
        // Mostrar perfiles posibles si existen
        let perfilesPosiblesHTML = '';
        if (evaluacion.perfiles_posibles && evaluacion.perfiles_posibles.length > 0) {
            perfilesPosiblesHTML = '<div class="perfiles-posibles"><strong>Perfiles que cumple:</strong><ul>';
            evaluacion.perfiles_posibles.forEach(p => {
                const cumpleIcon = p.cumple ? '✅' : '⚠️';
                perfilesPosiblesHTML += `<li>${cumpleIcon} <strong>${p.nombre}</strong>: ${p.condicion}</li>`;
            });
            perfilesPosiblesHTML += '</ul></div>';
        }
        
        // Configuración de colores para perfiles
        const perfilesConfig = {
            'CON_HORAS_INVESTIGACION': { nombre: '🔬 INVESTIGADOR+', color: '#1e40af' },
            'DOCENTE_INVESTIGADOR': { nombre: '🔬 INVESTIGADOR', color: '#3b82f6' },
            'DTC': { nombre: '📚 DTC', color: '#0d9488' },
            'DTP': { nombre: '📖 DTP', color: '#0891b2' },
            'PRACTITIONER': { nombre: '💼 PRACTITIONER', color: '#6366f1' },
            'NO_CALIFICA': { nombre: '❌ NO CALIFICA', color: '#dc2626' },
            'NO_ELEGIBLE_PERFIL_DOCENTE': { nombre: '⛔ NO ELEGIBLE', color: '#64748b' }
        };
        const configPerfil = perfilesConfig[evaluacion.clasificacion] || { nombre: evaluacion.clasificacion, color: '#34495e' };
        
        detalleDiv.innerHTML = `
            <h4>${evaluacion.nombre}</h4>
            <p><strong>Puntaje Total:</strong> ${evaluacion.total} / 200 puntos (${evaluacion.porcentaje}%)</p>
            <p><strong>Clasificación:</strong> <span style="color: ${configPerfil.color}; font-weight: bold;">${configPerfil.nombre}</span></p>
            <p><strong>Tipo de Perfil:</strong> ${_badgeTipoPerfil(evaluacion.tipo_perfil)}</p>
            <p><strong>Elegible:</strong> ${evaluacion.es_elegible ? '✅ SÍ' : '❌ NO'}</p>
            ${perfilesPosiblesHTML}
            ${infoFaltanteHTML}
            <div class="criterios-lista">${criteriosHTML}</div>
        `;
        detallesContainer.appendChild(detalleDiv);
    });
    
    // Se eliminó la configuración del botón JSON ya que fue removido de la interfaz
    
    // Botón de Excel detallado — usa fetch+blob para no navegar fuera de la página
    document.getElementById('btn-descargar-excel-detallado').onclick = async () => {
        const btn = document.getElementById('btn-descargar-excel-detallado');
        const textoOriginal = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳ Generando Excel...';
        try {
            const resp = await fetch('/descargar-excel-detallado');
            if (!resp.ok) {
                let msg = 'Error al generar el Excel';
                try { const err = await resp.json(); msg = err.error || msg; } catch(_) {}
                alert('❌ ' + msg);
                return;
            }
            const blob = await resp.blob();
            const url  = URL.createObjectURL(blob);
            const a    = document.createElement('a');
            // Obtener nombre del archivo desde Content-Disposition si existe
            const cd   = resp.headers.get('Content-Disposition') || '';
            const match = cd.match(/filename\*?=['"]?(?:UTF-8'')?([^;\r\n"']+)/);
            a.download = match ? decodeURIComponent(match[1]) :
                         `Analisis_Detallado_${new Date().toISOString().slice(0,10)}.xlsx`;
            a.href = url;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch(e) {
            alert('❌ Error de conexión: ' + e.message);
        } finally {
            btn.disabled = false;
            btn.textContent = textoOriginal;
        }
    };
    
    // Mostrar resumen de problemas (links inválidos y datos faltantes)
    mostrarResumenProblemas(resultado.resumen_problemas);
    
    // Mostrar panel de comunicación a facultades
    mostrarPanelComunicacion(resultado.resumen_problemas);
}

function mostrarResumenProblemas(resumenProblemas) {
    console.log("📊 Datos de resumen de problemas recibidos:", resumenProblemas);
    
    // Buscar contenedor existente en el HTML
    let contenedorProblemas = document.getElementById('resumen-problemas-container');
    
    if (!contenedorProblemas) {
        console.log("⚠️ No se encontró el contenedor, creando uno nuevo...");
        // Crear contenedor después del resumen de perfiles
        const resumenPerfiles = document.getElementById('resumen-perfiles');
        if (resumenPerfiles) {
            contenedorProblemas = document.createElement('div');
            contenedorProblemas.id = 'resumen-problemas-container';
            contenedorProblemas.className = 'resumen-problemas-section';
            resumenPerfiles.parentNode.insertBefore(contenedorProblemas, resumenPerfiles.nextSibling);
        } else {
            console.error("❌ No se encontró el elemento resumen-perfiles");
            return;
        }
    }
    
    // Si no hay problemas, ocultar
    console.log("📊 Verificando si hay problemas...");
    console.log("   links_invalidos:", resumenProblemas.links_invalidos);
    console.log("   datos_faltantes:", resumenProblemas.datos_faltantes);
    console.log("   Cantidad links_invalidos:", resumenProblemas.links_invalidos?.length || 0);
    
    if (!resumenProblemas || 
        (!resumenProblemas.links_invalidos?.length && !resumenProblemas.datos_faltantes?.length)) {
        console.log("❌ No hay problemas para mostrar, ocultando contenedor");
        contenedorProblemas.style.display = 'none';
        return;
    }
    
    console.log("✅ Hay problemas, mostrando contenedor");
    contenedorProblemas.style.display = 'block';
    
    const linksInvalidos = resumenProblemas.links_invalidos || [];
    const resumenFacultades = resumenProblemas.resumen_facultades || {};
    
    // Contar por facultad cuántas personas faltan
    const faltantesPorFacultad = {};
    linksInvalidos.forEach(p => {
        const fac = p.facultad || 'SIN FACULTAD';
        if (!faltantesPorFacultad[fac]) {
            faltantesPorFacultad[fac] = [];
        }
        faltantesPorFacultad[fac].push(p);
    });
    
    // Ordenar por cantidad de faltantes (mayor a menor)
    const facultadesOrdenadas = Object.entries(faltantesPorFacultad)
        .sort((a, b) => b[1].length - a[1].length);
    
    let html = `
        <div class="problemas-header">
            <h3>⚠️ CANDIDATOS QUE REQUIEREN INFORMACIÓN CTI VITAE</h3>
            <div class="total-faltantes">
                <span class="numero-grande">${linksInvalidos.length}</span>
                <span class="texto-faltantes">candidatos pendientes de validación</span>
            </div>
        </div>
    `;
    
    // ======== RESUMEN RÁPIDO POR TIPO DE PROBLEMA ========
    const resumenTipos = {};
    linksInvalidos.forEach(p => {
        const motivo = p.motivo || 'OTRO';
        resumenTipos[motivo] = (resumenTipos[motivo] || 0) + 1;
    });
    
    html += `
        <div class="tipos-problema-resumen">
            ${resumenTipos['SIN LINK CTI'] ? `<div class="tipo-badge sin-link">❌ Sin link: ${resumenTipos['SIN LINK CTI']}</div>` : ''}
            ${resumenTipos['EN CONSTRUCCIÓN'] ? `<div class="tipo-badge construccion">🚧 En construcción: ${resumenTipos['EN CONSTRUCCIÓN']}</div>` : ''}
            ${resumenTipos['LINK INVÁLIDO'] ? `<div class="tipo-badge invalido">⚠️ Link inválido: ${resumenTipos['LINK INVÁLIDO']}</div>` : ''}
            ${resumenTipos['DESACTUALIZADO'] ? `<div class="tipo-badge desactualizado">📅 Desactualizado (+6 meses): ${resumenTipos['DESACTUALIZADO']}</div>` : ''}
            ${resumenTipos['PERFIL VACÍO'] ? `<div class="tipo-badge vacio">📭 Perfil vacío: ${resumenTipos['PERFIL VACÍO']}</div>` : ''}
        </div>
    `;
    
    // ======== TABLA PRINCIPAL DE CANDIDATOS PENDIENTES ========
    html += `
        <div class="tabla-rechazados-container">
            <h4>📋 Lista Completa de Candidatos Pendientes</h4>
            <p class="subtitulo-tabla">Estos candidatos no pueden ser evaluados correctamente. Contactar a sus facultades.</p>
            
            <div class="filtros-tabla">
                <input type="text" id="filtro-nombre-rechazados" placeholder="🔍 Buscar por nombre..." onkeyup="filtrarTablaRechazados()">
                <select id="filtro-facultad-rechazados" onchange="filtrarTablaRechazados()">
                    <option value="">Todas las facultades</option>
                    ${facultadesOrdenadas.map(([fac, _]) => `<option value="${fac}">${fac}</option>`).join('')}
                </select>
                <select id="filtro-motivo" onchange="filtrarTablaRechazados()">
                    <option value="">Todos los motivos</option>
                    ${Object.keys(resumenTipos).map(m => `<option value="${m}">${m}</option>`).join('')}
                </select>
            </div>
            
            <table class="tabla-rechazados" id="tabla-rechazados">
                <thead>
                    <tr>
                        <th class="th-num">#</th>
                        <th class="th-nombre">NOMBRE DEL CANDIDATO</th>
                        <th class="th-dni">DNI</th>
                        <th class="th-facultad">FACULTAD</th>
                        <th class="th-motivo">MOTIVO DE RECHAZO</th>
                        <th class="th-accion">ACCIÓN</th>
                    </tr>
                </thead>
                <tbody id="tbody-rechazados">
    `;
    
    linksInvalidos.forEach((p, idx) => {
        const motivoClass = obtenerClaseMotivo(p.motivo);
        const motivoIcono = obtenerIconoMotivo(p.motivo);
        
        html += `
            <tr data-nombre="${(p.nombre || '').toLowerCase()}" 
                data-facultad="${p.facultad || ''}" 
                data-motivo="${p.motivo || ''}">
                <td class="td-num">${idx + 1}</td>
                <td class="td-nombre">
                    <strong>${p.nombre || 'SIN NOMBRE'}</strong>
                </td>
                <td class="td-dni">${p.dni || 'N/A'}</td>
                <td class="td-facultad">${p.facultad || 'N/A'}</td>
                <td class="td-motivo ${motivoClass}">
                    <span class="motivo-badge">${motivoIcono} ${p.motivo || 'DESCONOCIDO'}</span>
                </td>
                <td class="td-accion">
                    <button class="btn-investigar"
                        data-dni="${(p.dni || '').replace(/"/g, '&quot;')}"
                        data-nombre="${(p.nombre || '').replace(/"/g, '&quot;')}"
                        data-facultad="${(p.facultad || '').replace(/"/g, '&quot;')}"
                        data-carrera="${(p.carrera || '').replace(/"/g, '&quot;')}"
                        onclick="investigarPendiente(this)">
                        🔬 Investigar
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
            
            <div class="tabla-footer">
                <span id="contador-filtrados">Mostrando ${linksInvalidos.length} de ${linksInvalidos.length} candidatos</span>
                <button class="btn-exportar" onclick="exportarListaRechazados()">
                    📥 Exportar Lista
                </button>
            </div>
        </div>
    `;
    
    // ======== RESUMEN POR FACULTAD (sin gráficas, solo tarjetas) ========
    html += `
        <div class="resumen-facultades-section">
            <h4>🏛️ Resumen por Facultad - Acción Requerida</h4>
            <div class="facultades-grid">
    `;
    
    facultadesOrdenadas.forEach(([facultad, personas], index) => {
        const colores = ['#dc2626', '#f59e0b', '#3b82f6', '#8b5cf6', '#10b981', '#f97316', '#06b6d4', '#6366f1'];
        const color = colores[index % colores.length];
        
        html += `
            <div class="facultad-accion-card" style="--color-facultad: ${color}">
                <div class="fac-header">
                    <span class="fac-numero">${index + 1}</span>
                    <span class="fac-titulo">${facultad}</span>
                </div>
                <div class="fac-stats">
                    <div class="fac-stat-main">
                        <span class="stat-numero">${personas.length}</span>
                        <span class="stat-label">pendiente${personas.length !== 1 ? 's' : ''}</span>
                    </div>
                </div>
                <div class="fac-personas-preview">
                    ${personas.slice(0, 3).map(p => `<span class="persona-chip">${(p.nombre || 'N/A').split(' ').slice(0, 2).join(' ')}</span>`).join('')}
                    ${personas.length > 3 ? `<span class="persona-chip mas">+${personas.length - 3} más</span>` : ''}
                </div>
                <button class="btn-ver-detalle" onclick="toggleListaFacultad('${facultad.replace(/'/g, "\\'")}')">
                    Ver detalle completo →
                </button>
            </div>
        `;
    });
    
    html += `
            </div>
        </div>
    `;
    
    // LISTADO DETALLADO POR FACULTAD (oculto inicialmente)
    html += `<div class="listados-por-facultad">`;
    
    facultadesOrdenadas.forEach(([facultad, personas]) => {
        const facId = facultad.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-]/g, '');
        html += `
            <div id="lista-${facId}" class="lista-facultad" style="display: none;">
                <div class="lista-facultad-header">
                    <h4>📍 ${facultad} - ${personas.length} persona${personas.length > 1 ? 's' : ''}</h4>
                    <button class="btn-cerrar" onclick="toggleListaFacultad('${facultad.replace(/'/g, "\\'")}')">✕ Cerrar</button>
                </div>
                <table class="tabla-personas-facultad">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>NOMBRE DEL CANDIDATO</th>
                            <th>DNI</th>
                            <th>PROBLEMA</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        personas.forEach((p, idx) => {
            const motivoClass = p.motivo === 'SIN LINK CTI' ? 'motivo-sin-link' : 
                               p.motivo === 'EN CONSTRUCCIÓN' ? 'motivo-construccion' : 'motivo-invalido';
            html += `
                <tr>
                    <td>${idx + 1}</td>
                    <td><strong>${p.nombre || 'SIN NOMBRE'}</strong></td>
                    <td class="dni-cell">${p.dni || 'SIN DNI'}</td>
                    <td class="${motivoClass}">${p.motivo}</td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
    });
    
    html += `</div>`;
    
    // TABLA RESUMEN COMPACTA
    html += `
        <div class="resumen-compacto">
            <h4>📊 RESUMEN PARA SOLICITAR INFORMACIÓN</h4>
            <table class="tabla-resumen-solicitar">
                <thead>
                    <tr>
                        <th>FACULTAD</th>
                        <th>CANTIDAD FALTANTE</th>
                        <th>ACCIÓN REQUERIDA</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    facultadesOrdenadas.forEach(([facultad, personas]) => {
        html += `
            <tr>
                <td><strong>${facultad}</strong></td>
                <td class="cantidad-cell">${personas.length} persona${personas.length > 1 ? 's' : ''}</td>
                <td class="accion-cell">📧 Solicitar ${personas.length} link${personas.length > 1 ? 's' : ''} CTI</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    contenedorProblemas.innerHTML = html;
    
    // Ya no se renderiza gráficos - ahora es tabla
    console.log("✅ Tabla de candidatos pendientes generada correctamente");
}

// Funciones auxiliares para la tabla de rechazados
function obtenerClaseMotivo(motivo) {
    const clases = {
        'SIN LINK CTI': 'motivo-sin-link',
        'EN CONSTRUCCIÓN': 'motivo-construccion',
        'LINK INVÁLIDO': 'motivo-invalido',
        'DESACTUALIZADO': 'motivo-desactualizado',
        'PERFIL VACÍO': 'motivo-vacio'
    };
    return clases[motivo] || 'motivo-otro';
}

function obtenerIconoMotivo(motivo) {
    const iconos = {
        'SIN LINK CTI': '❌',
        'EN CONSTRUCCIÓN': '🚧',
        'LINK INVÁLIDO': '⚠️',
        'DESACTUALIZADO': '📅',
        'PERFIL VACÍO': '📭'
    };
    return iconos[motivo] || '❓';
}

function filtrarTablaRechazados() {
    const filtroNombre = (document.getElementById('filtro-nombre-rechazados')?.value || '').toLowerCase();
    const filtroFacultad = document.getElementById('filtro-facultad-rechazados')?.value || '';
    const filtroMotivo = document.getElementById('filtro-motivo')?.value || '';
    
    const filas = document.querySelectorAll('#tbody-rechazados tr');
    let visibles = 0;
    
    filas.forEach(fila => {
        const nombre = fila.dataset.nombre || '';
        const facultad = fila.dataset.facultad || '';
        const motivo = fila.dataset.motivo || '';
        
        const coincideNombre = nombre.includes(filtroNombre);
        const coincideFacultad = !filtroFacultad || facultad === filtroFacultad;
        const coincideMotivo = !filtroMotivo || motivo === filtroMotivo;
        
        if (coincideNombre && coincideFacultad && coincideMotivo) {
            fila.style.display = '';
            visibles++;
        } else {
            fila.style.display = 'none';
        }
    });
    
    document.getElementById('contador-filtrados').textContent = 
        `Mostrando ${visibles} de ${filas.length} candidatos`;
}

function marcarPendiente(dni, nombre) {
    console.log(`📧 Marcar para solicitar: ${nombre} (DNI: ${dni})`);
    // Aquí se podría agregar a una lista de pendientes o abrir modal
    alert(`Se ha marcado para solicitar información a:\n\n${nombre}\nDNI: ${dni}\n\nSe enviará notificación a la facultad correspondiente.`);
}

function exportarListaRechazados() {
    const tabla = document.getElementById('tabla-rechazados');
    if (!tabla) return;
    
    let csv = 'Número,Nombre,DNI,Facultad,Motivo\n';
    
    const filas = tabla.querySelectorAll('tbody tr');
    filas.forEach((fila, idx) => {
        if (fila.style.display !== 'none') {
            const celdas = fila.querySelectorAll('td');
            const datos = [
                idx + 1,
                celdas[1]?.textContent?.trim() || '',
                celdas[2]?.textContent?.trim() || '',
                celdas[3]?.textContent?.trim() || '',
                celdas[4]?.textContent?.trim() || ''
            ];
            csv += datos.map(d => `"${d}"`).join(',') + '\n';
        }
    });
    
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `candidatos_pendientes_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
}

// Función para mostrar/ocultar lista de una facultad
function toggleListaFacultad(facultad) {
    const facId = facultad.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-]/g, '');
    const lista = document.getElementById('lista-' + facId);
    if (lista) {
        // Ocultar todas las otras listas
        document.querySelectorAll('.lista-facultad').forEach(l => {
            if (l.id !== 'lista-' + facId) {
                l.style.display = 'none';
            }
        });
        // Toggle esta lista
        lista.style.display = lista.style.display === 'none' ? 'block' : 'none';
        
        // Scroll hacia la lista si se muestra
        if (lista.style.display === 'block') {
            lista.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
}

// ============================================================
// PANEL DE COMUNICACIÓN A FACULTADES - NUEVA FUNCIONALIDAD
// ============================================================

function mostrarPanelComunicacion(resumenProblemas) {
    console.log("📧 Generando panel de comunicación a facultades...");
    console.log("📧 Datos recibidos:", resumenProblemas);
    
    const panelContainer = document.getElementById('panel-comunicacion-container');
    if (!panelContainer) {
        console.log("⚠️ No se encontró el contenedor del panel de comunicación");
        return;
    }
    
    // Verificar si hay datos de problemas
    if (!resumenProblemas) {
        console.log("❌ resumenProblemas es null o undefined");
        panelContainer.style.display = 'none';
        return;
    }
    
    if (!resumenProblemas.resumen_facultades) {
        console.log("❌ No hay resumen_facultades en los datos");
        console.log("   Claves disponibles:", Object.keys(resumenProblemas));
        panelContainer.style.display = 'none';
        return;
    }
    
    console.log("✅ Facultades encontradas:", Object.keys(resumenProblemas.resumen_facultades));
    
    const linksInvalidos = resumenProblemas.links_invalidos || [];
    const resumenFacultades = resumenProblemas.resumen_facultades || {};
    
    // Calcular totales
    let totalPendientes = 0;
    let totalRegistros = 0;
    let totalConLink = 0;
    
    // Procesar facultades con pendientes
    const facultadesConPendientes = [];
    for (const [fac, stats] of Object.entries(resumenFacultades)) {
        const pendientes = (stats.sin_link || 0) + (stats.link_invalido || 0);
        totalRegistros += stats.total || 0;
        totalConLink += stats.con_link_valido || 0;
        totalPendientes += pendientes; // Sumar pendientes de cada facultad
        
        if (pendientes > 0) {
            facultadesConPendientes.push({
                facultad: fac,
                total: stats.total || 0,
                conLink: stats.con_link_valido || 0,
                sinLink: stats.sin_link || 0,
                linkInvalido: stats.link_invalido || 0,
                pendientes: pendientes,
                porcentajePendiente: ((pendientes / (stats.total || 1)) * 100).toFixed(1),
                carreras: stats.carreras || {},
                personas: (stats.personas_sin_link || []).concat(stats.personas_link_invalido || [])
            });
        }
    }
    
    console.log(`📊 Totales calculados: ${totalRegistros} registros, ${totalConLink} con link, ${totalPendientes} pendientes`);
    
    // Si no hay pendientes, ocultar panel
    if (totalPendientes === 0 && facultadesConPendientes.length === 0) {
        console.log("⚠️ No hay pendientes para mostrar, ocultando panel");
        panelContainer.style.display = 'none';
        return;
    }
    
    panelContainer.style.display = 'block';
    
    // Ordenar facultades por cantidad de pendientes
    facultadesConPendientes.sort((a, b) => b.pendientes - a.pendientes);
    
    // Colores para las tarjetas
    const colores = [
        { bg: '#fee2e2', border: '#dc2626', text: '#991b1b' },
        { bg: '#fef3c7', border: '#f59e0b', text: '#92400e' },
        { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af' },
        { bg: '#e0e7ff', border: '#6366f1', text: '#3730a3' },
        { bg: '#d1fae5', border: '#10b981', text: '#065f46' },
        { bg: '#fce7f3', border: '#ec4899', text: '#9d174d' },
        { bg: '#f3e8ff', border: '#a855f7', text: '#6b21a8' },
        { bg: '#ecfccb', border: '#84cc16', text: '#3f6212' }
    ];
    
    // ===== RESUMEN GENERAL =====
    const resumenGeneral = document.getElementById('resumen-general-pendientes');
    if (resumenGeneral) {
        const porcentajeCompletado = ((totalConLink / totalRegistros) * 100).toFixed(1);
        resumenGeneral.innerHTML = `
            <div class="stats-cards-row">
                <div class="stat-card total">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">${totalRegistros}</div>
                    <div class="stat-label">Total Candidatos</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">${totalConLink}</div>
                    <div class="stat-label">Con Link CTI</div>
                </div>
                <div class="stat-card danger">
                    <div class="stat-icon">⚠️</div>
                    <div class="stat-value">${totalPendientes}</div>
                    <div class="stat-label">Pendientes</div>
                </div>
                <div class="stat-card info">
                    <div class="stat-icon">📈</div>
                    <div class="stat-value">${porcentajeCompletado}%</div>
                    <div class="stat-label">Completado</div>
                </div>
            </div>
            <div class="progress-completitud">
                <div class="progress-completitud-bar" style="width: ${porcentajeCompletado}%"></div>
            </div>
        `;
    }
    
    // ===== TARJETAS DE FACULTADES =====
    const gridFacultades = document.getElementById('facultades-comunicar-grid');
    if (gridFacultades) {
        let htmlFacultades = '';
        
        facultadesConPendientes.forEach((fac, index) => {
            const color = colores[index % colores.length];
            const carrerasArray = Object.entries(fac.carreras).filter(([_, stats]) => 
                (stats.sin_link || 0) + (stats.link_invalido || 0) > 0
            );
            
            htmlFacultades += `
                <div class="facultad-comunicar-card" 
                     style="background-color: ${color.bg}; border-color: ${color.border};"
                     onclick="mostrarDetalleCarreras('${fac.facultad.replace(/'/g, "\\'")}')">
                    <div class="fac-card-header" style="color: ${color.text};">
                        <span class="fac-emoji">🏛️</span>
                        <span class="fac-nombre">${fac.facultad}</span>
                    </div>
                    <div class="fac-card-stats">
                        <div class="fac-stat-big" style="color: ${color.border};">
                            <span class="fac-stat-num">${fac.pendientes}</span>
                            <span class="fac-stat-label">pendiente${fac.pendientes !== 1 ? 's' : ''}</span>
                        </div>
                        <div class="fac-stat-small">
                            <span>📋 ${fac.total} total</span>
                            <span>✅ ${fac.conLink} OK</span>
                        </div>
                    </div>
                    <div class="fac-card-carreras">
                        ${carrerasArray.length > 0 ? `<span class="fac-carreras-badge">${carrerasArray.length} carrera${carrerasArray.length !== 1 ? 's' : ''}</span>` : ''}
                    </div>
                    <div class="fac-card-action">
                        👆 Ver detalle por carrera
                    </div>
                </div>
            `;
        });
        
        gridFacultades.innerHTML = htmlFacultades;
    }
    
    // ===== ALMACENAR DATOS PARA DETALLE =====
    window.datosResumenFacultades = resumenFacultades;
    window.datosLinksInvalidos = linksInvalidos;
    
    console.log("✅ Panel de comunicación generado correctamente");
}

// Función para mostrar el detalle de carreras de una facultad
function mostrarDetalleCarreras(facultad) {
    console.log(`📋 Mostrando detalle de carreras para: ${facultad}`);
    
    const seccionCarreras = document.getElementById('carreras-detalle-section');
    if (!seccionCarreras) return;
    
    const resumenFacultades = window.datosResumenFacultades || {};
    const datosLinksInvalidos = window.datosLinksInvalidos || [];
    const facultadData = resumenFacultades[facultad];
    
    if (!facultadData) {
        console.log("❌ No se encontraron datos para la facultad:", facultad);
        return;
    }
    
    // Obtener personas de esta facultad
    const personasFacultad = datosLinksInvalidos.filter(p => p.facultad === facultad);
    
    // Agrupar por carrera
    const personasPorCarrera = {};
    personasFacultad.forEach(p => {
        const carrera = p.carrera || 'SIN CARRERA';
        if (!personasPorCarrera[carrera]) {
            personasPorCarrera[carrera] = [];
        }
        personasPorCarrera[carrera].push(p);
    });
    
    // Generar HTML
    let html = `
        <div class="carreras-detalle-header">
            <h4>📍 ${facultad}</h4>
            <button class="btn-cerrar-detalle" onclick="cerrarDetalleCarreras()">✕ Cerrar</button>
        </div>
        <div class="carreras-lista">
    `;
    
    Object.entries(personasPorCarrera)
        .sort((a, b) => b[1].length - a[1].length)
        .forEach(([carrera, personas]) => {
            html += `
                <div class="carrera-item">
                    <div class="carrera-header" onclick="toggleListaPersonas('${facultad.replace(/'/g, "\\'")}', '${carrera.replace(/'/g, "\\'")}')">
                        <span class="carrera-nombre">📚 ${carrera}</span>
                        <span class="carrera-count">${personas.length} persona${personas.length !== 1 ? 's' : ''}</span>
                        <span class="carrera-arrow">▼</span>
                    </div>
                    <div class="personas-lista" id="personas-${facultad.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-]/g, '')}-${carrera.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-]/g, '')}" style="display: none;">
                        <table class="tabla-personas-carrera">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Nombre</th>
                                    <th>DNI</th>
                                    <th>Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${personas.map((p, idx) => `
                                    <tr>
                                        <td>${idx + 1}</td>
                                        <td><strong>${p.nombre || 'SIN NOMBRE'}</strong></td>
                                        <td>${p.dni || 'SIN DNI'}</td>
                                        <td class="motivo-${p.motivo === 'SIN LINK CTI' ? 'sin-link' : p.motivo === 'EN CONSTRUCCIÓN' ? 'construccion' : 'invalido'}">${p.motivo}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        });
    
    html += `</div>`;
    
    seccionCarreras.innerHTML = html;
    seccionCarreras.style.display = 'block';
    seccionCarreras.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function cerrarDetalleCarreras() {
    const seccionCarreras = document.getElementById('carreras-detalle-section');
    if (seccionCarreras) {
        seccionCarreras.style.display = 'none';
    }
}

function toggleListaPersonas(facultad, carrera) {
    const facId = facultad.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-]/g, '');
    const carId = carrera.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-]/g, '');
    const lista = document.getElementById(`personas-${facId}-${carId}`);
    if (lista) {
        lista.style.display = lista.style.display === 'none' ? 'block' : 'none';
    }
}

// ============================================================

function mostrarError(mensaje) {
    mostrarPantalla(errorScreen);
    document.getElementById('mensaje-error').textContent = mensaje;
}

function reiniciarApp() {
    if (intervalId) {
        clearInterval(intervalId);
    }
    disarmBtnSafety();

    // Restaurar el botón "Iniciar" — si quedó deshabilitado/"Iniciando..." de una
    // corrida anterior (búsqueda masiva, error, resultados), aquí se limpia siempre.
    if (btnIniciar) {
        btnIniciar.disabled = false;
        btnIniciar.textContent = '🚀 Iniciar Análisis de Talento';
    }

    // Reset client-side state — crítico para evitar que se mezclen datos de sesiones anteriores
    archivoSeleccionado = null;
    archivosExcelSeleccionados = [];
    carpetaPdfsSeleccionada = null;

    // Reset Excel upload UI
    if (archivoInput) archivoInput.value = '';
    if (uploadArea) uploadArea.style.display = 'block';
    if (archivoSeleccionadoDiv) archivoSeleccionadoDiv.style.display = 'none';
    if (archivoInfoDiv) archivoInfoDiv.style.display = 'none';

    // Reset PDF upload UI
    if (archivosInput) archivosInput.value = '';
    if (uploadAreaPdfs) uploadAreaPdfs.style.display = 'block';
    if (carpetaSeleccionadaDiv) carpetaSeleccionadaDiv.style.display = 'none';
    if (carpetaInfoDiv) carpetaInfoDiv.style.display = 'none';

    // Notificar al servidor para limpiar archivos de sesión anterior
    fetch('/quitar-archivo', { method: 'POST' }).catch(() => {});
    fetch('/quitar-carpeta-pdfs', { method: 'POST' }).catch(() => {});

    mostrarPantalla(inicioScreen);
}

// Animación inicial
document.addEventListener('DOMContentLoaded', () => {
    mostrarPantalla(inicioScreen);
    inicializarBuscadorRanking();
});

// ============================================================
// BUSCADOR DE RANKING
// ============================================================

function inicializarBuscadorRanking() {
    const buscador = document.getElementById('buscador-ranking');
    const btnLimpiar = document.getElementById('btn-limpiar-busqueda');
    
    if (buscador) {
        // Evento de búsqueda en tiempo real
        buscador.addEventListener('input', (e) => {
            filtrarTablaRanking();
            
            // Mostrar/ocultar botón limpiar
            if (btnLimpiar) {
                btnLimpiar.style.display = buscador.value.trim().length > 0 ? 'flex' : 'none';
            }
        });

        // Eventos para los filtros (datos del Excel + criterios de la rúbrica)
        ['filtro-facultad', 'filtro-tipo-candidato', 'filtro-puesto', 'filtro-cat-practitioner',
         'filtro-perfil', 'filtro-elegibilidad', 'filtro-puntaje-min', 'filtro-docencia-min'].forEach(id => {
            const select = document.getElementById(id);
            if (select) {
                select.addEventListener('change', () => {
                    filtrarTablaRanking();
                });
            }
        });

        // Botón "Limpiar filtros": resetea todo y vuelve a mostrar la tabla completa
        const btnLimpiarFiltros = document.getElementById('btn-limpiar-filtros');
        if (btnLimpiarFiltros) {
            btnLimpiarFiltros.addEventListener('click', () => {
                ['filtro-facultad', 'filtro-tipo-candidato', 'filtro-puesto', 'filtro-cat-practitioner',
                 'filtro-perfil', 'filtro-elegibilidad', 'filtro-puntaje-min', 'filtro-docencia-min'].forEach(id => {
                    const sel = document.getElementById(id);
                    if (sel) sel.value = '';
                });
                if (buscador) buscador.value = '';
                if (btnLimpiar) btnLimpiar.style.display = 'none';
                filtrarTablaRanking();
            });
        }
        
        // Limpiar con Escape
        buscador.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                buscador.value = '';
                filtrarTablaRanking();
                if (btnLimpiar) btnLimpiar.style.display = 'none';
            }
        });
    }
    
    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', () => {
            if (buscador) {
                buscador.value = '';
                filtrarTablaRanking();
                btnLimpiar.style.display = 'none';
                buscador.focus();
            }
        });
    }
}

function filtrarTablaRanking() {
    const tbody = document.getElementById('tabla-clasificacion-tbody');
    const statsDiv = document.getElementById('buscador-stats');
    const buscador = document.getElementById('buscador-ranking');
    
    if (!tbody) return;
    
    const termino = buscador ? buscador.value.trim() : '';
    const terminoLower = termino.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    
    const filtroFacultad = document.getElementById('filtro-facultad')?.value || '';
    const filtroTipoCandidato = document.getElementById('filtro-tipo-candidato')?.value || '';
    const filtroPuesto = document.getElementById('filtro-puesto')?.value || '';
    const filtroCatPractitioner = document.getElementById('filtro-cat-practitioner')?.value || '';
    const filtroPerfil = document.getElementById('filtro-perfil')?.value || '';
    const filtroElegibilidad = document.getElementById('filtro-elegibilidad')?.value || '';
    const filtroPuntajeMin = parseFloat(document.getElementById('filtro-puntaje-min')?.value || '') || 0;
    const filtroDocenciaMin = parseFloat(document.getElementById('filtro-docencia-min')?.value || '') || 0;

    const filas = tbody.querySelectorAll('tr');
    let visibles = 0;
    let total = filas.length;

    filas.forEach(fila => {
        // Filtros de los selects
        const rowFacultad = fila.getAttribute('data-facultad') || '';
        const rowTipoCand = fila.getAttribute('data-tipo-candidato') || '';
        const rowPuesto = fila.getAttribute('data-puesto') || '';
        const rowCatPract = fila.getAttribute('data-cat-practitioner') || '';
        const rowPerfil = fila.getAttribute('data-perfil') || '';
        const rowElegible = fila.getAttribute('data-elegible') || '';
        const rowPorcentaje = parseFloat(fila.getAttribute('data-porcentaje')) || 0;
        const rowDocencia = parseFloat(fila.getAttribute('data-anos-docencia')) || 0;

        let matchFilters = true;
        if (filtroFacultad && rowFacultad !== filtroFacultad) matchFilters = false;
        if (filtroTipoCandidato && rowTipoCand !== filtroTipoCandidato) matchFilters = false;
        if (filtroPuesto && rowPuesto !== filtroPuesto) matchFilters = false;
        if (filtroCatPractitioner && rowCatPract !== filtroCatPractitioner) matchFilters = false;
        if (filtroPerfil && rowPerfil !== filtroPerfil) matchFilters = false;
        if (filtroElegibilidad !== '' && rowElegible !== filtroElegibilidad) matchFilters = false;
        if (filtroPuntajeMin > 0 && rowPorcentaje < filtroPuntajeMin) matchFilters = false;
        if (filtroDocenciaMin > 0 && rowDocencia < filtroDocenciaMin) matchFilters = false;

        // Obtener todo el texto de la fila
        const textoFila = fila.textContent.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        
        // También buscar en atributos data si existen
        const dataSearch = fila.getAttribute('data-search') || '';
        const textoCompleto = textoFila + ' ' + dataSearch.toLowerCase();
        
        const matchSearch = terminoLower === '' || textoCompleto.includes(terminoLower);
        
        if (matchFilters && matchSearch) {
            fila.classList.remove('hidden-row');
            visibles++;
        } else {
            fila.classList.add('hidden-row');
        }
    });
    
    // Actualizar estadísticas
    if (statsDiv) {
        const hayFiltro = termino.length > 0 || filtroFacultad || filtroTipoCandidato ||
            filtroPuesto || filtroCatPractitioner || filtroPerfil ||
            filtroElegibilidad !== '' || filtroPuntajeMin > 0 || filtroDocenciaMin > 0;
        if (hayFiltro) {
            statsDiv.innerHTML = `Mostrando <span class="resultado-count">${visibles}</span> de ${total} candidatos`;
        } else {
            statsDiv.innerHTML = '';
        }
    }
}

// Función para agregar data-search a las filas (llamar después de llenar la tabla)
function agregarDataSearchAFilas() {
    const tbody = document.getElementById('tabla-clasificacion-tbody');
    if (!tbody) return;
    
    const filas = tbody.querySelectorAll('tr');
    filas.forEach(fila => {
        // El data-search se puede agregar cuando se genera la tabla
        // con información adicional como facultad, carrera, DNI, etc.
    });
}

//  MODO OSCURO 

function toggleTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const newTheme = isDark ? 'light' : 'dark';
    applyTheme(newTheme);
    localStorage.setItem('pa-theme', newTheme);
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const icon = document.getElementById('theme-icon');
    if (icon) icon.textContent = theme === 'dark' ? '\u2600\uFE0F' : '\uD83C\uDF19';
}

// Aplicar tema guardado al cargar la pagina
(function() {
    const saved = localStorage.getItem('pa-theme') || 'light';
    applyTheme(saved);
})();
