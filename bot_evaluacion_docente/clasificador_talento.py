"""
Clasificador de Talento v2.0 — Sistema de Pesos por Señal
==========================================================
Ejecutar DESPUÉS del motor de scoring. No modifica puntajes.

Genera tres ejes de análisis:
  - dominio:    Área de conocimiento (Salud, Ingeniería, Negocios...)
  - talento:    Rol dominante (Investigador Elite, Gestor Académico...)
  - subtalento: Rol secundario
  - nivel:      Basado en puntaje total (A+, A, B, C, D)
"""
import re
import os
import json

REQUERIMIENTOS_CACHE = None

def _cargar_requerimientos():
    global REQUERIMIENTOS_CACHE
    if REQUERIMIENTOS_CACHE is None:
        try:
            ruta = os.path.join(os.path.dirname(__file__), "requerimientos_2026.json")
            with open(ruta, "r", encoding="utf-8") as f:
                REQUERIMIENTOS_CACHE = json.load(f)
        except Exception:
            REQUERIMIENTOS_CACHE = []
    return REQUERIMIENTOS_CACHE

# TABLA DE SEÑALES Y PESOS
# Cada señal aporta puntos a uno o más roles.
# El rol con más puntos acumulados gana.
# ─────────────────────────────────────────────────────────────────────────────
SENALES_ROL = [
    # ─── GESTOR ACADÉMICO ───────────────────────────────────────────────────
    (r'\brector\b',                     {"Gestor Académico": 100}),
    (r'\bvicerrector\b',                {"Gestor Académico": 90}),
    (r'\bdecano\b',                     {"Gestor Académico": 70}),
    (r'\bdirector (académico|academico|universitario|de escuela|de departamento|de instituto)\b',
                                        {"Gestor Académico": 60}),
    (r'\bcoordinador (académico|de carrera|de programa)\b',
                                        {"Gestor Académico": 30}),

    # ─── INVESTIGADOR ELITE ─────────────────────────────────────────────────
    (r'\bpremio nobel\b|\bnobel prize\b|\bnobel laureate\b|\bpremio pulitzer\b|\bpremio cervantes\b', 
                                        {"Investigador Elite": 200, "Practitioner Elite": 200, "Gestor Académico": 100}),
    (r'\bscopus\b',                     {"Investigador Elite": 50, "Investigador Senior": 30}),
    (r'\bweb of science\b|\bwos\b',     {"Investigador Elite": 50, "Investigador Senior": 30}),
    (r'\bq1\b',                         {"Investigador Elite": 40}),
    (r'\bq2\b',                         {"Investigador Elite": 30, "Investigador Senior": 20}),
    (r'\bfinanciamiento competitivo\b',  {"Investigador Elite": 35}),
    (r'\bproyecto internacional\b|\binternacional de investigaci[oó]n\b',
                                        {"Investigador Elite": 35}),
    (r'\brenacyt\b',                    {"Investigador Elite": 30, "Investigador Senior": 25}),
    (r'\binvestigador principal\b',     {"Investigador Elite": 25}),

    # ─── INVESTIGADOR SENIOR ────────────────────────────────────────────────
    (r'\bpublicaci[oó]n indexada\b|\bartículo indexado\b',
                                        {"Investigador Senior": 20}),
    (r'\brevisor de revista\b|\bpeer review\b',
                                        {"Investigador Senior": 15}),
    (r'\binvestigador\b',               {"Investigador Senior": 10, "Docente Investigador": 8}),

    # ─── DOCENTE INVESTIGADOR ───────────────────────────────────────────────
    (r'\bjefe de pr[aá]cticas\b',       {"Docente Investigador": 10, "Docente Profesional": 5}),
    (r'\bdocente investigador\b|\bprofesor investigador\b',
                                        {"Docente Investigador": 30}),
    (r'\bdocente\b|\bprofesor\b|\bcatedrático\b',
                                        {"Docente Investigador": 5, "Docente Profesional": 5}),

    # ─── PRACTITIONER ELITE ─────────────────────────────────────────────────
    (r'\bceo\b|\bchief executive\b',    {"Practitioner Elite": 100}),
    (r'\bfounder\b|\bcofundador\b|\bco-fundador\b',
                                        {"Practitioner Elite": 80}),
    (r'\bgerente general\b',            {"Practitioner Elite": 80}),
    (r'\bcountry manager\b',            {"Practitioner Elite": 70}),
    (r'\bvicepresidente\b|\bvp\b(?! \w)',{"Practitioner Elite": 65}),
    (r'\bchief\b',                      {"Practitioner Elite": 50}),
    (r'\bdirector corporativo\b|\bdirector comercial\b|\bdirector de operaciones\b',
                                        {"Practitioner Elite": 45}),
    (r'\bgerente\b',                    {"Practitioner Elite": 25}),

    # ─── CONSULTOR EXPERTO ──────────────────────────────────────────────────
    (r'\bconsultor\b',                  {"Consultor Experto": 30}),
    (r'\basesor\b',                     {"Consultor Experto": 20}),
    (r'\bevaluador\b',                  {"Consultor Experto": 15}),
    (r'\bespecialista\b',               {"Consultor Experto": 10}),

    # ─── CLÍNICO ────────────────────────────────────────────────────────────
    (r'\btutor cl[ií]nico\b|\bresidencia\b|\bcoordinador de residencia\b',
                                        {"Clínico": 40}),
    (r'\bmédico asistencial\b|\bm[eé]dico de planta\b',
                                        {"Clínico": 35}),
    (r'\bcirujano\b|\bmedico cirujano\b',{"Clínico": 30}),
    (r'\bservicio de guardia\b|\bhospital\b|\bclínica\b|\bcentro de salud\b',
                                        {"Clínico": 20}),
    (r'\bneurólogo\b|\bcardiólogo\b|\boncólogo\b|\bpediatra\b|\bginecólogo\b',
                                        {"Clínico": 25}),
]

