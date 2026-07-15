"""
Configuración del sistema de evaluación docente
"""
import os
import sys

def get_base_dir():
    """
    Obtiene el directorio base del proyecto.
    Funciona tanto en modo desarrollo como cuando se ejecuta como .exe
    """
    # Si hay variable de entorno configurada (desde launcher.py)
    if 'EVALUACION_DOCENTE_BASE' in os.environ:
        return os.environ['EVALUACION_DOCENTE_BASE']
    
    # Si estamos ejecutando como .exe (PyInstaller)
    if getattr(sys, 'frozen', False):
        # El directorio base es donde está el .exe
        return os.path.dirname(sys.executable)
    
    # Modo desarrollo normal
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Rutas base
BASE_DIR = get_base_dir()
CVS_DIR = os.path.join(BASE_DIR, "Cvs")
RUBRICA_DIR = os.path.join(BASE_DIR, "Rubrica")
RESULTADOS_DIR = os.path.join(BASE_DIR, "bot_evaluacion_docente", "resultados")

# Carpeta LINKS con archivos de entrada
LINKS_DIR = os.path.join(BASE_DIR, "LINKS")

# Archivo principal con links CTI (columna K), nombres (columna I), DNI (columna J)
INFORMACION_VALIDACION_PATH = os.path.join(LINKS_DIR, "INFORMACION DE VALIDACION.xlsx")

# Archivo de requerimientos para match de facultades (cuando no hay en el principal)
REQUERIMIENTOS_DOCENTES_PATH = os.path.join(LINKS_DIR, "Requerimiento docentes 2026-1 300126.xlsx")

# Ruta legacy (mantener compatibilidad)
EXCEL_LINKS_PATH = INFORMACION_VALIDACION_PATH

# ─── Directorio de legajos (kit de contratación) ─────────────────────────────
# Estructura real (OneDrive):
#   OneDrive/Ingresos o Categorías - Docentes TP - Legajos/
#     BP_{BP}/Kit de Contratación/{categoria}/{COD} APELLIDOS, NOMBRES/
#       1 CV/          ← CVs principales
#       2 CREDENCIALES/  ← títulos y grados
#       3 EXPERIENCIA/DOCENTE/, /PUBLICACIONES/, /NO DOCENTE/, /INVESTIGACION/
# Búsqueda dinámica: sube desde BASE_DIR hasta encontrar la carpeta de legajos.
# Esto evita asumir una cantidad fija de niveles de directorio (portable entre equipos).
_LEGAJOS_FOLDER_NAME = "Ingresos o Categorías - Docentes TP - Legajos"

def _buscar_legajos_dir():
    """Busca la carpeta de legajos subiendo desde BASE_DIR hasta la raíz del disco."""
    carpeta = os.path.dirname(BASE_DIR)
    for _ in range(10):  # máximo 10 niveles arriba
        candidato = os.path.join(carpeta, _LEGAJOS_FOLDER_NAME)
        if os.path.isdir(candidato):
            return candidato
        padre = os.path.dirname(carpeta)
        if padre == carpeta:
            break  # llegamos a la raíz del disco
        carpeta = padre
    # Fallback: carpeta local dentro del proyecto (se crea si no existe al necesitarla)
    return os.path.join(BASE_DIR, "Legajos")

LEGAJOS_INPUT_DIR = _buscar_legajos_dir()

# Archivo de rúbrica
RUBRICA_FILE = "Ficha_Individual_Seleccion_Docente_2026-1.xlsx"
RUBRICA_PATH = os.path.join(RUBRICA_DIR, RUBRICA_FILE)

# TABLAS DE PUNTUACIÓN SEGÚN RÚBRICA INSTITUCIONAL USIL
# Basado en: Ficha de Evaluación Perfil - Selección Docente

