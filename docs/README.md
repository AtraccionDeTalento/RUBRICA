# Sistema de Evaluación Automática de Docentes — USIL

**Universidad San Ignacio de Loyola · People Analytics**
**Versión:** 3.0 · **Estado:** Producción · **Plataforma:** Windows (ejecutable standalone)

---

## Descripción

El **Sistema de Evaluación Automática de Docentes** automatiza el proceso de selección y clasificación de candidatos a docente universitario aplicando una rúbrica base institucional de 5 criterios, ampliada en el motor actual con 2 criterios complementarios. En total, la evaluación implementada opera con 7 componentes ponderados. El sistema extrae datos de perfiles académicos publicados en CTI Vitae (CONCYTEC) y de CVs en formato PDF, los evalúa contra la rúbrica y produce un ranking con perfiles de contratación recomendados.

El resultado elimina la revisión manual de cientos de CVs, estandariza el criterio evaluador y genera trazabilidad documental del proceso de selección.

---

## Características principales

| Característica | Descripción |
|---------------|-------------|
| Evaluación multi-criterio | 5 criterios base + 2 criterios complementarios, con puntaje normalizado a 200 puntos |
| Extracción automatizada | Web scraping de CTI Vitae + parseo de PDFs |
| Clasificación de perfiles | 9 perfiles de contratación según la rúbrica institucional |
| Interfaz web local | Flask en localhost:5000, sin necesidad de instalación de servidor |
| Exportación de resultados | Excel multi-hoja + JSON con ranking completo |
| Progreso en tiempo real | Server-Sent Events (SSE) para actualización del estado |
| Distribución standalone | Ejecutable `.exe` de 67.7 MB sin dependencias externas |

---

## Criterios de evaluación

La rúbrica base contiene 5 criterios principales (C1-C5). El código actual agrega C6 y C7 como criterios complementarios para reforzar la detección de liderazgo profesional y especialización.

| # | Criterio | Peso máximo |
|---|---------|-------------|
| C1 | Formación académica (grado máximo obtenido) | 50 pts |
| C2 | Experiencia docente (años en aula universitaria) | 40 pts |
| C3 | Experiencia profesional (nivel jerárquico alcanzado) | 40 pts |
| C4 | Centro de labores actual (empresa TOP / institución de referencia) | 20 pts |
| C5 | Producción académica (publicaciones, proyectos de investigación) | 40 pts |
| C6 | Liderazgo profesional (cargos directivos y gestión) | 20 pts |
| C7 | Especialización (certificaciones, subespecialidades) | 10 pts |
| **TOTAL** | | **200 pts** |

---

## Perfiles de contratación resultantes

| Perfil | Condición mínima | Descripción |
|--------|-----------------|-------------|
| `DOCENTE_INVESTIGADOR_HORAS` | Total ≥ 150 · C5 ≥ 30 · C1 ≥ 40 · C2 ≥ 20 | Investigador activo con experiencia docente |
| `DOCENTE_INVESTIGADOR` | C5 ≥ 30 · C1 ≥ 30 | Perfil mixto investigación + docencia |
| `DTC` | Total ≥ 110 · C1 ≥ 30 · C2 ≥ 20 | Docente a Tiempo Completo |
| `DTP` | Total ≥ 100 · C2 > 0 · C3 ≥ 15 | Docente a Tiempo Parcial |
| `PRACTITIONER` | Total ≥ 90 (perfil clínico) | Profesional con experiencia sectorial |
| `PROFESIONAL_POTENCIAL` | C3 ≥ 15 · C1 ≥ 15 | Candidato con proyección docente |
| `ACADEMICO_FORMACION` | C1 ≥ 30 | Fuerte formación académica, poca práctica |
| `ACEPTABLE` | Total ≥ 60 · C1 ≥ 10 | Cumple mínimo institucional |
| `NO_ELEGIBLE` | C1 = 0 AND C5 = 0 | No cumple criterios base |

