# Manual de Usuario — Sistema de Evaluación Automática de Docentes USIL

**Universidad San Ignacio de Loyola · People Analytics**
**Audiencia:** Coordinadores académicos, analistas de selección docente
**Versión:** 3.0 · **Fecha:** 2026-06-01

---

## Índice

1. [¿Para qué sirve este sistema?](#1-para-qué-sirve-este-sistema)
2. [¿Qué necesito para usarlo?](#2-qué-necesito-para-usarlo)
3. [Instalación y primer uso](#3-instalación-y-primer-uso)
4. [Preparar los archivos de entrada](#4-preparar-los-archivos-de-entrada)
5. [Iniciar el sistema](#5-iniciar-el-sistema)
6. [Realizar una evaluación](#6-realizar-una-evaluación)
7. [Interpretar los resultados](#7-interpretar-los-resultados)
8. [Descargar los reportes](#8-descargar-los-reportes)
9. [Casos especiales y situaciones comunes](#9-casos-especiales-y-situaciones-comunes)
10. [Preguntas frecuentes](#10-preguntas-frecuentes)
11. [Consideraciones éticas y legales](#11-consideraciones-éticas-y-legales)

---

## 1. ¿Para qué sirve este sistema?

El sistema **evalúa automáticamente candidatos a docente universitario** aplicando la rúbrica institucional de USIL. En lugar de revisar manualmente decenas o cientos de CVs, el sistema:

1. **Descarga** automáticamente los datos académicos de cada candidato desde CTI Vitae (CONCYTEC)
2. **Lee** los CVs en PDF que hayas subido
3. **Puntúa** a cada candidato en 5 criterios base y 2 criterios complementarios (formación, experiencia docente, experiencia profesional, liderazgo, especialización, etc.)
4. **Clasifica** a cada candidato en un perfil de contratación recomendado
5. **Genera** un ranking descargable en Excel y JSON

El proceso que manualmente tomaría horas, el sistema lo completa en minutos.

---

## 2. ¿Qué necesito para usarlo?

### Requisitos del equipo

| Requisito | Detalle |
|-----------|---------|
| Sistema operativo | Windows 10 o Windows 11 (64 bits) |
| RAM | Al menos 4 GB disponibles |
| Espacio en disco | 500 MB libres (el .exe ocupa 67.7 MB) |
| Internet | Requerido durante la evaluación (para consultar CTI Vitae) |
| Navegador | Google Chrome, Edge o Firefox (versión reciente) |

> No necesitas instalar Python, ni ninguna librería adicional. El programa es un ejecutable que funciona de manera autónoma.

### Archivos que debes tener listos

| Archivo | Formato | ¿Obligatorio? | ¿Qué contiene? |
|---------|---------|:---:|------------|
| Excel de candidatos | `.xlsx` | Sí | Nombres, DNI y URLs de CTI Vitae |
| CVs en PDF | `.pdf` | No | Currículums vitae en formato PDF |

---

## 3. Instalación y primer uso

### Paso 1 — Copiar el ejecutable

Copia el archivo `EvaluacionDocente_USIL.exe` a una carpeta de tu equipo. Por ejemplo:
```
C:\Users\TuNombre\Desktop\Evaluacion Docentes\
```

### Paso 2 — Crear las carpetas de trabajo

En la misma carpeta donde copiaste el `.exe`, crea manualmente estas carpetas:

```
Evaluacion Docentes/
├── EvaluacionDocente_USIL.exe   ← el programa
├── LINKS/                        ← aquí irá el Excel de candidatos
├── Cvs/                          ← aquí irán los PDFs (opcional)
└── Rubrica/                      ← aquí irá la plantilla de rúbrica
```

> **Importante:** Los nombres de las carpetas deben ser exactamente `LINKS`, `Cvs` y `Rubrica` (respetando mayúsculas).

### Paso 3 — Primera ejecución

1. Haz doble clic en `EvaluacionDocente_USIL.exe`
2. Windows puede mostrar una advertencia de seguridad ("Windows protegió tu PC"). Haz clic en **Más información** → **Ejecutar de todas formas**
3. El sistema abrirá automáticamente tu navegador en `http://127.0.0.1:5000`

Si el navegador no se abre solo, escribe manualmente en la barra de direcciones:
```
http://127.0.0.1:5000
```

---

## 4. Preparar los archivos de entrada

### El Excel de candidatos

Este es el archivo más importante. Debe tener el siguiente formato:

| Columna I | Columna J | Columna K |
|-----------|-----------|-----------|
| **Nombres** | **DNI** | **Links CTI Vitae** |
| García López, Juan Carlos | 70123456 | https://ctivitae.concytec.gob.pe/appDirectorioCTI/VerDatosInvestigador.do?id=12345 |
| Ramírez Torres, Ana María | 45678901 | https://ctivitae.concytec.gob.pe/... |

**Reglas importantes para el Excel:**
- La primera fila puede ser encabezado o datos (el sistema detecta automáticamente)
- La columna I debe contener el nombre completo del candidato
- La columna J debe contener el número de DNI (solo números)
- La columna K debe contener la URL completa del perfil CTI Vitae del candidato
- No combinar celdas
- Guardar en formato `.xlsx` (no `.xls` ni `.csv`)

**¿Cómo encontrar el enlace CTI Vitae de un candidato?**

1. Ir a https://ctivitae.concytec.gob.pe
2. Buscar al candidato por nombre
3. Abrir su perfil
4. Copiar la URL completa de la barra de direcciones

> Si el candidato no tiene perfil en CTI Vitae, dejar la columna K vacía. El sistema solo evaluará con la información del PDF si existe.

### Los CVs en PDF

- Guardar cada CV como un archivo `.pdf` en la carpeta `Cvs/`
- Nombre sugerido: `CV Apellido Nombre.pdf`
- El sistema procesará todos los `.pdf` que encuentre en esa carpeta
- **Los PDFs son opcionales.** Si no hay PDFs, el sistema usa solo los datos de CTI Vitae.

---

## 5. Iniciar el sistema

### Al abrir el programa, verás esta pantalla:

```
┌─────────────────────────────────────────────────────────────┐
│          SISTEMA DE EVALUACIÓN DOCENTE USIL                 │
│                                                             │
│  [1] Cargar Excel de candidatos    [Arrastrar o hacer clic] │
│                                                             │
│  [2] Cargar CVs en PDF (opcional)  [Arrastrar o hacer clic] │
│                                                             │
│  [  INICIAR EVALUACIÓN  ]                                   │
│                                                             │
│  ☐ Modo rápido (omitir re-análisis de perfiles lentos)      │
└─────────────────────────────────────────────────────────────┘
```

### Cargar el Excel

1. Haz clic en el área "Cargar Excel de candidatos"
2. Navega hasta tu archivo Excel en `LINKS/`
3. Selecciónalo y confirma

O también puedes **arrastrar y soltar** el archivo directamente sobre esa área.

Verás un mensaje de confirmación con el nombre del archivo y la cantidad de candidatos detectados.

### Cargar los CVs (opcional)

1. Haz clic en el área "Cargar CVs en PDF"
2. Puedes seleccionar múltiples archivos PDF a la vez (usa Ctrl+clic)
3. O arrastra la carpeta completa sobre el área

### Modo rápido

Marcar esta opción hace que el sistema omita el re-análisis de perfiles que tardaron más de 2 minutos en la primera extracción. Útil cuando procesas muchos candidatos y algunos tienen perfiles CTI Vitae lentos de cargar.

---

## 6. Realizar una evaluación

### Paso 1 — Verificar los datos cargados

Antes de iniciar, confirma que ves:
- ✅ Nombre del archivo Excel cargado
- ✅ Número de candidatos detectados
- ✅ (Opcional) Número de PDFs cargados

### Paso 2 — Iniciar

Haz clic en el botón **INICIAR EVALUACIÓN**.

### Paso 3 — Monitorear el progreso

El sistema mostrará el avance en tiempo real:

```
Extrayendo datos de CTI Vitae...
████████████░░░░░░░░  60%   (9 de 15 candidatos)

Procesando: García López, Juan Carlos...
✅ Ramírez Torres, Ana María    → 3.2 segundos
✅ Mendoza Quispe, Carlos       → 5.1 segundos
⏳ López Huanca, Patricia...    → procesando
```

El tiempo estimado depende de la cantidad de candidatos y la velocidad de CTI Vitae:
- 10 candidatos: ~2–3 minutos
- 50 candidatos: ~5–8 minutos
- 100 candidatos: ~10–15 minutos

> **No cierres el navegador ni el programa mientras el proceso está en curso.**

### Paso 4 — Ver resultados

Al completarse, la pantalla mostrará automáticamente la tabla de resultados.

---

## 7. Interpretar los resultados

### La tabla de ranking

```
┌────┬──────────────────────────┬────┬────┬────┬────┬────┬────┬────┬───────┬──────┬──────────────────────────┐
│ #  │ Nombre                   │ C1 │ C2 │ C3 │ C4 │ C5 │ C6 │ C7 │ Total │  %   │ Perfil recomendado       │
├────┼──────────────────────────┼────┼────┼────┼────┼────┼────┼────┼───────┼──────┼──────────────────────────┤
│  1 │ García López, Juan C.    │ 40 │ 30 │ 30 │ 15 │ 30 │ 15 │  6 │  166  │ 83%  │ DTC                      │
│  2 │ Ramírez Torres, Ana M.   │ 50 │ 20 │ 25 │ 10 │ 40 │ 10 │  0 │  155  │ 77%  │ DOCENTE_INVESTIGADOR     │
│  3 │ Mendoza Quispe, Carlos   │ 30 │ 30 │ 20 │ 10 │ 10 │ 10 │  0 │  110  │ 55%  │ DTP                      │
│ 15 │ Flores Ríos, Beatriz     │ 15 │  0 │ 10 │  0 │  0 │  0 │  0 │   25  │ 12%  │ NO_ELEGIBLE              │
└────┴──────────────────────────┴────┴────┴────┴────┴────┴────┴────┴───────┴──────┴──────────────────────────┘
```

### ¿Qué significa cada columna?

| Columna | Descripción | Máximo |
|---------|-------------|--------|
| **#** | Posición en el ranking (1 = mejor puntuado) | — |
| **C1** | Formación académica (grado más alto obtenido) | 50 pts |
| **C2** | Experiencia docente universitaria (años) | 40 pts |
| **C3** | Experiencia profesional (nivel jerárquico) | 40 pts |
| **C4** | Centro de labores (tipo de empresa/institución) | 20 pts |
| **C5** | Producción académica (publicaciones, proyectos) | 40 pts |
| **C6** | Liderazgo profesional | 20 pts |
| **C7** | Especialización y certificaciones | 10 pts |
| **Total** | Suma de C1 a C7 | 200 pts |
| **%** | Total como porcentaje del máximo posible | 100% |

### Escala de colores

| Color | Rango | Interpretación |
|-------|-------|----------------|
| Verde | ≥ 60% (≥ 120/200) | Candidato sólido |
| Amarillo | 40% – 59% (80–119/200) | Requiere evaluación adicional |
| Rojo | < 40% (< 80/200) | Perfil débil |

### ¿Qué significa cada perfil recomendado?

| Perfil | Significado | ¿Cuándo contratar? |
|--------|-------------|-------------------|
| **DTC** | Docente a Tiempo Completo | Perfil académico consolidado, alto compromiso institucional |
| **DTP** | Docente a Tiempo Parcial | Profesional con experiencia docente, ideal para dictar cursos específicos |
| **PRACTITIONER** | Profesional practicante | Experto sectorial, ideal para cursos prácticos / casos reales |
| **DOCENTE_INVESTIGADOR** | Docente investigador | Perfil mixto, con producción científica activa |
| **DOCENTE_INVESTIGADOR_HORAS** | Investigador por horas | Investigador de alto nivel con capacidad docente |
| **PROFESIONAL_POTENCIAL** | Potencial docente | Buen perfil profesional pero poca experiencia en aula |
| **ACADEMICO_FORMACION** | Académico en formación | Buena formación teórica pero limitada experiencia |
| **ACEPTABLE** | Cumple mínimo | Cumple los criterios base; puede ingresar con reservas |
| **NO_ELEGIBLE** | No elegible | No cumple los criterios institucionales mínimos |

### Ver detalle de un candidato

Haz clic en cualquier fila de la tabla para ver:
- Desglose de puntos por cada criterio con la justificación
- Gráfico de radar con el perfil académico visual
- Datos extraídos de CTI Vitae (institución, carrera, publicaciones)

---

## 8. Descargar los reportes

Al finalizar la evaluación, aparecerán dos botones de descarga:

### Reporte Excel

Haz clic en **"Descargar Excel"** para obtener `Analisis_Detallado_YYYYMMDD_HHMMSS.xlsx`.

El archivo contiene 3 hojas:

| Hoja | Contenido |
|------|-----------|
| **Ranking General** | Todos los candidatos con puntuaciones C1–C7, total, porcentaje y perfil |
| **Clasificaciones** | Candidatos agrupados por perfil de contratación |
| **Resumen por Perfil** | Cuántos candidatos hay en cada perfil + estadísticos |

### Reporte JSON

Haz clic en **"Descargar JSON"** para obtener `clasificacion_final_YYYYMMDD_HHMMSS.json`.

Este archivo es útil para integración con otros sistemas o análisis adicional en herramientas como Power BI.

### Ubicación de los archivos

Todos los reportes generados se guardan automáticamente en:
```
bot_evaluacion_docente/resultados/
```

---

## 9. Casos especiales y situaciones comunes

### El candidato no tiene perfil CTI Vitae

Si la columna K del Excel está vacía para un candidato:
- El sistema intentará usar el PDF si existe en `Cvs/`
- Si tampoco hay PDF, el candidato tendrá datos mínimos y probablemente aparecerá como **NO_ELEGIBLE** o con puntuación baja
- Recomendación: solicitar al candidato que active su perfil en CTI Vitae

### El perfil CTI Vitae no cargó (error de extracción)

Si durante el proceso ves un mensaje como "Error al extraer datos de [nombre]":
- El sistema reintentó 3 veces automáticamente
- El candidato es evaluado solo con datos del PDF (si existe) o con datos vacíos
- El campo `fuente` en el reporte indicará `CTI_VITAE_ERROR`
- Puedes usar el botón "Analizar link individual" para reintentar solo ese candidato

### La puntuación parece incorrecta para un candidato

El sistema evalúa automáticamente con base en los datos extraídos. Las causas más comunes de discrepancia:

1. **El perfil CTI Vitae está desactualizado** — el candidato puede tener más experiencia de lo que refleja su perfil
2. **El CV en PDF no se pudo leer correctamente** — PDFs escaneados como imagen no son legibles por el sistema
3. **Palabras clave no reconocidas** — cargos o instituciones en idioma extranjero o abreviados

En estos casos, la puntuación del sistema debe ser tomada como referencia, no como decisión final.

### PDFs escaneados (imágenes)

El sistema **no puede leer PDFs que son imágenes** (escaneados sin capa de texto). Solo procesa PDFs con texto real seleccionable. En este caso:
- El sistema reportará que el PDF produjo texto vacío
- La evaluación usará solo datos de CTI Vitae
- Solicitar al candidato un CV en formato nativo (Word exportado a PDF)

### Evaluación de muchos candidatos tarda demasiado

Si tienes más de 50 candidatos y la evaluación parece haberse detenido:
1. Verifica la barra de progreso: ¿sigue avanzando aunque sea lentamente?
2. Algunos perfiles CTI Vitae son lentos por la carga del servidor CONCYTEC
3. Activa el **Modo rápido** para la próxima evaluación
4. Evalúa en lotes de 30–40 candidatos para mayor control

---

## 10. Preguntas frecuentes

**¿El sistema reemplaza la decisión del comité de selección?**
No. El sistema produce un ranking y una recomendación de perfil, pero la decisión final de contratación siempre debe ser tomada por el comité institucional, considerando factores adicionales como la entrevista, referencias y necesidades específicas de la carrera.

**¿Se guardan los datos de los candidatos?**
Sí, los resultados se guardan en archivos Excel y JSON en la carpeta `bot_evaluacion_docente/resultados/`. Estos archivos contienen datos personales (nombre, DNI) y deben tratarse con confidencialidad. Ver Sección 11.

**¿Puedo evaluar el mismo candidato dos veces?**
Sí. El sistema guarda un historial en `historial_personas.json` y actualiza el registro del candidato con la evaluación más reciente.

**¿Puedo cambiar los pesos de los criterios?**
Los pesos están definidos institucionalmente en la rúbrica y no pueden modificarse desde la interfaz. Si la rúbrica institucional cambia, el equipo de People Analytics debe actualizar el archivo `config.py` y recompilar el programa.

**¿El sistema funciona sin internet?**
Parcialmente. Sin internet, el sistema no puede consultar CTI Vitae y solo procesa los CVs en PDF que hayas cargado. Los perfiles con URL en el Excel aparecerán con error de extracción.

**¿Cuántos candidatos puedo evaluar a la vez?**
No hay un límite técnico fijo. En la práctica se ha probado con hasta 100 candidatos en una sola ejecución. Para convocatorias más grandes, se recomienda dividir en lotes.

**¿Qué pasa si cierro el navegador durante la evaluación?**
El proceso continúa ejecutándose en segundo plano. Puedes volver a abrir el navegador en `http://127.0.0.1:5000` y retomar la visualización del progreso.

**¿Qué pasa si cierro el programa .exe durante la evaluación?**
El proceso se detiene y los resultados parciales pueden no guardarse correctamente. **No cerrar el programa hasta que el proceso esté completo.**

---

## 11. Consideraciones éticas y legales

### Uso de datos personales

El sistema procesa información personal de candidatos (nombre, DNI, datos académicos y laborales). El uso de este sistema implica las siguientes responsabilidades:

1. **Consentimiento:** Los candidatos deben haber sido informados de que sus datos serán procesados de forma automatizada como parte del proceso de selección
2. **Finalidad:** Los datos deben usarse exclusivamente para el proceso de selección docente de USIL
3. **Acceso restringido:** Solo personal autorizado del área de People Analytics debe tener acceso al programa y a los reportes generados
4. **Retención:** Los archivos de resultados contienen datos sensibles y deben almacenarse en equipos institucionales seguros, no en dispositivos personales

### Transparencia en la decisión

Cuando un candidato sea notificado del resultado de su postulación, se recomienda:
- No comunicar el puntaje exacto del sistema como si fuera la única razón de la decisión
- Indicar que el proceso incluyó una evaluación de perfil académico como parte de un proceso integral
- Guardar los registros de evaluación como respaldo en caso de impugnaciones

### Limitaciones del sistema

El sistema es una **herramienta de apoyo a la decisión**, no un evaluador definitivo. Sus limitaciones incluyen:
- Solo accede a información pública disponible en CTI Vitae y PDFs provistos
- No evalúa competencias blandas, desempeño en clase o adaptación cultural
- Candidatos con perfiles CTI Vitae desactualizados pueden recibir una puntuación más baja de la real
- La lista de empresas TOP (MERCO) se actualiza una vez al año; empresas emergentes pueden no estar incluidas

> Estas limitaciones no invalidan el sistema, pero deben ser consideradas al usar sus resultados como insumo de decisión.

---

*Universidad San Ignacio de Loyola · People Analytics · 2026*
