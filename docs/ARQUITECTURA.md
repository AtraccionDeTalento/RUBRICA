# Arquitectura del Sistema — Evaluación Automática de Docentes USIL

**Universidad San Ignacio de Loyola · People Analytics**
**Versión:** 3.0 · **Fecha:** 2026-06-01

---

## Índice

1. [Visión general](#1-visión-general)
2. [Patrón arquitectónico](#2-patrón-arquitectónico)
3. [Diagrama de componentes](#3-diagrama-de-componentes)
4. [Diagrama de capas](#4-diagrama-de-capas)
5. [Flujo de ejecución principal](#5-flujo-de-ejecución-principal)
6. [Flujo de extracción de datos](#6-flujo-de-extracción-de-datos)
7. [Motor de evaluación — lógica de clasificación](#7-motor-de-evaluación--lógica-de-clasificación)
8. [Comunicación frontend-backend](#8-comunicación-frontend-backend)
9. [Modelo de datos](#9-modelo-de-datos)
10. [Despliegue y distribución](#10-despliegue-y-distribución)
11. [Restricciones arquitectónicas](#11-restricciones-arquitectónicas)
12. [Deuda arquitectónica y evolución propuesta](#12-deuda-arquitectónica-y-evolución-propuesta)

---

## 1. Visión general

El sistema es un **monolito Flask de proceso único** distribuido como ejecutable Windows. Combina una interfaz web servida localmente con un pipeline de procesamiento de datos ejecutado en hilo de background. No requiere conectividad de red más allá del acceso a CTI Vitae (CONCYTEC) durante la extracción.

```
Entrada (Excel + PDFs)
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│                EvaluacionDocente_USIL.exe                 │
│  Python 3.13 embebido · Flask 3.0 · todas las librerías   │
│                                                           │
│  [Servidor web local]  ◄──── Usuario (navegador)         │
│  [Pipeline de datos]   ──→   CTI Vitae (CONCYTEC)        │
│  [Sistema de archivos] ──→   resultados/ (JSON + Excel)  │
└───────────────────────────────────────────────────────────┘
```

---

## 2. Patrón arquitectónico

| Dimensión | Decisión | Justificación |
|-----------|---------|---------------|
| Estilo | Monolito de proceso único | Simplicidad de distribución como .exe |
| Concurrencia | Hilo de background para el pipeline | Evitar bloqueo del servidor web durante extracción larga |
| Persistencia | Sistema de archivos (JSON + Excel) | Sin necesidad de instalación de base de datos en el cliente |
| Interfaz | Flask + HTML/JS vanilla | Evita dependencias de build para el frontend |
| Distribución | PyInstaller (--onefile) | Un único archivo .exe portable |
| Comunicación asíncrona | Server-Sent Events (SSE) | Progreso en tiempo real sin WebSocket |

---

## 3. Diagrama de componentes

```mermaid
graph TB
    subgraph "Entrada de datos"
        EXCEL["📊 Excel de candidatos<br/>(LINKS/*.xlsx)"]
        PDFS["📄 CVs en PDF<br/>(Cvs/*.pdf)"]
        CTI["🌐 CTI Vitae<br/>concytec.gob.pe"]
    end

    subgraph "Capa de presentación"
        HTML["index.html<br/>UI completa (17 KB)"]
        JS["script.js<br/>lógica frontend (113 KB)"]
        CSS["styles.css<br/>estilos (73 KB)"]
        CHART["Chart.js (CDN)<br/>gráficos radar"]
    end

    subgraph "Capa de aplicación — app_web.py"
        FLASK["Flask Router<br/>8 endpoints REST"]
        ORCH["Orquestador<br/>_evaluar_candidatos()"]
        STATE["Estado global<br/>estado_proceso{}"]
        SSE["SSE Stream<br/>/api/estado_proceso"]
    end

    subgraph "Capa de extracción"
        EXT_PDF["ExtractorCV<br/>extractor_cvs.py"]
        EXT_WEB["ExtractorWebCVs<br/>extractor_web_cvs.py"]
    end

    subgraph "Capa de evaluación"
        CONFIG["config.py<br/>748 líneas<br/>tablas + keywords"]
        MOTOR["MotorEvaluacion<br/>motor_evaluacion.py<br/>5 base + 2 complementarios"]
    end

    subgraph "Capa de reporte"
        GEN_REP["GeneradorReportes<br/>generador_reportes.py"]
        GEN_DEC["GeneradorDecisiones<br/>generador_decisiones_mejorado.py"]
    end

    subgraph "Persistencia"
        JSON_OUT["clasificacion_final_*.json"]
        XLSX_OUT["Analisis_Detallado_*.xlsx"]
        HIST["historial_personas.json"]
    end

    EXCEL --> FLASK
    PDFS --> FLASK
    FLASK --> ORCH
    ORCH --> EXT_PDF
    ORCH --> EXT_WEB
    EXT_WEB --> CTI
    EXT_PDF --> PDFS
    EXT_PDF --> MOTOR
    EXT_WEB --> MOTOR
    CONFIG --> MOTOR
    MOTOR --> GEN_DEC
    GEN_DEC --> GEN_REP
    GEN_REP --> JSON_OUT
    GEN_REP --> XLSX_OUT
    GEN_REP --> HIST
    ORCH --> STATE
    STATE --> SSE
    SSE --> JS
    HTML --> JS
    JS --> CHART
    JS --> CSS
    JS --> FLASK
```

---

## 4. Diagrama de capas

```mermaid
graph LR
    subgraph "Capa 0 — Bootstrap"
        L["launcher.py / run_server.py<br/>Verificación de librerías<br/>Resolución de rutas"]
    end

    subgraph "Capa 1 — Presentación"
        P["index.html + script.js + styles.css<br/>SPA mínima · sin framework JS"]
    end

    subgraph "Capa 2 — API y Orquestación"
        A["app_web.py (GOD OBJECT)<br/>Flask routes · estado global · threading"]
    end

    subgraph "Capa 3 — Dominio"
        D1["motor_evaluacion.py<br/>Lógica de rúbrica"]
        D2["config.py<br/>Base de conocimiento"]
    end

    subgraph "Capa 4 — Infraestructura"
        I1["extractor_cvs.py<br/>pdfplumber / PyPDF2"]
        I2["extractor_web_cvs.py<br/>requests / BeautifulSoup"]
        I3["generador_reportes.py<br/>openpyxl / json"]
    end

    subgraph "Capa 5 — Persistencia"
        FS["Sistema de archivos<br/>resultados/*.json · *.xlsx"]
    end

    L --> P
    P --> A
    A --> D1
    A --> I1
    A --> I2
    D1 --> D2
    A --> I3
    I3 --> FS
    I1 --> D1
    I2 --> D1
```

---

## 5. Flujo de ejecución principal

```mermaid
sequenceDiagram
    actor Usuario
    participant Browser as Navegador
    participant Flask as Flask (app_web.py)
    participant Thread as Hilo Background
    participant Extractor as Extracción (PDF + Web)
    participant Motor as Motor Evaluación
    participant Reportes as Generador Reportes
    participant FS as Sistema de archivos

    Usuario->>Browser: Abre EvaluacionDocente_USIL.exe
    Browser->>Flask: GET /
    Flask-->>Browser: index.html

    Usuario->>Browser: Sube Excel + PDFs
    Browser->>Flask: POST /api/subir_archivo
    Browser->>Flask: POST /api/subir_pdfs
    Flask-->>Browser: 200 OK

    Usuario->>Browser: Clic "Iniciar evaluación"
    Browser->>Flask: POST /api/iniciar_evaluacion
    Flask->>Thread: lanzar _evaluar_candidatos()
    Flask-->>Browser: 200 OK {estado: "iniciado"}

    Browser->>Flask: GET /api/estado_proceso (SSE)

    loop Progreso en tiempo real
        Thread->>Flask: actualizar estado_proceso{}
        Flask-->>Browser: SSE event {progreso, mensaje}
        Browser-->>Usuario: Actualizar barras de progreso
    end

    Thread->>Extractor: procesar_todos_cvs() + procesar_excel_links()
    Extractor-->>Thread: lista de dicts normalizados

    Thread->>Motor: evaluar_multiples_cvs(lista_cvs)
    Motor-->>Thread: lista con scores C1-C7 + perfil

    Thread->>Reportes: generar_excel_comparativo() + generar_json_decision()
    Reportes->>FS: guardar .xlsx + .json

    Thread->>Flask: estado_proceso["completado"] = True

    Browser->>Flask: GET /api/resultados
    Flask-->>Browser: JSON con ranking completo
    Browser-->>Usuario: Tabla de resultados + gráficos radar
```

---

## 6. Flujo de extracción de datos

```mermaid
flowchart TD
    START([Inicio extracción]) --> READ_EXCEL[Leer Excel LINKS/]
    READ_EXCEL --> HAS_URL{¿Tiene URL<br/>CTI Vitae?}

    HAS_URL -->|Sí| WEB_EXTRACT[ExtractorWebCVs<br/>extraer_cv_desde_url]
    HAS_URL -->|No| PDF_CHECK{¿Hay PDF<br/>coincidente?}

    WEB_EXTRACT --> HTTP_REQ[GET URL · timeout=35s]
    HTTP_REQ --> HTTP_OK{¿Respuesta<br/>200 OK?}

    HTTP_OK -->|Sí| PARSE_HTML[BeautifulSoup<br/>parsear tablas HTML]
    HTTP_OK -->|No, reintento ≤3| RETRY[Reintentar<br/>timeout += 20s]
    HTTP_OK -->|No, agotados| EMPTY_WEB[Datos vacíos<br/>fuente=CTI_VITAE_ERROR]

    RETRY --> HTTP_REQ

    PARSE_HTML --> EXTRACT_FIELDS[Extraer campos:<br/>grado · años · publicaciones<br/>RENATI · actualización]
    EXTRACT_FIELDS --> NORM_WEB[Normalizar datos web]

    PDF_CHECK -->|Sí| PDF_EXTRACT[ExtractorCV<br/>extraer_texto pdfplumber]
    PDF_CHECK -->|No| EMPTY_PDF[Datos mínimos<br/>fuente=SIN_DATOS]

    PDF_EXTRACT --> PDF_OK{¿pdfplumber<br/>OK?}
    PDF_OK -->|Sí| PARSE_PDF[Texto extraído]
    PDF_OK -->|No| PDF_FALLBACK[Fallback PyPDF2]
    PDF_FALLBACK --> PARSE_PDF

    PARSE_PDF --> NORM_PDF[Normalizar datos PDF]

    NORM_WEB --> MERGE[Unificar datos<br/>_normalizar_datos_cv]
    NORM_PDF --> MERGE
    EMPTY_WEB --> MERGE
    EMPTY_PDF --> MERGE

    MERGE --> OUTPUT([Dict normalizado<br/>listo para el motor])
```

---

## 7. Motor de evaluación — lógica de clasificación

```mermaid
flowchart TD
    INPUT([cv_data normalizado]) --> DETECT[_detectar_tipo_perfil<br/>análisis de keywords]

    DETECT --> TIPO{Tipo de perfil}
    TIPO --> CLINICO[clínico<br/>pesos: C3=32% C4=18%]
    TIPO --> INVEST[investigador<br/>pesos: C5=28% C1=25%]
    TIPO --> INDUST[industrial<br/>pesos: C3=38% C4=22%]
    TIPO --> DOCENT[docente<br/>pesos: C2=30% C1=22%]
    TIPO --> GENERAL[general<br/>pesos balanceados]

    CLINICO --> EVAL
    INVEST --> EVAL
    INDUST --> EVAL
    DOCENT --> EVAL
    GENERAL --> EVAL

    subgraph EVAL[Evaluación 5+2 Criterios]
        C1[C1: Formación académica<br/>Doctorado=50 · Maestría=30 · Lic=15]
        C2[C2: Experiencia docente<br/>≥10 años=40 · 6-9=30 · 3-5=20]
        C3[C3: Experiencia profesional<br/>Alta dirección=40 · Mando medio=30]
        C4[C4: Centro de labores<br/>TOP 100 MERCO=20 · Big4=15]
        C5[C5: Producción académica<br/>Libros/indexados=40 · Scopus/WoS=30]
        C6[C6: Liderazgo<br/>Alto=20 · Medio=15 · Básico=10]
        C7[C7: Especialización<br/>Alta=10 · Media=6 · Básica=3]
    end

    EVAL --> TOTAL[TOTAL = C1+C2+C3+C4+C5+C6+C7<br/>máximo = 200 pts]

    TOTAL --> CLASS[_clasificar_candidato]

    subgraph CLASS[Árbol de clasificación — orden de prioridad]
        R1{C1=0 AND C5=0} -->|Sí| NO_ELEG[NO_ELEGIBLE]
        R1 -->|No| R2{Total≥150 AND C5≥30<br/>AND C1≥40 AND C2≥20}
        R2 -->|Sí| INV_H[DOCENTE_INVESTIGADOR_HORAS]
        R2 -->|No| R3{C5≥30 AND C1≥30}
        R3 -->|Sí| INV[DOCENTE_INVESTIGADOR]
        R3 -->|No| R4{DTC: Total≥110<br/>C1≥30 AND C2≥20}
        R4 -->|Sí| DTC[DTC]
        R4 -->|No| R5{DTP: Total≥100<br/>C2>0 AND C3≥15}
        R5 -->|Sí| DTP[DTP]
        R5 -->|No| R6{PRACTITIONER:<br/>clínico OR Total≥90}
        R6 -->|Sí| PRAC[PRACTITIONER]
        R6 -->|No| R7{C3≥15 AND C1≥15}
        R7 -->|Sí| POT[PROFESIONAL_POTENCIAL]
        R7 -->|No| R8{C1≥30 AND C2<20}
        R8 -->|Sí| ACAD[ACADEMICO_FORMACION]
        R8 -->|No| R9{Total≥60 AND C1≥10}
        R9 -->|Sí| ACEPT[ACEPTABLE]
        R9 -->|No| NO_ELEG2[NO_ELEGIBLE]
    end
```

---

## 8. Comunicación frontend-backend

```mermaid
sequenceDiagram
    participant JS as script.js
    participant Flask as Flask API
    participant SSE as SSE Stream

    Note over JS,Flask: Carga inicial
    JS->>Flask: GET /
    Flask-->>JS: index.html

    Note over JS,Flask: Upload de archivos
    JS->>Flask: POST /api/subir_archivo<br/>multipart/form-data
    Flask-->>JS: {success: true, nombre_archivo: "..."}

    JS->>Flask: POST /api/subir_pdfs<br/>multipart/form-data
    Flask-->>JS: {success: true, cantidad_pdfs: N}

    Note over JS,Flask: Inicio de evaluación
    JS->>Flask: POST /api/iniciar_evaluacion<br/>{modo_rapido: bool}
    Flask-->>JS: {estado: "iniciado", mensaje: "..."}

    Note over JS,SSE: Stream de progreso
    JS->>SSE: GET /api/estado_proceso<br/>Accept: text/event-stream
    loop SSE events
        SSE-->>JS: data: {progreso: 45, mensaje: "Procesando candidato 3/10..."}
        JS-->>JS: actualizar barras UI
    end
    SSE-->>JS: data: {completado: true}

    Note over JS,Flask: Obtención de resultados
    JS->>Flask: GET /api/resultados
    Flask-->>JS: JSON con lista de evaluaciones

    Note over JS,Flask: Análisis individual
    JS->>Flask: POST /api/analizar_link<br/>{url: "https://ctivitae..."}
    Flask-->>JS: {datos_cv: {...}, evaluacion: {...}}
```

---

## 9. Modelo de datos

### Estructura del dict de candidato (circula por todo el pipeline)

```mermaid
classDiagram
    class CandidatoData {
        +String nombre
        +String dni
        +String url
        +String fuente
        +Dict educacion
        +int anos_experiencia_docente
        +int anos_experiencia_profesional
        +List experiencia_laboral
        +int publicaciones
        +int articulos_indexados
        +bool tiene_scopus
        +bool tiene_wos
        +int libros
        +int proyectos
        +bool perfil_desactualizado
        +int meses_sin_actualizar
        +String texto_completo
    }

    class Educacion {
        +bool doctorado
        +bool doctorado_completo
        +bool maestria
        +bool maestria_completa
        +bool licenciatura
        +String grado_maximo
    }

    class EvaluacionResultado {
        +String nombre
        +String perfil_recomendado
        +int c1_formacion
        +int c2_docente
        +int c3_profesional
        +int c4_centro_labores
        +int c5_produccion
        +int c6_liderazgo
        +int c7_especializacion
        +int puntuacion_total
        +float porcentaje
        +String tipo_perfil_detectado
        +List perfiles_cumplidos
        +Dict detalle_criterios
    }

    CandidatoData "1" --> "1" Educacion
    CandidatoData "1" --> "1" EvaluacionResultado : evaluar_cv_completo()
```

### Esquema JSON de salida (`clasificacion_final_*.json`)

```json
{
  "timestamp": "2026-06-01T10:30:00",
  "total_evaluados": 25,
  "resumen": {
    "DTC": 3,
    "DTP": 8,
    "PRACTITIONER": 5,
    "NO_ELEGIBLE": 2
  },
  "ranking": [
    {
      "posicion": 1,
      "nombre": "...",
      "dni": "...",
      "perfil_recomendado": "DTC",
      "puntuacion_total": 145,
      "porcentaje": 72.5,
      "c1_formacion": 40,
      "c2_docente": 30,
      "c3_profesional": 30,
      "c4_centro_labores": 15,
      "c5_produccion": 20,
      "c6_liderazgo": 10,
      "c7_especializacion": 0
    }
  ]
}
```

---

## 10. Despliegue y distribución

```mermaid
graph LR
    subgraph "Desarrollo"
        SRC["Código fuente<br/>bot_evaluacion_docente/"]
        VENV[".venv/<br/>Python 3.13+"]
        VENV2[".venv2/<br/>PyInstaller build"]
    end

    subgraph "Build"
        COMP["compilar.py<br/>PyInstaller --onefile"]
        SPEC["Recopila:<br/>templates/ · static/<br/>librerías Python"]
    end

    subgraph "Distribución"
        EXE["EvaluacionDocente_USIL.exe<br/>67.7 MB · standalone"]
        DIST["dist/<br/>LEEME_INSTRUCCIONES.md"]
    end

    subgraph "Ejecución usuario final"
        USER["Usuario ejecuta .exe"]
        FLASK_RT["Flask 127.0.0.1:5000<br/>Python embebido"]
        BROWSER["Navegador del usuario"]
        DATA_DIRS["Cvs/ · LINKS/ · Rubrica/"]
    end

    SRC --> COMP
    VENV2 --> COMP
    COMP --> SPEC
    SPEC --> EXE
    EXE --> DIST
    DIST --> USER
    USER --> FLASK_RT
    FLASK_RT --> BROWSER
    DATA_DIRS --> FLASK_RT
```

**Requisitos en el equipo del usuario final:**
- Windows 10 / 11 (x64)
- Sin Python instalado (embebido en el .exe)
- Sin instalación de librerías
- Conexión a Internet para extracción de CTI Vitae

---

## 11. Restricciones arquitectónicas

| Restricción | Descripción | Impacto |
|------------|-------------|---------|
| **Sin base de datos** | Todo el estado en archivos JSON/Excel | No escala a múltiples usuarios concurrentes |
| **Un solo usuario simultáneo** | Estado global compartido sin aislamiento de sesión | Dos ejecuciones paralelas corrompen `estado_proceso` |
| **Solo localhost** | Flask no implementa autenticación | No puede desplegarse en servidor compartido sin cambios |
| **Dependencia de CTI Vitae** | No existe API oficial; el scraper depende del HTML actual | Cambios en la web de CONCYTEC rompen el pipeline |
| **Lista MERCO hardcodeada** | 150+ empresas TOP en `config.py` | Requiere modificar código para actualizar la lista anualmente |
| **Windows solamente** | Rutas con `os.path.join` y carpetas con nombres en español | La distribución .exe es exclusiva para Windows |

---

## 12. Deuda arquitectónica y evolución propuesta

### Estado actual vs. estado objetivo

```mermaid
graph TD
    subgraph "Estado Actual — Monolito"
        M["app_web.py (~3000 líneas)<br/>Routes + Logic + State + I/O"]
    end

    subgraph "Estado Objetivo — Capas separadas"
        R["routes/<br/>api_routes.py<br/>upload_routes.py"]
        S["services/<br/>evaluacion_service.py<br/>extraccion_service.py"]
        ST["state/<br/>session_manager.py<br/>threading.Lock()"]
        DB["persistence/<br/>SQLite o DuckDB<br/>historial_repo.py"]
    end

    M -.->|Fase 3 refactoring| R
    M -.->|Fase 3 refactoring| S
    M -.->|Fase 2 estabilidad| ST
    M -.->|Fase 4 calidad| DB
```

### Roadmap de evolución

| Fase | Descripción | Prioridad | Esfuerzo estimado |
|------|-------------|-----------|-------------------|
| **Fase 1 — Seguridad** | Hash de DNI · sanitización de uploads · audit log | CRÍTICA | 3 días |
| **Fase 2 — Estabilidad** | `threading.Lock` · manejo de errores de extracción · `None` vs `0` | ALTA | 2 días |
| **Fase 3 — Mantenibilidad** | Dividir `app_web.py` en routers + services | ALTA | 5 días |
| **Fase 4 — Calidad** | Suite pytest · CI básico · type hints en `app_web.py` | MEDIA | 5 días |
| **Fase 5 — Configuración** | Externalizar lista MERCO a Excel · UI de configuración | MEDIA | 2 días |
| **Fase 6 — Escalabilidad** | SQLite como backend · soporte multi-usuario | BAJA | 10 días |

---

*Universidad San Ignacio de Loyola · People Analytics · 2026*