# ─────────────────────────────────────────────────────────────────────────────
# DOMINIOS DE CONOCIMIENTO
# ─────────────────────────────────────────────────────────────────────────────
DOMINIOS = [
    ("Salud",               [r'\bmedicina\b', r'\bsalud\b', r'\benfermería\b', r'\bnutrición\b',
                             r'\bfarmacia\b', r'\bodontología\b', r'\bpsicolog[ií]a cl[ií]nica\b',
                             r'\bveterinaria\b', r'\bfisioterap\b', r'\bepidemiolog\b',
                             r'\bsalud p[úu]blica\b']),
    ("Ingeniería",          [r'\bingeniería?\b', r'\bingeniero\b', r'\bsistemas\b',
                             r'\belectrónica\b', r'\bcivil\b', r'\bindustrial\b',
                             r'\bmecánica\b', r'\btelecomunicaciones\b', r'\binformática\b']),
    ("Negocios",            [r'\badministración\b', r'\bnegocios\b', r'\bmba\b',
                             r'\bmarketing\b', r'\bfinanzas\b', r'\bcontabilidad\b',
                             r'\beconom[ií]a\b', r'\bcomercio\b', r'\bgestión\b']),
    ("Derecho",             [r'\bderecho\b', r'\bjur[ií]dico\b', r'\babogado\b',
                             r'\bjudicial\b', r'\bnotarial\b']),
    ("Educación",           [r'\beducación\b', r'\bpedagog[ií]a\b', r'\bdidáctica\b',
                             r'\bcurrículum\b', r'\bdocencia\b']),
    ("Ciencias Exactas",    [r'\bfísica\b', r'\bquímica\b', r'\bmatem[aá]tica\b',
                             r'\bbiolog[ií]a\b', r'\bbioquímica\b', r'\bgenética\b']),
    ("Ciencias Sociales",   [r'\bsociolog[ií]a\b', r'\bpsicologa?\b', r'\bantropolog[ií]a\b',
                             r'\bcomunicaciones\b', r'\btraba(?:jo|jadora?) social\b',
                             r'\bcriminolog[ií]a\b']),
    ("Arte y Humanidades",  [r'\barte\b', r'\bhistoria\b', r'\bfilosofía\b',
                             r'\blingüística\b', r'\bliteratura\b', r'\barqueología\b']),
]