# CRITERIO 1: FORMACIÓN ACADÉMICA (Puntaje máximo: 50)
# Escala mejorada que diferencia estudiantes de titulados
TABLA_FORMACION_ACADEMICA = {
    "doctorado_completo": 50,          # Título de doctor obtenido
    "doctorado_en_curso": 40,          # Candidato a doctor, en proceso
    "maestria_completa": 30,           # Título de magíster/maestría
    "maestria_en_curso": 25,           # Cursando maestría
    "licenciatura_titulo": 15,         # Título profesional/licenciatura
    "bachiller_egresado": 10,          # Bachiller o egresado
    "estudiante_avanzado": 5,          # Estudiante 9no-10mo ciclo
    "estudiante_inicial": 0,           # Estudiante <9no ciclo
    "no_cumple": 0
}

# Keywords que indican NO tener el grado (solo estar estudiando)
KEYWORDS_ESTUDIANTE = [
    "estudiante de", "alumno de", "cursando", "en curso",
    "candidato a", "pursuing", "student", "tesista",
    "ciclo", "semestre", "año académico"
]

# Keywords que indican grado COMPLETO
KEYWORDS_GRADO_COMPLETO = [
    "titulado", "graduado", "grado obtenido", "título obtenido",
    "egresado con título", "graduated", "degree obtained",
    "colegiado", "licenciado", "ingeniero", "doctor en", "magíster en"
]

# CRITERIO 2: EXPERIENCIA DOCENTE UNIVERSITARIA (Puntaje máximo: 40)
TABLA_EXPERIENCIA_DOCENTE = [
    {"anos_min": 10, "anos_max": 999, "puntos": 40, "descripcion": ">= 10 años"},
    {"anos_min": 6, "anos_max": 9, "puntos": 30, "descripcion": "6-9 años"},
    {"anos_min": 3, "anos_max": 5, "puntos": 20, "descripcion": "3-5 años"},
    {"anos_min": 0, "anos_max": 2, "puntos": 0, "descripcion": "Sin experiencia"}
]

# CRITERIO 3: EXPERIENCIA PROFESIONAL (Puntaje máximo: 40)
# ORDEN DE PRECEDENCIA: Alta Dirección > Mando Medio > Profesional Senior (7+ años O expertise) > Intermedio/Junior > Analista
TABLA_EXPERIENCIA_PROFESIONAL = {
    "alta_direccion_gerencia": {
        "puntos": 40, 
        "keywords": [
            "ceo", "chief executive", "director general", "gerente general",
            "director de", "gerencia general", "vicepresidente", "vicepresident",
            "director ejecutivo", "executive director", "managing director",
            # Médico / salud de alta dirección
            "director del departamento", "director del servicio",
            "director médico", "director de departamento",
            "jefe del departamento", "jefe de departamento",
            "director de la unidad", "director de unidad",
            "encargado de la direccion", "encargado de la dirección",
            "encargado de direccion",
        ]
    },
    "mando_medio": {
        "puntos": 30, 
        "keywords": [
            "jefe de", "jefatura", "subjefe", "sub-jefe",
            "supervisor", "supervisora", 
            "coordinador", "coordinadora",
            "líder de equipo", "team leader", "líder técnico",
            "responsable de", "encargado de",
            # Mando medio médico/hospitalario
            "jefe del servicio", "jefe de servicio",
            "médico jefe", "medico jefe",
            "coordinador médico", "coordinador medico",
            "médico coordinador", "medico coordinador",
            "adjunto de", "médico adjunto de", "médico de guardia jefe",
            # Investigación
            "investigador principal", "investigador titular",
            "jefe de proyecto", "lider de investigacion",
        ]
    },
    "profesional_senior": {
        "puntos": 25, 
        "keywords": [
            "senior", "sr.", "sénior",
            "experto", "expert", "especialista senior",
            "consultor senior", "senior consultant",
            "arquitecto", "architect",
            "15+ años", "10+ años", "más de 10 años",
            "amplia experiencia", "vasta experiencia",
            # Médico senior / especialista
            "médico especialista", "medico especialista",
            "especialista en", "médico staff", "medico staff",
            "médico adscrito", "medico adscrito",
            # Años de ejercicio profesional largo
            "20 años", "18 años", "15 años", "12 años",
        ],
        "anos_minimos": 7  # Criterio principal: 7+ años = automático
    },
    "intermedio_junior": {
        "puntos": 15, 
        "keywords": [
            "intermedio", "intermediate",
            "junior", "jr.",
            "asociado", "associate",
            "profesional", "professional",
            # Médico residente / en formación especializada (NO analista)
            "medico residente", "médico residente", "residente de",
            "médico interno", "medico interno",
        ],
        "anos_rango": (2, 7)  # 2-7 años
    },
    "analista_operativo": {
        "puntos": 10, 
        "keywords": [
            "analista", "analyst",
            "operativo", "operative",
            "técnico", "technician",
            # NOTA: "asistente" NO se incluye aquí para evitar confusión con
            # "médico asistente" que en Perú es categoría laboral de nivel profesional pleno
            # "asistente", "assistant",  ← eliminado intencionalmente
            "practicante", "intern",
            "trainee", "auxiliar"
        ]
    },
    "sin_experiencia": {
        "puntos": 0, 
        "keywords": []
    }
}