---

## Inicio rápido

### Opción A — Ejecutable Windows (recomendado para usuarios finales)

```
1. Descargar EvaluacionDocente_USIL.exe
2. Crear las siguientes carpetas en el mismo directorio:
   ├── LINKS/    ← colocar aquí el Excel de candidatos
   ├── Cvs/      ← colocar aquí los PDFs de CVs (opcional)
   └── Rubrica/  ← colocar aquí la plantilla de rúbrica
3. Ejecutar EvaluacionDocente_USIL.exe
4. El navegador abre automáticamente en http://127.0.0.1:5000
```

### Opción B — Ejecución desde código fuente

```bash
# 1. Activar entorno virtual
.venv\Scripts\activate

# 2. Instalar dependencias
pip install -r bot_evaluacion_docente/requirements.txt

# 3. Ejecutar
cd bot_evaluacion_docente
python launcher.py
```

### Opción C — Pipeline CLI (sin interfaz web)

```bash
cd bot_evaluacion_docente
python main.py
```

---

## Estructura de datos de entrada

El sistema espera un archivo Excel en `LINKS/` con el siguiente esquema:

| Columna | Campo | Descripción |
|---------|-------|-------------|
| I | Nombres | Nombre completo del candidato |
| J | DNI | Documento de identidad |
| K | Links CTI Vitae | URL del perfil en https://ctivitae.concytec.gob.pe |

---

## Salida generada

Todos los archivos de salida se guardan en `bot_evaluacion_docente/resultados/`:

| Archivo | Formato | Contenido |
|---------|---------|-----------|
| `clasificacion_final_YYYYMMDD_HHMMSS.json` | JSON | Ranking completo con scores C1–C7 |
| `Analisis_Detallado_YYYYMMDD_HHMMSS.xlsx` | Excel | 3 hojas: ranking, clasificaciones, resumen |
| `historial_personas.json` | JSON | Registro acumulativo histórico |

---

## Dependencias

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

---

## Compilación del ejecutable

```bash
cd bot_evaluacion_docente
python compilar.py
# Genera: dist/EvaluacionDocente_USIL.exe (≈ 67.7 MB)
```

---

## Documentación adicional

| Documento | Contenido |
|-----------|-----------|
| [ARQUITECTURA.md](ARQUITECTURA.md) | Diagramas de arquitectura y flujos de datos |
| [MANUAL_TECNICO.md](MANUAL_TECNICO.md) | Referencia técnica completa de módulos y clases |
| [MANUAL_USUARIO.md](MANUAL_USUARIO.md) | Guía paso a paso para usuarios finales |
| [API_REFERENCE.md](API_REFERENCE.md) | Especificación de todos los endpoints REST |
| [AUDITORIA_CODIGO.md](AUDITORIA_CODIGO.md) | Deuda técnica, seguridad y plan de remediación |
| [PORTAFOLIO_PROYECTO.md](PORTAFOLIO_PROYECTO.md) | Descripción ejecutiva del proyecto |
| [INVENTARIO_TECNICO.md](INVENTARIO_TECNICO.md) | Inventario completo del código fuente |

---

## Advertencias importantes

> **Privacidad de datos:** El sistema procesa DNI (documentos de identidad). Los archivos de resultados contienen datos personales en texto plano. Almacenar exclusivamente en equipos institucionales seguros. Ver [AUDITORIA_CODIGO.md](AUDITORIA_CODIGO.md) para el detalle de riesgos.

> **Uso exclusivo en localhost:** El servidor Flask no implementa autenticación. Ejecutar únicamente en equipos locales; nunca exponer el puerto 5000 a una red pública.

> **Scraping CTI Vitae:** El sistema realiza peticiones HTTP a la plataforma CONCYTEC. Un cambio en la estructura HTML de CTI Vitae puede interrumpir la extracción de datos sin previo aviso.

---

*Universidad San Ignacio de Loyola · People Analytics · 2026*