PRIORIDAD_ROL = [
    "Investigador Elite",
    "Gestor Académico",
    "Practitioner Elite",
    "Investigador Senior",
    "Docente Investigador",
    "Consultor Experto",
    "Clínico",
    "Docente Profesional",
]


class ClasificadorTalento:

    @staticmethod
    def _recomendar_puesto(texto_cv, dominio, nivel, perfil_dominante):
        reqs = _cargar_requerimientos()
        if not reqs:
            return "", "", ""
            
        # Asignar un score a cada requerimiento
        mejor_req = None
        max_score = 0
        
        # Mapeo simple de dominio a facultades comunes para dar boost
        mapa_dominio = {
            "Salud": ["CC SALUD"],
            "Ingeniería": ["ING"],
            "Negocios": ["CC EMP", "FHTG", "CPEL"],
            "Derecho": ["DERECHO"],
            "Arte y Humanidades": ["ARTES Y HUM", "CLS"],
            "Educación": ["EMPRENDIM", "ARTES Y HUM"]
        }
        
        for req in reqs:
            score = 0
            carrera_req = req["carrera"].lower()
            cursos_req = req["cursos"].lower()
            facultad_req = req["facultad"]
            
            # Boost por dominio
            if facultad_req in mapa_dominio.get(dominio, []):
                score += 10
                
            # Match carrera exacta o subcadena en el CV
            if carrera_req in texto_cv:
                score += 20
                
            # Match de cursos (palabras clave)
            cursos_tokens = [c.strip() for c in cursos_req.replace(",", " ").replace(";", " ").split() if len(c) > 4]
            for token in set(cursos_tokens):
                if token in texto_cv:
                    score += 5
                    
            # Boost por perfil
            if "investigador" in perfil_dominante.lower() and "TC" in req["puesto"]:
                score += 10
                
            if score > max_score:
                max_score = score
                mejor_req = req
                
        if mejor_req and max_score > 0:
            return mejor_req["facultad"], mejor_req["carrera"], mejor_req["cursos"]
        return "", "", ""

    @staticmethod
    def clasificar(evaluacion: dict, cv_data: dict) -> dict:
        puntaje_total = evaluacion.get('total', evaluacion.get('puntuacion_total', 0))
        puntajes = evaluacion.get('puntajes', {})

        # ── Nivel de Talento ─────────────────────────────────────────────────
        if puntaje_total >= 180:
            nivel = "A+"
        elif puntaje_total >= 160:
            nivel = "A"
        elif puntaje_total >= 130:
            nivel = "B"
        elif puntaje_total >= 110:
            nivel = "C"
        elif puntaje_total >= 90:
            nivel = "D"
        else:
            nivel = "E"

        # ── Texto completo para búsqueda ──────────────────────────────────────
        texto_cv = (
            cv_data.get('texto_completo', '') + ' ' +
            cv_data.get('texto_combinado', '') + ' ' +
            cv_data.get('texto_norm', '')
        ).lower()

        # Agregar cargos de experiencia laboral si están disponibles
        for exp in cv_data.get('experiencia_laboral', []) or []:
            if isinstance(exp, dict):
                texto_cv += ' ' + exp.get('cargo', '').lower()
                texto_cv += ' ' + exp.get('institucion', '').lower()

        # ── Puntajes de scoring para reforzar señales ─────────────────────────
        c2 = puntajes.get('C2', 0)
        c3 = puntajes.get('C3', 0)
        c5 = puntajes.get('C5', 0)

        # ── Calcular scores por rol usando señales ponderadas ─────────────────
        scores_rol: dict = {}
        for patron, pesos in SENALES_ROL:
            if re.search(patron, texto_cv):
                for rol, peso in pesos.items():
                    scores_rol[rol] = scores_rol.get(rol, 0) + peso

        # ── Reforzar con puntajes del motor ──────────────────────────────────
        if c5 >= 45:
            scores_rol["Investigador Elite"] = scores_rol.get("Investigador Elite", 0) + 25
            scores_rol["Investigador Senior"] = scores_rol.get("Investigador Senior", 0) + 20
        if c2 >= 30 and c5 >= 30:
            scores_rol["Docente Investigador"] = scores_rol.get("Docente Investigador", 0) + 30
        if c2 >= 30 and c3 >= 25 and c5 < 30:
            scores_rol["Docente Profesional"] = scores_rol.get("Docente Profesional", 0) + 35
        if c3 >= 35 and c5 < 20:
            scores_rol["Practitioner Elite"] = scores_rol.get("Practitioner Elite", 0) + 15
            scores_rol["Consultor Experto"] = scores_rol.get("Consultor Experto", 0) + 10

        # ── Si no hay señales, asignar perfil base ────────────────────────────
        if not scores_rol:
            scores_rol["Docente Profesional"] = 10

        # ── Ordenar por score, luego por prioridad como desempate ─────────────
        roles_ordenados = sorted(
            scores_rol.items(),
            key=lambda x: (x[1], -PRIORIDAD_ROL.index(x[0]) if x[0] in PRIORIDAD_ROL else -99),
            reverse=True
        )

        perfil_dominante = roles_ordenados[0][0]
        perfil_secundario = roles_ordenados[1][0] if len(roles_ordenados) > 1 else ""

        # ── Detectar Dominio de Conocimiento ─────────────────────────────────
        # IMPORTANTE: no usar texto_cv (texto completo de la página web) para
        # esto. CTI Vitae muestra tablas de clasificación OCDE con encabezados
        # como "Temática Médica y de la Salud" en TODAS las fichas sin importar
        # la carrera real del candidato, lo que etiquetaba a cualquiera (ej. un
        # ingeniero de sistemas) como "especialista en Salud" por accidente.
        # Se usa solo el título/carrera real (educación) y los cargos/institución
        # de su experiencia laboral real.
        texto_dominio_parts = list(cv_data.get('educacion', {}).get('titulos_texto', []) or [])
        for exp in cv_data.get('experiencia_laboral', []) or []:
            if isinstance(exp, dict):
                texto_dominio_parts.append(exp.get('cargo', ''))
                texto_dominio_parts.append(exp.get('institucion', ''))
        texto_dominio = ' '.join(texto_dominio_parts).lower()

        dominio = "General"
        for nombre_dominio, patrones in DOMINIOS:
            for patron in patrones:
                if re.search(patron, texto_dominio):
                    dominio = nombre_dominio
                    break
            if dominio != "General":
                break

        # ── Justificación legible ─────────────────────────────────────────────
        top_senales = [rol for rol, _ in roles_ordenados[:3]]
        scores_str = ", ".join(f"{rol}: {sc}pts" for rol, sc in roles_ordenados[:3])
        justificacion = (
            f"Sistema de pesos: {scores_str}. "
            f"Rol dominante asignado por mayor acumulación de señales en el texto del perfil."
        )

        # ── Recomendación de Puesto (Filtro Funcional) ─────────────────────────
        fac_rec, car_rec, cur_rec = ClasificadorTalento._recomendar_puesto(texto_cv, dominio, nivel, perfil_dominante)
        
        etiqueta_reclutamiento = f"Profesor para {car_rec}" if car_rec else "Profesor General"
        if perfil_dominante:
            etiqueta_reclutamiento += f" con perfil de {perfil_dominante}"
        if dominio != "General":
            etiqueta_reclutamiento += f", especialista en {dominio}"

        return {
            "nivel": nivel,
            "dominio": dominio,
            "perfil_dominante": perfil_dominante,
            "perfil_secundario": perfil_secundario,
            "justificacion_perfil": justificacion,
            "facultad_recomendada": fac_rec,
            "carrera_recomendada": car_rec,
            "cursos_recomendados": cur_rec,
            "etiqueta_reclutamiento": etiqueta_reclutamiento,
            "_scores_debug": dict(roles_ordenados[:5]),  # debug interno
        }