# CRITERIO 4: CENTRO DE LABORES (Puntaje máximo: 20)
# Empresas TOP del Perú - Basado en Ranking MERCO 2025
# Top 100 empresas con mejor reputación corporativa en Perú
EMPRESAS_TOP_PERU = [
    # Top 20 - Puntaje más alto
    "banco de crédito", "bcp", "credicorp",
    "alicorp",
    "bbva", "bbva continental",
    "ferreyros",
    "backus", "ab inbev",
    "interbank",
    "nestlé", "nestle",
    "natura", "natura cosméticos",
    "latam", "latam airlines",
    "cementos pacasmayo",
    "rimac", "rimac seguros",
    "sodimac",
    "aje", "grupo aje",
    "pacífico", "pacifico seguros",
    "gloria", "grupo gloria",
    "google",
    "saga falabella",
    "scotiabank",
    "supermercados peruanos", "plaza vea",
    
    # Top 21-50
    "belcorp",
    "entel",
    "toyota",
    "cencosud",
    "lindley", "arca continental lindley",
    "calidda",
    "claro", "américa móvil", "america movil",
    "kimberly-clark", "kimberly clark",
    "microsoft",
    "primax",
    "adidas",
    "yanbal",
    "minsur",
    "mibanco",
    "tottus",
    "unacem",
    "ripley",
    "mapfre",
    "integra", "afp integra",
    "prima afp",
    "komatsu",
    "antamina", "minera antamina",
    "ransa",
    
    # Top 51-100
    "las bambas", "minera las bambas",
    "gold fields",
    "coca-cola", "coca cola",
    "danper",
    "repsol",
    "promart",
    "yura", "cemento yura",
    "engie",
    "ibm",
    "aceros arequipa",
    "laive",
    "cerro verde", "minera cerro verde",
    "procter and gamble", "procter & gamble", "p&g",
    "pepsico",
    "quellaveco", "anglo american",
    "san fernando",
    "marriott",
    "mondelez",
    "buenaventura", "compañía de minas buenaventura",
    "santander",
    "southern", "southern copper",
    "molitalia",
    "pwc", "pricewaterhouse", "price water house coopers",
    "grupo breca", "breca",
    "marcobre",
    "hochschild",
    "ernst and young", "ey",
    "tasa",
    "yanacocha", "newmont yanacocha", "newmont",
    "camposol",
    "lap", "lima airport",
    "unilever",
    "glencore",
    "chinalco", "minera chinalco",
    "pluspetrol",
    "volcan", "volcan compañía minera",
    
    # Tecnología y Consultoría Internacional
    "amazon",
    "samsung",
    "nike",
    "mercado libre",
    "deloitte",
    "kpmg",
    "accenture",
    "oracle",
    "sap",
    "meta", "facebook",
    "cisco",

    # ─── Instituciones públicas de alta relevancia (Perú) ────────────────────
    # Salud pública nacional
    "inen", "instituto nacional de enfermedades neoplasicas", "instituto nacional de enfermedades neoplásicas",
    "essalud", "es salud", "seguro social de salud",
    "minsa", "ministerio de salud",
    "ins", "instituto nacional de salud",
    "inmp", "instituto nacional materno perinatal",
    "ingo", "instituto nacional de oftalmologia",
    "incor", "instituto nacional cardiovascular",
    "insn", "instituto nacional de salud del nino",
    "inh", "instituto nacional de higiene",
    "digesa",
    "digemid",
    # Hospitales de nivel nacional o regional de referencia
    "hospital nacional",
    "hospital rebagliati",
    "hospital almenara",
    "hospital loayza",
    "hospital arzobispo loayza",
    "hospital dos de mayo",
    "hospital cayetano heredia",
    "hospital edgardo rebagliati",
    "hospital guillermo almenara",
    "hospital victor larco herrera",
    "hospital regional",
    # Universidades reconocidas (para investigadores-docentes)
    "pontificia universidad católica", "pucp",
    "universidad peruana cayetano heredia", "upch",
    "universidad de lima",
    "universidad del pacífico",
    "universidad nacional mayor de san marcos", "unmsm",
    "universidad nacional de ingenieria", "uni",
    "universidad nacional agraria", "unalm",
    "universidad san ignacio de loyola", "usil",
    "universidad esan", "esan",
    # Gobierno y entidades reguladoras de alto nivel
    "congreso", "poder judicial",
    "ministerio",
    "pcm", "presidencia del consejo de ministros",
    "banco central de reserva", "bcrp",
    "superintendencia de banca", "sbs",
    "sunat",
    "sunafil",
    "sunedu",
    "indecopi",
    "oefa",
    "osiptel", "osinergmin",
    # Organismos internacionales
    "oms", "who",
    "ops", "paho",
    "pnud", "undp",
    "banco mundial", "world bank",
    "bid", "banco interamericano",
    "onu", "united nations", "unicef",
    "fao",
    "oit", "ilo"
]

