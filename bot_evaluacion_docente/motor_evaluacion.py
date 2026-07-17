"""
Motor de Evaluación de Candidatos Docentes
==========================================
Versión 4.0 — Driven by Rúbrica (Rubrica/*.json es la única fuente de verdad)

Mejoras respecto a v3.0:
  * Puntajes y umbrales se leen de Rubrica/Criterios de evaluacion.json
    (antes estaban hardcodeados en config.py y desactualizados).
  * C4 usa las ~500 empresas de empresas_top500.json (antes: lista parcial
    de 100 que dejaba sin puntaje a muchos candidatos válidos).
  * C2 / C3 usan los diccionarios diccionario_c2_docencia.json y
    diccionario_c3_profesional.json para identificar cargos.
  * Soporta los 3 shapes de cv_data: extractor web (CTI Vitae) con
    'experiencia_docente' numérico y 'publicaciones_detalle' dict,
    extractor PDF con 'educacion' dict, y el shape legacy del test.
  * Lógica de aprobación POR PERFIL (DTC/DTP/Practitioner/Docente
    Investigador/Horas Investigación/Medicina) — antes solo se miraba
    el total y se ignoraban las additional_conditions.
  * Máximo total = 200 (50+40+40+20+50), no 170.

Contrato de salida preservado para app_web.py y main.py:
    {nombre, dni, total, maximo, porcentaje, puntuacion_total,
     clasificacion, es_elegible, tipo_perfil,
     puntajes: {C1, C2, C3, C4, C5},
     detalles: {formacion_academica, experiencia_docente,
                experiencia_profesional, centro_labores,
                produccion_academica},
     archivo, fuente, perfiles_aprobados}
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from rubrica_loader import Rubrica, cargar_rubrica, normalizar

# ─────────────────────────────────────────────────────────────────────────── #
#  Constantes y prioridades                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

# El máximo se calcula de la rúbrica (50+40+40+20+50 = 200), pero exponemos
# TOTAL_MAXIMO como atributo de módulo para mantener compatibilidad con
# `from motor_evaluacion import TOTAL_MAXIMO` en app_web.py y main.py.
try:
    TOTAL_MAXIMO = int(cargar_rubrica().total_maximo)  # 200
except Exception:
    TOTAL_MAXIMO = 200

# Cuando un candidato aprueba varios perfiles a la vez, elegimos uno
# como etiqueta principal en este orden (más específico → más genérico).
PRIORIDAD_PERFILES = [
    "DOCENTE_INVESTIGADOR",
    "HORAS_INVESTIGACION",
    "MEDICINA",
    "DTC",
    "DTP",
    "PRACTITIONER",
]

# ─────────────────────────────────────────────────────────────────────────── #
#  Helpers de extracción de evidencias                                         #
# ─────────────────────────────────────────────────────────────────────────── #

MESES_ES = {
    "enero": 1, "ene": 1, "febrero": 2, "feb": 2, "marzo": 3, "mar": 3,
    "abril": 4, "abr": 4, "mayo": 5, "junio": 6, "jun": 6, "julio": 7, "jul": 7,
    "agosto": 8, "ago": 8, "septiembre": 9, "setiembre": 9, "sep": 9, "set": 9,
    "octubre": 10, "oct": 10, "noviembre": 11, "nov": 11, "diciembre": 12, "dic": 12,
    # English months & abbreviations
    "january": 1, "jan": 1, "february": 2, "march": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "aug": 8, "september": 9,
    "october": 10, "november": 11, "december": 12, "dec": 12,
}


def _parse_fecha(texto: str) -> Optional[Tuple[int, int]]:
    """Devuelve (año, mes) a partir de un texto tipo 'Setiembre 2021',
    'Abril 2023', '09/2021' o 'A la actualidad'."""
    if not texto:
        return None
    t = normalizar(texto)
    if any(p in t for p in ("actualidad", "presente", "actual", "hoy", "a la fecha")):
        now = datetime.now()
        return (now.year, now.month)
    m_ano = re.search(r"(19\d{2}|20\d{2})", t)
    if not m_ano:
        return None
    ano = int(m_ano.group(1))
    mes = 1
    for nombre, num in sorted(MESES_ES.items(), key=lambda x: -len(x[0])):
        if nombre in t:
            mes = num
            break
    m_num = re.search(r"\b(\d{1,2})[/-](\d{4})\b", t)
    if m_num:
        mes = max(1, min(12, int(m_num.group(1))))
    return (ano, mes)


def _meses_entre(inicio: Tuple[int, int], fin: Tuple[int, int]) -> int:
    return max(0, (fin[0] - inicio[0]) * 12 + (fin[1] - inicio[1]))


def _meses_total_sin_solapes(periodos: List[Tuple[int, int, int, int]]) -> int:
    """Periodos como (ano_i, mes_i, ano_f, mes_f). Devuelve meses únicos."""
    if not periodos:
        return 0
    a_meses = lambda a, m: a * 12 + (m - 1)
    intervalos = sorted([(a_meses(ai, mi), a_meses(af, mf)) for ai, mi, af, mf in periodos])
    fusionados = [intervalos[0]]
    for ini, fin in intervalos[1:]:
        if ini <= fusionados[-1][1]:
            fusionados[-1] = (fusionados[-1][0], max(fusionados[-1][1], fin))
        else:
            fusionados.append((ini, fin))
    return sum(f - i for i, f in fusionados)


# ─────────────────────────────────────────────────────────────────────────── #
#  Motor                                                                       #
# ─────────────────────────────────────────────────────────────────────────── #

class MotorEvaluacion:
    """Motor principal de evaluación de candidatos docentes USIL.

    Cada CV es puntuado contra los 5 criterios de la rúbrica institucional,
    leyendo los puntajes, umbrales y perfiles directamente desde
    Rubrica/*.json en lugar de tablas hardcodeadas.
    """

    def __init__(self, rubrica: Optional[Rubrica] = None, **_kwargs):
        # Aceptamos **_kwargs por compatibilidad con llamadas que pasaban
        # criterios y pesos en versiones anteriores.
        self.rubrica: Rubrica = rubrica or cargar_rubrica()
        self.total_maximo: int = int(self.rubrica.total_maximo)

    # ------------------------------------------------------------------ #
    #  API pública                                                         #
    # ------------------------------------------------------------------ #
    def evaluar_multiples_cvs(self, lista_cvs: List[Dict]) -> List[Dict]:
        """Evalúa una lista de CVs y devuelve el ranking ordenado."""
        evaluaciones: List[Dict] = []
        for cv in lista_cvs:
            try:
                evaluaciones.append(self.evaluar_cv_completo(cv))
            except Exception as e:
                evaluaciones.append(self._evaluacion_error(cv, e))
        evaluaciones.sort(key=lambda x: x.get("total", 0), reverse=True)
        return evaluaciones

    def evaluar_cv_completo(self, cv_data: Dict, is_second_pass: bool = False) -> Dict:
        """Evalúa un CV y devuelve el dict con la estructura esperada por
        app_web.py / main.py / generador_reportes.py."""
        cv = self._normalizar_cv(cv_data)

        c1 = self._evaluar_c1_formacion(cv)
        c2 = self._evaluar_c2_docencia(cv)
        c3 = self._evaluar_c3_profesional(cv)
        c4 = self._evaluar_c4_centro_labores(cv)
        c5 = self._evaluar_c5_produccion(cv)

        total = c1["puntos"] + c2["puntos"] + c3["puntos"] + c4["puntos"] + c5["puntos"]
        porcentaje = round((total / self.total_maximo) * 100, 1) if self.total_maximo else 0.0

        clasificacion, es_elegible, perfiles_aprobados = self._clasificar(
            total, {"C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5}
        )

        tipo_perfil = self._inferir_tipo_perfil(cv)

        # -- LÓGICA DE RE-EVALUACIÓN CON FICHA PRACTITIONER --
        # La ficha "PRACTITIONER DOCENTE CARRERA MH.json" prioriza experiencia
        # profesional (C3 hasta 50) sobre producción académica (C5 = 20) y usa
        # un máximo de 180 pts. Es la "otra forma" que aplica a los practitioners.
        #
        # Disparador (en orden de prioridad):
        #   1) El solicitante marcó al candidato como PRACTITIONER en la hoja 2026.1
        #      (columna CATEGORIA PRACTITIONER). Esta marca MANDA.
        #   2) Respaldo heurístico: carrera de Medicina + clasificación Practitioner
        #      por puntaje (para casos sin marca explícita).
        if not is_second_pass:
            cat_pract = normalizar(cv.get("categoria_practitioner", ""))
            marcado_practitioner = "practitioner" in cat_pract

            carrera_norm = normalizar(cv.get("carrera", ""))
            es_medicina = "medicina" in carrera_norm or "medico" in carrera_norm
            es_practitioner_por_puntaje = "PRACTITIONER" in clasificacion.upper()

            usar_ficha_practitioner = marcado_practitioner or (es_practitioner_por_puntaje and es_medicina)

            if usar_ficha_practitioner:
                motivo = "marca en hoja 2026.1" if marcado_practitioner else "carrera de Medicina + puntaje"
                print(f"   [Motor] Re-evaluando a {cv.get('nombre', '')} con ficha PRACTITIONER ({motivo})...")
                from rubrica_loader import cargar_rubrica
                rubrica_practitioner = cargar_rubrica(
                    archivo_criterios="PRACTITIONER DOCENTE CARRERA MH.json",
                    archivo_empresas="empresas_top500.json",
                    archivo_dicc_c2="diccionario_c2_docencia.json",
                    archivo_dicc_c3="diccionario_c3_profesional.json"
                )
                motor_practitioner = MotorEvaluacion(rubrica=rubrica_practitioner)
                # Re-evaluar pasando is_second_pass=True para evitar recursión
                evaluacion_ficha = motor_practitioner.evaluar_cv_completo(cv_data, is_second_pass=True)

                # Etiquetar según sea médico o practitioner profesional
                if es_medicina:
                    evaluacion_ficha["clasificacion"] = "PRACTITIONER MÉDICO (Evaluación Especializada)"
                    evaluacion_ficha["tipo_perfil"] = "medico"
                else:
                    evaluacion_ficha["clasificacion"] = "PRACTITIONER (Ficha Profesional)"
                    evaluacion_ficha["tipo_perfil"] = "practitioner"

                return evaluacion_ficha
        # -- FIN LÓGICA DE RE-EVALUACIÓN --

        evaluacion = {
            "nombre": cv.get("nombre", "Sin nombre"),
            "dni": cv.get("dni", ""),
            "total": total,
            "maximo": self.total_maximo,
            "porcentaje": porcentaje,
            "puntuacion_total": total,           # alias legacy
            "clasificacion": clasificacion,
            "es_elegible": es_elegible,
            "perfiles_aprobados": perfiles_aprobados,
            "tipo_perfil": tipo_perfil,
            "puntajes": {
                "C1": c1["puntos"], "C2": c2["puntos"], "C3": c3["puntos"],
                "C4": c4["puntos"], "C5": c5["puntos"],
            },
            "detalles": {
                "formacion_academica": c1,
                "experiencia_docente": c2,
                "experiencia_profesional": c3,
                "centro_labores": c4,
                "produccion_academica": c5,
            },
            "carrera": cv.get("carrera", ""),
            "facultad": cv.get("facultad", ""),
            "tipo_candidato": cv.get("tipo_candidato", ""),
            "puesto": cv.get("puesto", ""),
            "categoria_practitioner": cv.get("categoria_practitioner", ""),
            "archivo": cv_data.get("archivo", cv_data.get("url", "")),
            "fuente": cv_data.get("fuente", "pdf"),
            "perfil_desactualizado": cv_data.get("perfil_desactualizado", False),
            "perfil_vacio": cv_data.get("perfil_vacio", False),
        }
        
        # Ejecutar módulo adicional de clasificación de perfil de talento (NO MODIFICA SCORING)
        try:
            from clasificador_talento import ClasificadorTalento
            info_talento = ClasificadorTalento.clasificar(evaluacion, cv_data)
            evaluacion.update(info_talento)
        except Exception as e:
            print(f"[!] Error al ejecutar ClasificadorTalento: {e}")
            
        return evaluacion

    # ------------------------------------------------------------------ #
    #  Normalización del cv_data (soporta los 3 shapes)                     #
    # ------------------------------------------------------------------ #
    def _normalizar_cv(self, cv: Dict) -> Dict:
        """Construye una vista uniforme del CV con campos derivados:
            texto_norm, experiencia_laboral, anos_docencia,
            educacion, publicaciones_detalle.
        """
        out = dict(cv)

        # Texto completo unificado (lower + sin acentos) para matching
        partes = [
            cv.get("texto_completo", ""),
            cv.get("texto", ""),
            str(cv.get("educacion", "")),
            str(cv.get("publicaciones_detalle", "")),
        ]
        for exp in cv.get("experiencia_laboral", []) or []:
            if isinstance(exp, dict):
                partes.extend([exp.get("institucion", ""), exp.get("cargo", "")])
            else:
                partes.append(str(exp))
        for exp in cv.get("experiencia_profesional", []) or []:
            partes.append(str(exp))
        for exp in cv.get("experiencia_docente", []) if isinstance(
                cv.get("experiencia_docente"), list) else []:
            partes.append(str(exp))
        out["texto_norm"] = normalizar(" ".join(p for p in partes if p))

        # Años de docencia: el extractor web ya devuelve un número.
        exp_doc = cv.get("experiencia_docente")
        if isinstance(exp_doc, (int, float)):
            out["anos_docencia"] = float(exp_doc)
        elif isinstance(exp_doc, list):
            out["anos_docencia"] = self._anos_docencia_desde_lista(exp_doc)
        else:
            out["anos_docencia"] = 0.0

        # Si no hay docencia explícita, intentar deducir desde experiencia_laboral
        # filtrando por cargos del diccionario C2.
        if out["anos_docencia"] == 0:
            out["anos_docencia"] = self._anos_docencia_desde_laboral(
                cv.get("experiencia_laboral", [])
            )

        # Años totales de experiencia (para C3 senior)
        out["anos_totales"] = cv.get("anos_experiencia", 0) or \
            self._anos_totales_desde_laboral(cv.get("experiencia_laboral", []))

        # Estructura uniforme de educación
        out["educacion_dict"] = self._normalizar_educacion(cv)

        # Estructura uniforme de publicaciones
        out["publicaciones_dict"] = self._normalizar_publicaciones(cv)

        return out

    @staticmethod
    def _anos_docencia_desde_lista(lista: List) -> float:
        total = 0.0
        for exp in lista:
            if isinstance(exp, dict):
                total += float(exp.get("anos", 0) or 0)
            elif isinstance(exp, str):
                m = re.search(r"(\d+(?:\.\d+)?)\s*a[nñ]os?", exp.lower())
                if m:
                    total += float(m.group(1))
        return total

    def _anos_docencia_desde_laboral(self, lista: List) -> float:
        """Si experiencia_laboral trae cargos docentes, suma sus años."""
        if not isinstance(lista, list):
            return 0.0
        periodos = []
        for exp in lista:
            if not isinstance(exp, dict):
                continue
            cargo_norm = normalizar(exp.get("cargo", ""))
            inst_norm = normalizar(exp.get("institucion", ""))
            # Nunca contar como docencia universitaria un cargo en colegio/educación
            # escolar (K-12), sin importar que el cargo diga "docente"/"tutor".
            if any(kw in inst_norm for kw in ("colegio", "institucion educativa", "i.e.")):
                continue
            es_docente = self.rubrica.es_cargo_docencia(cargo_norm) or \
                any(kw in cargo_norm for kw in (
                    "docente", "profesor", "catedratico", "instructor",
                    "tutor", "jefe de practicas", "jefe de practica",
                    "investigador", "investigadora",
                )) or \
                (("universidad" in inst_norm or "universidade" in inst_norm) and any(
                    kw in cargo_norm for kw in (
                        "docente", "profesor", "jefe", "asistente",
                        "director", "directora", "investigador", "investigadora",
                        "editor", "editora", "asesor", "asesora", "coordinador",
                        "apoyo", "encargado", "responsable",
                    )
                ))
            if not es_docente:
                continue
            ini = _parse_fecha(exp.get("fecha_inicio", ""))
            fin = _parse_fecha(exp.get("fecha_fin", ""))
            if not ini:
                continue
            if not fin:
                now = datetime.now()
                fin = (now.year, now.month)
            periodos.append((ini[0], ini[1], fin[0], fin[1]))
        meses = _meses_total_sin_solapes(periodos)
        return round(meses / 12, 2)

    @staticmethod
    def _anos_totales_desde_laboral(lista: List) -> float:
        if not isinstance(lista, list):
            return 0.0
        periodos = []
        for exp in lista:
            if not isinstance(exp, dict):
                continue
            ini = _parse_fecha(exp.get("fecha_inicio", ""))
            fin = _parse_fecha(exp.get("fecha_fin", ""))
            if not ini:
                continue
            if not fin:
                now = datetime.now()
                fin = (now.year, now.month)
            periodos.append((ini[0], ini[1], fin[0], fin[1]))
        return round(_meses_total_sin_solapes(periodos) / 12, 2)

    @staticmethod
    def _normalizar_educacion(cv: Dict) -> Dict[str, bool]:
        """Devuelve siempre {doctorado, doctorado_completo, maestria,
        maestria_completa, licenciatura} a partir de los distintos shapes."""
        out = {
            "doctorado_completo": False, "doctorado": False,
            "maestria_completa": False, "maestria": False,
            "maestria_en_curso": False, "licenciatura": False,
        }
        edu = cv.get("educacion")
        if isinstance(edu, dict):
            for k in out:
                if edu.get(k):
                    out[k] = True

        # Shape legacy: lista de strings 'formacion_academica'
        fa = cv.get("formacion_academica") or cv.get("grados_academicos") or []
        if isinstance(fa, str):
            fa = [fa]
        texto_fa = normalizar(" ".join(str(g) for g in fa)) if fa else ""

        # Texto completo para detecciones blandas
        texto = normalizar(
            (cv.get("texto_completo") or "") + " " +
            (cv.get("texto") or "") + " " + texto_fa
        )

        # El doctorado EN CURSO se evalúa primero: si el CV dice "doctorando/a"
        # o equivalente, ninguna otra mención (p.ej. "Doctor en X" de un firmante
        # de constancia) debe marcar el grado como obtenido.
        if any(kw in texto for kw in ("doctorando", "doctoranda", "doctorado en curso",
                                       "candidato a doctor", "candidata a doctor",
                                       "phd candidate", "doctorado (c)",
                                       "estudios de doctorado", "estudiante de doctorado",
                                       "egresado del doctorado", "egresada del doctorado")):
            out["doctorado"] = True
        elif any(kw in texto for kw in ("doctorado completo", "doctorado concluido",
                                         "doctor en ", "doctora en ", "phd in ",
                                         "grado de doctor", "grado academico de doctor",
                                         # English doctorate patterns
                                         "doctor of ", "dba",
                                         "doctor of business", "doctor of philosophy",
                                         "doctor of education", "doctor of science",
                                         "doctor of public", "doctor of medicine",
                                         "ed.d", "edd", "d.sc",
                                         )):
            out["doctorado"] = True
            out["doctorado_completo"] = True
        elif "doctorado" in texto or "phd" in texto or "doctorate" in texto:
            out["doctorado"] = True
            # Sin señal explícita de "completo" no asumimos C1_1.

        # ── Maestría ──
        # Primero verificar si la maestría está EN CURSO (señales que anulan "completa")
        maestria_en_curso_signals = (
            "maestria en curso", "candidato a magister", "candidata a magister",
            "cursando maestria", "cursando la maestria", "estudiante de maestria",
            "master in progress", "currently pursuing", "currently enrolled",
            "expected graduation", "expected completion",
            "en progreso", "en proceso",  # common in Spanish CVs
        )
        maestria_en_curso = any(kw in texto for kw in maestria_en_curso_signals)

        # Keywords que indican maestría COMPLETA (solo si no está en curso)
        if not maestria_en_curso and any(kw in texto for kw in (
                "maestria completa", "maestro en ", "magister en ",
                "mba", "msc", "m.sc", "master of ",
                "master of business", "master of science",
                "master of arts", "master in ",
                "master's in ", "master's degree",
                )):
            out["maestria"] = True
            out["maestria_completa"] = True
        elif maestria_en_curso:
            out["maestria"] = True
            out["maestria_en_curso"] = True
            out["maestria_completa"] = False
        elif "maestria" in texto or "magister" in texto:
            out["maestria"] = True
        elif re.search(r'\bmaster\b', texto):  # word-boundary to avoid 'mastering'
            out["maestria"] = True

        if any(kw in texto for kw in ("licenciado", "bachiller", "ingeniero",
                                       "titulo profesional", "cirujano dentista",
                                       "medico cirujano", "abogado", "contador",
                                       "arquitecto", "economista",
                                       # English equivalents
                                       "bachelor of", "bachelor's",
                                       "industrial engineer", "civil engineer",
                                       "mechanical engineer", "electrical engineer",
                                       "chemical engineer", "systems engineer",
                                       "certified public accountant", "cpa",
                                       )):
            out["licenciatura"] = True

        return out

    @staticmethod
    def _normalizar_publicaciones(cv: Dict) -> Dict:
        """Devuelve {tiene_scopus, tiene_wos, articulos_indexados, libros,
        articulos, proyectos, total} a partir de los shapes disponibles."""
        out = {
            "tiene_scopus": False, "tiene_wos": False,
            "articulos_indexados": 0, "libros": 0, "articulos": 0,
            "proyectos": 0, "total": 0,
        }
        pd = cv.get("publicaciones_detalle")
        if isinstance(pd, dict):
            for k in out:
                if k in pd:
                    out[k] = pd[k]
            # El extractor (fuente CTI Vitae) ya cuenta filas reales de la tabla
            # "Producción Científica" y sanea correctamente tiene_scopus/tiene_wos.
            # NO se vuelve a buscar "scopus"/"q1"/"q2"/etc. en el texto completo de
            # la página: ese encabezado de sección aparece en TODAS las fichas de
            # CTI Vitae aunque la tabla esté vacía, así que ese matching generaba
            # falsos positivos sistemáticos (C5=50/50 para candidatos sin ninguna
            # producción real). Cuando ya tenemos publicaciones_detalle del
            # extractor web, confiamos únicamente en esos datos estructurados.
            return out

        # Shape simple: 'publicaciones' int (fuente PDF/legacy, sin extractor web)
        if isinstance(cv.get("publicaciones"), int):
            out["total"] = max(out["total"], cv["publicaciones"])

        # Señales en texto SOLO quando no hay publicaciones_detalle estructurado
        # (p.ej. CVs en PDF sin ese campo). Aquí sí es razonable un fallback por
        # palabras clave, porque el texto viene del propio CV del candidato y no
        # de una plantilla web con encabezados fijos.
        prod = cv.get("produccion_academica") or []
        if isinstance(prod, str):
            prod = [prod]
        texto = normalizar(
            (cv.get("texto_completo") or "") + " " +
            (cv.get("texto") or "") + " " +
            " ".join(str(p) for p in prod)
        )
        if any(kw in texto for kw in ("scopus", "scopus author")):
            out["tiene_scopus"] = True
        if any(kw in texto for kw in ("web of science", " wos ", "wos.")):
            out["tiene_wos"] = True
        if any(kw in texto for kw in ("q1", "q2", "scimagojr", "scimago")):
            # Cuartil indexado implica revista indexada
            out["articulos_indexados"] = max(out["articulos_indexados"], 1)
            out["tiene_scopus"] = True

        return out

    # ------------------------------------------------------------------ #
    #  C1 - Formación Académica                                            #
    # ------------------------------------------------------------------ #
    def _evaluar_c1_formacion(self, cv: Dict) -> Dict:
        edu = cv["educacion_dict"]
        texto = cv["texto_norm"]
        max_c1 = self.rubrica.max_criterio("C1")
        
        es_elite_mundial = any(kw in texto for kw in (
            "premio nobel", "nobel prize", "nobel laureate", "doctor honoris causa"
        ))

        if edu["doctorado_completo"] or es_elite_mundial:
            cat = "C1_1"
            just = "Doctorado completo / Honoris Causa / Elite Mundial"
        elif edu["doctorado"]:
            cat = "C1_2"
            just = "Doctorado en curso / candidato a doctor"
        elif edu["maestria_completa"] or (edu["maestria"] and not edu.get("maestria_en_curso", False)):
            # En CTI Vitae 'maestria' suele venir con grado obtenido
            # (SUNEDU verifica el grado); damos C1_3 si hay maestría
            # siempre y cuando NO esté explícitamente "en curso".
            cat = "C1_3"
            just = "Maestría completa (grado de Magíster)"
        elif edu.get("maestria_en_curso", False) and edu["licenciatura"]:
            cat = "C1_4"
            just = "Título profesional / Licenciatura (Maestría en curso)"
        elif edu["licenciatura"]:
            cat = "C1_4"
            just = "Título profesional / Licenciatura"
        else:
            cat = "C1_5"
            just = "Sin formación académica detectada"
        puntos = self.rubrica.score(cat)
        return {
            "puntos": puntos,
            "maximo": max_c1,
            "categoria": cat,
            "nivel": self.rubrica.nombre_categoria(cat),
            "justificacion": just,
            "evidencia": [k for k, v in edu.items() if v],
        }

    # ------------------------------------------------------------------ #
    #  C2 - Experiencia Docente Universitaria                              #
    # ------------------------------------------------------------------ #
    def _evaluar_c2_docencia(self, cv: Dict) -> Dict:
        anos = float(cv.get("anos_docencia", 0) or 0)
        max_c2 = self.rubrica.max_criterio("C2")

        if anos >= 5:
            cat = "C2_1"
        elif anos >= 3:
            cat = "C2_2"
        elif anos >= 1:
            cat = "C2_3"
        else:
            cat = "C2_4"

        puntos = self.rubrica.score(cat)

        evidencia = []
        # Preferir las evidencias de docencia detectadas por analizador_experiencia
        for ev in (cv.get("evidencias_docencia") or [])[:5]:
            if isinstance(ev, str) and ev.strip():
                evidencia.append(ev.strip())
        # Solo mostrar experiencia laboral como evidencia si HAY docencia detectada.
        # Si anos == 0 y no hay evidencias, NO llenar con cargos laborales genéricos
        # porque confunde al usuario al mostrar texto no relacionado con docencia.
        if not evidencia and anos > 0:
            for exp in (cv.get("experiencia_laboral") or [])[:5]:
                if isinstance(exp, dict):
                    ev = f"{exp.get('cargo', '')} — {exp.get('institucion', '')}".strip(" —")
                    if ev and ev != "—":
                        evidencia.append(ev)

        return {
            "puntos": puntos,
            "maximo": max_c2,
            "categoria": cat,
            "anos_detectados": round(anos, 2),
            "nivel": self.rubrica.nombre_categoria(cat),
            "justificacion": f"{round(anos, 1)} años de docencia universitaria detectada",
            "evidencia": evidencia,
        }

    # ------------------------------------------------------------------ #
    #  C3 - Experiencia Profesional                                        #
    # ------------------------------------------------------------------ #
    # Keywords por categoría de C3 (extraídas de la rúbrica y enriquecidas
    # con vocabulario médico/educativo equivalente).
    # NB: la rúbrica define C3_1 con keywords muy genéricas
    # ("director","gerente","chief","vp","head"). Aquí las acotamos con
    # espacios para no atrapar "directorio", "rectorado", etc.
    _C3_KEYWORDS = {
        "C3_1": [  # Alta Dirección
            "chief executive", "chief financial", "chief operating",
            "chief technology", "chief information", "chief marketing",
            "chief commercial", "chief human", "chief digital",
            "vicepresidente", "vicepresidenta", "vicepresident", "vice president",
            "director ejecutivo", "directora ejecutiva", "managing director",
            "gerente general", "gerenta general",
            "decano", "decana",
            "vicerrector", "vicerrectora", "rector ", "rectora",
            "head of ", "country manager",
        ],
        # Keywords que necesitan comprobación por regex (boundary-aware)
        # para no matchear substrings como "director" dentro de "directorio"
        "C3_1_regex": [
            r"\bceo\b", r"\bcfo\b", r"\bcto\b", r"\bcoo\b", r"\bcio\b", r"\bcmo\b",
            r"\bvp\b",
            r"\bdirector(?:a)?\s+(?:de|del|general|ejecutiv|financier|comercial|administrativ|operad)",
            r"\bgerente(?:a)?\s", r"\bgerencia\s",
            r"\bdirector(?:a)?\b(?!\s*(?:io|ia|ado|atorio))",  # director but NOT directorio/directoriado
        ],
        "C3_2": [  # Mando Medio
            "jefe ", "jefa ", "jefatura", "subjefe", "sub-jefe",
            "supervisor", "supervisora",
            "coordinador", "coordinadora",
            "team lead", "lider de equipo", "lider tecnico",
            "lider de", "líder de", "lider en", "líder en",
            "responsable de", "encargado de", "encargada de",
            "investigador principal", "jefe de proyecto",
            "finance manager", "administration manager",
            "project manager", "operations manager", "service manager",
            "general manager", "agile coach", "scrum master",
        ],
        "C3_4": [  # Intermedio / Junior
            "junior", " jr.", " jr ",
            "asociado", "associate",
            "analista junior",
        ],
        "C3_5": [  # Analista / Operativo
            "analista", "analyst", "asistente ", "assistant",
            "operativo", "operative", "tecnico ", "technician",
            "practicante", "intern ", "trainee", "auxiliar",
        ],
    }

    def _evaluar_c3_profesional(self, cv: Dict) -> Dict:
        texto = cv["texto_norm"]
        anos = float(cv.get("anos_totales", 0) or 0)
        max_c3 = self.rubrica.max_criterio("C3")

        # Construir texto de cargos (más confiable que texto libre)
        cargos_norm: List[str] = []
        for exp in cv.get("experiencia_laboral") or []:
            if isinstance(exp, dict):
                cargo = normalizar(exp.get("cargo", ""))
                if cargo:
                    cargos_norm.append(cargo)
        texto_cargos = " ".join(cargos_norm)

        # Si hay cargos estructurados, las keywords de dirección/jefatura se
        # buscan SOLO ahí: en CVs documentados de 50+ páginas el texto completo
        # contiene constancias firmadas por directores/decanos/gerentes y
        # cualquier candidato terminaba en C3_1 sin haber dirigido nada.
        texto_busqueda_cargos = texto_cargos if cargos_norm else texto

        cat = None
        evidencia_match = ""
        
        es_elite_mundial = any(kw in texto for kw in (
            "premio nobel", "nobel prize", "nobel laureate", 
            "premio cervantes", "premio pulitzer", "reconocimiento mundial"
        ))

        # 1) Alta dirección o Elite Mundial
        if es_elite_mundial:
            cat = "C3_1"
            evidencia_match = "elite mundial"
            
        if cat is None:
            for kw in self._C3_KEYWORDS["C3_1"]:
                if kw in texto_busqueda_cargos:
                    cat = "C3_1"
                    evidencia_match = kw.strip()
                    break

        # 1bis) Regex-based keywords for C3_1 (boundary-aware: cfo, ceo, director etc.)
        if cat is None:
            for pattern in self._C3_KEYWORDS.get("C3_1_regex", []):
                m = re.search(pattern, texto_busqueda_cargos)
                if m:
                    cat = "C3_1"
                    # Mostrar el texto real que matcheó, no el patrón regex crudo
                    # (antes se mostraba literalmente "gerente(?:a)?\s" al usuario).
                    evidencia_match = m.group().strip()
                    break

        # 1ter) Fallback for English CVs: check FULL text for high-confidence
        # executive-level titles. These short acronyms (CFO, CEO, CTO, COO)
        # are unambiguous and never appear as false positives in constancias.
        # Also check for English management titles in full text.
        if cat is None:
            _EXECUTIVE_REGEX_FULLTEXT = [
                r"\bcfo\b", r"\bceo\b", r"\bcto\b", r"\bcoo\b", r"\bcio\b", r"\bcmo\b",
                r"\bchief\s+(?:financial|executive|operating|technology|information|marketing)\s+officer\b",
                r"\bcorporate\s+cfo\b", r"\bvice\s+president\b",
                r"\bmanaging\s+director\b", r"\bcountry\s+manager\b",
                r"\bhead\s+of\s+(?:finance|operations|administration)\b",
                r"\badministration\s+and\s+finance\s+manager\b",
            ]
            for pattern in _EXECUTIVE_REGEX_FULLTEXT:
                m = re.search(pattern, texto)
                if m:
                    cat = "C3_1"
                    evidencia_match = m.group().strip()
                    break

        # 2) Mando medio (incluye cargos del diccionario_c3_profesional)
        if cat is None:
            if self.rubrica.es_cargo_profesional(texto_cargos):
                cat = "C3_2"
                evidencia_match = "cargo de gestión (diccionario C3)"
            else:
                for kw in self._C3_KEYWORDS["C3_2"]:
                    if kw in texto_busqueda_cargos:
                        cat = "C3_2"
                        evidencia_match = kw.strip()
                        break

        # 3) Senior por años (>= 7) o expertise
        if cat is None:
            if anos >= 7:
                cat = "C3_3"
                evidencia_match = f"{anos:.0f}+ años de experiencia"
            elif any(kw in texto for kw in ("senior", " sr.", "especialista senior",
                                              "consultor senior", "arquitecto",
                                              "medico especialista", "medico staff",
                                              "medico adscrito")):
                cat = "C3_3"
                evidencia_match = "experiencia senior"

        # 4) Intermedio / Junior por años o keywords
        if cat is None:
            if 2 <= anos < 7:
                cat = "C3_4"
                evidencia_match = f"{anos:.0f} años de experiencia"
            else:
                for kw in self._C3_KEYWORDS["C3_4"]:
                    if kw in texto_cargos or kw in texto:
                        cat = "C3_4"
                        evidencia_match = kw.strip()
                        break

        # 5) Analista / Operativo
        if cat is None:
            for kw in self._C3_KEYWORDS["C3_5"]:
                if kw in texto_cargos or kw in texto:
                    cat = "C3_5"
                    evidencia_match = kw.strip()
                    break

        # 6) Sin experiencia relevante
        if cat is None:
            cat = "C3_6"
            evidencia_match = ""

        puntos = self.rubrica.score(cat)
        return {
            "puntos": puntos,
            "maximo": max_c3,
            "categoria": cat,
            "nivel": self.rubrica.nombre_categoria(cat),
            "anos_detectados": round(anos, 2),
            "justificacion": f"{self.rubrica.nombre_categoria(cat)} ({evidencia_match})".strip(" ()"),
            "evidencia": cargos_norm[:3],
        }

    # ------------------------------------------------------------------ #
    #  C4 - Centro de Labores                                              #
    # ------------------------------------------------------------------ #
    # Alias para acrónimos / nombres cortos comunes en CVs peruanos que
    # NO aparecen literalmente en empresas_top500.json (que tiene la razón
    # social completa). Mapean acrónimo → empresa formal Top 500.
    _C4_ALIAS_TOP500 = {
        "bcp": "banco de credito del peru",
        "bbva": "banco bbva peru",
        "ibk": "interbank",
        "scotia": "scotiabank",
        "ripley": "grupo ripley",
        "pucp": "pontificia universidad catolica del peru",
        "upch": "universidad peruana cayetano heredia",
        "unmsm": "universidad nacional mayor de san marcos",
        "uni": "universidad nacional de ingenieria",
        "unalm": "universidad nacional agraria la molina",
        "upn": "universidad privada del norte",
        "ucv": "universidad cesar vallejo",
        "ulima": "universidad de lima",
        "usmp": "universidad de san martin de porres",
        "utp": "universidad tecnologica del peru",
        "uladech": "universidad catolica los angeles de chimbote",
        "uap": "universidad alas peruanas",
        "ucsur": "universidad cientifica del sur",
        "urp": "universidad ricardo palma",
        "ietsi": "essalud",
        "essalud": "essalud",
        "petroperu": "petroperu",
        "antamina": "antamina",
        "yanacocha": "minera yanacocha",
    }

    _C4_KEYWORDS_MEDIANA = (
        "mediana empresa", "empresa establecida", "sector privado",
        "corporacion regional",
    )
    _C4_KEYWORDS_PEQUENA = (
        "startup", "pyme", "microempresa", "consultora propia",
        "negocio propio", "empresa pequena",
    )
    _C4_KEYWORDS_INDEP = (
        "freelance", "trabajador independiente", "consultor independiente",
        "autonomo",
    )

    def _evaluar_c4_centro_labores(self, cv: Dict) -> Dict:
        # Construir un texto que SÓLO contenga instituciones/empresas
        instituciones_norm: List[str] = []
        for exp in cv.get("experiencia_laboral") or []:
            if isinstance(exp, dict):
                inst = exp.get("institucion") or exp.get("empresa") or ""
                if inst:
                    instituciones_norm.append(normalizar(inst))
                elif not inst:
                    # Fallback: many English CVs put company name in the cargo/context field.
                    # Try to extract company names from context lines separated by ' | '
                    cargo_raw = exp.get("cargo", "")
                    if cargo_raw and "|" in cargo_raw:
                        for part in cargo_raw.split("|"):
                            part = part.strip()
                            # A company name is typically short (< 80 chars), doesn't start with bullet/verb
                            if (part and len(part) < 80 
                                and not part.startswith(('•', '-', '–', '·'))
                                and not part.lower().startswith(('managed', 'led', 'directed', 'developed',
                                    'supervised', 'implemented', 'structured', 'generated', 'maintained',
                                    'oversaw', 'coordinated', 'designed', 'created', 'established',
                                    'negotiated', 'achieved', 'reduced', 'increased', 'optimized',
                                    'education', 'additional', 'master ', 'doctor ', 'industrial',
                                    'bachelor', 'languages', 'certific', 'skills', 'professional',
                                    'executive summary'))):
                                # Check if it looks like an organization name (has capital letters, 
                                # contains S.A., Corp, LLC, Group, etc.)
                                if (any(c.isupper() for c in part[:3]) or 
                                    any(marker in part.lower() for marker in 
                                        ('s.a.', 'sac', 'corp', 'llc', 'inc', 'group', 'grupo',
                                         'peru', 'perú', 'company', 'compañia', 'compania',
                                         'universidad', 'university', 'institute', 'instituto'))):
                                    instituciones_norm.append(normalizar(part))
            elif isinstance(exp, str):
                instituciones_norm.append(normalizar(exp))
        for emp in cv.get("empresas") or []:
            instituciones_norm.append(normalizar(str(emp)))

        # Also extract company names from texto_completo if CV is in English
        # Look for patterns like "Company Name Month Year – Month Year"
        texto_raw = cv.get("texto_completo", "") or cv.get("texto", "") or ""
        if not instituciones_norm and texto_raw:
            # English CV pattern: company name on its own line or before date ranges
            company_patterns = [
                # Pattern: "Company Name S.A." or "Company Name (Group Name)"
                r'\n([A-Z][A-Za-záéíóúñÁÉÍÓÚÑ\s\.\,\(\)]+(?:S\.?A\.?C?\.?|Corp(?:oración|oration)?|Inc|LLC|Group|Grupo|S\.?R\.?L\.?))\s*\n',
                # Pattern: "Company Name" followed by bullet points on next line
                r'\n([A-Z][A-Za-záéíóúñ\s\.\,]+)\s*\n\s*[•\-–]',
            ]
            for pat in company_patterns:
                for m in re.finditer(pat, texto_raw):
                    name = m.group(1).strip()
                    if 3 < len(name) < 80:
                        instituciones_norm.append(normalizar(name))

        texto_inst = " ; ".join(instituciones_norm)
        # IMPORTANTE: si ya tenemos instituciones reales (de experiencia_laboral,
        # o del fallback de texto en inglés), buscar el empleador SOLO ahí. Antes
        # se agregaba siempre cv["texto_norm"] (texto completo de la página:
        # educación, docencia, etc.), lo que hacía que la universidad donde el
        # candidato ESTUDIÓ o DA CLASES apareciera como si fuera su empleador
        # actual (falso positivo de Centro de Labores).
        texto_busqueda = texto_inst if instituciones_norm else (texto_inst + " " + cv["texto_norm"])

        max_c4 = self.rubrica.max_criterio("C4")

        # 0) Elite Global (ej. Premio Nobel, universidades top mundiales)
        es_elite_mundial = any(kw in texto_busqueda for kw in (
            "premio nobel", "nobel prize", "nobel laureate", 
            "harvard", "princeton", "oxford", "cambridge", "stanford", "massachusetts institute of technology"
        ))
        
        if es_elite_mundial:
            return {
                "puntos": self.rubrica.score("C4_1"),
                "maximo": max_c4,
                "categoria": "C4_1",
                "nivel": "Institución de Elite Mundial",
                "empresa_detectada": "Institución Global Top",
                "justificacion": "Institución de Elite Mundial / Reconocimiento Global",
                "evidencia": instituciones_norm[:3],
            }

        # 1) Top 500 — coincidencia directa (substring normalizado)
        empresa_top = self.rubrica.es_empresa_top(texto_busqueda)

        # 1bis) Alias (acrónimos): si no hubo match directo, probar acrónimos
        # comunes (BCP→Banco de Crédito, PUCP→Pontificia U. Católica…).
        # Solo cuentan si el acrónimo aparece como TOKEN (entre delimitadores),
        # no como subcadena dentro de otra palabra.
        if not empresa_top:
            for alias, formal in self._C4_ALIAS_TOP500.items():
                # \b no funciona bien con tokens de 3 chars en algunas regex;
                # exigimos delimitador explícito.
                if re.search(rf"(^|[^a-z0-9]){re.escape(alias)}([^a-z0-9]|$)", texto_busqueda):
                    empresa_top = formal
                    break

        if empresa_top:
            return {
                "puntos": self.rubrica.score("C4_1"),
                "maximo": max_c4,
                "categoria": "C4_1",
                "nivel": "Empresa Top 500 Perú",
                "empresa_detectada": empresa_top,
                "justificacion": f"Coincide con Top 500 Perú: '{empresa_top}'",
                "evidencia": instituciones_norm[:3],
            }

        # 2) Trabajo independiente — se evalúa antes que "pequeña" para
        # que freelancers no sumen indebidamente.
        if any(kw in texto_busqueda for kw in self._C4_KEYWORDS_INDEP):
            return {
                "puntos": self.rubrica.score("C4_4"),
                "maximo": max_c4,
                "categoria": "C4_4",
                "nivel": "Trabajo independiente",
                "empresa_detectada": "",
                "justificacion": "Trabajo independiente / freelance",
                "evidencia": instituciones_norm[:3],
            }

        # 3) Empresa pequeña / startup / consultora propia
        if any(kw in texto_busqueda for kw in self._C4_KEYWORDS_PEQUENA):
            return {
                "puntos": self.rubrica.score("C4_3"),
                "maximo": max_c4,
                "categoria": "C4_3",
                "nivel": "Empresa pequeña",
                "empresa_detectada": instituciones_norm[0] if instituciones_norm else "",
                "justificacion": "Startup / pyme / consultora propia",
                "evidencia": instituciones_norm[:3],
            }

        # 4) Empresa mediana (default si tiene alguna institución reconocible
        # pero no está en Top 500). Solo damos C4_2 si HAY institución;
        # si no hay nada, damos C4_4 (0).
        if instituciones_norm:
            return {
                "puntos": self.rubrica.score("C4_2"),
                "maximo": max_c4,
                "categoria": "C4_2",
                "nivel": "Empresa mediana / sector reconocido",
                "empresa_detectada": instituciones_norm[0],
                "justificacion": f"Institución reconocida (no en Top 500): '{instituciones_norm[0]}'",
                "evidencia": instituciones_norm[:3],
            }

        return {
            "puntos": 0,
            "maximo": max_c4,
            "categoria": "C4_4",
            "nivel": "Sin centro de labores",
            "empresa_detectada": "",
            "justificacion": "No se detectó centro de labores",
            "evidencia": [],
        }

    # ------------------------------------------------------------------ #
    #  C5 - Producción Académica / Investigación                           #
    # ------------------------------------------------------------------ #
    def _evaluar_c5_produccion(self, cv: Dict) -> Dict:
        pub = cv["publicaciones_dict"]
        texto = cv["texto_norm"]
        max_c5 = self.rubrica.max_criterio("C5")

        # 1) Scopus / WoS / Elite Global — máxima categoría
        es_elite_mundial = any(kw in texto for kw in (
            "premio nobel", "nobel prize", "nobel laureate",
            "premio cervantes", "premio pulitzer", "premio pritzker"
        ))

        # IMPORTANTE: NO buscar "scopus"/"orcid"/"web of science"/etc. en el texto
        # completo de la página. CTI Vitae muestra ese encabezado de sección
        # ("Producción Científica - Scopus/WoS") en TODAS las fichas, incluso
        # cuando la tabla está vacía, así que ese matching daba falsos positivos
        # sistemáticos (C5=50/50 a candidatos sin ninguna producción real).
        # El extractor (`_extraer_publicaciones`) ya cuenta filas reales de la
        # tabla y sanea `tiene_scopus`/`tiene_wos` a False si no hay artículos
        # indexados de verdad — confiamos únicamente en esos datos estructurados.
        if es_elite_mundial or pub["tiene_scopus"] or pub["tiene_wos"] or pub["articulos_indexados"] > 0:
            just_str = "Reconocimiento Mundial Elite (ej. Premio Nobel)" if es_elite_mundial else f"Producción indexada Scopus/WoS — {pub['articulos_indexados']} artículo(s) indexado(s)"
            return self._c5_resultado(
                "C5_1", max_c5,
                just_str,
                pub
            )

        # 2) Libro o revista indexada (sin Scopus explícito)
        # Igual que en C5_1: no se busca "isbn"/"scielo"/etc. en el texto
        # completo porque son encabezados de sección presentes aunque la
        # tabla esté vacía. Solo se confía en el conteo real de libros.
        if pub["libros"] > 0:
            return self._c5_resultado(
                "C5_2", max_c5,
                f"Libro / revista indexada ({pub['libros']} libro(s))",
                pub
            )

        # 3) Investigación / proyectos
        if pub["proyectos"] > 0:
            return self._c5_resultado(
                "C5_3", max_c5,
                f"Investigación / proyectos ({pub['proyectos']} proyecto(s))",
                pub
            )

        # 4) Producción inicial (documento técnico)
        if pub["articulos"] > 0:
            return self._c5_resultado(
                "C5_4", max_c5,
                f"Producción inicial / técnica ({pub['articulos']} artículo(s))",
                pub
            )

        # 5) Sin evidencia
        return self._c5_resultado("C5_5", max_c5, "Sin producción académica detectada", pub)

    def _c5_resultado(self, cat: str, max_c5: float, just: str, pub: Dict) -> Dict:
        return {
            "puntos": self.rubrica.score(cat),
            "maximo": max_c5,
            "categoria": cat,
            "tipo": self.rubrica.nombre_categoria(cat),
            "justificacion": just,
            "evidencia": [
                f"Scopus: {pub['tiene_scopus']}",
                f"Indexados: {pub['articulos_indexados']}",
                f"Libros: {pub['libros']}",
                f"Proyectos: {pub['proyectos']}",
            ],
        }

    # ------------------------------------------------------------------ #
    #  Clasificación por perfil (lee Rubrica/Criterios de evaluacion.json) #
    # ------------------------------------------------------------------ #
    def _clasificar(self, total: float, detalles_por_crit: Dict[str, Dict]) -> Tuple[str, bool, List[str]]:
        """Determina qué perfiles aprueba el candidato y devuelve:
            (etiqueta_principal, es_elegible_en_alguno, lista_de_perfiles_aprobados)
        """
        # Regla dura: sin formación ni producción = no elegible.
        if detalles_por_crit["C1"]["puntos"] == 0 and detalles_por_crit["C5"]["puntos"] == 0:
            return ("NO_ELEGIBLE (Sin formación ni producción)", False, [])

        # Mapeo: criterio_id ('C1') → puntos. Usado por additional_conditions.
        puntos_por_crit = {cid: detalles_por_crit[cid]["puntos"] for cid in ("C1", "C2", "C3", "C4", "C5")}
        # Categoría asignada por criterio (ej: 'C5_5')
        cat_por_crit = {cid: detalles_por_crit[cid]["categoria"] for cid in ("C1", "C2", "C3", "C4", "C5")}

        aprobados: List[str] = []
        for perfil in self.rubrica.perfiles:
            if self._cumple_perfil(perfil, total, puntos_por_crit, cat_por_crit):
                aprobados.append(perfil["profile_id"])

        if not aprobados:
            # No aprueba ningún perfil — devolvemos algo informativo.
            if total < 90:
                return ("NO_CALIFICA (Puntaje insuficiente)", False, [])
            return ("NO_CALIFICA (No cumple condiciones de ningún perfil)", False, [])

        # Elegir etiqueta principal por prioridad
        principal = next((p for p in PRIORIDAD_PERFILES if p in aprobados), aprobados[0])
        nombre = next((p.get("name", p.get("profile_id", principal)) for p in self.rubrica.perfiles if p["profile_id"] == principal), principal)
        otros = [p for p in aprobados if p != principal]
        if otros:
            etiqueta = f"{nombre} (+ {', '.join(otros)})"
        else:
            etiqueta = nombre
        return (etiqueta, True, aprobados)

    @staticmethod
    def _cumple_perfil(perfil: Dict, total: float,
                         puntos_por_crit: Dict[str, float],
                         cat_por_crit: Dict[str, str]) -> bool:
        # Puntaje mínimo
        minimo = perfil.get("minimum_score", perfil.get("puntaje_minimo", 0))
        if total < minimo:
            return False

        # additional_conditions de la rúbrica
        for cond in perfil.get("additional_conditions", []):
            tipo = cond.get("type", "")

            # Tipos que exigen que CADA criterio listado tenga puntos > 0
            # (priority_balance, balanced_profile, medical_priority)
            if tipo in ("priority_balance", "balanced_profile", "medical_priority"):
                requeridos = cond.get("required_criteria", [])
                if not all(puntos_por_crit.get(c, 0) > 0 for c in requeridos):
                    return False

            # professional_priority: C3 mínimo
            elif tipo == "professional_priority":
                if puntos_por_crit.get("C3", 0) < cond.get("minimum_c3_score", 0):
                    return False

            # high_research_required: alguna de las required_categories debe
            # estar asignada en C5.
            elif tipo == "high_research_required":
                requeridas = cond.get("required_categories", [])
                if not any(cat_por_crit.get("C5") == r for r in requeridas):
                    return False

            # research_evidence_required: la categoría asignada NO debe estar
            # en forbidden_categories (típicamente C5_5).
            elif tipo == "research_evidence_required":
                prohibidas = cond.get("forbidden_categories", [])
                if cat_por_crit.get("C5") in prohibidas:
                    return False

        return True

    # ------------------------------------------------------------------ #
    #  Tipo de perfil (heurístico, usado por la UI para colorear)          #
    # ------------------------------------------------------------------ #
    def _inferir_tipo_perfil(self, cv: Dict) -> str:
        texto = cv["texto_norm"]
        score = {"clinico": 0, "investigador": 0, "industrial": 0, "docente": 0}
        if any(kw in texto for kw in ("medico", "hospital", "clinica", "essalud",
                                        "minsa", "residente", "cirujano", "cmp",
                                        "odontologo", "enfermero", "obstetra")):
            score["clinico"] += 3
        if any(kw in texto for kw in ("scopus", "wos", "concytec", "renacyt",
                                        "investigador", "phd")):
            score["investigador"] += 3
        if any(kw in texto for kw in ("ceo", "gerente general", "vicepresidente",
                                        "multinacional", "supply chain")):
            score["industrial"] += 3
        if any(kw in texto for kw in ("docente", "profesor", "catedratico",
                                        "universidad", "syllabus", "silabo")):
            score["docente"] += 2
        if max(score.values()) == 0:
            return "general"
        return max(score.items(), key=lambda x: x[1])[0]

    # ------------------------------------------------------------------ #
    #  Error fallback                                                      #
    # ------------------------------------------------------------------ #
    def _evaluacion_error(self, cv_data: Dict, e: Exception = None) -> Dict:
        """Devuelve un objeto de evaluación vacío con el error marcado."""
        import traceback
        import os
        
        log_msg = ""
        if e:
            log_msg = f"[!] Error crítico evaluando a {cv_data.get('nombre', 'Desconocido')}: {e}\n{traceback.format_exc()}\n"
            print(log_msg)
        else:
            log_msg = f"[!] Error crítico evaluando a {cv_data.get('nombre', 'Desconocido')}\n"
            print(log_msg)
            
        try:
            with open("error_log.txt", "a", encoding="utf-8") as f:
                f.write(log_msg)
        except Exception:
            pass
            
        return {
            "nombre": cv_data.get("nombre", "Sin nombre"),
            "dni": cv_data.get("dni", ""),
            "total": 0, "maximo": self.total_maximo, "porcentaje": 0.0,
            "puntuacion_total": 0,
            "clasificacion": "ERROR_EVALUACION",
            "es_elegible": False, "perfiles_aprobados": [],
            "tipo_perfil": "general",
            "puntajes": {"C1": 0, "C2": 0, "C3": 0, "C4": 0, "C5": 0},
            "detalles": {"error": str(e)},
            "archivo": cv_data.get("archivo", ""),
            "fuente": cv_data.get("fuente", "desconocida"),
        }


# ─────────────────────────────────────────────────────────────────────────── #
#  Función legacy usada por algunos puntos de entrada                          #
# ─────────────────────────────────────────────────────────────────────────── #

def ejecutar_evaluacion_completa() -> Dict:
    """Ejecuta el pipeline completo (PDF + Web). Conservada por
    compatibilidad con scripts antiguos."""
    from extractor_cvs import procesar_todos_cvs
    from extractor_web_cvs import procesar_excel_links

    cvs_pdf = procesar_todos_cvs()
    cvs_web = procesar_excel_links()
    todos = (cvs_pdf or []) + (cvs_web or [])
    if not todos:
        return {"error": "No se encontraron CVs para evaluar", "evaluaciones": []}
    motor = MotorEvaluacion()
    evals = motor.evaluar_multiples_cvs(todos)
    return {
        "total_evaluados": len(evals),
        "evaluaciones": evals,
        "elegibles": [e for e in evals if e["es_elegible"]],
        "no_elegibles": [e for e in evals if not e["es_elegible"]],
    }


if __name__ == "__main__":
    # Smoke test rápido — caso AZAÑEDO VILCHEZ DIEGO EDUARDO
    azanedo = {
        "nombre": "AZAÑEDO VILCHEZ DIEGO EDUARDO",
        "anos_experiencia": 10,
        "educacion": {
            "doctorado": False, "doctorado_completo": False,
            "maestria": True, "maestria_completa": True,
            "licenciatura": True,
        },
        "experiencia_laboral": [
            {"institucion": "UNIVERSIDAD CIENTIFICA DEL SUR S.A.C.",
             "cargo": "DOCENTE",
             "fecha_inicio": "Setiembre 2021", "fecha_fin": "Actualidad"},
            {"institucion": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
             "cargo": "PROFESOR ASISTENTE",
             "fecha_inicio": "Abril 2023", "fecha_fin": "Actualidad"},
            {"institucion": "ESSALUD - IETSI",
             "cargo": "CONSULTOR",
             "fecha_inicio": "Noviembre 2019", "fecha_fin": "Actualidad"},
            {"institucion": "UNIVERSIDAD CATOLICA LOS ANGELES DE CHIMBOTE",
             "cargo": "DIRECTOR - INSTITUTO DE INVESTIGACIÓN",
             "fecha_inicio": "Mayo 2018", "fecha_fin": "Setiembre 2018"},
            {"institucion": "UNIVERSIDAD CATOLICA LOS ANGELES DE CHIMBOTE",
             "cargo": "JEFE DE PRÁCTICAS",
             "fecha_inicio": "Setiembre 2014", "fecha_fin": "Enero 2019"},
        ],
        "experiencia_docente": 5.5,  # años acumulados de docencia
        "publicaciones_detalle": {
            "total": 60, "libros": 0, "articulos": 5,
            "articulos_indexados": 55, "proyectos": 1,
            "tiene_scopus": True, "tiene_wos": False,
        },
        "texto_completo": (
            "Scopus Author Identifier: 57188922848 RENACYT P0029701 "
            "Maestro en Estomatologia UPCH Director Instituto de Investigacion "
            "ULADECH Q1 publicaciones indexadas"
        ),
        "fuente": "CTI_VITAE",
    }
    m = MotorEvaluacion()
    r = m.evaluar_cv_completo(azanedo)
    print(f"Nombre: {r['nombre']}")
    print(f"Total: {r['total']}/{r['maximo']} ({r['porcentaje']}%)")
    print(f"Clasificación: {r['clasificacion']}")
    print(f"Perfiles aprobados: {r['perfiles_aprobados']}")
    print(f"Puntajes: {r['puntajes']}")
    for cid, d in r["detalles"].items():
        print(f"  {cid}: {d['puntos']} — {d.get('justificacion', '')}")
