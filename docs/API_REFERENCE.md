# Referencia de API — Sistema de Evaluación Automática de Docentes USIL

**Universidad San Ignacio de Loyola · People Analytics**
**Audiencia:** Desarrolladores, integradores de sistemas
**Base URL:** `http://127.0.0.1:5000`
**Versión:** 3.0 · **Fecha:** 2026-06-01

---

## Índice

1. [Resumen de endpoints](#1-resumen-de-endpoints)
2. [Convenciones](#2-convenciones)
3. [GET /](#3-get-)
4. [POST /api/subir_archivo](#4-post-apisubir_archivo)
5. [POST /api/subir_pdfs](#5-post-apisubir_pdfs)
6. [POST /api/iniciar_evaluacion](#6-post-apiniciar_evaluacion)
7. [GET /api/estado_proceso](#7-get-apiestado_proceso)
8. [GET /api/resultados](#8-get-apiresultados)
9. [POST /api/analizar_link](#9-post-apianalizar_link)
10. [GET /api/obtener_datos_requerimientos](#10-get-apiobtener_datos_requerimientos)
11. [Esquemas de datos](#11-esquemas-de-datos)
12. [Códigos de error](#12-códigos-de-error)
13. [Ejemplo de flujo completo](#13-ejemplo-de-flujo-completo)

---

## 1. Resumen de endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Interfaz web principal |
| POST | `/api/subir_archivo` | Cargar el Excel de candidatos |
| POST | `/api/subir_pdfs` | Cargar archivos PDF de CVs |
| POST | `/api/iniciar_evaluacion` | Iniciar el pipeline de evaluación |
| GET | `/api/estado_proceso` | Stream SSE de progreso en tiempo real |
| GET | `/api/resultados` | Obtener resultados finales de la evaluación |
| POST | `/api/analizar_link` | Analizar un perfil CTI Vitae individual |
| GET | `/api/obtener_datos_requerimientos` | Leer el Excel de requerimientos docentes |

---

## 2. Convenciones

### Formato de respuesta

Todas las respuestas de la API (excepto SSE y la interfaz web) usan `Content-Type: application/json`.

```json
{
  "success": true,
  "mensaje": "descripción del resultado",
  "datos": { ... }
}
```

En caso de error:
```json
{
  "success": false,
  "error": "descripción del error"
}
```

### Autenticación

La API **no implementa autenticación**. Solo es accesible desde `127.0.0.1` (localhost). No exponer el puerto 5000 a redes externas.

### Límites

| Límite | Valor |
|--------|-------|
| Tamaño máximo de archivo subido | 50 MB |
| Timeout por request HTTP | Estándar Flask (sin límite explícito) |
| Concurrencia soportada | 1 evaluación activa a la vez |

---

## 3. GET /

### Descripción

Sirve la interfaz web completa (SPA).

### Request

```http
GET / HTTP/1.1
Host: 127.0.0.1:5000
```

### Response

```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

<!-- Contenido de templates/index.html -->
```

---

## 4. POST /api/subir_archivo

### Descripción

Carga el archivo Excel que contiene la lista de candidatos con sus URLs de CTI Vitae.

### Request

```http
POST /api/subir_archivo HTTP/1.1
Content-Type: multipart/form-data

archivo: <binario del archivo .xlsx>
```

**Campo del formulario:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|:---------:|-------------|
| `archivo` | File (.xlsx) | Sí | Archivo Excel de candidatos |

**Estructura esperada del Excel:**

| Columna | Campo | Tipo |
|---------|-------|------|
| I | Nombres del candidato | String |
| J | DNI | String/Número |
| K | URL CTI Vitae | String (URL) |

### Response 200 — Éxito

```json
{
  "success": true,
  "mensaje": "Archivo cargado correctamente",
  "nombre_archivo": "INFORMACION DE VALIDACION 2026-1.xlsx",
  "cantidad_candidatos": 25,
  "candidatos_preview": [
    {
      "nombre": "García López, Juan Carlos",
      "dni": "70123456",
      "tiene_url": true
    }
  ]
}
```

### Response 400 — Error de validación

```json
{
  "success": false,
  "error": "Formato de archivo no soportado. Se esperaba .xlsx"
}
```

```json
{
  "success": false,
  "error": "No se encontraron candidatos en el archivo. Verificar que las columnas I, J, K contengan datos."
}
```

### Response 413 — Archivo demasiado grande

```json
{
  "success": false,
  "error": "El archivo supera el límite de 50 MB"
}
```

---

## 5. POST /api/subir_pdfs

### Descripción

Carga uno o más archivos PDF de CVs.

### Request

```http
POST /api/subir_pdfs HTTP/1.1
Content-Type: multipart/form-data

pdfs: <binario PDF 1>
pdfs: <binario PDF 2>
...
```

**Campo del formulario:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|:---------:|-------------|
| `pdfs` | File[] (.pdf) | No | Uno o más archivos PDF |

### Response 200 — Éxito

```json
{
  "success": true,
  "mensaje": "CVs cargados correctamente",
  "cantidad_pdfs": 8,
  "archivos": [
    "CV García López Juan Carlos.pdf",
    "CV Ramírez Torres Ana María.pdf"
  ]
}
```

### Response 200 — Sin archivos válidos

```json
{
  "success": true,
  "mensaje": "No se cargaron archivos PDF válidos",
  "cantidad_pdfs": 0
}
```

---

## 6. POST /api/iniciar_evaluacion

### Descripción

Inicia el pipeline de evaluación en un hilo de background. Requiere que previamente se haya subido al menos el archivo Excel.

### Request

```http
POST /api/iniciar_evaluacion HTTP/1.1
Content-Type: application/json

{
  "modo_rapido": false
}
```

**Cuerpo:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|:---------:|-------------|
| `modo_rapido` | Boolean | No | Si `true`, omite re-análisis de perfiles que tardaron > 2 min. Default: `false` |

### Response 200 — Proceso iniciado

```json
{
  "success": true,
  "estado": "iniciado",
  "mensaje": "Pipeline de evaluación iniciado. Conectar a /api/estado_proceso para seguir el progreso.",
  "total_candidatos": 25
}
```

### Response 400 — Sin datos de entrada

```json
{
  "success": false,
  "error": "No hay archivo Excel cargado. Llamar primero a /api/subir_archivo."
}
```

### Response 409 — Proceso ya en ejecución

```json
{
  "success": false,
  "error": "Ya hay un proceso de evaluación en curso. Esperar a que termine."
}
```

### Comportamiento asíncrono

Una vez que retorna `200`, el proceso continúa en background. El cliente debe escuchar el endpoint SSE `/api/estado_proceso` para monitorear el progreso.

---

## 7. GET /api/estado_proceso

### Descripción

Stream de Server-Sent Events (SSE) que emite el estado del pipeline en tiempo real. La conexión se mantiene abierta hasta que el proceso termine.

### Request

```http
GET /api/estado_proceso HTTP/1.1
Accept: text/event-stream
Cache-Control: no-cache
```

### Response — Stream SSE

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

**Formato de cada evento:**

```
data: {"progreso": 45, "mensaje": "Procesando candidato 9 de 20...", "completado": false}

data: {"progreso": 100, "mensaje": "Evaluación completada", "completado": true}
```

**Esquema de cada evento SSE:**

```json
{
  "progreso": 45,
  "mensaje": "Procesando: Ramírez Torres, Ana María (extrayendo CTI Vitae...)",
  "completado": false,
  "candidatos_procesados": 9,
  "total_candidatos": 20,
  "exitosos": 8,
  "errores": 1,
  "tiempo_transcurrido_segundos": 47
}
```

**Evento final (completado):**

```json
{
  "progreso": 100,
  "mensaje": "Evaluación completada. 20 candidatos procesados.",
  "completado": true,
  "candidatos_procesados": 20,
  "total_candidatos": 20,
  "exitosos": 18,
  "errores": 2,
  "tiempo_total_segundos": 312
}
```

**Evento de error:**

```json
{
  "progreso": 0,
  "mensaje": "Error en el proceso de evaluación",
  "completado": false,
  "error": "descripción del error"
}
```

### Ejemplo en JavaScript

```javascript
const eventSource = new EventSource('/api/estado_proceso');

eventSource.onmessage = function(event) {
  const datos = JSON.parse(event.data);
  
  actualizarBarraProgreso(datos.progreso);
  mostrarMensaje(datos.mensaje);
  
  if (datos.completado) {
    eventSource.close();
    cargarResultados();
  }
};

eventSource.onerror = function() {
  eventSource.close();
};
```

---

## 8. GET /api/resultados

### Descripción

Retorna los resultados completos de la última evaluación completada.

### Request

```http
GET /api/resultados HTTP/1.1
```

### Response 200 — Resultados disponibles

```json
{
  "success": true,
  "timestamp": "2026-06-01T10:30:00",
  "total_evaluados": 20,
  "resumen": {
    "DTC": 3,
    "DTP": 6,
    "PRACTITIONER": 4,
    "DOCENTE_INVESTIGADOR": 2,
    "DOCENTE_INVESTIGADOR_HORAS": 1,
    "PROFESIONAL_POTENCIAL": 2,
    "ACADEMICO_FORMACION": 1,
    "ACEPTABLE": 0,
    "NO_ELEGIBLE": 1
  },
  "ranking": [
    {
      "posicion": 1,
      "nombre": "García López, Juan Carlos",
      "dni": "70123456",
      "perfil_recomendado": "DTC",
      "puntuacion_total": 166,
      "porcentaje": 83.0,
      "tipo_perfil_detectado": "docente",
      "c1_formacion": 40,
      "c2_docente": 30,
      "c3_profesional": 30,
      "c4_centro_labores": 15,
      "c5_produccion": 30,
      "c6_liderazgo": 15,
      "c7_especializacion": 6,
      "perfiles_cumplidos": ["DTC", "DTP"],
      "fuente": "CTI_VITAE",
      "detalle_criterios": {
        "c1": {
          "nivel_detectado": "Doctorado en curso",
          "puntos": 40,
          "justificacion": "Se detectó matrícula activa en programa doctoral"
        },
        "c2": {
          "nivel_detectado": "6-9 años",
          "puntos": 30,
          "justificacion": "8 años de experiencia docente universitaria"
        }
      }
    }
  ],
  "rutas_archivos": {
    "excel": "resultados/Analisis_Detallado_20260601_103000.xlsx",
    "json": "resultados/clasificacion_final_20260601_103000.json"
  }
}
```

### Response 404 — Sin resultados

```json
{
  "success": false,
  "error": "No hay resultados disponibles. Iniciar una evaluación primero."
}
```

### Response 409 — Proceso en curso

```json
{
  "success": false,
  "error": "El proceso de evaluación aún está en curso.",
  "progreso": 67
}
```

---

## 9. POST /api/analizar_link

### Descripción

Extrae y evalúa los datos de un único perfil CTI Vitae. Útil para verificar un candidato individual o re-analizar perfiles que fallaron en el proceso batch.

### Request

```http
POST /api/analizar_link HTTP/1.1
Content-Type: application/json

{
  "url": "https://ctivitae.concytec.gob.pe/appDirectorioCTI/VerDatosInvestigador.do?id=12345",
  "nombre": "García López, Juan Carlos"
}
```

**Cuerpo:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|:---------:|-------------|
| `url` | String (URL) | Sí | URL completa del perfil CTI Vitae |
| `nombre` | String | No | Nombre del candidato (para mostrar en la respuesta) |

### Response 200 — Análisis exitoso

```json
{
  "success": true,
  "datos_cv": {
    "nombre": "García López, Juan Carlos",
    "url": "https://ctivitae.concytec.gob.pe/...",
    "fuente": "CTI_VITAE",
    "educacion": {
      "doctorado": true,
      "doctorado_completo": false,
      "maestria": true,
      "maestria_completa": true,
      "licenciatura": true,
      "grado_maximo": "Doctorado en curso"
    },
    "anos_experiencia_docente": 8,
    "anos_experiencia_profesional": 12,
    "publicaciones": 5,
    "articulos_indexados": 3,
    "tiene_scopus": true,
    "tiene_wos": false,
    "proyectos": 2,
    "perfil_desactualizado": false,
    "meses_sin_actualizar": 2
  },
  "evaluacion": {
    "perfil_recomendado": "DTC",
    "puntuacion_total": 166,
    "porcentaje": 83.0,
    "c1_formacion": 40,
    "c2_docente": 30,
    "c3_profesional": 30,
    "c4_centro_labores": 15,
    "c5_produccion": 30,
    "c6_liderazgo": 15,
    "c7_especializacion": 6
  },
  "tiempo_extraccion_segundos": 3.8
}
```

### Response 200 — Error de extracción (CTI Vitae no respondió)

```json
{
  "success": true,
  "datos_cv": {
    "nombre": "García López, Juan Carlos",
    "fuente": "CTI_VITAE_ERROR",
    "error_detalle": "Timeout después de 3 intentos (75 segundos total)"
  },
  "evaluacion": null,
  "tiempo_extraccion_segundos": 75.2
}
```

### Response 400 — URL inválida

```json
{
  "success": false,
  "error": "URL inválida. Debe ser una URL completa de CTI Vitae (https://ctivitae.concytec.gob.pe/...)."
}
```

---

## 10. GET /api/obtener_datos_requerimientos

### Descripción

Lee y retorna los datos del Excel de requerimientos docentes ubicado en `LINKS/`. Este endpoint es utilizado por la interfaz para pre-cargar información de facultad y carrera.

### Request

```http
GET /api/obtener_datos_requerimientos HTTP/1.1
```

### Response 200 — Datos disponibles

```json
{
  "success": true,
  "datos": [
    {
      "facultad": "Facultad de Negocios",
      "carrera": "Administración de Empresas",
      "nombre": "García López, Juan Carlos",
      "dni": "70123456",
      "url_cti": "https://ctivitae.concytec.gob.pe/..."
    },
    {
      "facultad": "Facultad de Salud",
      "carrera": "Medicina Humana",
      "nombre": "Ramírez Torres, Ana María",
      "dni": "45678901",
      "url_cti": "https://ctivitae.concytec.gob.pe/..."
    }
  ],
  "total": 25,
  "facultades": ["Facultad de Negocios", "Facultad de Salud", "Facultad de Ingeniería"],
  "archivo": "Requerimiento docentes 2026-1 300126.xlsx"
}
```

### Response 404 — Archivo no encontrado

```json
{
  "success": false,
  "error": "No se encontró el archivo de requerimientos en LINKS/. Verificar que exista un archivo con 'Requerimiento' en el nombre."
}
```

---

## 11. Esquemas de datos

### CandidatoData (input del motor)

```json
{
  "nombre": "string — nombre completo",
  "dni": "string — documento de identidad",
  "url": "string | null — URL CTI Vitae",
  "fuente": "CTI_VITAE | PDF | CTI_VITAE_ERROR | SIN_DATOS",
  "educacion": {
    "doctorado": "boolean",
    "doctorado_completo": "boolean",
    "maestria": "boolean",
    "maestria_completa": "boolean",
    "licenciatura": "boolean",
    "grado_maximo": "string — nivel descriptivo"
  },
  "anos_experiencia_docente": "integer",
  "anos_experiencia_profesional": "integer",
  "experiencia_laboral": [
    {
      "cargo": "string",
      "empresa": "string",
      "fecha_inicio": "string",
      "fecha_fin": "string | null"
    }
  ],
  "publicaciones": "integer",
  "articulos_indexados": "integer",
  "tiene_scopus": "boolean",
  "tiene_wos": "boolean",
  "libros": "integer",
  "articulos": "integer",
  "proyectos": "integer",
  "perfil_desactualizado": "boolean",
  "meses_sin_actualizar": "integer",
  "texto_completo": "string — texto crudo del PDF o CTI Vitae"
}
```

### EvaluacionResultado (output del motor)

```json
{
  "posicion": "integer — rank en el listado",
  "nombre": "string",
  "dni": "string",
  "perfil_recomendado": "DTC | DTP | PRACTITIONER | DOCENTE_INVESTIGADOR | DOCENTE_INVESTIGADOR_HORAS | PROFESIONAL_POTENCIAL | ACADEMICO_FORMACION | ACEPTABLE | NO_ELEGIBLE",
  "puntuacion_total": "integer — 0 a 200",
  "porcentaje": "float — 0.0 a 100.0",
  "tipo_perfil_detectado": "clínico | investigador | industrial | docente | general",
  "c1_formacion": "integer — 0 a 50",
  "c2_docente": "integer — 0 a 40",
  "c3_profesional": "integer — 0 a 40",
  "c4_centro_labores": "integer — 0 a 20",
  "c5_produccion": "integer — 0 a 40",
  "c6_liderazgo": "integer — 0 a 20",
  "c7_especializacion": "integer — 0 a 10",
  "perfiles_cumplidos": ["array de perfiles que el candidato cumple"],
  "fuente": "CTI_VITAE | PDF | CTI_VITAE_ERROR | SIN_DATOS",
  "detalle_criterios": {
    "c1": {
      "nivel_detectado": "string",
      "puntos": "integer",
      "justificacion": "string"
    }
  }
}
```

### ClasificacionFinal (archivo JSON de salida)

```json
{
  "timestamp": "ISO 8601 datetime",
  "version_sistema": "3.0",
  "total_evaluados": "integer",
  "resumen": {
    "DTC": "integer",
    "DTP": "integer",
    "PRACTITIONER": "integer",
    "DOCENTE_INVESTIGADOR": "integer",
    "DOCENTE_INVESTIGADOR_HORAS": "integer",
    "PROFESIONAL_POTENCIAL": "integer",
    "ACADEMICO_FORMACION": "integer",
    "ACEPTABLE": "integer",
    "NO_ELEGIBLE": "integer"
  },
  "estadisticos": {
    "promedio_total": "float",
    "maximo_total": "integer",
    "minimo_total": "integer",
    "desviacion_estandar": "float"
  },
  "ranking": ["array de EvaluacionResultado"]
}
```

---

## 12. Códigos de error

| Código HTTP | Situación | Descripción |
|------------|-----------|-------------|
| 200 | Éxito | Request procesado correctamente |
| 400 | Bad Request | Datos de entrada inválidos o faltantes |
| 404 | Not Found | Recurso no encontrado (archivo Excel, resultados) |
| 409 | Conflict | Conflicto de estado (proceso ya en curso, sin resultados aún) |
| 413 | Payload Too Large | Archivo supera 50 MB |
| 500 | Internal Server Error | Error inesperado en el servidor |

### Estructura de error estándar

```json
{
  "success": false,
  "error": "Mensaje descriptivo del error",
  "codigo": "CODIGO_INTERNO_OPCIONAL",
  "detalle": "Información adicional para debugging (solo en desarrollo)"
}
```

---

## 13. Ejemplo de flujo completo

El siguiente ejemplo muestra cómo integrar los endpoints en un cliente Python:

```python
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

# Paso 1: Subir el Excel de candidatos
with open("LINKS/INFORMACION DE VALIDACION.xlsx", "rb") as f:
    resp = requests.post(f"{BASE_URL}/api/subir_archivo",
                         files={"archivo": f})
resp.raise_for_status()
print(f"Candidatos cargados: {resp.json()['cantidad_candidatos']}")

# Paso 2: Subir PDFs (opcional)
pdf_files = [
    ("pdfs", open("Cvs/CV García López.pdf", "rb")),
    ("pdfs", open("Cvs/CV Ramírez Torres.pdf", "rb")),
]
resp = requests.post(f"{BASE_URL}/api/subir_pdfs", files=pdf_files)
print(f"PDFs cargados: {resp.json()['cantidad_pdfs']}")

# Paso 3: Iniciar evaluación
resp = requests.post(f"{BASE_URL}/api/iniciar_evaluacion",
                     json={"modo_rapido": False})
resp.raise_for_status()
print("Evaluación iniciada")

# Paso 4: Monitorear progreso (polling simple — en producción usar SSE)
while True:
    resp = requests.get(f"{BASE_URL}/api/resultados")
    datos = resp.json()
    if datos.get("success") and "ranking" in datos:
        break
    time.sleep(5)
    print("Esperando resultados...")

# Paso 5: Obtener resultados
print(f"\nTotal evaluados: {datos['total_evaluados']}")
print(f"Resumen por perfil: {json.dumps(datos['resumen'], indent=2)}")
print(f"\nTop 3 candidatos:")
for candidato in datos["ranking"][:3]:
    print(f"  {candidato['posicion']}. {candidato['nombre']}: "
          f"{candidato['puntuacion_total']}/200 → {candidato['perfil_recomendado']}")
```

### Ejemplo de monitoreo con SSE en Python

```python
import sseclient  # pip install sseclient-py

resp = requests.get(f"{BASE_URL}/api/estado_proceso", stream=True)
client = sseclient.SSEClient(resp)

for event in client.events():
    datos = json.loads(event.data)
    print(f"[{datos['progreso']:3d}%] {datos['mensaje']}")
    if datos.get("completado"):
        print("Proceso completado")
        break
```

---

*Universidad San Ignacio de Loyola · People Analytics · 2026*