TABLA_CENTRO_LABORES = {
    "empresa_top": {"puntos": 20, "keywords": EMPRESAS_TOP_PERU},
    "consultora_reconocida": {
        "puntos": 15,
        "keywords": [
            # Consultoras Big 4
            "pwc", "pricewaterhouse", "price water house coopers",
            "deloitte",
            "ernst and young", "ernst & young", "ey",
            "kpmg",
            # Consultoras tecnológicas
            "accenture",
            "ibm", "ibm consulting",
            "capgemini",
            "cognizant",
            "wipro",
            "tcs", "tata consultancy",
            # Consultoras estratégicas
            "mckinsey", "bain", "boston consulting", "bcg",
            # Consultoras locales reconocidas
            "apoyo consultoría", "apoyo consultoria",
            "macroconsult",
            "maximixe",
            "consultora", "consulting", "advisors"
        ]
    },
    "empresa_mediana": {
        "puntos": 15,
        "keywords": [
            "mediana empresa", "sector", "profesional adecuado",
            "nivel profesional", "empresa establecida"
        ]
    },
    "empresa_pequena": {
        "puntos": 10,
        "keywords": [
            "pequeña empresa", "startup", "pyme", "emprendimiento"
        ]
    },
    "trabajo_independiente": {
        "puntos": 0,
        "keywords": [
            "independiente", "freelance", "consultor independiente",
            "autónomo", "trabajador independiente"
        ]
    }
}

# CRITERIO 5: PRODUCCIÓN ACADÉMICA/INVESTIGACIÓN (Puntaje máximo: 40)
TABLA_PRODUCCION_ACADEMICA = {
    "libro_revista_indexada": {"puntos": 40, "keywords": ["libro", "revista indexada", "indexed journal", "editorial"]},
    "publicaciones_scopus_wos": {"puntos": 30, "keywords": ["scopus", "wos", "web of science", "q1", "q2", "scielo"]},
    "investigacion_innovacion": {"puntos": 30, "keywords": ["investigación", "innovation", "proyecto de investigación", "paper"]},
    "produccion_inicial": {"puntos": 10, "keywords": ["documento técnico", "informe", "reporte", "conference"]},
    "sin_evidencia": {"puntos": 0, "keywords": []}
}

