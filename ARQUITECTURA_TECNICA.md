# Documentación Técnica de Arquitectura
## Sistema de Evaluación Automática de Perfiles Docentes — USIL v3.0

**Proyecto:** PROYECTO RUBRICA  
**Área:** People Analytics — Universidad San Ignacio de Loyola  
**Fecha:** 27 de mayo de 2026  
**Versión del documento:** 1.0  
**Audiencia:** Arquitecto Senior de Proyecto

---

## Tabla de Contenidos

1. [Propósito y Alcance](#1-propósito-y-alcance)
2. [Stack Tecnológico](#2-stack-tecnológico)
3. [Arquitectura del Sistema](#3-arquitectura-del-sistema)
4. [Flujo de Datos](#4-flujo-de-datos)
5. [Motor de Evaluación — Rúbrica 5+2 Criterios](#5-motor-de-evaluación--rúbrica-52-criterios)
6. [Integraciones Externas](#6-integraciones-externas)
7. [Brechas de Datos](#7-brechas-de-datos)
8. [Análisis de Seguridad](#8-análisis-de-seguridad)
9. [Sostenibilidad y Deuda Técnica](#9-sostenibilidad-y-deuda-técnica)
10. [Conclusiones y Roadmap](#10-conclusiones-y-roadmap)

---

## 1. Propósito y Alcance

### 1.1 Problema que Resuelve

El equipo de Talento & Cultura de USIL recibía CVs de candidatos docentes en múltiples formatos (PDF, links CTI Vitae, Excel) y los evaluaba manualmente aplicando una rúbrica base institucional de 5 criterios. En la implementación actual del sistema, esa base se amplía con 2 criterios complementarios de evaluación automática, por lo que el motor opera con 7 componentes evaluativos ponderados. Este proceso tomaba horas por convocatoria y era susceptible a inconsistencias entre evaluadores.

**Este sistema automatiza el 100% de ese proceso:** ingesta, extracción, evaluación, clasificación y generación de ranking comparativo.

### 1.2 Usuarios del Sistema

| Usuario | Rol | Interacción |
|---------|-----|-------------|
| Analistas de Talento & Cultura | Primario | Sube Excel + PDFs, revisa ranking web |
| Líderes de Facultad | Secundario | Consulta reportes Excel exportados |
| TI / Administrador | Soporte | Ejecuta el .exe, gestiona rutas de archivos |

### 1.3 Alcance Actual

- **Versión:** 3.0 (Simplificada)
- **Distribución:** Ejecutable `.exe` de 67.7 MB (compilado con PyInstaller)
- **Usuarios simultáneos soportados:** 1 (arquitectura single-user)
- **Volumen típico:** 20–200 candidatos por convocatoria
- **Tiempo de procesamiento:** 5–8 minutos para 100 candidatos con extracción web

---

## 2. Stack Tecnológico

### 2.1 Dependencias — `requirements.txt`

| Librería | Versión | Rol |
|----------|---------|-----|
| `Flask` | 3.0.0 | Servidor web local, API REST, SSE |
| `pdfplumber` | 0.10.3 | Extracción principal de texto desde PDFs |
| `PyPDF2` | 3.0.1 | Fallback de extracción PDF |
| `pandas` | 2.1.4 | Lectura de Excel, manipulación de datos tabulares |
| `openpyxl` | 3.1.5 | Escritura de reportes Excel de salida |
| `requests` | 2.31.0 | HTTP requests para web scraping |
| `beautifulsoup4` | 4.12.0 | Parsing HTML de portales web (CTI Vitae, etc.) |
| `python-dateutil` | 2.8.2 | Parsing de fechas en texto libre |
| `numpy` | 1.26.3 | Cálculos numéricos en normalización de puntajes |
| `Werkzeug` | 3.0.0 | Utilidades Flask (routing, file handling) |

**Versión de Python:** 3.13+  
**Sistema operativo objetivo:** Windows 10/11 (64-bit)

### 2.2 Frontend

| Componente | Tecnología | Notas |
|------------|------------|-------|
| UI principal | HTML5 + CSS3 | Responsive, drag-and-drop |
| Interactividad | JavaScript vanilla | Sin frameworks externos |
| Gráficos | Chart.js (CDN) | Gráficos radar y barras |
| Comunicación backend | Fetch API + SSE | Progreso en tiempo real |

### 2.3 Herramientas de Construcción y Distribución

- **PyInstaller** — empaqueta el proyecto completo en un único `.exe` con runtime Python embebido
- `compilar.py` — script de build que invoca PyInstaller con `--collect-all` para incluir templates, static files y DLLs

---

## 3. Arquitectura del Sistema

### 3.1 Diagrama de Capas

```
┌─────────────────────────────────────────────────────────────────┐
│  PRESENTACIÓN                                                   │
│  Flask 3.0.0 + index.html + script.js (113 KB) + styles.css    │
│  Rutas: / | /api/iniciar_evaluacion | /api/estado_proceso (SSE) │
│          /api/resultados | /api/subir_archivo | /api/subir_pdfs  │
├─────────────────────────────────────────────────────────────────┤
│  LÓGICA DE NEGOCIO                                              │
│  motor_evaluacion.py — Criterios C1 a C7                        │
│  config.py — Rúbrica institucional, pesos, keywords (749 líneas)│
│  analizador_rubrica.py — Mapeo XML → Python                     │
│  generador_reportes.py — Salida Excel + JSON                    │
├─────────────────────────────────────────────────────────────────┤
│  EXTRACCIÓN DE DATOS                                            │
│  extractor_cvs.py — PDFs locales (pdfplumber + PyPDF2)         │
│  extractor_web_cvs.py — CTI Vitae (requests + BS4)             │
│  buscador_web_cv.py v2.0 — Búsqueda masiva por nombre          │
├─────────────────────────────────────────────────────────────────┤
│  ALMACENAMIENTO (sin base de datos)                             │
│  resultados/*.json — Evaluaciones previas                       │
│  *.xlsx — Reportes comparativos                                 │
│  Cvs/ + Legajos/ — PDFs de entrada en OneDrive                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Estructura de Archivos del Proyecto

```
bot_evaluacion_docente/
│
├── ENTRY POINTS
│   ├── launcher.py          — Entry point .exe; verifica librerías, configura rutas
│   ├── run_server.py        — Arranca Flask, verifica puerto, abre navegador
│   └── main.py              — CLI simplificado (pipeline: extracción → evaluación → ranking)
│
├── LÓGICA DE NEGOCIO (Core)
│   ├── motor_evaluacion.py  — 427 líneas; clase MotorEvaluacion con 7 métodos de criterio
│   ├── config.py            — 749 líneas; tablas de rúbrica, pesos, keywords, rutas
│   ├── analizador_rubrica.py
│   └── generador_reportes.py
│
├── EXTRACCIÓN
│   ├── extractor_cvs.py     — 259 líneas; ExtractorCV para PDFs locales
│   ├── extractor_web_cvs.py — 400+ líneas; ExtractorWebCVs para CTI Vitae
│   └── buscador_web_cv.py   — 600+ líneas; búsqueda masiva experimental
│
├── PRESENTACIÓN (Flask)
│   ├── app_web.py           — 3000+ líneas; toda la API REST y lógica de sesión
│   ├── templates/index.html — 17 KB; interfaz completa
│   └── static/
│       ├── script.js        — 113 KB
│       └── styles.css       — 73 KB
│
├── BUILD
│   └── compilar.py          — Builder PyInstaller → .exe
│
├── TESTING (legacy, no automatizado)
│   ├── test_sistema_completo.py
│   ├── test_extraccion.py
│   └── test_perfil.py
│
└── requirements.txt         — 10 dependencias declaradas

Total: ~37 archivos .py | ~7,000 líneas de código
```

### 3.3 Diagrama de Dependencias entre Módulos

```
launcher.py / run_server.py
        ↓
    app_web.py (Flask — 3000+ líneas)
        ├──→ motor_evaluacion.py
        │        ├──→ config.py
        │        ├──→ analizador_rubrica.py
        │        └──→ buscador_web_cv.py (experimental)
        │
        ├──→ extractor_cvs.py
        │        ├──→ pdfplumber
        │        └──→ PyPDF2 (fallback)
        │
        ├──→ extractor_web_cvs.py
        │        ├──→ requests
        │        ├──→ beautifulsoup4
        │        └──→ extractor_cvs.py (reutiliza parsing)
        │
        └──→ generador_reportes.py
                 ├──→ pandas
                 └──→ openpyxl
```

---

## 4. Flujo de Datos

### 4.1 Pipeline Completo

```
INGESTA
  ├─ OPCIÓN A: Excel (INFORMACION DE VALIDACION.xlsx)
  │   Columnas usadas: I (Nombres), J (DNI), K (Links CTI Vitae)
  │   Librería: pandas.read_excel()
  │
  ├─ OPCIÓN B: CVs PDF locales (carpeta Cvs/)
  │   Librería: pdfplumber → fallback PyPDF2
  │   Extrae: nombre, fechas de experiencia, keywords
  │
  └─ OPCIÓN C: Búsqueda por nombre (experimental)
      Fuentes: CTI Vitae, OpenAlex, RENATI, DuckDuckGo, Scholar
      Resultado: mismo formato que Opción B

         ↓

NORMALIZACIÓN (extractor_cvs.py / extractor_web_cvs.py)
  Estructura común de CV:
  {
    "nombre": str,
    "dni": str,
    "fuente": "CTI_VITAE" | "PDF" | "BUSQUEDA",
    "educacion": {"doctorado": bool, "maestria": bool, ...},
    "anos_experiencia_docente": int,
    "anos_experiencia_profesional": int,
    "publicaciones": int,
    "cargo_actual": str,
    "empresa_actual": str,
    "texto_completo": str
  }

         ↓

EVALUACIÓN (motor_evaluacion.py)
  C1: Formación Académica     → 0–50 pts
  C2: Experiencia Docente     → 0–40 pts
  C3: Experiencia Profesional → 0–40 pts
  C4: Centro de Labores       → 0–20 pts
  C5: Producción Académica    → 0–40 pts
  C6: Liderazgo Profesional   → 0–20 pts
  C7: Especialización         → 0–10 pts
  Total crudo máximo: 220 pts → normalizado a 200 para presentación

         ↓

CLASIFICACIÓN
  Elegibilidad: SI / NO
  Perfil: DTC | DTP | Practitioner | Investigador | Horas_Investigación
  Rango: < 90 (No califica) | 90–110 (Intermedio) | > 110 (Avanzado)

         ↓

SALIDA
  ├─ JSON: resultados/clasificacion_final_YYYYMMDD_HHMMSS.json
  ├─ Excel: comparativa_candidatos_YYYYMMDD_HHMMSS.xlsx
  └─ UI web: ranking interactivo + tabla comparativa + gráficos
```

### 4.2 Datos Personales en Tránsito

| Dato | Origen | Almacenamiento | Clasificación | Riesgo |
|------|--------|----------------|---------------|--------|
| Nombres completos | Excel / PDF / Web | JSON + Excel | PII | MEDIO |
| DNI | Excel / PDF / Web | JSON + Excel en texto plano | PII Sensible | **ALTO** |
| Correo electrónico | Extraído de PDF | No se almacena explícitamente | PII | BAJO |
| Fechas laborales | PDF / CTI Vitae | JSON | No sensible | BAJO |
| Publicaciones | CTI Vitae / OpenAlex | JSON | Público | BAJO |

---

## 5. Motor de Evaluación — Rúbrica 5+2 Criterios

### 5.1 Criterio 1: Formación Académica (C1) — Máx. 50 pts

| Nivel | Puntos | Detección |
|-------|--------|-----------|
| Doctorado completo | 50 | Keywords: "doctor", "ph.d", "phd" |
| Doctorado en curso | 40 | Keywords anteriores + "en curso", "candidato" |
| Maestría completa | 30 | Keywords: "magíster", "master", "maestría" |
| Maestría en curso | 25 | Keywords anteriores + "cursando" |
| Licenciatura titulada | 15 | Keywords: "titulado", "licenciado", "ingeniero" |
| Bachiller | 10 | Keyword: "bachiller" |
| Sin formación | 0 | Sin match |

**Método:** keywords matching sobre `texto_completo` normalizado a minúsculas.

### 5.2 Criterio 2: Experiencia Docente (C2) — Máx. 40 pts

| Años | Puntos |
|------|--------|
| ≥ 10 años | 40 |
| 6–9 años | 30 |
| 3–5 años | 20 |
| 0–2 años | 0 |

**Método:** Parsing de rangos de fecha ("Marzo 2015 – Agosto 2022") con `python-dateutil`, filtrado por keywords docentes ("docente", "profesor", "catedrático").

### 5.3 Criterio 3: Experiencia Profesional (C3) — Máx. 40 pts

| Nivel | Puntos | Cargos típicos |
|-------|--------|---------------|
| Alta dirección | 40 | CEO, Director General, Gerente General |
| Mando medio | 30 | Jefe de área, Supervisor, Coordinador |
| Profesional senior | 25 | Especialista senior, 7+ años en rol |
| Intermedio | 15 | Asociado, consultor junior |
| Analista/operativo | 10 | Analista, técnico |
| Sin experiencia | 0 | — |

**Método:** Keywords matching con precedencia (si detecta "director" → asigna máximo sin continuar).

### 5.4 Criterio 4: Centro de Labores (C4) — Máx. 20 pts

| Tipo de empresa | Puntos |
|-----------------|--------|
| TOP 100 MERCO Perú 2025 (BCP, Alicorp, BBVA, LATAM, etc.) | 20 |
| Big 4 / Consultoras líderes (PwC, Deloitte, EY, KPMG, McKinsey, BCG) | 15 |
| Empresa mediana reconocida | 15 |
| Empresa pequeña | 10 |
| Hospital/institución nacional de salud (INEN, INCOR, EsSalud) | 20 |
| Trabajo independiente | 0 |

**Configuración:** Lista de ~100 empresas hardcodeadas en `config.py`.

### 5.5 Criterio 5: Producción Académica (C5) — Máx. 40 pts

| Nivel | Puntos | Indicadores |
|-------|--------|-------------|
| Libro o revista indexada | 40 | Keywords: "libro", "ISBN", "editorial" |
| Publicaciones Scopus/WoS | 30 | Keywords: "scopus", "wos", "web of science" |
| Investigación / innovación | 30 | Keywords: "investigación", "patent", "proyecto" |
| Producción inicial | 10 | Ponencias, congresos, working papers |
| Sin evidencia | 0 | — |

**Limitación importante:** El sistema no verifica realmente contra las APIs de Scopus o WoS; detecta las palabras clave en el texto extraído.

### 5.6 Criterio 6: Liderazgo Profesional (C6) — Máx. 20 pts

| Nivel | Puntos | Ejemplos |
|-------|--------|---------|
| Liderazgo alto | 20 | Director médico, CEO, Decano, Rector |
| Liderazgo medio | 15 | Jefe de servicio, Gerente de área, Coordinador |
| Liderazgo básico | 10 | Supervisor, Responsable de equipo, Investigador principal |

### 5.7 Criterio 7: Especialización (C7) — Máx. 10 pts

| Nivel | Puntos | Ejemplos |
|-------|--------|---------|
| Especialización alta | 10 | Medicina Intensiva, UCI, Oncología, Neurocirugía |
| Especialización media | 6 | Cardiología, Geriatría, Master especializado |
| Especialización básica | 3 | Diplomado, Segunda especialidad, Residencia |

### 5.8 Pesos Dinámicos por Tipo de Perfil

El motor detecta el perfil del candidato (`clinico`, `investigador`, `industrial`, `docente`) y aplica pesos distintos:

| Criterio | Clínico | Investigador | Industrial | Docente |
|----------|---------|-------------|------------|---------|
| C1 Formación | 18% | 25% | 18% | 22% |
| C2 Docencia | 12% | 10% | 8% | **30%** |
| C3 Profesional | **32%** | 15% | **38%** | 18% |
| C4 Empresa | 18% | 10% | **22%** | 10% |
| C5 Producción | 5% | **28%** | 5% | 10% |
| C6 Liderazgo | 8% | 6% | 6% | 6% |
| C7 Especialización | 7% | 6% | 3% | 4% |

### 5.9 Fórmula de Puntaje Final

```
puntaje_ponderado = (
    (C1/50) * peso_C1 +
    (C2/40) * peso_C2 +
    (C3/40) * peso_C3 +
    (C4/20) * peso_C4 +
    (C5/40) * peso_C5 +
    (C6/20) * peso_C6 +
    (C7/10) * peso_C7
) * 200

total = round(puntaje_ponderado)   # Sobre 200
porcentaje = (total / 200) * 100
```

### 5.10 Reglas de Elegibilidad y Clasificación

```python
# Regla de exclusión automática
if C1 == 0 AND C5 == 0:
    → NO ELEGIBLE (Sin formación ni producción)
elif total < 90:
    → NO CALIFICA

# Clasificación por perfil
DTC         → total ≥ 110 | C1 ≥ 30 | C2 ≥ 20
DTP         → total ≥ 110 | C2 ≥ 5  | C3 ≥ 15
Practitioner → total ≥ 90 | C3 ≥ 25 | C4 ≥ 10
Investigador → total ≥ 110 | C5 ≥ 30 | C1 ≥ 30 | indexado requerido
Horas_Investigación → total ≥ 150 | C5 ≥ 10 | C1 ≥ 40 | C2 ≥ 30
```

---

## 6. Integraciones Externas

| Servicio | Tipo | Autenticación | Uso | Resiliencia |
|----------|------|---------------|-----|-------------|
| **CTI Vitae (CONCYTEC)** | Web scraping | Ninguna (público) | Educación, publicaciones, experiencia | Exponential backoff, 3 reintentos, timeout 35s |
| **OpenAlex API** | REST API | Ninguna (público) | Publicaciones científicas | Sin circuit-breaker |
| **RENATI / SUNEDU** | Web scraping | Ninguna (público) | Grados académicos oficiales | Básico |
| **DuckDuckGo** | Web scraping | Ninguna (público) | Búsqueda masiva por nombre | Circuit-breaker implementado |
| **Google Scholar** | Web scraping | Ninguna (público) | Papers indexados | User-Agent rotation |
| **ResearchGate / Academia.edu** | Web scraping | Ninguna (público) | Publicaciones académicas | Básico |

**Nota de riesgo:** Todo el web scraping se realiza sin acuerdos formales con los servicios. CTI Vitae es el proveedor principal; si el CONCYTEC modifica su estructura HTML, el extractor falla silenciosamente.

---

## 7. Brechas de Datos

### Brecha 1: Sin Validación Cruzada de Datos

**Descripción:** El sistema acepta como válido cualquier dato extraído sin cotejarlo contra fuentes autorizadas.  
**Ejemplo concreto:** El motor asigna 30 puntos por "publicaciones Scopus" si detecta la palabra "scopus" en el CV, sin verificar realmente en la API de Elsevier.  
**Impacto:** Candidatos con CV inflado pueden obtener puntajes altos no merecidos.  
**Solución recomendada:** Integrar Scopus Author Search API (disponible con suscripción institucional USIL) o la API pública de OpenAlex para contar publicaciones reales.

### Brecha 2: Sin Deduplicación de Candidatos

**Descripción:** Si el mismo candidato aparece en el Excel, en CTI Vitae y como PDF local, se evalúa tres veces como tres personas distintas.  
**Ejemplo concreto:** `main.py` concatena directamente `cvs_pdf + cvs_web` sin ningún proceso de matching.  
**Impacto:** Ranking con duplicados; candidatos pueden aparecer en posición 3 y 47 simultáneamente.  
**Solución recomendada:** Deduplicación por DNI exacto como primer criterio; fuzzy matching por nombre (>85% similitud) como segundo criterio.

### Brecha 3: Datos de Perfil Desactualizados sin Penalización

**Descripción:** El extractor detecta si un perfil CTI Vitae tiene más de 6 meses sin actualizar, pero el motor de evaluación ignora esta señal y otorga el mismo puntaje.  
**Ubicación:** `extractor_web_cvs.py` genera el flag `perfil_desactualizado`; `motor_evaluacion.py` no lo consume.  
**Impacto:** Un candidato con un CV de hace 3 años en CTI puntúa igual que uno actualizado la semana pasada.  
**Solución recomendada:** Aplicar descuento del 10–20% en puntaje total cuando `meses_sin_actualizar > 6`.

### Brecha 4: Sin Trazabilidad de Origen de Datos (Data Lineage)

**Descripción:** El resultado final no registra de qué fuente provino cada dato evaluado.  
**Ejemplo concreto:** El JSON de salida dice `"educacion": "DOCTORADO"` pero no indica si vino del PDF, de CTI Vitae o de una búsqueda web; ni el nivel de confianza de esa extracción.  
**Impacto:** Imposible auditar decisiones. Si el puntaje de un candidato es cuestionado, no hay forma de rastrear por qué se le asignó ese valor.  
**Solución recomendada:** Agregar campo `_lineage` en cada atributo evaluado con `{source, confidence, timestamp}`.

### Brecha 5: Manejo de Datos Faltantes con Ceros por Defecto

**Descripción:** Cuando la extracción de un candidato falla (timeout, error HTTP, PDF corrupto), el sistema asigna `años_experiencia: 0` y `publicaciones: 0`, que son evaluados como datos reales.  
**Ubicación:** `extractor_web_cvs.py`, función `_cv_vacio()`.  
**Impacto:** Un candidato del que no se pudo obtener datos recibe el mismo puntaje que uno que genuinamente tiene cero experiencia.  
**Solución recomendada:** Usar `None` para campos faltantes y marcar el candidato con `necesita_revision_manual: True` en lugar de evaluarlo con datos ficticios.

### Brecha 6: Rúbrica de Empresas Estática

**Descripción:** La lista de "empresas TOP" para el Criterio 4 está hardcodeada en `config.py` con la lista MERCO 2025.  
**Impacto:** El sistema no se actualiza automáticamente; si USIL quiere incorporar rankings 2026, alguien debe editar manualmente el código.  
**Solución recomendada:** Externalizar la lista a un archivo Excel o JSON editable por el equipo de Talento sin tocar código.

---

## 8. Análisis de Seguridad

### 8.1 Vulnerabilidades Críticas

#### V1 — DNI en Texto Plano (Severidad: ALTA)

**Problema:** Los números de DNI de los candidatos se almacenan sin encriptación en archivos JSON en el directorio `resultados/`.  
**Regulación afectada:** Ley N° 29733 de Protección de Datos Personales (Perú), Art. 11 sobre medidas de seguridad.  
**Remediación:**
```python
import hashlib, os

def hash_dni(dni: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}{dni}".encode()).hexdigest()

# Almacenar solo el hash; nunca el DNI raw
resultado["dni_hash"] = hash_dni(dni, os.environ["DNI_SALT"])
```

#### V2 — Sin Sanitización de Nombres de Archivo en Upload (Severidad: ALTA)

**Problema:** El nombre del archivo Excel subido por el usuario no pasa por `secure_filename()` antes de construir la ruta de almacenamiento temporal. Esto expone a Path Traversal.  
**Ubicación:** `app_web.py`, rutas `/api/subir_archivo` y `/api/subir_pdfs`.  
**Remediación:**
```python
from werkzeug.utils import secure_filename

nombre_seguro = secure_filename(archivo.filename)
if not nombre_seguro:
    return {"error": "Nombre de archivo inválido"}, 400
ruta_destino = os.path.join(UPLOAD_FOLDER, nombre_seguro)
```

#### V3 — Estado Global sin Thread Safety (Severidad: ALTA)

**Problema:** El diccionario `estado_proceso` se modifica desde múltiples threads (el thread de evaluación + el thread del SSE endpoint) sin ningún mecanismo de exclusión mutua.  
**Ubicación:** `app_web.py`, líneas ~49–64.  
**Riesgo:** Race condition que puede provocar estados inconsistentes o crash si dos evaluaciones se inician al mismo tiempo.  
**Remediación:**
```python
from threading import Lock
_estado_lock = Lock()

def actualizar_estado(key, valor):
    with _estado_lock:
        estado_proceso[key] = valor
```

### 8.2 Vulnerabilidades Altas

#### V4 — Sin Auditoría de Acceso y Evaluaciones

**Problema:** No existe ningún registro de quién realizó qué evaluación y cuándo. Imposible auditar decisiones de contratación que pueden ser cuestionadas legalmente.  
**Remediación:** Implementar audit log rotativo:
```python
import logging
from logging.handlers import RotatingFileHandler

audit_log = logging.getLogger("audit")
audit_log.addHandler(RotatingFileHandler("audit.log", maxBytes=5_000_000, backupCount=10))

# Registrar cada evaluación
audit_log.info(f"EVALUACION | usuario={usuario} | candidatos={len(lista)} | timestamp={datetime.now().isoformat()}")
```

#### V5 — Web Scraping sin Identificación del Solicitante

**Problema:** Las peticiones HTTP a CTI Vitae y otras fuentes no incluyen headers de identificación institucional. Esto viola las buenas prácticas de scraping responsable y puede resultar en bloqueo de IP.  
**Remediación:**
```python
session.headers.update({
    "User-Agent": "USIL-TalentoAcademico/3.0 (+rrhh@usil.edu.pe)",
    "From": "rrhh@usil.edu.pe"
})
```

#### V6 — Sin Validación de Tipo de Archivo en Upload

**Problema:** El endpoint de upload no verifica que el archivo sea realmente un Excel o PDF válido; solo verifica la extensión.  
**Remediación:**
```python
import magic  # python-magic
mime = magic.from_buffer(archivo.read(1024), mime=True)
if mime not in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/pdf"]:
    return {"error": "Tipo de archivo no permitido"}, 415
```

### 8.3 Compliance — Ley 29733 (Perú) y Buenas Prácticas

| Requisito | Estado Actual | Acción Requerida |
|-----------|---------------|-----------------|
| Datos personales protegidos (DNI) | ❌ Texto plano | Encriptar o hashear DNI |
| Consentimiento para procesamiento | ❌ No documentado | Registrar base legal de procesamiento |
| Retención limitada de datos | ❌ Sin política | Implementar borrado automático tras N días |
| Acceso controlado a resultados | ⚠️ Solo local | Aceptable hoy; requiere autenticación si se despliega en red |
| Registro de actividad (auditoría) | ❌ No existe | Implementar audit log |
| Derecho de cancelación (candidatos) | ❌ No implementado | Mecanismo de borrado por DNI |

---

## 9. Sostenibilidad y Deuda Técnica

### 9.1 Métricas del Código

| Archivo | Líneas | Estado |
|---------|--------|--------|
| `app_web.py` | 3,000+ | Crítico — God object, viola SRP |
| `config.py` | 749 | Alto — Mezcla configuración con lógica de negocio |
| `motor_evaluacion.py` | 427 | Aceptable |
| `extractor_web_cvs.py` | 400+ | Aceptable |
| `buscador_web_cv.py` | 600+ | Alto — Experimental sin tests |

**Cobertura de tests:** 0% automatizados (existen scripts manuales `test_*.py` sin pytest).  
**Documentación de funciones:** ~60% tienen docstrings básicos.

### 9.2 Deuda Técnica Identificada

| Problema | Severidad | Descripción |
|----------|-----------|-------------|
| `app_web.py` monolítico de 3,000+ líneas | Alta | Mezcla routing, lógica de negocio, manejo de archivos y estado |
| Archivos duplicados legacy | Alta | `motor_evaluacion-DESKTOP-4AR05VT.py`, `generador_decisiones*.py` (3 versiones) |
| Estado global mutable | Alta | `estado_proceso` dict global sin thread safety |
| Keywords hardcodeadas en código | Media | 1,000+ strings en `config.py`; no editables sin modificar código |
| Sin type hints | Media | Dificulta refactorización y detección temprana de errores |
| Sin base de datos | Media | JSON files no permiten queries, backups incrementales ni concurrencia |
| Sin CI/CD | Media | No hay pipeline de build, test ni deploy automático |
| Versiones legacy sin eliminar | Baja | Confusión sobre cuál es el archivo canónico |

### 9.3 Rendimiento del Sistema

| Operación | Velocidad | Memoria |
|-----------|-----------|---------|
| Parsing PDF (100 docs) | ~2 CVs/segundo | ~50 MB base + 5 MB/100 CVs |
| Extracción CTI Vitae (100 perfiles) | 1 perfil/3–5s (rate-limited) | ~100 MB con HTML en memoria |
| Evaluación (1,000 candidatos) | < 2 segundos | < 200 MB |
| Total pipeline (100 candidatos) | 5–8 minutos | ~150 MB pico |

### 9.4 Limitaciones de Escalabilidad

El sistema está diseñado para un único usuario ejecutando evaluaciones de manera secuencial. Las limitaciones actuales que impiden escalar son:

1. **Sin base de datos** — resultados en JSON no permiten búsqueda ni concurrencia
2. **Estado global** — una sola evaluación activa a la vez por instancia Flask
3. **Distribución como .exe** — no desplegable en servidor web compartido
4. **Sin autenticación** — cualquier persona en la misma red (si se expone el puerto) puede acceder

---

## 10. Conclusiones y Roadmap

### 10.1 Evaluación de Dimensiones Arquitectónicas

| Dimensión | Calificación | Resumen |
|-----------|:-----------:|---------|
| Funcionalidad | BUENA | Sistema cumple el objetivo principal; rúbrica bien implementada |
| Seguridad | DÉBIL | DNI sin protección, sin auditoría, sin sanitización de inputs |
| Compliance (Ley 29733) | NO CUMPLE | Sin encriptación de PII, sin política de retención |
| Calidad de Datos | MEDIA | Sin validación cruzada ni deduplicación |
| Mantenibilidad | POBRE | Monolítico, sin tests, sin type hints, código duplicado |
| Escalabilidad | LIMITADA | Single-user, sin DB, race conditions |
| Rendimiento | ACEPTABLE | Timeouts bien configurados, reintentos con backoff |

### 10.2 Roadmap de Remediación por Fases

#### Fase 1 — Urgente (2 semanas)
- [ ] Hashear DNI antes de almacenar en JSON (`SHA-256 + salt`)
- [ ] Agregar `secure_filename()` en todos los endpoints de upload
- [ ] Agregar `Lock` al estado global de evaluación
- [ ] Eliminar archivos legacy duplicados del repositorio

#### Fase 2 — Crítico (1 mes)
- [ ] Implementar audit log rotativo (quién evaluó, cuándo, cuántos candidatos)
- [ ] Crear test suite con `pytest` — mínimo 60% cobertura en `motor_evaluacion.py`
- [ ] Refactorizar `app_web.py` en blueprints separados por dominio
- [ ] Agregar headers de identificación institucional al web scraper

#### Fase 3 — Importante (2 meses)
- [ ] Externalizar lista de empresas TOP a Excel editable (sin tocar código)
- [ ] Implementar deduplicación de candidatos por DNI + nombre fuzzy
- [ ] Usar `None` para campos con extracción fallida (no ceros)
- [ ] Agregar campo `_lineage` en resultados (fuente + confianza + timestamp)
- [ ] Política de retención: borrado automático de JSON tras 90 días

#### Fase 4 — Mejora continua (3–6 meses)
- [ ] Migrar almacenamiento a SQLite (base para futuro PostgreSQL)
- [ ] Integrar validación real contra OpenAlex API para conteo de publicaciones
- [ ] Contenedorizar con Docker para despliegue en servidor compartido
- [ ] Implementar autenticación básica si se despliega en red institucional

### 10.3 Recomendación Final

**El sistema es funcionalmente sólido y resuelve el problema de negocio.** La lógica de evaluación combina 5 criterios base con 2 criterios complementarios y pesos dinámicos por tipo de perfil docente.

**Los riesgos principales son de seguridad y compliance**, no de lógica de negocio. El almacenamiento de DNI en texto plano y la ausencia total de auditoría son las brechas más urgentes de cerrar, especialmente considerando que el sistema procesa datos personales de candidatos externos a la universidad.

**Recomendación:** Mantener y refactorizar el sistema actual (no reescribir) siguiendo el roadmap de fases, priorizando seguridad y compliance en las primeras dos fases antes de ampliar funcionalidad.

---

*Documento preparado para evaluación de arquitectura senior.*  
*Basado en análisis estático del código fuente del proyecto: ~7,000 líneas en ~37 archivos Python.*
