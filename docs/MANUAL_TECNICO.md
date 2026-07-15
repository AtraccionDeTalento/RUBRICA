# Manual Técnico — Sistema de Evaluación Automática de Docentes USIL

**Universidad San Ignacio de Loyola · People Analytics**
**Audiencia:** Desarrolladores, mantenedores, equipo de TI
**Versión:** 3.0 · **Fecha:** 2026-06-01

---

## Índice

1. [Entorno de desarrollo](#1-entorno-de-desarrollo)
2. [Estructura del proyecto](#2-estructura-del-proyecto)
3. [Módulo: launcher.py / run_server.py](#3-módulo-launcherpy--run_serverpy)
4. [Módulo: app_web.py](#4-módulo-app_webpy)
5. [Módulo: motor_evaluacion.py](#5-módulo-motor_evaluacionpy)
6. [Módulo: config.py](#6-módulo-configpy)
7. [Módulo: extractor_cvs.py](#7-módulo-extractor_cvspy)
8. [Módulo: extractor_web_cvs.py](#8-módulo-extractor_web_cvspy)
9. [Módulo: generador_reportes.py](#9-módulo-generador_reportespy)
10. [Módulo: generador_decisiones_mejorado.py](#10-módulo-generador_decisiones_mejoradopy)
11. [Módulo: main.py (CLI)](#11-módulo-mainpy-cli)
12. [Módulo: compilar.py](#12-módulo-compilarpy)
13. [Frontend: templates y static](#13-frontend-templates-y-static)
14. [Gestión de dependencias](#14-gestión-de-dependencias)
15. [Pipeline de datos: referencia completa](#15-pipeline-de-datos-referencia-completa)
16. [Configuración del sistema](#16-configuración-del-sistema)
17. [Mantenimiento operacional](#17-mantenimiento-operacional)
18. [Procedimientos de troubleshooting](#18-procedimientos-de-troubleshooting)

---

## 1. Entorno de desarrollo

### Requisitos

| Componente | Versión mínima | Notas |
|-----------|---------------|-------|
| Python | 3.13+ | Embebido en el .exe final |
| pip | 23+ | |
| Sistema operativo | Windows 10/11 x64 | El .exe es exclusivo para Windows |
| RAM recomendada | 4 GB | El pipeline con 100+ candidatos usa ~150 MB peak |
| Conectividad | Internet | Requerida para extracción CTI Vitae |

### Configuración inicial

```bash
# 1. Crear entorno virtual
python -m venv .venv

# 2. Activar
.venv\Scripts\activate

# 3. Instalar dependencias
pip install -r bot_evaluacion_docente/requirements.txt

# 4. Verificar instalación
python -c "import flask, pdfplumber, pandas, bs4, requests; print('OK')"
```

### Estructura de entornos virtuales

| Directorio | Propósito |
|-----------|-----------|
| `.venv/` | Entorno de desarrollo y ejecución en modo código |
| `.venv2/` | Entorno de build para PyInstaller (incluye `cffi`, `beautifulsoup4-4.14.3`) |

> Los dos entornos son necesarios porque PyInstaller requiere recopilar dependencias compiladas (`.pyd`, `.dll`) que difieren del entorno de desarrollo estándar.

---

## 2. Estructura del proyecto

```
PROYECTO RUBRICA/
├── EvaluacionDocente_USIL.exe          ← Distribución actual (67.7 MB)
├── evaluacion_docente_log.txt          ← Log de runtime (vacío por defecto)
├── ARQUITECTURA_TECNICA.md             ← Documentación preexistente (650 líneas)
│
├── bot_evaluacion_docente/             ← APLICACIÓN PRINCIPAL
│   ├── launcher.py                     ← Punto de entrada del .exe
│   ├── run_server.py                   ← Lanzador alternativo (PyInstaller-compatible)
│   ├── main.py                         ← Pipeline CLI headless
│   ├── app_web.py                      ← God Object: Flask + orquestador
│   ├── config.py                       ← Base de conocimiento (tablas, keywords)
│   ├── motor_evaluacion.py             ← Motor de evaluación 5 criterios base + 2 complementarios
│   ├── extractor_cvs.py                ← Extractor de PDFs
│   ├── extractor_web_cvs.py            ← Scraper CTI Vitae
│   ├── procesar_cvs_web.py             ← Procesamiento batch web CVs
│   ├── generador_reportes.py           ← Export Excel/JSON
│   ├── generador_decisiones_mejorado.py← Clasificador principal (v2)
│   ├── generador_decisiones.py         ← Clasificador v1 (LEGADO)
│   ├── generador_decisiones_nuevo.py   ← Clasificador v3 (STATUS INCIERTO)
│   ├── compilar.py                     ← Script de build PyInstaller
│   ├── requirements.txt                ← 10 dependencias Python
│   │
│   ├── templates/index.html            ← UI completa (SPA)
│   ├── static/script.js                ← Lógica frontend (113 KB)
│   ├── static/styles.css               ← Estilos (73 KB)
│   │
│   └── resultados/                     ← Salida (generada en runtime)
│       ├── clasificacion_final_*.json
│       ├── Analisis_Detallado_*.xlsx
│       └── historial_personas.json
│
├── Cvs/                                ← Entrada: PDFs de CVs
├── LINKS/                              ← Entrada: Excel de candidatos
├── Rubrica/                            ← Plantilla de rúbrica institucional
│
├── .venv/                              ← Entorno desarrollo
├── .venv2/                             ← Entorno build
├── build/                              ← Artefactos PyInstaller (no versionar)
└── dist/                               ← Distribución compilada
```

---

## 3. Módulo: launcher.py / run_server.py

### Responsabilidad

Punto de arranque del sistema. Resuelve rutas según el entorno de ejecución (código fuente vs. ejecutable `.exe`), verifica la presencia de librerías críticas y lanza el servidor Flask.

### launcher.py — Funciones clave

```python
def verificar_librerias() -> bool:
    """
    Verifica que todas las librerías requeridas estén instaladas.
    Comprueba: flask, pandas, pdfplumber, openpyxl, PyPDF2,
               requests, bs4, dateutil.
    Retorna True si todo OK. Si falla, imprime error y retorna False.
    """

def get_base_path() -> str:
    """
    Detecta el entorno de ejecución.
    - En modo .exe (PyInstaller): retorna sys._MEIPASS (directorio temporal)
    - En modo desarrollo: retorna el directorio del script
    """

def get_data_path() -> str:
    """
    Resuelve el directorio de datos del usuario (Cvs/, LINKS/, Rubrica/).
    - En modo .exe: directorio del .exe en disco
    - En modo desarrollo: directorio padre del script
    """

def abrir_navegador() -> None:
    """
    Abre http://127.0.0.1:5000 en el navegador por defecto.
    Se ejecuta en un hilo separado con delay de 1.5s para dar
    tiempo a Flask de inicializar.
    """

def main() -> None:
    """
    Función principal: verifica librerías, establece variables de entorno,
    crea directorios necesarios y arranca Flask.
    Variables de entorno que establece:
    - EVALUACION_DOCENTE_BASE: ruta base del ejecutable
    - EVALUACION_DOCENTE_APP: ruta del directorio de la aplicación
    """
```

### run_server.py — Diferencias respecto a launcher.py

| Característica | launcher.py | run_server.py |
|---------------|-------------|---------------|
| Comprobación de puerto | No | Sí — `puerto_disponible(5000)` |
| Logging a archivo | No | Sí — cuando es .exe, redirige stdout/stderr a `evaluacion_docente_log.txt` |
| Flag `--no-browser` | No | Sí — permite lanzar sin abrir navegador |
| Mensaje de error GUI | No | Sí — `ctypes.windll.user32.MessageBoxW` en caso de fallo |
| Encoding Windows | Básico | Forzado: `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` |

### Variables de entorno utilizadas

| Variable | Establecida por | Leída por | Descripción |
|---------|----------------|-----------|-------------|
| `EVALUACION_DOCENTE_BASE` | launcher.py | app_web.py, config.py | Ruta base del ejecutable |
| `EVALUACION_DOCENTE_APP` | launcher.py | app_web.py | Ruta del directorio de la aplicación |

---

## 4. Módulo: app_web.py

### Responsabilidad

Servidor Flask principal. Concentra en un único archivo (~3 000 líneas): definición de rutas, orquestación del pipeline de evaluación, manejo de estado global, uploads de archivos y generación de reportes.

> **Nota de mantenimiento:** Este módulo es el principal riesgo de mantenibilidad del sistema. Viola el Principio de Responsabilidad Única (SRP). Cualquier modificación requiere leer y entender el archivo completo para evitar efectos secundarios.

### Estado global (variables a nivel de módulo)

```python
estado_proceso: Dict = {
    "iniciado": False,
    "completado": False,
    "progreso": 0,            # 0-100
    "mensaje": "",
    "resultados": [],
    "error": None,
    "total_candidatos": 0,
    "candidatos_procesados": 0
}

archivo_excel_subido: Optional[str] = None    # Ruta del Excel subido
carpeta_pdfs_subida: Optional[str] = None     # Ruta de PDFs subidos
modo_rapido_activo: bool = False              # Flag de modo rápido

HISTORIAL_PERSONAS_PATH: str = "resultados/historial_personas.json"
```

> **Riesgo crítico:** `estado_proceso` se modifica desde el hilo principal y desde el hilo de background `_evaluar_candidatos()` sin ningún mecanismo de sincronización (`threading.Lock`). En acceso concurrente, esto puede producir lecturas inconsistentes o escrituras perdidas.

### Rutas Flask registradas

| Método | Ruta | Función | Descripción |
|--------|------|---------|-------------|
| GET | `/` | `index()` | Sirve `templates/index.html` |
| POST | `/api/subir_archivo` | `subir_archivo()` | Upload Excel de candidatos |
| POST | `/api/subir_pdfs` | `subir_pdfs()` | Upload carpeta de PDFs |
| POST | `/api/iniciar_evaluacion` | `iniciar_evaluacion()` | Lanza pipeline en background |
| GET | `/api/estado_proceso` | `estado_proceso_stream()` | SSE: stream de progreso |
| GET | `/api/resultados` | `obtener_resultados()` | JSON con ranking final |
| POST | `/api/analizar_link` | `analizar_link()` | Analizar un URL CTI Vitae |
| GET | `/api/obtener_datos_requerimientos` | `obtener_datos_requerimientos()` | Leer Excel de requerimientos |

### Funciones internas principales

```python
def leer_datos_desde_requerimientos() -> List[Dict]:
    """
    Lee el archivo Excel de requerimientos docentes.
    Busca en LINKS/ el archivo con 'Requerimiento' en el nombre.
    Hoja: '2026.1'
    Columnas: FACULTAD, CARRERA, APELLIDOS Y NOMBRES DEL CANDIDATO, DNI, CTI
    Retorna lista de dicts con los datos de cada candidato.
    """

def _clave_persona(dni: str, nombre: str) -> str:
    """
    Genera una clave única para identificar a una persona.
    Usa DNI si está disponible, sino normaliza el nombre.
    Se usa para deduplicar en historial_personas.json.
    """

def _guardar_historial_personas(evaluaciones: List[Dict]) -> None:
    """
    Persiste evaluaciones en historial_personas.json.
    Merge con historial existente por _clave_persona.
    Las evaluaciones más recientes sobreescriben las anteriores.
    No implementa versioning ni rollback.
    """

def _evaluar_candidatos() -> None:
    """
    Pipeline principal — ejecutado en threading.Thread.
    Orquesta todo el proceso:
    1. Extrae CVs de PDFs
    2. Extrae CVs de URLs CTI Vitae (Excel)
    3. Combina fuentes por nombre/DNI
    4. Llama a MotorEvaluacion.evaluar_multiples_cvs()
    5. Genera reportes
    6. Actualiza estado_proceso["completado"] = True
    
    IMPORTANTE: No tiene manejo de excepciones global.
    Un error en cualquier paso deja estado_proceso["completado"] = False
    sin informar al usuario la causa exacta del fallo.
    """
```

### Configuración Flask

```python
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

# Directorio de uploads
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'evaluacion_docente_uploads')
```

---

## 5. Módulo: motor_evaluacion.py

### Responsabilidad

Núcleo algorítmico del sistema. Implementa la rúbrica institucional base de 5 criterios, ampliada en código con 2 criterios complementarios, la detección dinámica de tipo de perfil y el árbol de clasificación de candidatos.

### Clase MotorEvaluacion

```python
class MotorEvaluacion:
    def __init__(self, criterios: Optional[Dict] = None, pesos: Optional[Dict] = None):
        """
        Inicializa el motor con las tablas de config.py por defecto.
        criterios: override de las tablas de puntuación
        pesos: override de los pesos por tipo de perfil
        """
```

### Métodos públicos

```python
def evaluar_multiples_cvs(self, lista_cvs: List[Dict]) -> List[Dict]:
    """
    Evalúa una lista de candidatos aplicando evaluar_cv_completo a cada uno.
    Ordena los resultados por puntuacion_total descendente.
    Agrega el campo 'posicion' (1-based ranking).
    Retorna lista ordenada de dicts de evaluación.
    """

def evaluar_cv_completo(self, cv_data: Dict) -> Dict:
    """
    Pipeline de evaluación para un candidato:
    1. _normalizar_datos_cv(cv_data)
    2. _detectar_tipo_perfil(cv_data)
    3. Evaluar C1-C7
    4. Sumar total
    5. _clasificar_candidato()
    
    Retorna dict con:
    {
      nombre, perfil_recomendado, puntuacion_total, porcentaje,
      tipo_perfil_detectado, c1-c7 (scores individuales),
      detalle_criterios (dict con justificación de cada score),
      perfiles_cumplidos (lista de perfiles que el candidato cumple)
    }
    """
```

### Métodos privados — Criterios

#### `_evaluar_formacion_academica(cv_data) -> int`

| Condición detectada | Puntos |
|-------------------|--------|
| Doctorado completo | 50 |
| Doctorado en curso | 40 |
| Maestría completa | 30 |
| Maestría en curso | 25 |
| Licenciatura / Título profesional | 15 |
| Bachiller | 10 |
| Estudiante universitario | 5 |
| Sin evidencia académica | 0 |

Detección: keywords en `texto_completo` + campos estructurados de `educacion{}`. Prioriza los campos estructurados (extraídos de CTI Vitae) sobre el texto libre (PDFs).

#### `_evaluar_experiencia_docente(cv_data) -> int`

| Rango de años | Puntos |
|--------------|--------|
| ≥ 10 años | 40 |
| 6 – 9 años | 30 |
| 3 – 5 años | 20 |
| 0 – 2 años | 0 |

Fuente: campo `anos_experiencia_docente`. Si la extracción falló, puede retornar 0 aunque el candidato tenga experiencia real (falso negativo — ver DT-09 en AUDITORIA_CODIGO.md).

#### `_evaluar_experiencia_profesional(cv_data) -> int`

| Nivel detectado | Puntos |
|----------------|--------|
| Alta dirección (CEO, Director, Gerente General) | 40 |
| Mando medio (Gerente, Jefe, Coordinador) | 30 |
| Senior profesional | 25 |
| Intermedio / Junior | 15 |
| Analista / Operativo | 10 |
| Sin experiencia | 0 |

Detección basada en keywords de nivel jerárquico en `experiencia_laboral` y `texto_completo`.

#### `_evaluar_centro_labores(cv_data) -> int`

| Tipo de institución | Puntos |
|--------------------|--------|
| Empresa TOP 100 MERCO 2025 (`EMPRESAS_TOP_PERU`) | 20 |
| Big 4 (Deloitte, PwC, EY, KPMG) | 15 |
| Institución de alta complejidad en salud | 20 |
| Empresa mediana reconocida | 15 |
| Empresa pequeña | 10 |
| Trabajo independiente / freelance | 0 |

La lista `EMPRESAS_TOP_PERU` en `config.py` contiene ~150 empresas hardcodeadas. Se actualiza manualmente una vez al año.

#### `_evaluar_produccion_academica(cv_data) -> int`

| Nivel de producción | Puntos |
|--------------------|--------|
| Libros publicados o artículos en revistas indexadas | 40 |
| Artículos en Scopus / Web of Science | 30 |
| Proyectos de investigación activos | 30 |
| Producción inicial (artículos no indexados) | 10 |
| Sin evidencia | 0 |

**Limitación conocida:** La detección de "Scopus" se basa en presencia de la palabra clave en el texto. No verifica el artículo en la base de datos de Scopus (se registra como DT-07 en el inventario técnico).

#### `_evaluar_liderazgo_profesional(cv_data) -> int`

| Nivel | Puntos |
|-------|--------|
| Alto (Director de área, Decano, Rector, CEO) | 20 |
| Medio (Jefe de área, Coordinador académico) | 15 |
| Básico (Líder de proyecto, Representante estudiantil) | 10 |
| Sin evidencia | 0 |

#### `_evaluar_especializacion(cv_data) -> int`

| Nivel | Puntos |
|-------|--------|
| Alta especialización (UCI, Oncología, Neurocirugía, Trasplantes) | 10 |
| Especialización media (Cardiología, Geriatría, Cirugía) | 6 |
| Especialización básica (Residencia médica, Diplomado) | 3 |
| Sin especialización | 0 |

### Método `_detectar_tipo_perfil`

Analiza el `texto_completo` del candidato buscando keywords definidas en `PERFIL_TIPO_KEYWORDS` de `config.py`. Retorna uno de: `"clínico"`, `"investigador"`, `"industrial"`, `"docente"`, `"general"`.

El tipo detectado modifica los pesos de los criterios en `PESOS_POR_TIPO`:

| Tipo | C1 | C2 | C3 | C4 | C5 | C6 | C7 |
|------|----|----|----|----|----|----|-----|
| clínico | 18% | 12% | 32% | 18% | 10% | 8% | 2% |
| investigador | 25% | 12% | 15% | 5% | 28% | 10% | 5% |
| industrial | 18% | 8% | 38% | 22% | 5% | 7% | 2% |
| docente | 22% | 30% | 18% | 8% | 12% | 8% | 2% |
| general | 25% | 20% | 20% | 10% | 15% | 8% | 2% |

> **Nota:** Los pesos no alteran la puntuación directa de cada criterio sino el cálculo de puntuación ponderada que se usa como desempate en clasificaciones límite. El score principal siempre es la suma directa C1+C2+...+C7.

---

## 6. Módulo: config.py

### Responsabilidad

Base de conocimiento del sistema. Contiene todas las tablas de puntuación, listas de referencia y vocabulario de keywords. Es el único archivo que debe editarse para ajustar la lógica de evaluación sin tocar el código del motor.

### Variables de configuración de rutas

```python
BASE_DIR                     # Directorio raíz del proyecto
CVS_DIR                      # Ruta de Cvs/
RUBRICA_DIR                  # Ruta de Rubrica/
RESULTADOS_DIR               # Ruta de resultados/
LINKS_DIR                    # Ruta de LINKS/
INFORMACION_VALIDACION_PATH  # Ruta al Excel principal de candidatos
REQUERIMIENTOS_DOCENTES_PATH # Ruta al Excel de requerimientos por facultad
```

### Tablas de puntuación

```python
TABLA_FORMACION_ACADEMICA: Dict[str, int]
TABLA_EXPERIENCIA_DOCENTE: Dict[str, int]
TABLA_EXPERIENCIA_PROFESIONAL: Dict[str, int]
TABLA_CENTRO_LABORES: Dict[str, int]
TABLA_PRODUCCION_ACADEMICA: Dict[str, int]
TABLA_LIDERAZGO: Dict[str, int]
TABLA_ESPECIALIZACION: Dict[str, int]
```

### Listas de referencia

```python
EMPRESAS_TOP_PERU: List[str]
# ~150 empresas. Fuente: MERCO 2025.
# MANTENIMIENTO ANUAL: actualizar con lista MERCO del año en curso.

INSTITUCIONES_ALTA_COMPLEJIDAD_SALUD: List[str]
# ~30 hospitales e institutos de referencia nacional.
```

### Vocabulario de keywords

```python
KEYWORDS_ESTUDIANTE: List[str]
KEYWORDS_GRADO_COMPLETO: List[str]
KEYWORDS_TITULOS_PROFESIONALES: List[str]   # ~50 títulos
KEYWORDS_EDUCACION: List[str]
KEYWORDS_EXPERIENCIA: List[str]
KEYWORDS_INVESTIGACION: List[str]
KEYWORDS_CONTEXTO_EDUCATIVO: List[str]
PERFIL_TIPO_KEYWORDS: Dict[str, List[str]]  # por tipo de perfil
```

### Procedimiento de actualización anual

1. Obtener nueva lista MERCO del año correspondiente
2. Editar `EMPRESAS_TOP_PERU` en `config.py`
3. Recompilar el ejecutable (`python compilar.py`)
4. Distribuir nuevo `.exe`

> **Mejora propuesta:** Externalizar esta lista a un archivo Excel editable por el equipo de People Analytics, eliminando la necesidad de modificar código.

---

## 7. Módulo: extractor_cvs.py

### Responsabilidad

Extracción de texto y datos estructurados de archivos PDF de CVs.

### Clase ExtractorCV

```python
class ExtractorCV:
    def __init__(self, cv_path: str):
        """
        cv_path: ruta absoluta al archivo PDF
        Inicializa texto_completo = "" y datos = {}
        """

    def extraer_texto(self) -> str:
        """
        Estrategia dual:
        1. Intenta con pdfplumber (maneja columnas, tablas)
        2. Si pdfplumber falla o retorna vacío, fallback a PyPDF2
        Retorna texto plano concatenado de todas las páginas.
        """

    def extraer_nombre(self) -> str:
        """
        Heurística: busca el nombre en las primeras 3 líneas del texto.
        Si detecta un patrón "CV de X" o "Curriculum X", extrae X.
        Fallback: usa el nombre del archivo sin extensión.
        """

    def contar_keywords(self, keywords: List[str]) -> int:
        """
        Cuenta ocurrencias de cada keyword en texto_completo (case-insensitive).
        Retorna el total de coincidencias.
        """

    def extraer_anos_experiencia(self) -> int:
        """
        Busca patrones de años en el texto: "X años de experiencia",
        "desde YYYY hasta YYYY", rangos de fechas laborales.
        Retorna el máximo encontrado o 0 si no hay evidencia.
        """
```

### Función de módulo

```python
def procesar_todos_cvs() -> List[Dict]:
    """
    Itera todos los archivos .pdf en CVS_DIR.
    Para cada PDF crea un ExtractorCV y extrae datos básicos.
    Retorna lista de dicts con estructura:
    {
      "nombre": str,
      "archivo": str (nombre del archivo),
      "fuente": "PDF",
      "educacion": {
        "doctorado": bool,
        "maestria": bool,
        "licenciatura": bool
      },
      "anos_experiencia": int,
      "publicaciones": int,
      "texto_completo": str
    }
    """
```

---

## 8. Módulo: extractor_web_cvs.py

### Responsabilidad

Web scraping de perfiles académicos de la plataforma CTI Vitae de CONCYTEC (https://ctivitae.concytec.gob.pe). Es el módulo con mayor riesgo de ruptura ante cambios en la plataforma externa.

### Clase ExtractorWebCVs

```python
class ExtractorWebCVs:
    MAX_REINTENTOS: int = 3
    TIMEOUT_INICIAL: int = 35     # segundos por intento
    TIMEOUT_INCREMENTO: int = 20  # segundos adicionales por reintento
    TIMEOUT_REANALISIS: int = 180 # timeout para re-análisis manual

    def __init__(self):
        """
        Crea requests.Session con headers que simulan un navegador.
        Headers incluyen: User-Agent, Accept-Language, Accept-Encoding.
        MEJORA PENDIENTE: agregar User-Agent institucional USIL.
        """
```

### Estrategia de reintentos

```
Intento 1: timeout = 35s
Intento 2: timeout = 55s (35 + 20)
Intento 3: timeout = 75s (35 + 40)
Si los 3 fallan: retorna dict vacío con fuente="CTI_VITAE_ERROR"
```

### Método principal de extracción

```python
def extraer_cv_desde_url(self, url: str) -> Dict:
    """
    Pipeline de extracción para un perfil CTI Vitae:
    1. _hacer_peticion_con_reintentos(url) → HTML
    2. BeautifulSoup: parsear estructura de la página
    3. Extraer tablas de:
       - Formación académica (RENATI registrado)
       - Producción científica (publicaciones por tipo)
       - Proyectos de investigación
       - Experiencia laboral (lista con fechas)
       - Datos personales (institución, carrera)
    4. Calcular campos derivados:
       - perfil_desactualizado (si última actualización > 6 meses)
       - meses_sin_actualizar
    5. Retorna dict normalizado (ver schema en Sección 8 del inventario)
    """
```

### Estado global de progreso

```python
# Variables a nivel de módulo (thread-safe)
_progress_state: Dict = {
    "total": 0,
    "completados": 0,
    "exitosos": 0,
    "errores": 0,
    "tiempos_individuales": [],
    "registros_con_error": []
}
_progress_lock: threading.Lock = threading.Lock()
```

El lock protege las actualizaciones de `_progress_state` desde múltiples hilos en la función `procesar_multiples_urls`.

### Limitaciones conocidas del scraper

| Limitación | Descripción | Riesgo |
|-----------|-------------|--------|
| Sin API oficial | Depende del HTML de CTI Vitae | ALTO: cualquier rediseño rompe la extracción |
| Sin autenticación | Solo accede a perfiles públicos | Perfiles privados retornan datos vacíos |
| Rate limiting | No implementa delays entre requests | CTI Vitae puede bloquear la IP temporalmente |
| Encoding | Páginas con caracteres especiales pueden fallar | Nombres con tildes o ñ a veces se distorsionan |

---

## 9. Módulo: generador_reportes.py

### Responsabilidad

Exportación de resultados de evaluación a formatos Excel y JSON para distribución institucional.

### Clase GeneradorReportes

```python
class GeneradorReportes:
    def generar_excel_comparativo(self, evaluaciones: List[Dict],
                                   ruta_salida: Optional[str] = None) -> str:
        """
        Genera libro Excel con 3 hojas usando openpyxl.
        Nombre de archivo: Analisis_Detallado_YYYYMMDD_HHMMSS.xlsx
        
        Hoja 1 — Ranking General:
          Columnas: Pos | Nombre | DNI | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Total | % | Perfil
          Ordenado por puntuacion_total descendente
          Formato condicional: verde ≥ 60%, amarillo 40-60%, rojo < 40%
        
        Hoja 2 — Clasificaciones:
          Agrupado por perfil recomendado
          Lista de candidatos con puntuaciones
        
        Hoja 3 — Resumen por Perfil:
          Count de candidatos por perfil
          Estadísticos básicos (promedio, máximo, mínimo por criterio)
        
        Retorna ruta del archivo generado.
        """

    def generar_json_decision(self, evaluaciones: List[Dict],
                               ruta_salida: Optional[str] = None) -> str:
        """
        Genera JSON con estructura completa de decisión.
        Nombre de archivo: clasificacion_final_YYYYMMDD_HHMMSS.json
        Incluye timestamp, totales por perfil y lista completa de evaluaciones.
        Retorna ruta del archivo generado.
        """

    def generar_reporte_texto(self, evaluaciones: List[Dict]) -> str:
        """
        Genera resumen en texto plano para consola.
        ESTADO: implementado pero NO USADO en el pipeline web.
        Solo se invoca desde main.py (modo CLI).
        """
```

---

## 10. Módulo: generador_decisiones_mejorado.py

### Responsabilidad

Implementa la lógica de clasificación de candidatos en perfiles de contratación. Es la versión v2 del clasificador; se presume que es la versión activa, pero coexiste con v1 (`generador_decisiones.py`) y v3 (`generador_decisiones_nuevo.py`) sin documentación que indique cuál es el canónico.

> **Acción requerida:** Confirmar cuál versión usa `app_web.py` (buscar el import) y eliminar las otras dos. Esta ambigüedad es la deuda técnica DT-03.

### Lógica principal

La clasificación aplica un árbol de decisión con condiciones en orden de prioridad decreciente:

```
1. NO_ELEGIBLE        → C1=0 AND C5=0
2. DOCENTE_INVESTIGADOR_HORAS → Total≥150 AND C5≥30 AND C1≥40 AND C2≥20
3. DOCENTE_INVESTIGADOR       → C5≥30 AND C1≥30
4. DTC                        → (C1≥30 AND C2≥20) OR (C1≥40 AND C2≥5) AND Total≥110
5. DTP                        → C2>0 AND C3≥15 AND C1≥15 AND Total≥100
6. PRACTITIONER               → (perfil=clínico AND score clínico≥umbral) OR Total≥90
7. PROFESIONAL_POTENCIAL      → C3≥15 AND C1≥15
8. ACADEMICO_FORMACION        → C1≥30 AND C2<20 AND C3<15
9. ACEPTABLE                  → Total≥60 AND C1≥10
10. NO_ELEGIBLE               → (por defecto si ninguna condición se cumple)
```

---

## 11. Módulo: main.py (CLI)

### Responsabilidad

Implementa el pipeline completo de evaluación sin interfaz web. Útil para ejecución automatizada o integración con otros sistemas.

### Flujo de ejecución

```
python main.py
  1. imprimir_banner()
  2. procesar_todos_cvs()           → extrae PDFs de Cvs/
  3. procesar_excel_links()         → extrae URLs de LINKS/
  4. MotorEvaluacion.evaluar_multiples_cvs(todos_cvs)
  5. GeneradorReportes.generar_json_decision()
  6. Imprimir tabla de resultados en consola
  7. Imprimir estadísticas de resumen
```

### Salida en consola

```
========================================
  SISTEMA DE EVALUACIÓN DOCENTE USIL
  Versión 3.0
========================================

Procesando CVs en PDF...  3 archivos encontrados
Extrayendo de CTI Vitae... 15 URLs procesadas

RANKING DE CANDIDATOS
============================================================
Pos  Nombre                    Total    %      Perfil
------------------------------------------------------------
1    Apellido, Nombre          165/200  82.5%  DTC
2    Apellido2, Nombre2        142/200  71.0%  DOCENTE_INVESTIGADOR
...

RESUMEN:
  Total evaluados: 18
  DTC: 3 | DTP: 7 | PRACTITIONER: 4 | NO_ELEGIBLE: 2 | Otros: 2
```

---

## 12. Módulo: compilar.py

### Responsabilidad

Script de build que genera el ejecutable `.exe` distribuible usando PyInstaller.

### Uso

```bash
cd bot_evaluacion_docente
python compilar.py
# Output: dist/EvaluacionDocente_USIL.exe (~67.7 MB)
```

### Parámetros de PyInstaller utilizados

```python
pyinstaller_args = [
    'launcher.py',
    '--onefile',                    # Un único archivo .exe
    '--name', 'EvaluacionDocente_USIL',
    '--collect-all', 'flask',       # Incluir todo Flask
    '--collect-all', 'pandas',
    '--collect-all', 'pdfplumber',
    '--collect-all', 'bs4',
    '--collect-all', 'requests',
    '--add-data', 'templates;templates',    # Incluir templates/
    '--add-data', 'static;static',          # Incluir static/
    '--hidden-import', 'motor_evaluacion',
    '--hidden-import', 'extractor_cvs',
    '--hidden-import', 'extractor_web_cvs',
    '--hidden-import', 'generador_reportes',
    '--hidden-import', 'config',
    # ... y más hidden-imports para dependencias transitivas
]
```

### Tiempo de compilación estimado

| Fase | Tiempo aproximado |
|------|-----------------|
| Análisis de dependencias | 30–60 segundos |
| Recopilación de archivos | 2–3 minutos |
| Compresión y empaquetado | 1–2 minutos |
| **Total** | **~5 minutos** |

---

## 13. Frontend: templates y static

### templates/index.html (17 KB)

SPA (Single Page Application) mínima sin framework JavaScript. Cargada una vez al inicio y actualizada dinámicamente por `script.js`.

**Secciones principales:**
1. Header con logo institucional
2. Panel de carga de archivos (drag-and-drop)
3. Botón de inicio y configuración (modo rápido)
4. Panel de progreso (barras animadas + SSE)
5. Tabla de resultados (sortable por cualquier columna)
6. Gráficos radar por candidato (Chart.js)
7. Botones de descarga (Excel, JSON)

### static/script.js (113 KB)

Lógica completa del frontend. Incluye:

| Función/Sección | Descripción |
|----------------|-------------|
| Upload handlers | Drag-and-drop + click para Excel y PDFs |
| `iniciarEvaluacion()` | POST a `/api/iniciar_evaluacion` |
| SSE listener | `EventSource('/api/estado_proceso')` → actualiza UI |
| `cargarResultados()` | GET a `/api/resultados` → renderiza tabla |
| `renderizarTabla(datos)` | Genera HTML de la tabla de ranking |
| `ordenarPor(columna)` | Sorting client-side de la tabla |
| `crearGraficoRadar(datos)` | Chart.js radar por candidato |
| Filtros de elegibilidad | Ocultar/mostrar por perfil o score |

### static/styles.css (73 KB)

CSS vanilla (sin preprocesador). Incluye:
- Variables CSS para colores institucionales
- Layout responsive con Flexbox
- Tema claro con soporte de impresión
- Animaciones de progreso
- Clases de semáforo para scores (verde/amarillo/rojo)

---

## 14. Gestión de dependencias

### requirements.txt (bot_evaluacion_docente/)

```
Flask==3.0.0
pdfplumber==0.10.3
PyPDF2==3.0.1
pandas>=2.1.4
openpyxl>=3.1.5
requests>=2.31.0
beautifulsoup4>=4.12.0
python-dateutil==2.8.2
numpy>=1.26.3
```

### Dependencias transitivas relevantes

| Paquete | Requerido por | Versión en .venv2 |
|---------|--------------|-------------------|
| `werkzeug` | Flask | — |
| `jinja2` | Flask | — |
| `blinker` | Flask signals | 1.9.0 |
| `certifi` | requests (TLS) | 2026.2.25 |
| `cffi` | PyInstaller build | — |
| `lxml` | BeautifulSoup4 (parser alternativo) | — |

### Actualizar dependencias

```bash
# Ver qué está desactualizado
pip list --outdated

# Actualizar una dependencia específica (luego recompilar)
pip install --upgrade pdfplumber
python compilar.py
```

---

## 15. Pipeline de datos: referencia completa

### Esquema de transformación

```
Excel de candidatos
  ↓ pandas.read_excel()
  ↓ columnas I, J, K → nombre, dni, url

URL CTI Vitae
  ↓ requests.get(url, timeout=35)
  ↓ BeautifulSoup(html, 'html.parser')
  ↓ extracción estructurada de tablas
  → CandidatoData (fuente="CTI_VITAE")

PDF de CV
  ↓ pdfplumber.open(path)
  ↓ page.extract_text() para cada página
  ↓ concatenar texto
  → CandidatoData (fuente="PDF")

CandidatoData
  ↓ MotorEvaluacion._normalizar_datos_cv()
  ↓ MotorEvaluacion._detectar_tipo_perfil()
  ↓ MotorEvaluacion._evaluar_C1() ... _evaluar_C7()
  ↓ MotorEvaluacion._clasificar_candidato()
  → EvaluacionResultado

EvaluacionResultado
  ↓ GeneradorReportes.generar_excel_comparativo()
  → Analisis_Detallado_YYYYMMDD_HHMMSS.xlsx

EvaluacionResultado
  ↓ GeneradorReportes.generar_json_decision()
  → clasificacion_final_YYYYMMDD_HHMMSS.json
```

---

## 16. Configuración del sistema

### Variables de entorno

| Variable | Valor típico | Descripción |
|---------|-------------|-------------|
| `EVALUACION_DOCENTE_BASE` | `C:\...\PROYECTO RUBRICA` | Ruta al directorio raíz |
| `EVALUACION_DOCENTE_APP` | `C:\...\bot_evaluacion_docente` | Ruta al directorio de la app |

### Parámetros ajustables (actualmente hardcodeados en config.py)

| Parámetro | Valor actual | Ubicación |
|-----------|-------------|-----------|
| Puerto Flask | 5000 | `launcher.py` |
| Máximo upload | 50 MB | `app_web.py` |
| Timeout inicial scraping | 35 s | `extractor_web_cvs.py` |
| Máximo reintentos | 3 | `extractor_web_cvs.py` |
| Score total máximo | 200 pts | `motor_evaluacion.py` |
| Umbral DTC | 110 pts | `motor_evaluacion.py` |
| Umbral DTP | 100 pts | `motor_evaluacion.py` |
| Umbral ACEPTABLE | 60 pts | `motor_evaluacion.py` |

---

## 17. Mantenimiento operacional

### Tareas periódicas

| Frecuencia | Tarea | Archivo a modificar |
|-----------|-------|-------------------|
| Anual (inicio de año) | Actualizar lista MERCO con nuevas empresas TOP | `config.py → EMPRESAS_TOP_PERU` |
| Semestral | Verificar que CTI Vitae no cambió su estructura HTML | `extractor_web_cvs.py` (prueba manual) |
| Por convocatoria | Actualizar plantilla de rúbrica si cambian los criterios | `config.py → TABLA_*` |
| Mensual | Limpiar archivos antiguos de `resultados/` | Manual o script de retención |

### Monitoreo de salud del scraper

```bash
# Ejecutar una extracción de prueba
cd bot_evaluacion_docente
python -c "
from extractor_web_cvs import ExtractorWebCVs
ext = ExtractorWebCVs()
# Reemplazar con URL de perfil de prueba conocido
resultado = ext.extraer_cv_desde_url('https://ctivitae.concytec.gob.pe/...')
print('Nombre:', resultado.get('nombre'))
print('Grado:', resultado.get('educacion', {}).get('grado_maximo'))
print('Fuente:', resultado.get('fuente'))
"
```

### Rotación de archivos de resultados

No existe política automática. Se recomienda archivar o eliminar manualmente archivos con antigüedad mayor a 3 meses en `bot_evaluacion_docente/resultados/`.

---

## 18. Procedimientos de troubleshooting

### El ejecutable .exe no abre

```
Síntoma: Doble clic en .exe, no pasa nada o aparece una ventana y se cierra.
Causa probable: Falta una carpeta requerida (LINKS/, Cvs/, Rubrica/).
Solución: Crear las carpetas vacías en el mismo directorio que el .exe.
```

### La extracción de CTI Vitae falla para todos los candidatos

```
Síntoma: 0 candidatos extraídos de URLs, todos con score 0.
Causas posibles:
  1. Sin conexión a Internet
  2. CTI Vitae cambió su estructura HTML
  3. IP bloqueada temporalmente por CONCYTEC
Diagnóstico:
  - Abrir una URL del Excel manualmente en el navegador
  - Si carga: el scraper necesita actualización (revisar extractor_web_cvs.py)
  - Si no carga: problema de conectividad
```

### La evaluación no inicia / queda trabada en 0%

```
Síntoma: Se hace clic en "Iniciar evaluación", la barra no avanza.
Causa probable: El hilo de background crasheó silenciosamente.
Diagnóstico: Ejecutar en modo CLI para ver el traceback completo:
  python main.py
```

### Error de encoding en Windows

```
Síntoma: UnicodeDecodeError / UnicodeEncodeError en consola.
Causa: Windows usa cp1252 por defecto; el sistema requiere UTF-8.
Solución: Usar run_server.py en lugar de launcher.py (fuerza UTF-8).
```

### Excel de candidatos no se carga

```
Síntoma: "No se encontró el archivo de candidatos".
Verificar:
  - El archivo está en LINKS/
  - El nombre del archivo contiene "INFORMACION" o "Requerimiento"
  - La hoja activa es '2026.1' (para requerimientos)
  - Las columnas I, J, K contienen Nombre, DNI, URL
  - Sin celdas combinadas en el encabezado
```

---

*Universidad San Ignacio de Loyola · People Analytics · 2026*