# PESOS DE CADA CRITERIO (según rúbrica)
PESOS_CRITERIOS = {
    "formacion_academica": 30,      # C1
    "experiencia_docente": 5,        # C2
    "experiencia_profesional": 30,   # C3
    "centro_labores": 20,            # C4
    "produccion_academica": 0        # C5 (peso 0 en ejemplo)
}

# RANGOS APROBATORIOS POR TIPO DE DOCENTE
# Cada perfil tiene criterios específicos además del puntaje mínimo
RANGOS_APROBATORIOS = {
    "DTC": {
        "minimo": 110, 
        "cumple_si_no": "No",
        "descripcion": "Docente Tiempo Completo",
        "condicion_adicional": "Prioriza formación, docencia e investigación",
        "criterios_prioritarios": ["C1_Formacion_Academica", "C2_Experiencia_Docente", "C5_Produccion_Academica"],
        "requisitos": {
            "formacion_minima": 30,  # Mínimo maestría completa
            "docencia_minima": 20,   # Al menos 1-2 años docencia
            "produccion_deseable": True  # Preferible con producción
        }
    },
    "DTP": {
        "minimo": 110, 
        "cumple_si_no": "No",
        "descripcion": "Docente Tiempo Parcial",
        "condicion_adicional": "Equilibrio docencia-profesión",
        "criterios_prioritarios": ["C2_Experiencia_Docente", "C3_Experiencia_Profesional"],
        "requisitos": {
            "docencia_minima": 5,     # Al menos algo de docencia
            "profesional_minima": 15  # Experiencia profesional media
        }
    },
    "Practitioner": {
        "minimo": 90, 
        "cumple_si_no": "No",
        "descripcion": "Practitioner (Profesional que enseña)",
        "condicion_adicional": "Prioriza experiencia profesional",
        "criterios_prioritarios": ["C3_Experiencia_Profesional", "C4_Centro_Labores"],
        "requisitos": {
            "profesional_minima": 25,  # Fuerte experiencia profesional
            "centro_labores_minimo": 10  # Centro laboral reconocido
        }
    },
    "Docente_Investigador": {
        "minimo": 110, 
        "cumple_si_no": "No",
        "descripcion": "Docente Investigador",
        "condicion_adicional": "Requiere producción alta (Scopus/WoS o similar)",
        "criterios_prioritarios": ["C5_Produccion_Academica", "C1_Formacion_Academica"],
        "requisitos": {
            "produccion_minima": 30,  # Producción alta obligatoria
            "formacion_minima": 30,   # Al menos maestría
            "requiere_indexado": True  # Scopus/WoS preferido
        }
    },
    "Con_horas_investigacion": {
        "minimo": 150, 
        "cumple_si_no": "No",
        "descripcion": "Docente con Horas de Investigación",
        "condicion_adicional": "Requiere producción distinta de 'Sin evidencia'",
        "criterios_prioritarios": ["C5_Produccion_Academica", "C1_Formacion_Academica", "C2_Experiencia_Docente"],
        "requisitos": {
            "produccion_minima": 10,  # DEBE tener alguna producción (no 0)
            "formacion_minima": 40,   # Doctorado en curso o completo
            "docencia_minima": 30     # Experiencia docente significativa
        }
    }
}

