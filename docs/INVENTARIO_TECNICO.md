# INVENTARIO TÉCNICO — PROYECTO RÚBRICA USIL
**Universidad San Ignacio de Loyola — People Analytics**
**Versión del sistema:** 3.0 (Simplificada)
**Fecha de análisis:** 2026-06-01
**Estado del sistema:** Producción

---

## ÍNDICE

1. [Qué hace el sistema](#1-qué-hace-el-sistema)
2. [Arquitectura general](#2-arquitectura-general)
3. [Componentes principales](#3-componentes-principales)
4. [Flujo de datos completo](#4-flujo-de-datos-de-inicio-a-fin)
5. [Estructura de carpetas](#5-estructura-de-carpetas)
6. [Módulos y archivos Python](#6-módulos-y-archivos-python)
7. [Clases y funciones](#7-clases-y-funciones)
8. [Dependencias](#8-dependencias)
9. [Archivos de datos](#9-archivos-de-datos)
10. [Puntos de entrada](#10-puntos-de-entrada)
11. [Archivos no utilizados / duplicados](#11-archivos-no-utilizados--duplicados)
12. [Deuda técnica](#12-deuda-técnica)
13. [Riesgos de seguridad](#13-riesgos-de-seguridad)
14. [Riesgos de mantenimiento](#14-riesgos-de-mantenimiento)
15. [Métricas de calidad](#15-métricas-de-calidad)

---

## 1. QUÉ HACE EL SISTEMA

El sistema **evalúa automáticamente candidatos a docente** en la Universidad San Ignacio de Loyola (USIL) contra una rúbrica base institucional de 5 criterios. La implementación actual del motor agrega 2 criterios complementarios, por lo que el cálculo operativo usa 7 componentes evaluativos y produce un ranking con perfiles de contratación recomendados.

### Proceso en resumen

| Paso | Qué ocurre |
|------|-----------|
| Entrada | Excel con candidatos + URLs CTI Vitae + PDFs de CVs |
| Extracción | Scraping de perfiles CTI Vitae (CONCYTEC) + parseo de PDFs |
| Evaluación | Motor con 5 criterios base + 2 complementarios, normalizado a 200 pts |
| Salida | Ranking en JSON + Excel con clasificación de perfil docente |

### Criterios de evaluación (rúbrica)

Los criterios C1-C5 corresponden a la base principal de evaluación. C6 y C7 están implementados en el motor como criterios complementarios de liderazgo y especialización.

| # | Criterio | Máximo |
|---|---------|--------|
| C1 | Formación académica (grado máximo) | 50 pts |
| C2 | Experiencia docente (años) | 40 pts |
| C3 | Experiencia profesional (nivel jerárquico) | 40 pts |
| C4 | Centro de labores (empresa TOP / institución reconocida) | 20 pts |
| C5 | Producción académica (publicaciones, proyectos) | 40 pts |
| C6 | Liderazgo profesional | 20 pts |
| C7 | Especialización | 10 pts |
| **TOTAL** | | **200 pts** |

### Perfiles de contratación resultantes

- **DTC** — Docente a Tiempo Completo
- **DTP** — Docente a Tiempo Parcial
- **PRACTITIONER** — Profesional con experiencia sectorial
- **DOCENTE_INVESTIGADOR** — Perfil mixto docencia + investigación
- **DOCENTE_INVESTIGADOR_HORAS** — Investigador por horas
- **PROFESIONAL_POTENCIAL** — Candidato con proyección
- **ACADEMICO_FORMACION** — Fuerte formación, poca experiencia
- **ACEPTABLE** — Mínimo cumplido
- **NO_ELEGIBLE** — No cumple criterios base

---

## 2. ARQUITECTURA GENERAL

```
┌──────────────────────────────────────────────────────────────────┐
│                    USUARIO (Navegador Web)                       │
│              http://127.0.0.1:5000  (localhost only)             │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP / SSE
┌────────────────────────────▼─────────────────────────────────────┐
│                CAPA DE PRESENTACIÓN                               │
│  index.html + script.js (113 KB) + styles.css (73 KB)            │
│  Framework: Chart.js (CDN) — sin bundler, sin framework JS       │
└────────────────────────────┬─────────────────────────────────────┘
                             │ Flask routes
┌────────────────────────────▼─────────────────────────────────────┐
│              CAPA DE APLICACIÓN (app_web.py — GOD OBJECT)        │
│  Rutas Flask · Manejo de archivos · Orquestación del pipeline    │
│  Estado global mutable · Hilo de evaluación en background        │
└────┬────────────────────────────────────────────┬────────────────┘
     │ invoca                                     │ invoca
┌────▼─────────────────────┐        ┌─────────────▼──────────────┐
│   EXTRACCIÓN DE DATOS    │        │   MOTOR DE EVALUACIÓN      │
│  extractor_cvs.py (PDF)  │        │  motor_evaluacion.py       │
│  extractor_web_cvs.py    │        │  (1134 líneas, soporte de evaluación 5+2) │
│  (CTI Vitae scraping)    │        │  config.py (tablas/pesos)  │
└────┬─────────────────────┘        └─────────────┬──────────────┘
     │ datos normalizados                          │ evaluaciones
     └──────────────────────┬──────────────────────┘
                            │
             ┌──────────────▼───────────────┐
             │     GENERACIÓN DE REPORTES   │
             │  generador_decisiones*.py    │
             │  generador_reportes.py       │
             │  → JSON + Excel en resultados│
             └──────────────────────────────┘
```

**Patrón arquitectónico:** Monolito Flask de un solo proceso, con hilo de background para el pipeline de evaluación.

**Comunicación frontend-backend:** REST JSON + Server-Sent Events (SSE) para progreso en tiempo real.

**Persistencia:** Sistema de archivos local (JSON + Excel). Sin base de datos.

---

## 3. COMPONENTES PRINCIPALES

### 3.1 Orquestador — `app_web.py` (~3 000 líneas)
El componente central. Concentra: servidor Flask, API REST, manejo de sesión, orquestación del pipeline y estado global. Es el componente de mayor riesgo por su tamaño y acoplamiento.

### 3.2 Motor de evaluación — `motor_evaluacion.py` (1 134 líneas)
Núcleo algorítmico. Implementa 5 criterios base de la rúbrica y 2 criterios complementarios con tablas de puntuación, detección de tipo de perfil (clínico / investigador / industrial / docente) y reglas de clasificación final.

### 3.3 Configuración — `config.py` (748 líneas)
Base de conocimiento del sistema: tablas de puntuación, listas de empresas TOP, instituciones de salud, listas de keywords (>1 000 términos). Todo hardcodeado.

### 3.4 Extractor PDF — `extractor_cvs.py` (387 líneas)
Parseo de PDFs usando pdfplumber (primario) con fallback a PyPDF2.

### 3.5 Extractor web — `extractor_web_cvs.py` (1 670 líneas)
Web scraping de perfiles CTI Vitae (CONCYTEC). Implementa reintentos con backoff exponencial (3 intentos, timeout inicial 35 s + 20 s por reintento).

### 3.6 Lanzador — `launcher.py` / `run_server.py`
Bootstrap: verifica librerías, resuelve rutas (dev vs .exe), inicia Flask en localhost:5000.

### 3.7 Generadores de reporte — `generador_reportes.py` + `generador_decisiones*.py`
Exportación a Excel multi-hoja y JSON. Tres versiones del generador de decisiones coexisten sin política clara de deprecación.

---

## 4. FLUJO DE DATOS DE INICIO A FIN

```
INICIO
  │
  ▼
[1] ARRANQUE (launcher.py / run_server.py)
    ├─ Verificar 8 librerías Python
    ├─ Resolver BASE_DIR (dev: directorio actual / .exe: sys._MEIPASS)
    ├─ Crear carpetas: Cvs, LINKS, Rubrica, resultados
    └─ Arrancar Flask en 127.0.0.1:5000 → abrir navegador

[2] CARGA DE DATOS (UI → app_web.py)
    ├─ Usuario sube Excel (columnas I=Nombre, J=DNI, K=URL CTI Vitae)
    ├─ Usuario sube carpeta de PDFs (opcional)
    └─ POST /api/iniciar_evaluacion

[3] EXTRACCIÓN — hilo de background
    │
    ├─ [3a] EXTRACCIÓN PDF (extractor_cvs.py)
    │       ├─ Abrir PDF con pdfplumber
    │       ├─ Si falla → fallback a PyPDF2
    │       └─ Retornar dict: {nombre, archivo, educacion, anos_experiencia,
    │                          publicaciones, texto_completo}
    │
    └─ [3b] EXTRACCIÓN WEB (extractor_web_cvs.py)
            ├─ Para cada URL CTI Vitae del Excel:
            │   ├─ GET URL (timeout=35s, hasta 3 intentos)
            │   ├─ BeautifulSoup: parsear tablas HTML
            │   ├─ Extraer: grados, años experiencia, publicaciones,
            │   │           proyectos, verificación RENATI, última actualización
            │   └─ Si falla → datos vacíos + flag de error
            └─ Retornar lista de dicts normalizados

[4] NORMALIZACIÓN (motor_evaluacion.py → _normalizar_datos_cv)
    ├─ Unificar campos de fuentes PDF y Web
    ├─ Parsear fechas (python-dateutil)
    └─ Calcular años de experiencia acumulados

[5] DETECCIÓN DE PERFIL (_detectar_tipo_perfil)
    ├─ Analizar texto libre con keywords (PERFIL_TIPO_KEYWORDS en config.py)
    └─ Clasificar: clínico | investigador | industrial | docente | general
       (cambia los pesos de cada criterio)

[6] EVALUACIÓN 7 CRITERIOS (motor_evaluacion.py)
    ├─ C1 _evaluar_formacion_academica   → 0–50 pts
    ├─ C2 _evaluar_experiencia_docente   → 0–40 pts
    ├─ C3 _evaluar_experiencia_profesional → 0–40 pts
    ├─ C4 _evaluar_centro_labores        → 0–20 pts (vs. lista MERCO 2025)
    ├─ C5 _evaluar_produccion_academica  → 0–40 pts
    ├─ C6 _evaluar_liderazgo_profesional → 0–20 pts
    └─ C7 _evaluar_especializacion       → 0–10 pts
         └─ TOTAL máximo = 200 pts

[7] CLASIFICACIÓN (_clasificar_candidato)
    ├─ Aplicar árbol de reglas (prioridad por condiciones AND/OR)
    └─ Asignar uno de los 9 perfiles de contratación

[8] GENERACIÓN DE REPORTES
    ├─ generador_reportes.py → Excel multi-hoja
    │   ├─ Hoja 1: Ranking General (todos los candidatos con C1–C7)
    │   ├─ Hoja 2: Clasificaciones por perfil
    │   └─ Hoja 3: Resumen estadístico
    └─ generador_decisiones*.py → JSON con estructura de decisión

[9] ALMACENAMIENTO
    ├─ resultados/clasificacion_final_YYYYMMDD_HHMMSS.json
    ├─ resultados/Analisis_Detallado_YYYYMMDD_HHMMSS.xlsx
    └─ resultados/historial_personas.json  (acumulativo)

[10] PRESENTACIÓN (script.js)
     ├─ SSE en /api/estado_proceso → barras de progreso en tiempo real
     ├─ GET /api/resultados → tabla de ranking interactiva
     └─ Gráficos radar (Chart.js) + botones de descarga

FIN
```

---

## 5. ESTRUCTURA DE CARPETAS

```
PROYECTO RUBRICA/
│
├── EvaluacionDocente_USIL.exe          [67.7 MB — ejecutable compilado]
├── evaluacion_docente_log.txt          [Log de runtime — vacío en repo]
├── ARQUITECTURA_TECNICA.md             [650 líneas — doc preexistente]
│
├── bot_evaluacion_docente/             ★ APLICACIÓN PRINCIPAL
│   ├── launcher.py                     [225 líneas — punto de entrada .exe]
│   ├── run_server.py                   [129 líneas — lanzador alternativo]
│   ├── main.py                         [155 líneas — CLI sin UI web]
│   ├── app_web.py                      [~3 000 líneas — GOD OBJECT Flask]
│   ├── app_web.py.bak_encoding         [Backup con fix de encoding — obsoleto]
│   ├── config.py                       [748 líneas — configuración hardcodeada]
│   ├── motor_evaluacion.py             [1 134 líneas — motor 5+2 criterios]
│   ├── motor_evaluacion-DESKTOP-4AR05VT.py  [644 líneas — DUPLICADO legacy]
│   ├── extractor_cvs.py                [387 líneas — extractor PDF]
│   ├── extractor_web_cvs.py            [1 670 líneas — scraper CTI Vitae]
│   ├── procesar_cvs_web.py             [228 líneas — procesamiento batch web]
│   ├── extraer_links_columna_k.py      [177 líneas — extrae URLs del Excel]
│   ├── actualizar_nombres_links.py     [helper — actualiza metadatos links]
│   ├── analizar_links.py               [helper — validación URLs]
│   ├── buscador_web_cv.py              [~600 líneas — EXPERIMENTAL, no en prod]
│   ├── analizador_rubrica.py           [parser de rúbrica Excel]
│   ├── generador_reportes.py           [205 líneas — export Excel/JSON]
│   ├── generador_decisiones.py         [379 líneas — clasificador v1]
│   ├── generador_decisiones_mejorado.py [580 líneas — clasificador v2]
│   ├── generador_decisiones_nuevo.py   [229 líneas — clasificador v3]
│   ├── compilar.py                     [147 líneas — script PyInstaller]
│   ├── requirements.txt                [10 dependencias]
│   │
│   ├── templates/
│   │   └── index.html                  [17 KB — UI completa]
│   │
│   ├── static/
│   │   ├── script.js                   [113 KB — lógica frontend]
│   │   └── styles.css                  [73 KB — estilos]
│   │
│   ├── resultados/                     [SALIDA — archivos generados en runtime]
│   │   ├── clasificacion_final_*.json  [60+ archivos timestamped]
│   │   ├── Analisis_Detallado_*.xlsx   [10+ archivos timestamped]
│   │   └── historial_personas.json     [acumulativo de evaluaciones]
│   │
│   └── test_*.py                       [Varios tests manuales]
│
├── Cvs/                                [ENTRADA — PDFs de CVs]
│   └── CV Joshua Lopez.pdf             [190 KB — archivo de prueba]
│
├── LINKS/                              [ENTRADA — Excel con candidatos] (vacía)
│
├── Rubrica/
│   └── Ficha_Individual_Seleccion_Docente_2026-1.xlsx  [35 KB — plantilla]
│
├── Extraccion de data/
│   └── Docentes empresas top - copia.xlsx
│
├── Testear/                            [LEGACY — tests manuales]
│   ├── calculadora_FINAL_CORREGIDA.py  [12 KB]
│   ├── calculadora_OFICIAL.py          [12 KB]
│   ├── calculadora_perfil_docente.py   [20 KB]
│   └── test_sistema.py                 [13 KB]
│
├── Testear - copia/                    [DUPLICADO de Testear — eliminar]
│
├── build/                              [Artefactos PyInstaller — no versionar]
├── dist/                               [Distribución compilada]
├── .venv/                              [Python 3.13+ — entorno principal]
├── .venv2/                             [Entorno para build PyInstaller]
│
└── test_*.py (raíz)                    [Tests legacy — no integrados al app]
    ├── test_empresas.py
    ├── test_resumen_problemas.py
    ├── test_sistema_completo.py
    └── verificar_excel.py
```

---

## 6. MÓDULOS Y ARCHIVOS PYTHON

| Archivo | Líneas | Rol | Estado |
|---------|--------|-----|--------|
| `app_web.py` | ~3 000 | Aplicación Flask + orquestador | ACTIVO — refactoring urgente |
| `motor_evaluacion.py` | 1 134 | Motor 5 criterios base + 2 complementarios | ACTIVO — buena calidad |
| `extractor_web_cvs.py` | 1 670 | Scraper CTI Vitae | ACTIVO — funcional |
| `config.py` | 748 | Tablas y keywords | ACTIVO — hardcodeado |
| `extractor_cvs.py` | 387 | Parser PDF | ACTIVO |
| `generador_decisiones_mejorado.py` | 580 | Clasificador v2 | ACTIVO (presumiblemente) |
| `generador_reportes.py` | 205 | Export Excel/JSON | ACTIVO |
| `launcher.py` | 225 | Entry point .exe | ACTIVO |
| `procesar_cvs_web.py` | 228 | Batch web CVs | ACTIVO |
| `generador_decisiones.py` | 379 | Clasificador v1 | LEGADO — duplicado |
| `generador_decisiones_nuevo.py` | 229 | Clasificador v3 | STATUS INCIERTO |
| `motor_evaluacion-DESKTOP-4AR05VT.py` | 644 | Motor — backup | ELIMINAR |
| `run_server.py` | 129 | Lanzador alternativo | ACTIVO (redundante) |
| `main.py` | 155 | CLI pipeline | ACTIVO |
| `compilar.py` | 147 | Build script | ACTIVO |
| `buscador_web_cv.py` | ~600 | Búsqueda experimental | EXPERIMENTAL — no producción |
| `extraer_links_columna_k.py` | 177 | Helper Excel | ACTIVO (utilitario) |
| `analizador_rubrica.py` | ? | Parser rúbrica | STATUS INCIERTO |
| `actualizar_nombres_links.py` | ? | Helper links | STATUS INCIERTO |
| `analizar_links.py` | ? | Validador URLs | STATUS INCIERTO |

---

## 7. CLASES Y FUNCIONES

### `MotorEvaluacion` — `motor_evaluacion.py`

```python
class MotorEvaluacion:
    # Atributos
    criterios: Dict          # pesos por criterio
    pesos: Dict              # pesos por tipo de perfil

    # Métodos públicos
    evaluar_multiples_cvs(lista_cvs: List[Dict]) -> List[Dict]
    evaluar_cv_completo(cv_data: Dict) -> Dict

    # Métodos privados — criterios
    _evaluar_formacion_academica(cv_data) -> int      # 0–50
    _evaluar_experiencia_docente(cv_data) -> int       # 0–40
    _evaluar_experiencia_profesional(cv_data) -> int   # 0–40
    _evaluar_centro_labores(cv_data) -> int            # 0–20
    _evaluar_produccion_academica(cv_data) -> int      # 0–40
    _evaluar_liderazgo_profesional(cv_data) -> int     # 0–20
    _evaluar_especializacion(cv_data) -> int           # 0–10

    # Métodos privados — utilidades
    _clasificar_candidato(scores, perfil_tipo) -> str
    _detectar_tipo_perfil(cv_data) -> str
    _normalizar_datos_cv(cv_data) -> Dict
    _extraer_anos_texto(texto: str) -> int
    _calcular_anos_experiencia(cv_data) -> int
```

**Constantes de clasificación:**
```
TOTAL_MAXIMO = 200
Umbrales: NO_ELEGIBLE (C1=0 AND C5=0), DTC (≥110), DTP (≥100),
          DOCENTE_INVESTIGADOR_HORAS (≥150 AND C5≥30), ACEPTABLE (≥60)
```

---

### `ExtractorCV` — `extractor_cvs.py`

```python
class ExtractorCV:
    cv_path: str
    nombre_archivo: str
    texto_completo: str
    datos: Dict

    extraer_texto() -> str           # pdfplumber + fallback PyPDF2
    extraer_nombre() -> str
    contar_keywords(keywords) -> int
    extraer_anos_experiencia() -> int

# Función de módulo
procesar_todos_cvs() -> List[Dict]   # procesa todo el directorio Cvs/
```

---

### `ExtractorWebCVs` — `extractor_web_cvs.py`

```python
class ExtractorWebCVs:
    session: requests.Session
    MAX_REINTENTOS = 3
    TIMEOUT_INICIAL = 35     # segundos
    TIMEOUT_INCREMENTO = 20  # por reintento

    extraer_cv_desde_url(url: str) -> Dict
    procesar_excel_links() -> List[Dict]
    procesar_multiples_urls(urls, callback=None) -> List[Dict]
    _hacer_peticion_con_reintentos(url) -> Response
    _hacer_peticion_reanalisis(url) -> Response

# Estado global de progreso (thread-safe con Lock)
_progress_state: Dict
_progress_lock: threading.Lock
```

**Output por candidato:**
```json
{
  "nombre": "string",
  "url": "CTI Vitae URL",
  "fuente": "CTI_VITAE",
  "educacion": {
    "doctorado": bool, "doctorado_completo": bool,
    "maestria": bool, "maestria_completa": bool,
    "grado_maximo": "string"
  },
  "anos_experiencia_docente": int,
  "anos_experiencia_profesional": int,
  "publicaciones": int,
  "articulos_indexados": int,
  "tiene_scopus": bool,
  "tiene_wos": bool,
  "proyectos": int,
  "perfil_desactualizado": bool,
  "meses_sin_actualizar": int,
  "texto_completo": "string"
}
```

---

### `GeneradorReportes` — `generador_reportes.py`

```python
class GeneradorReportes:
    generar_excel_comparativo() -> str    # → path del archivo .xlsx
    generar_json_decision() -> str        # → path del archivo .json
    generar_reporte_texto() -> str        # → string (NO USADO en prod)
```

**Excel generado (3 hojas):**
1. Ranking General — todos los candidatos con C1–C7
2. Clasificaciones — perfil asignado por candidato
3. Resumen por Perfil — estadísticos agregados

---

### Funciones en `app_web.py` (selección)

```python
# Rutas Flask
@app.route('/')                          -> index.html
@app.route('/api/iniciar_evaluacion')    -> lanza hilo de evaluación
@app.route('/api/estado_proceso')        -> SSE stream de progreso
@app.route('/api/resultados')            -> JSON resultados finales
@app.route('/api/subir_archivo')         -> upload Excel
@app.route('/api/subir_pdfs')            -> upload PDFs
@app.route('/api/analizar_link')         -> analizar 1 URL CTI Vitae
@app.route('/api/obtener_datos_requerimientos') -> leer Excel requerimientos

# Funciones internas
leer_datos_desde_requerimientos() -> List[Dict]
cargar_datos_requerimientos_para_match() -> Dict
_clave_persona(dni, nombre) -> str
_guardar_historial_personas(evaluaciones) -> None
_evaluar_candidatos() -> None      # ejecutado en hilo background
_generar_reportes() -> None
```

---

## 8. DEPENDENCIAS

### `requirements.txt`

| Librería | Versión | Uso |
|---------|---------|-----|
| `Flask` | ==3.0.0 | Framework web |
| `pdfplumber` | ==0.10.3 | Extracción PDF (primario) |
| `PyPDF2` | ==3.0.1 | Extracción PDF (fallback) |
| `pandas` | >=2.1.4 | Manipulación de datos tabulares |
| `openpyxl` | >=3.1.5 | Lectura/escritura Excel |
| `requests` | >=2.31.0 | HTTP para web scraping |
| `beautifulsoup4` | >=4.12.0 | Parsing HTML (CTI Vitae) |
| `python-dateutil` | ==2.8.2 | Parsing de fechas en texto libre |
| `numpy` | >=1.26.3 | Operaciones numéricas |
| *(implícito)* | — | `werkzeug` (dependencia de Flask) |

### Entornos virtuales

| Entorno | Uso |
|--------|-----|
| `.venv/` | Desarrollo y ejecución — Python 3.13+ |
| `.venv2/` | Build PyInstaller — contiene `beautifulsoup4-4.14.3`, `cffi`, etc. |

### Dependencias de CDN (frontend)

- **Chart.js** — cargado desde CDN en `index.html` (sin lock de versión)

---

## 9. ARCHIVOS DE DATOS

### Entrada

| Archivo | Ubicación | Formato | Campos relevantes |
|---------|-----------|---------|-------------------|
| Lista de candidatos | `LINKS/INFORMACION DE VALIDACION.xlsx` | Excel | I=Nombre, J=DNI, K=URL CTI Vitae |
| Requerimientos | `LINKS/Requerimiento docentes 2026-1 300126.xlsx` | Excel | FACULTAD, CARRERA, DNI, CTI |
| CVs en PDF | `Cvs/*.pdf` | PDF | Texto libre |
| Rúbrica | `Rubrica/Ficha_Individual_Seleccion_Docente_2026-1.xlsx` | Excel | Referencia (no parseado dinámicamente) |

### Salida

| Archivo | Ubicación | Formato | Contenido |
|---------|-----------|---------|-----------|
| Clasificación | `resultados/clasificacion_final_YYYYMMDD_HHMMSS.json` | JSON | Ranking completo + scores |
| Análisis detallado | `resultados/Analisis_Detallado_YYYYMMDD_HHMMSS.xlsx` | Excel | 3 hojas con análisis |
| Historial | `resultados/historial_personas.json` | JSON | Acumulativo de todas las evaluaciones |

---

## 10. PUNTOS DE ENTRADA

| Modo | Comando | Descripción |
|------|---------|-------------|
| Ejecutable Windows | `EvaluacionDocente_USIL.exe` | Producción — todo incluido |
| Flask con UI | `python launcher.py` | Desarrollo — abre navegador |
| Flask alternativo | `python run_server.py` | PyInstaller-compatible |
| CLI sin UI | `python main.py` | Pipeline headless, salida en consola |
| Compilación | `python compilar.py` | Genera nuevo .exe en `dist/` |

### Flujo de arranque

```
EvaluacionDocente_USIL.exe
  └─> launcher.py
        ├─ verificar_librerias()       [chequea 8 librerías]
        ├─ get_base_path()             [detecta dev vs .exe]
        ├─ get_data_path()             [resuelve rutas Windows]
        ├─ crear carpetas              [Cvs, LINKS, Rubrica, resultados]
        └─> app_web.py                 [Flask en 127.0.0.1:5000]
              └─> index.html           [abre en navegador]
```

---

## 11. ARCHIVOS NO UTILIZADOS / DUPLICADOS

### Eliminar con seguridad

| Archivo | Razón |
|---------|-------|
| `motor_evaluacion-DESKTOP-4AR05VT.py` | Backup/legacy — 644 líneas duplicadas del motor principal |
| `app_web.py.bak_encoding` | Backup temporal con fix de encoding ya aplicado |
| `Testear - copia/` | Carpeta duplicada de `Testear/` |
| `build/` | Artefactos de compilación — no se versionan |

### Evaluar antes de eliminar

| Archivo | Situación |
|---------|-----------|
| `generador_decisiones.py` (v1) | Probablemente reemplazado por `_mejorado.py` pero puede ser importado |
| `generador_decisiones_nuevo.py` (v3) | Relación con v1 y v2 sin documentar |
| `buscador_web_cv.py` | Experimental — no está en el pipeline principal |
| `Testear/calculadora_*.py` | Prototipos del motor — sin conexión con código actual |
| Tests en raíz (`test_*.py`, `verificar_excel.py`) | Sin integración pytest |

### Archivos con historia incierta

| Archivo | Acción recomendada |
|---------|-------------------|
| `analizador_rubrica.py` | Verificar si es importado por `app_web.py` |
| `actualizar_nombres_links.py` | Verificar uso real |
| `analizar_links.py` | Verificar uso real |

---

## 12. DEUDA TÉCNICA

### Alta prioridad

| ID | Problema | Archivo | Impacto |
|----|---------|---------|---------|
| DT-01 | **God Object** — `app_web.py` (3 000 líneas) mezcla rutas, lógica de negocio, I/O, estado y orquestación | `app_web.py` | Mantenibilidad crítica |
| DT-02 | **Estado global mutable sin locks** — `estado_proceso`, `archivo_excel_subido` modificados desde múltiples hilos | `app_web.py:49–64` | Race conditions |
| DT-03 | **Tres versiones del generador de decisiones** sin política de deprecación | `generador_decisiones*.py` | Inconsistencia de resultados |
| DT-04 | **Sin base de datos** — JSON como almacenamiento principal no escala | `resultados/*.json` | Escalabilidad |
| DT-05 | **0% cobertura de tests automatizados** — todo manual | Toda la app | Regresiones sin detección |

### Media prioridad

| ID | Problema | Archivo | Impacto |
|----|---------|---------|---------|
| DT-06 | **Lista MERCO 2025 hardcodeada** (150+ empresas en `config.py`) | `config.py` | Mantenimiento anual costoso |
| DT-07 | **Tres entradas para el mismo campo** — Excel + CTI Vitae + PDF sin reconciliación | `motor_evaluacion.py` | Deduplicación ausente |
| DT-08 | **Flag `perfil_desactualizado` calculado pero ignorado** | `extractor_web_cvs.py` + `motor_evaluacion.py` | Evaluaciones sobre datos obsoletos |
| DT-09 | **Valores `None` vs `0` no distinguibles** — extracción fallida = 0 puntos | Todo el pipeline | Falsos negativos |
| DT-10 | **Sin type hints en `app_web.py`** | `app_web.py` | IDE sin ayuda, errores silenciosos |
| DT-11 | **Chart.js desde CDN sin versión fija** | `index.html` | Build no reproducible |
| DT-12 | **Tipos de perfil detectados con keywords hardcodeadas** en `config.py` | `config.py` | Requiere código para actualizar vocabulario |

### Valores mágicos relevantes

```python
# motor_evaluacion.py
TOTAL_MAXIMO = 200
C1_MAX, C2_MAX, C3_MAX, C4_MAX, C5_MAX, C6_MAX, C7_MAX = 50, 40, 40, 20, 40, 20, 10
UMBRAL_DTC = 110
UMBRAL_DTP = 100
UMBRAL_INVESTIGADOR_HORAS = 150
UMBRAL_ACEPTABLE = 60
UMBRAL_PRACTITIONER = 90

# extractor_web_cvs.py
TIMEOUT_INICIAL = 35      # segundos
TIMEOUT_INCREMENTO = 20   # por reintento
MAX_REINTENTOS = 3
```

---

## 13. RIESGOS DE SEGURIDAD

### Críticos (acción inmediata)

| ID | Vulnerabilidad | Ubicación | Norma afectada | Remediación |
|----|---------------|-----------|----------------|-------------|
| S-01 | **DNI almacenado en texto plano** en JSON | `resultados/*.json`, `historial_personas.json` | Ley 29733 (Perú) | Hash SHA-256 + salt antes de persistir |
| S-02 | **Sin sanitización de nombres de archivo** en uploads | `app_web.py` routes upload | OWASP A05 — Path Traversal | `werkzeug.utils.secure_filename()` |
| S-03 | **Sin validación de tipo MIME** en uploads | `app_web.py` upload handlers | OWASP A03 — Malicious Upload | `python-magic` para verificar contenido real |
| S-04 | **Estado global compartido entre usuarios** sin autenticación | `app_web.py` | — | Aislamiento por sesión + `threading.Lock()` |

### Altos

| ID | Vulnerabilidad | Ubicación | Remediación |
|----|---------------|-----------|-------------|
| S-05 | **Sin log de auditoría** para decisiones de contratación | `app_web.py` | `logging.RotatingFileHandler` con `audit.log` |
| S-06 | **Headers de scraping sin identificación institucional** | `extractor_web_cvs.py` | `User-Agent: USIL-TalentoAcademico/3.0` |
| S-07 | **Sin autenticación** — cualquier persona en la red puede usar la app | `app_web.py` | Solo localhost actualmente (mitigado parcialmente) |

---

## 14. RIESGOS DE MANTENIMIENTO

### Arquitectónicos

| Riesgo | Descripción | Severidad |
|--------|-------------|-----------|
| **Ruptura del scraper** | CTI Vitae puede cambiar su HTML sin previo aviso; no hay API oficial | ALTA |
| **Desactualización de MERCO** | Lista de empresas TOP se publica anualmente; requiere edición de código | ALTA |
| **Inconsistencia entre versiones de decisiones** | No está claro qué `generador_decisiones*.py` es el canónico | MEDIA |
| **Single point of failure** | `app_web.py` concentra todo; un bug afecta toda la aplicación | ALTA |
| **Acumulación de archivos de resultados** | `resultados/` ya tiene 70+ archivos; sin política de retención | BAJA |

### Operacionales

| Riesgo | Descripción | Severidad |
|--------|-------------|-----------|
| **Sin usuario único** | Dos evaluaciones simultáneas corrompen `estado_proceso` | ALTA |
| **Sin límite de tamaño de historial** | `historial_personas.json` crece indefinidamente | MEDIA |
| **Sin monitoreo de errores** | Fallos de extracción web pasan silenciosamente a 0 pts | ALTA |
| **Dependencia de rutas Windows** | `os.path.join` con nombres de carpeta en español con espacios | MEDIA |

---

## 15. MÉTRICAS DE CALIDAD

| Módulo | Líneas | Type hints | Docstrings | Tests | Calidad |
|--------|--------|-----------|-----------|-------|---------|
| `motor_evaluacion.py` | 1 134 | ~60% | ~70% | Manual | BUENA |
| `extractor_web_cvs.py` | 1 670 | ~40% | ~50% | Manual | ACEPTABLE |
| `config.py` | 748 | ~80% | ~30% | N/A | ACEPTABLE |
| `app_web.py` | ~3 000 | ~10% | ~20% | Manual | CRÍTICA |
| `extractor_cvs.py` | 387 | ~50% | ~60% | Manual | BUENA |
| `generador_reportes.py` | 205 | ~50% | ~60% | Manual | BUENA |
| `launcher.py` | 225 | ~30% | ~40% | — | ACEPTABLE |

**Cobertura de tests automatizados:** 0%
**Duplicación de código estimada:** MODERADA (3 versiones de generadores + motor duplicado)
**Deuda técnica total estimada:** ~3 semanas de trabajo para remediación completa

---

## RESUMEN EJECUTIVO

El sistema es **funcionalmente completo y operativamente desplegado** como ejecutable Windows para uso interno en USIL. El núcleo algorítmico (`motor_evaluacion.py`) tiene buena calidad estructural. El principal riesgo es la concentración de responsabilidades en `app_web.py` (~3 000 líneas), la ausencia de tests automatizados y las vulnerabilidades de datos personales (DNI en texto plano).

**Roadmap de remediación sugerido:**

| Fase | Acción | Esfuerzo |
|------|--------|---------|
| 1 — Seguridad | Hash de DNI + sanitización de uploads + audit log | 3 días |
| 2 — Estabilidad | `threading.Lock` en estado global + manejo de errores de extracción | 2 días |
| 3 — Mantenibilidad | Dividir `app_web.py` en routers + services | 5 días |
| 4 — Calidad | Suite pytest + CI básico | 5 días |
| 5 — Configuración | Externalizar lista MERCO a Excel editable | 2 días |

---

*Inventario generado automáticamente. Fecha: 2026-06-01.*
