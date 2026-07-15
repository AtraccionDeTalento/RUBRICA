"""
Analizador de experiencia laboral/docente desde texto plano de CVs en PDF.

Problema que resuelve: los CVs documentados (50+ páginas) declaran la docencia
con rangos de fechas en formatos muy variados ("DEL 2013-01 AL 2024-02",
"Marzo 2012 - Diciembre 2012", "ENERO 2010 A DICIEMBRE 2022", "2016-2019",
"desde 2018 a la actualidad"...) y el sistema solo detectaba la frase literal
"X años de experiencia docente". Este módulo extrae periodos estructurados,
los clasifica como docencia/no docencia por contexto y calcula años sin
solapamientos.

Uso:
    from analizador_experiencia import analizar_experiencia_texto
    res = analizar_experiencia_texto(texto_cv)
    res["anos_docencia"]        -> float
    res["anos_totales"]         -> float
    res["experiencia_laboral"]  -> [{cargo, institucion, fecha_inicio, fecha_fin, anos}]
    res["evidencias_docencia"]  -> [str]
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ───────────────────────── meses ─────────────────────────
_MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
    'noviembre': 11, 'diciembre': 12,
    # English months (full)
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11,
    'december': 12,
    # English months (abbreviated)
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}
# Sin \b inicial a propósito: en PDFs el texto suele venir pegado
# ("VIDAENERO 2010") y el nombre del mes queda adherido a la palabra anterior.
_RX_MES = '|'.join(sorted(_MESES.keys(), key=len, reverse=True))

_RX_ACTUAL = r'(?:la\s+|el\s+)?(?:actualidad|presente|present|actual(?:mente)?|a\s+la\s+fecha|hoy|vigente|today)'
_SEP = r'\s*(?:[-–—]|al?\b|hasta)\s*'

_ANO_MIN = 1970


def _normalizar(s: str) -> str:
    s = s.lower()
    for a, b in zip('áéíóúñü', 'aeiounu'):
        s = s.replace(a, b)
    return s


def _ano_valido(a: int) -> bool:
    return _ANO_MIN <= a <= datetime.now().year + 1


def _ciclo_a_mes(ciclo: str) -> int:
    """'01'/'I'/'1' -> marzo (inicio ciclo 1); '02'/'II'/'2' -> agosto."""
    c = ciclo.strip().upper()
    return 3 if c in ('01', '1', 'I') else 8


def _ahora() -> Tuple[int, int]:
    now = datetime.now()
    return (now.year, now.month)


# Cada patrón devuelve (ini, fin) como tuplas (año, mes) o None si no aplica.
def _extraer_periodos_linea(linea: str) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    t = _normalizar(linea)
    periodos = []
    consumido = []  # spans ya usados, para no contar dos veces el mismo rango

    def _libre(m):
        return not any(i < m.end() and m.start() < f for i, f in consumido)

    def _agregar(m, ini, fin):
        if ini and fin and _ano_valido(ini[0]) and _ano_valido(fin[0]):
            ini_m, fin_m = ini[0] * 12 + ini[1], fin[0] * 12 + fin[1]
            # rango razonable: positivo y menor a 45 años
            if 0 <= fin_m - ini_m <= 45 * 12:
                periodos.append((ini, fin))
                consumido.append((m.start(), m.end()))

    # 1) ciclo académico: "2013-01 al 2024-02", "2015-I al 2017-II"
    for m in re.finditer(
            r'(\d{4})\s*-\s*(0?[12]|i{1,2})\s*(?:[-–—]|\bal?\b|\bhasta\b)\s*(\d{4})\s*-\s*(0?[12]|i{1,2})\b',
            t):
        if _libre(m):
            _agregar(m, (int(m.group(1)), _ciclo_a_mes(m.group(2))),
                     (int(m.group(3)), _ciclo_a_mes(m.group(4)) + 4))

    # 2) "mes [de[l]] año <sep> mes [de[l]] año" (admite día delante)
    rx2 = re.compile(
        r'(?:\d{1,2}\s*(?:de\s+)?)?(' + _RX_MES + r')\s*(?:de[l]?\s+)?(\d{4})'
        + _SEP +
        r'(?:\d{1,2}\s*(?:de\s+)?)?(' + _RX_MES + r')\s*(?:de[l]?\s+)?(\d{4})')
    for m in rx2.finditer(t):
        if _libre(m):
            _agregar(m, (int(m.group(2)), _MESES[m.group(1)]),
                     (int(m.group(4)), _MESES[m.group(3)]))

    # 3) "dia de mes al dia de mes año" (un solo año: "29 de mayo al 29 de octubre 2025")
    rx3 = re.compile(
        r'\d{1,2}\s*(?:de\s+)?(' + _RX_MES + r')\s*(?:de[l]?\s+)?'
        + _SEP +
        r'\d{1,2}\s*(?:de\s+)?(' + _RX_MES + r')\s*(?:de[l]?\s+)?(?:de[l]?\s+)?(\d{4})')
    for m in rx3.finditer(t):
        if _libre(m):
            ano = int(m.group(3))
            _agregar(m, (ano, _MESES[m.group(1)]), (ano, _MESES[m.group(2)]))

    # 4) "mes año <sep> actualidad"
    rx4 = re.compile(
        r'(?:\d{1,2}\s*(?:de\s+)?)?(' + _RX_MES + r')\s*(?:de[l]?\s+)?(\d{4})'
        + _SEP + _RX_ACTUAL)
    for m in rx4.finditer(t):
        if _libre(m):
            _agregar(m, (int(m.group(2)), _MESES[m.group(1)]), _ahora())

    # 5) "mm/aaaa <sep> mm/aaaa|actualidad"
    rx5 = re.compile(
        r'\b(\d{1,2})[/.](\d{4})' + _SEP + r'(?:(\d{1,2})[/.](\d{4})|' + _RX_ACTUAL + r')')
    for m in rx5.finditer(t):
        if _libre(m):
            ini = (int(m.group(2)), max(1, min(12, int(m.group(1)))))
            if m.group(4):
                fin = (int(m.group(4)), max(1, min(12, int(m.group(3)))))
            else:
                fin = _ahora()
            _agregar(m, ini, fin)

    # 6) "aaaa <sep> aaaa|actualidad" (rango de años simples)
    rx6 = re.compile(r'\b(\d{4})' + _SEP + r'(?:(\d{4})\b|' + _RX_ACTUAL + r')')
    for m in rx6.finditer(t):
        if _libre(m):
            ini = (int(m.group(1)), 1)
            fin = (int(m.group(2)), 12) if m.group(2) else _ahora()
            _agregar(m, ini, fin)

    # 7) "desde aaaa" / "desde mes año" sin fecha fin explícita
    rx7 = re.compile(r'desde\s+(?:el\s+)?(?:(' + _RX_MES + r')\s*(?:de[l]?\s+)?)?(\d{4})\b')
    for m in rx7.finditer(t):
        if _libre(m):
            mes = _MESES[m.group(1)] if m.group(1) else 1
            _agregar(m, (int(m.group(2)), mes), _ahora())

    return periodos


# ───────────────────── clasificación de contexto ─────────────────────
_KW_DOCENCIA = (
    'docente', 'docencia', 'profesor', 'profesora', 'catedratic',
    'jefe de practica', 'jefa de practica', 'tutor academico',
    'tutora academica', 'dictado de', 'catedra', 'asignatura',
    'experiencias curriculares', 'curso a cargo', 'cursos a cargo',
    'teaching', 'lecturer', 'instructor universitario',
)
# señales de que el periodo NO es un trabajo (formación, cursos, premios)
_KW_NO_LABORAL = (
    'taller', 'curso de', 'diplomado', 'seminario', 'congreso',
    'certificado', 'constancia de', 'reconocimiento', 'felicitacion',
    'capacitacion', 'asistente al', 'ponente en', 'bachiller', 'titulo de',
    'maestria en', 'magister en', 'doctorado en', 'doctoranda', 'doctorando',
    'licenciatura en', 'estudios de', 'horas lectivas',
)
_RX_SECCION_EXP = re.compile(
    r'experiencia|trayectoria\s+(?:laboral|profesional)|cargos?\s+(?:desempenados|administrativos)|'
    r'work\s+experience|professional\s+experience|employment\s+history|career\s+summary')
_RX_SECCION_NOEXP = re.compile(
    r'formacion\s+academica|actualizacion\s+profesional|capacitacion|'
    r'reconocimient|publicacion|investigacion|referencias|idiomas|'
    r'cursos?\s+(?:y\s+)?talleres|estudios|grados\s+y\s+titulos|'
    r'education|certific|languages|additional\s+info|skills|awards|honors')


def _es_heading(linea: str) -> bool:
    s = linea.strip()
    if not (3 < len(s) < 90):
        return False
    letras = [c for c in s if c.isalpha()]
    return bool(letras) and sum(1 for c in letras if c.isupper()) / len(letras) > 0.8


def analizar_experiencia_texto(texto: str) -> Dict:
    """Extrae periodos laborales/docentes de un texto de CV.

    Devuelve dict con anos_docencia, anos_totales, experiencia_laboral
    (lista estructurada compatible con MotorEvaluacion) y evidencias_docencia.
    """
    out = {
        "anos_docencia": 0.0,
        "anos_totales": 0.0,
        "experiencia_laboral": [],
        "evidencias_docencia": [],
    }
    if not texto or not texto.strip():
        return out

    lineas = texto.split('\n')
    seccion = 'desconocida'   # 'experiencia' | 'otra' | 'desconocida'
    periodos_doc: List[Tuple[int, int, int, int]] = []
    periodos_tot: List[Tuple[int, int, int, int]] = []
    evidencias: List[str] = []
    estructurada: List[Dict] = []

    for i, linea in enumerate(lineas):
        ln = _normalizar(linea)

        # Actualizar sección al cruzar un encabezado
        if _es_heading(linea):
            if _RX_SECCION_NOEXP.search(ln):
                seccion = 'otra'
            elif _RX_SECCION_EXP.search(ln) or any(k in ln for k in _KW_DOCENCIA):
                seccion = 'experiencia'

        periodos = _extraer_periodos_linea(linea)
        if not periodos:
            continue

        # Contexto: la línea misma + hasta 3 líneas anteriores no vacías,
        # sin cruzar encabezados (un heading corta el bloque de contexto)
        contexto_lineas = [linea.strip()]
        j, atras = i - 1, 0
        while j >= 0 and atras < 3:
            if lineas[j].strip():
                contexto_lineas.insert(0, lineas[j].strip())
                atras += 1
                if _es_heading(lineas[j]):
                    break
            j -= 1
        contexto = ' | '.join(contexto_lineas)
        ctx_norm = _normalizar(contexto)

        es_no_laboral = (seccion == 'otra') or any(k in ctx_norm for k in _KW_NO_LABORAL)
        es_docente = any(k in ctx_norm for k in _KW_DOCENCIA) and not any(
            k in ctx_norm for k in _KW_NO_LABORAL)

        for ini, fin in periodos:
            cuadru = (ini[0], ini[1], fin[0], fin[1])
            if not es_no_laboral:
                periodos_tot.append(cuadru)
                estructurada.append({
                    # El nombre del puesto suele estar en la(s) línea(s) previas
                    # al rango de fechas, por eso el cargo lleva el contexto.
                    "cargo": contexto[:160],
                    "institucion": "",
                    "fecha_inicio": f"{ini[1]:02d}/{ini[0]}",
                    "fecha_fin": f"{fin[1]:02d}/{fin[0]}",
                    "anos": round(_meses(cuadru) / 12, 2),
                    "es_docente": bool(es_docente),
                })
            if es_docente:
                periodos_doc.append(cuadru)
                ev = linea.strip()
                if len(ev) > 110:
                    ev = ev[:110] + '…'
                evidencias.append(ev)

    out["anos_docencia"] = round(_meses_sin_solapes(periodos_doc) / 12, 2)
    out["anos_totales"] = round(_meses_sin_solapes(periodos_tot) / 12, 2)
    out["experiencia_laboral"] = estructurada
    # quitar duplicados conservando orden
    out["evidencias_docencia"] = list(dict.fromkeys(evidencias))[:8]
    return out


def _meses(p: Tuple[int, int, int, int]) -> int:
    return max(0, (p[2] - p[0]) * 12 + (p[3] - p[1]))


def _meses_sin_solapes(periodos: List[Tuple[int, int, int, int]]) -> int:
    if not periodos:
        return 0
    a_meses = lambda a, m: a * 12 + (m - 1)
    intervalos = sorted((a_meses(ai, mi), a_meses(af, mf)) for ai, mi, af, mf in periodos)
    fusion = [list(intervalos[0])]
    for ini, fin in intervalos[1:]:
        if ini <= fusion[-1][1]:
            fusion[-1][1] = max(fusion[-1][1], fin)
        else:
            fusion.append([ini, fin])
    return sum(f - i for i, f in fusion)


if __name__ == '__main__':
    import sys, io, json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith('.pdf'):
        import pdfplumber
        with pdfplumber.open(sys.argv[1]) as pdf:
            texto = '\n'.join((pg.extract_text() or '') for pg in pdf.pages)
    else:
        texto = sys.stdin.read()
    res = analizar_experiencia_texto(texto)
    print(json.dumps({k: v for k, v in res.items() if k != 'experiencia_laboral'},
                     ensure_ascii=False, indent=2))
    print(f"registros estructurados: {len(res['experiencia_laboral'])}")
    for r in res['experiencia_laboral'][:15]:
        print(' ', r['fecha_inicio'], '->', r['fecha_fin'],
              '| doc' if r['es_docente'] else '|    ', '|', r['cargo'][:80])