# Palabras clave para identificación general
# Títulos profesionales equivalentes a licenciatura en Perú
# (incluye todas las carreras de ciencias de la salud y otras profesiones)
KEYWORDS_TITULOS_PROFESIONALES = [
    # Ciencias de la salud
    "médico cirujano", "medico cirujano", "cirujano",
    "médico especialista", "medico especialista",
    "médico asistente", "medico asistente",  # Sólo como título de grado
    "cirujano dentista", "odontólogo", "odontologo",
    "obstetra", "obstetriz",
    "enfermero", "enfermera", "licenciado en enfermería",
    "químico farmacéutico", "quimico farmaceutico",
    "nutricionista", "tecnólogo médico", "tecnologo medico",
    "psicólogo", "psicologo",
    "biólogo", "biologo",
    # Ingeniería y ciencias exactas
    "ingeniero", "arquitecto",
    # Ciencias sociales y humanidades
    "abogado", "abogada",
    "economista",
    "contador", "contadora",
    "administrador", "administradora",
    "comunicador", "periodista",
    "sociólogo", "sociologo",
    "trabajador social",
    "antropólogo", "antropologo",
    # Educación
    "licenciado en educación", "licenciada en educacion",
    "profesor de",
    # Términos genéricos
    "título profesional", "titulo profesional",
    "licenciatura", "licenciado",
    "colegiado",  # en Perú implica haber obtenido título
    "habilitado",  # CMP habilitado = médico titulado
]

KEYWORDS_EDUCACION = [
    "doctorado", "phd", "ph.d", "doctor", "doctorate",
    "maestría", "magister", "master", "mba", "m.sc", "postgrado",
    "licenciatura", "bachiller", "bachelor", "ingeniero", "licenciado"
] + KEYWORDS_TITULOS_PROFESIONALES

# Keywords que indican CONTEXTO EDUCATIVO (NO laboral)
KEYWORDS_CONTEXTO_EDUCATIVO = [
    "estudiante en", "alumno de", "alumno en",
    "curso en", "capacitación en", "certificación en",
    "campus", "programa académico", "diplomado en",
    "participante en", "asistente a curso", "becario",
    "formación en", "entrenamiento en", "taller en",
    "seminario en", "workshop en", "training en"
]

KEYWORDS_EXPERIENCIA = [
    "experiencia", "trabajo", "profesor", "docente", "catedrático",
    "investigador", "consultor", "gerente", "director", "años", "year"
]

KEYWORDS_INVESTIGACION = [
    "publicación", "publication", "paper", "artículo", "article", "investigación",
    "research", "scopus", "scielo", "wos", "patent", "patente", "conference", "congreso"
]

# ─── NUEVO: Clasificación de tipo de perfil ───────────────────────────────────
# Palabras clave para detectar el tipo de perfil dominante del candidato
PERFIL_TIPO_KEYWORDS = {
    'clinico': [
        'médico', 'medico', 'cirujano', 'medicina intensiva', 'uci',
        'unidad de cuidados', 'cuidados críticos', 'cuidados criticos',
        'oncología', 'oncologia', 'cardiología', 'cardiologia',
        'hospital', 'clínica', 'clinica', 'neumología', 'neumologia',
        'pediatría', 'pediatria', 'ginecología', 'ginecologia',
        'traumatología', 'traumatologia', 'neurología', 'neurologia',
        'gastroenterología', 'gastroenterologia', 'dermatología', 'dermatologia',
        'anestesiología', 'anestesiologia', 'radiodiagnóstico', 'radiodiagnostico',
        'emergencias', 'urgencias', 'essalud', 'minsa', 'residente',
        'médico asistente', 'medico asistente', 'médico especialista',
        'facultad de medicina', 'cmp', 'colegio médico'
    ],
    'investigador': [
        'scopus', 'wos', 'web of science', 'publicaciones indexadas',
        'investigador', 'concytec', 'proyectos de investigación',
        'proyectos de investigacion', 'q1', 'q2', 'artículo científico',
        'articulo cientifico', 'doctorado en investigación', 'phd',
        'laboratorio', 'ensayo clínico', 'ensayo clinico',
        'grupo de investigación', 'grupo de investigacion',
        'researcher', 'research', 'instituto de investigación'
    ],
    'industrial': [
        'ceo', 'gerente general', 'director general', 'vicepresidente',
        'empresa privada', 'multinacional', 'manufactura', 'producción',
        'produccion', 'planta', 'supply chain', 'cadena de suministro',
        'finanzas corporativas', 'banca', 'seguros', 'holding',
        'grupo empresarial', 'operaciones', 'logística', 'logistica'
    ],
    'docente': [
        'docente', 'profesor', 'catedrático', 'catedratico',
        'coordinador académico', 'coordinador academico',
        'decano', 'vicerrector', 'director académico', 'director academico',
        'jefe de departamento académico', 'tutor académico',
        'universidad', 'enseñanza', 'educación universitaria',
        'educacion universitaria', 'syllabi', 'sílabo'
    ]
}

# Pesos dinámicos según tipo de perfil (suman 1.0, aplicados sobre puntaje normalizado)
PESOS_POR_TIPO = {
    'clinico': {
        'C1': 0.18, 'C2': 0.12, 'C3': 0.32,
        'C4': 0.18, 'C5': 0.05,
        'C6_liderazgo': 0.08, 'C7_especializacion': 0.07
    },
    'investigador': {
        'C1': 0.25, 'C2': 0.10, 'C3': 0.15,
        'C4': 0.10, 'C5': 0.28,
        'C6_liderazgo': 0.06, 'C7_especializacion': 0.06
    },
    'industrial': {
        'C1': 0.18, 'C2': 0.08, 'C3': 0.38,
        'C4': 0.22, 'C5': 0.05,
        'C6_liderazgo': 0.06, 'C7_especializacion': 0.03
    },
    'docente': {
        'C1': 0.22, 'C2': 0.30, 'C3': 0.18,
        'C4': 0.10, 'C5': 0.10,
        'C6_liderazgo': 0.06, 'C7_especializacion': 0.04
    },
    'general': {
        'C1': 0.20, 'C2': 0.15, 'C3': 0.25,
        'C4': 0.15, 'C5': 0.10,
        'C6_liderazgo': 0.10, 'C7_especializacion': 0.05
    }
}

# ─── CRITERIO 6: LIDERAZGO PROFESIONAL (Máximo: 20 puntos) ────────────────────
# Detecta roles de liderazgo / dirección en cualquier sector
TABLA_LIDERAZGO = {
    'liderazgo_alto': {
        'puntos': 20,
        'keywords': [
            # Dirección médica y hospitalaria
            'director médico', 'director medico',
            'director del departamento', 'director de departamento',
            'director del servicio', 'director de servicio',
            'director de la unidad', 'director de unidad',
            'jefe del departamento', 'jefe de departamento',
            'jefe de la unidad', 'jefe de unidad',
            'jefe del servicio médico', 'jefe de servicio médico',
            'jefe medico', 'jefe médico',
            # Dirección general / alta gerencia
            'director general', 'gerente general', 'ceo',
            'chief executive', 'vicepresidente', 'director ejecutivo',
            'managing director', 'decano', 'vicerrector', 'rector'
        ]
    },
    'liderazgo_medio': {
        'puntos': 15,
        'keywords': [
            # Jefaturas y coordinaciones hospitalarias
            'jefe de servicio', 'jefe de guardia',
            'médico jefe', 'medico jefe',
            'coordinador médico', 'coordinador medico',
            'médico coordinador', 'medico coordinador',
            'jefe de', 'jefatura de',
            'médico encargado', 'médico a cargo',
            # Gestión media empresarial
            'gerente de', 'subgerente',
            'director de', 'subdirector',
            'coordinador de', 'supervisor de',
            'responsable de área', 'responsable de area',
            'líder de equipo', 'lider de equipo', 'team lead',
            # Académico
            'coordinador académico', 'coordinador academico',
            'director académico', 'director academico',
            'director de carrera', 'jefe de departamento académico'
        ]
    },
    'liderazgo_basico': {
        'puntos': 10,
        'keywords': [
            'supervisor', 'supervisora',
            'encargado de', 'encargada de',
            'responsable de', 'líder', 'lider',
            'investigador principal', 'jefe de proyecto',
            'médico adjunto', 'medico adjunto'
        ]
    }
}

# ─── CRITERIO 7: ESPECIALIZACIÓN / EXPERTISE (Máximo: 10 puntos) ─────────────
# Detecta especialidades de alto valor clínico, técnico o de investigación
TABLA_ESPECIALIZACION = {
    'especializacion_alta': {
        'puntos': 10,
        'keywords': [
            # Especialidades médicas de alta complejidad
            'medicina intensiva', 'cuidados intensivos', 'cuidados críticos', 'cuidados criticos',
            'uci', 'ucin', 'utip', 'unidad de cuidados intensivos',
            'oncología clínica', 'oncologia clinica', 'oncología médica', 'oncologia medica',
            'hematología', 'hematologia', 'trasplante', 'trasplante de médula',
            'cardiología intervencionista', 'cardiologia intervencionista',
            'cirugía cardiovascular', 'cirugia cardiovascular',
            'neurocirugía', 'neurocirugia', 'neurocirugía pediátrica',
            'medicina fetal', 'fetomaternal',
            'radiooncología', 'radio oncologia',
            # Certificaciones y reconocimientos de alto impacto
            'board certified', 'fellow', 'fellowship',
            'certificación internacional', 'certificacion internacional',
            'especialidad con sub-especialidad', 'subespecialidad'
        ]
    },
    'especializacion_media': {
        'puntos': 6,
        'keywords': [
            # Especialidades médicas reconocidas
            'cardiología', 'cardiologia', 'neumología', 'neumologia',
            'gastroenterología', 'gastroenterologia',
            'endocrinología', 'endocrinologia', 'reumatología', 'reumatologia',
            'nefrología', 'nefrologia', 'infectología', 'infectologia',
            'geriatría', 'geriatria', 'medicina interna',
            # Especializaciones en otros campos
            'especialista en', 'experto en', 'certificado en',
            'maestría especializada', 'maestria especializada',
            'posdoctorado', 'postdoctorado',
            # Investigación especializada
            'investigador concytec', 'investigador renacyt',
            'nivel i renacyt', 'nivel ii renacyt'
        ]
    },
    'especializacion_basica': {
        'puntos': 3,
        'keywords': [
            'especialización en', 'especializacion en',
            'diplomado en', 'curso de especialización',
            'segunda especialidad', 'especialidad médica', 'especialidad medica',
            'residencia médica', 'residencia medica',
            'residente de', 'posgrado en', 'postgrado en'
        ]
    }
}

# ─── Instituciones de salud de alta complejidad (bonus C4) ───────────────────
# Cuando se detectan estas en el centro de labores, se garantiza puntuación máxima C4
INSTITUCIONES_ALTA_COMPLEJIDAD_SALUD = [
    'inen', 'instituto nacional de enfermedades neoplásicas', 'instituto nacional de enfermedades neoplasicas',
    'incor', 'instituto nacional cardiovascular',
    'insn', 'instituto nacional de salud del niño', 'instituto nacional de salud del nino',
    'inmp', 'instituto nacional materno perinatal',
    'ingo', 'instituto nacional de oftalmología', 'instituto nacional de oftalmologia',
    'inh', 'instituto nacional de higiene',
    'ins', 'instituto nacional de salud',
    'hospital rebagliati', 'edgardo rebagliati',
    'hospital almenara', 'guillermo almenara',
    'hospital loayza', 'arzobispo loayza',
    'hospital dos de mayo',
    'hospital cayetano heredia',
    'hospital victor larco herrera',
    'hospital de emergencias jose casimiro ulloa',
    'hospital nacional',
    'essalud', 'seguro social de salud',
    'minsa', 'ministerio de salud',
    'hospital militar central',
    'hospital naval',
    'hospital regional',
    'hospital base',
    'clínica anglo americana', 'clinica anglo americana',
    'clínica san pablo', 'clinica san pablo',
    'clínica internacional', 'clinica internacional',
    'clínica ricardo palma', 'clinica ricardo palma',
    'clínica delgado', 'clinica delgado',
    'clínica universitaria', 'clinica universitaria'
]

# Crear directorio de resultados si no existe
os.makedirs(RESULTADOS_DIR, exist_ok=True)
