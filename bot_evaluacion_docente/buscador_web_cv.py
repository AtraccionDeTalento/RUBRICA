# -*- coding: utf-8 -*-
"""
BÚSQUEDA EXPERIMENTAL DE CV EN WEB  v2.0
=========================================
Reconstruye el perfil académico completo de un docente buscando en fuentes públicas:
  - OpenAlex API (publicaciones científicas reales, SIN API key)
  - RENATI / SUNEDU (grados académicos oficiales del Perú)
  - CTI Vitae / ALICIA (CONCYTEC)
  - DuckDuckGo (búsqueda general)
  - Google Scholar (scraping)
  - LinkedIn público
  - ResearchGate / Academia.edu
  - Páginas institucionales universitarias
  - Estimación de edad y años en la industria

Uso:
    from buscador_web_cv import buscar_cv_en_web
    resultado = buscar_cv_en_web("MUÑOZ ALVA, GREASSE TATIANA", dni="40674765")
"""

import re, time, unicodedata, json, os
from urllib.parse import urlencode, quote_plus, urlparse

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False

# ──────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────────────
_TIMEOUT        = 14
_TIMEOUT_DDG    = 5       # timeout corto para DuckDuckGo (si la red lo bloquea se detecta rápido)
_MAX_RESULTADOS = 10
_PAUSA_ENTRE    = 0.6
_ddg_circuit_open = False  # circuit-breaker: True cuando DDG no es alcanzable por la red
_USER_AGENTS    = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0',
]
_ua_idx = 0

_URL_BLACKLIST = [
    'facebook.com/p/', 'twitter.com', 'instagram.com', 'tiktok.com',
    'youtube.com', 'reddit.com', 'amazon.com', 'ebay.com', 'wikipedia.org',
]

_URL_PRIORITY = [
    'alicia.concytec.gob.pe', 'ctivitae.concytec.gob.pe', 'renati.sunedu.gob.pe',
    'repositorio.', 'openalex.org', 'scholar.google', 'researchgate.net',
    'linkedin.com', 'academia.edu', '.edu.pe', 'inen.sld.pe', 'essalud.gob.pe',
    'minsa.gob.pe', 'usil.edu.pe', 'pucp.edu.pe', 'unmsm.edu.pe', 'upc.edu.pe', 'gob.pe',
]

# Año actual
_ANO_ACTUAL = 2026

# Mapeo de grado académico detectado → etiqueta legible
_GRADO_LABEL = {
    'doctorado': 'Doctor/PhD',
    'maestria':  'Magíster',
    'licenciatura': 'Licenciado/Titulado',
}

# Inferir grado acad\u00e9mico por profesi\u00f3n mencionada en snippet
_PROFESION_GRADO = {
    'm\u00e9dico':        {'licenciatura': True},
    'medico':         {'licenciatura': True},
    'abogado':        {'licenciatura': True},
    'ingeniero':      {'licenciatura': True},
    'arquitecto':     {'licenciatura': True},
    'economista':     {'licenciatura': True},
    'psic\u00f3logo':    {'licenciatura': True},
    'psicologo':      {'licenciatura': True},
    'enfermera':      {'licenciatura': True},
    'contador':       {'licenciatura': True},
    'especialista':   {'maestria': True},
    'magister':       {'maestria': True},
    'magíster':       {'maestria': True},
    'ph.d':           {'doctorado': True},
    'phd':            {'doctorado': True},
    'investigador':   {'maestria': True},
}


# ──────────────────────────────────────────────────────────────────────────────
#  UTILIDADES
# ──────────────────────────────────────────────────────────────────────────────
def _norm(texto: str) -> str:
    t = unicodedata.normalize('NFKD', str(texto or ''))
    return t.encode('ascii', 'ignore').decode('ascii').lower().strip()


def _sesion_http() -> 'requests.Session':
    global _ua_idx
    s = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5,
                  status_forcelist=[429, 500, 502, 503, 504])
    s.mount('https://', HTTPAdapter(max_retries=retry))
    s.mount('http://',  HTTPAdapter(max_retries=retry))
    s.headers.update({
        'User-Agent': _USER_AGENTS[_ua_idx % len(_USER_AGENTS)],
        'Accept-Language': 'es-PE,es;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    _ua_idx += 1
    return s


def _nombre_a_partes(nombre_completo: str) -> dict:
    n = nombre_completo.strip()
    if ',' in n:
        apellidos_raw, nombres_raw = n.split(',', 1)
    else:
        tok = n.split()
        apellidos_raw = ' '.join(tok[:2]) if len(tok) >= 2 else tok[0]
        nombres_raw   = ' '.join(tok[2:]) if len(tok) > 2 else ''
    natural = f"{nombres_raw.strip()} {apellidos_raw.strip()}".strip()
    return {
        'apellidos':      apellidos_raw.strip(),
        'nombres':        nombres_raw.strip(),
        'completo':       n,
        'natural':        natural,
        'natural_norm':   _norm(natural),
        'invertido_norm': _norm(n),
        'norm_apellido':  _norm(apellidos_raw.strip().split()[0] if apellidos_raw.strip() else ''),
    }


def _generar_variantes_nombre(partes: dict) -> list:
    """
    Genera variantes del nombre para entity resolution.
    Una misma persona puede aparecer como:
        - RONALD EDSON PEREZ MAITA
        - Ronald Edson Pérez Maita
        - Ronald E. Pérez Maita
        - R. Pérez Maita
        - Pérez Maita Ronald
        - R.E. Pérez Maita
    Retorna lista de strings (sin duplicados) para usar en queries de búsqueda.
    """
    apellidos = partes['apellidos'].strip()
    nombres   = partes['nombres'].strip()
    natural   = partes['natural'].strip()   # "NOMBRES APELLIDOS"
    invertido = partes['completo'].strip()  # "APELLIDOS, NOMBRES" o NOMBRES APELLIDOS

    def title(s): return s.title() if s else ''

    partes_nombres = nombres.split()
    primer_nombre  = title(partes_nombres[0]) if partes_nombres else ''
    inicial_nombre = f"{primer_nombre[0]}." if primer_nombre else ''

    segundo_nombre  = title(partes_nombres[1]) if len(partes_nombres) > 1 else ''
    inicial_segundo = f"{segundo_nombre[0]}." if segundo_nombre else ''

    ape_partes   = apellidos.split()
    primer_ape   = title(ape_partes[0]) if ape_partes else ''
    segundo_ape  = title(ape_partes[1]) if len(ape_partes) > 1 else ''

    variantes = set()

    # Formato canónico completo
    variantes.add(f'"{title(nombres)} {title(apellidos)}"')
    # Solo primer nombre + apellidos completos
    if segundo_nombre:
        variantes.add(f'"{primer_nombre} {title(apellidos)}"')
    # Inicial + apellidos
    variantes.add(f'"{inicial_nombre} {title(apellidos)}"')
    # Inicial + inicial segundo + apellidos
    if inicial_segundo:
        variantes.add(f'"{inicial_nombre}{inicial_segundo} {title(apellidos)}"')
    # Primer nombre + primer apellido (solo si apellido compuesto)
    if segundo_ape:
        variantes.add(f'"{primer_nombre} {segundo_nombre} {primer_ape}"' if segundo_nombre else f'"{primer_nombre} {primer_ape}"')
    # Apellido paterno solo + nombres
    variantes.add(f'"{primer_nombre} {primer_ape}"')
    # Sin comillas para búsquedas más amplias
    variantes.add(f'{title(nombres)} {title(apellidos)}')
    variantes.add(f'{primer_nombre} {title(apellidos)}')

    # Eliminar variantes muy cortas o vacías
    variantes = [v for v in variantes if len(v.replace('"','').strip()) > 5]
    return list(variantes)


# ──────────────────────────────────────────────────────────────────────────────
#  MINADO DE SNIPPETS (extrae datos sin visitar la página)
# ──────────────────────────────────────────────────────────────────────────────
def _minar_snippet(texto: str) -> dict:
    """Extrae toda la información semántica de un bloque corto de texto."""
    t = texto.lower()
    edu = {
        'doctorado':    bool(re.search(r'\b(doctor(?:ado)?|ph\.?\s*d\.?)\b', t)),
        'maestria':     bool(re.search(r'\b(maestr[íi]a|magist(?:er|r)?|m\.?s\.?c\.?|mba|mdm|mgp)\b', t)),
        'licenciatura': bool(re.search(r'\b(licenciat|bachiller|t[íi]tulo profesional)\b', t)),
    }
    # Inferir por profesión
    for prof, grados in _PROFESION_GRADO.items():
        if prof in t:
            for k, v in grados.items():
                if v and not edu.get(k):
                    edu[k] = True
    años = re.findall(r'\b(19[7-9]\d|20[0-2]\d)\b', texto)
    tiene_pub = bool(re.search(
        r'\b(artículo|tesis|publicaci[oó]n|paper|libro|investigaci[oó]n)\b', t))
    # Capturar frases de cargo de hasta 4 tokens (para que coincidan con keywords de rúbrica)
    cargos = re.findall(
        r'\b('
        r'director\s+(?:del?\s+)?(?:departamento|servicio|ejecutivo|m[eé]dico|general|de\s+\w+)|'
        r'jefe\s+(?:del?\s+)?(?:departamento|servicio|unidad|de\s+\w+)|'
        r'm[eé]dico\s+(?:jefe|especialista|asistente|adscrito|staff|coordinador)|'
        r'especialista\s+en\s+\w+|'
        r'coordinador\s+(?:m[eé]dico|de\s+\w+|t[eé]cnico)?|'
        r'jefe\s+de\s+\w+(?:\s+\w+)?|'
        r'gerente\s+(?:general|de\s+\w+)|'
        r'docente|profesor|catedr[aá]tico|investigador|decano|rector|consultor'
        r')\b', t)
    instituciones = re.findall(
        r'(?:USIL|UNMSM|PUCP|UPC|UP\b|UTP|UCH|UPCH|UDEP|UCSM|UNFV|UNT|INEN|'
        r'ESSALUD|MINSA|SUNAT|Hospital\s+[\w\s]+?(?=,|\.|$)|Cl[íi]nica\s+\w+|'
        r'Universidad\s+[\w\s]+?(?=,|\.|$)|Instituto\s+[\w\s]+?(?=,|\.|$))',
        texto, re.IGNORECASE)
    return {
        'educacion':     edu,
        'años':          sorted(set(años)),
        'tiene_pub':     tiene_pub,
        'cargos':        [c[0] if isinstance(c, tuple) else c for c in cargos[:5]],
        'instituciones': list(dict.fromkeys(i.strip() for i in instituciones))[:8],
        'grados':        [],
    }


# ──────────────────────────────────────────────────────────────────────────────
#  OPENALEX API  –  publicaciones científicas globales (SIN API key)
# ──────────────────────────────────────────────────────────────────────────────
def _buscar_openalex(partes: dict) -> dict:
    """
    Consulta la API gratuita de OpenAlex para obtener publicaciones reales.
    Retorna: {publicaciones, citas_total, año_primera_pub, año_ultima_pub,
              obras_sample, orcid, afiliaciones}
    """
    datos = {'publicaciones': 0, 'citas_total': 0, 'año_primera_pub': 0,
             'año_ultima_pub': 0, 'obras_sample': [], 'orcid': '',
             'afiliaciones': [], 'encontrado': False}
    try:
        s = _sesion_http()
        # Buscar por nombre en OpenAlex
        q = quote_plus(partes['natural'])
        url = f"https://api.openalex.org/authors?search={q}&filter=last_known_institution.country_code:PE&per-page=5"
        resp = s.get(url, timeout=_TIMEOUT, headers={'Accept': 'application/json',
                                                       'User-Agent': 'PeopleAnalyticsUSIL/2.0 (mailto:analytics@usil.edu.pe)'})
        data = resp.json()
        resultados = data.get('results', [])

        # Si no hay con filtro Perú, intentar sin filtro
        if not resultados:
            url2 = f"https://api.openalex.org/authors?search={q}&per-page=5"
            resp2 = s.get(url2, timeout=_TIMEOUT, headers={'Accept': 'application/json',
                                                            'User-Agent': 'PeopleAnalyticsUSIL/2.0 (mailto:analytics@usil.edu.pe)'})
            resultados = resp2.json().get('results', [])

        # Elegir el mejor match por nombre
        ape_norm = partes['norm_apellido']
        mejor = None
        for r in resultados:
            nombre_oa = _norm(r.get('display_name', ''))
            if ape_norm and ape_norm in nombre_oa:
                mejor = r
                break
        if not mejor and resultados:
            mejor = resultados[0]  # tomar el primero como candidato

        if mejor:
            datos['encontrado']      = True
            datos['publicaciones']   = mejor.get('works_count', 0)
            datos['citas_total']     = mejor.get('cited_by_count', 0)
            datos['orcid']           = mejor.get('orcid', '') or ''
            # Años primera y última publicación
            counts = mejor.get('counts_by_year', [])
            años_oa = [c['year'] for c in counts if c.get('works_count', 0) > 0]
            if años_oa:
                datos['año_primera_pub'] = min(años_oa)
                datos['año_ultima_pub']  = max(años_oa)
            # Afiliaciones
            inst = mejor.get('last_known_institution') or {}
            if inst.get('display_name'):
                datos['afiliaciones'] = [inst['display_name']]
            # Obras de muestra
            works_url = mejor.get('works_api_url', '')
            if works_url:
                wresp = s.get(works_url + '?per-page=5&sort=cited_by_count:desc',
                              timeout=_TIMEOUT, headers={'Accept': 'application/json',
                                                          'User-Agent': 'PeopleAnalyticsUSIL/2.0 (mailto:analytics@usil.edu.pe)'})
                obras = wresp.json().get('results', [])
                datos['obras_sample'] = [
                    {'titulo': w.get('title', ''), 'año': w.get('publication_year', 0),
                     'citas': w.get('cited_by_count', 0), 'tipo': w.get('type', '')}
                    for w in obras[:5]
                ]
        print(f"         [OpenAlex] encontrado={datos['encontrado']} "
              f"pubs={datos['publicaciones']} citas={datos['citas_total']}")
    except Exception as ex:
        print(f"   [WEB] OpenAlex error: {ex}")
    return datos


# ──────────────────────────────────────────────────────────────────────────────
#  RENATI / SUNEDU  –  grados académicos oficiales del Perú
# ──────────────────────────────────────────────────────────────────────────────
def _buscar_renati(partes: dict) -> dict:
    """
    Busca en RENATI (SUNEDU) el grado académico registrado oficialmente.
    Retorna: {grado_maximo, grados_encontrados, universidades, año_grado}
    """
    datos = {'grado_maximo': '', 'grados_encontrados': [],
             'universidades_grado': [], 'año_grado': 0, 'encontrado': False}
    try:
        s = _sesion_http()
        apellidos_q = quote_plus(partes['apellidos'])
        nombres_q   = quote_plus(partes['nombres'])
        url = (f"https://renati.sunedu.gob.pe/simple-search"
               f"?query={apellidos_q}+{nombres_q}&rpp=10&sort_by=score&order=desc")
        resp = s.get(url, timeout=_TIMEOUT)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # RENATI usa tabla con resultados
        filas = soup.select('table.table tr')
        ape_norm = partes['norm_apellido']
        prioridad = ['doctorado', 'maestría', 'maestria', 'magíster', 'magister',
                     'licenciatura', 'bachiller', 'título profesional']
        for fila in filas[1:20]:
            celdas = fila.find_all('td')
            if len(celdas) < 3:
                continue
            autor_txt = _norm(celdas[0].get_text())
            if not (ape_norm and ape_norm in autor_txt):
                continue
            datos['encontrado'] = True
            tipo_cel  = celdas[1].get_text(strip=True).lower() if len(celdas) > 1 else ''
            univ_cel  = celdas[2].get_text(strip=True)         if len(celdas) > 2 else ''
            año_match = re.search(r'(20[0-2]\d|19[8-9]\d)', fila.get_text())
            año       = int(año_match.group(1)) if año_match else 0

            if univ_cel and univ_cel not in datos['universidades_grado']:
                datos['universidades_grado'].append(univ_cel)

            grado_det = ''
            for p in prioridad:
                if p in tipo_cel:
                    grado_det = p
                    break
            if grado_det and grado_det not in datos['grados_encontrados']:
                datos['grados_encontrados'].append(grado_det)
                if año > datos['año_grado']:
                    datos['año_grado'] = año

        # Determinar grado máximo
        orden = ['doctorado', 'maestría', 'maestria', 'magíster', 'magister',
                 'licenciatura', 'bachiller', 'título profesional']
        for g in orden:
            if any(g in x for x in datos['grados_encontrados']):
                datos['grado_maximo'] = g
                break
        print(f"         [RENATI] encontrado={datos['encontrado']} "
              f"grado={datos['grado_maximo']} univ={datos['universidades_grado'][:2]}")
    except Exception as ex:
        print(f"   [WEB] RENATI error: {ex}")
    return datos


# ──────────────────────────────────────────────────────────────────────────────
#  GOOGLE SCHOLAR  –  perfil de investigador
# ──────────────────────────────────────────────────────────────────────────────
def _buscar_google_scholar(partes: dict) -> dict:
    """
    Busca el perfil público de Google Scholar (scraping sin API).
    Retorna: {publicaciones, citas_total, h_index, i10_index, áreas, encontrado}
    """
    datos = {'publicaciones': 0, 'citas_total': 0, 'h_index': 0,
             'i10_index': 0, 'areas': [], 'encontrado': False, 'url': ''}
    try:
        s  = _sesion_http()
        q  = quote_plus(partes['natural'] + ' Peru')
        url = f"https://scholar.google.com/scholar?q={q}&hl=es"
        resp = s.get(url, timeout=_TIMEOUT)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Buscar enlace a perfil de autor
        perfil_link = None
        for a in soup.select('a[href*="/citations?user="]'):
            nombre_a = _norm(a.get_text())
            if partes['norm_apellido'] and partes['norm_apellido'] in nombre_a:
                perfil_link = 'https://scholar.google.com' + a['href']
                break

        if perfil_link:
            datos['url'] = perfil_link
            datos['encontrado'] = True
            time.sleep(_PAUSA_ENTRE)
            resp2 = s.get(perfil_link, timeout=_TIMEOUT)
            soup2 = BeautifulSoup(resp2.text, 'html.parser')

            # Estadísticas (citas, h-index, i10-index)
            for td in soup2.select('#gsc_rsb_st td.gsc_rsb_std'):
                val = td.get_text(strip=True)
                if val.isdigit():
                    val_i = int(val)
                    if datos['citas_total'] == 0:
                        datos['citas_total'] = val_i
                    elif datos['h_index'] == 0:
                        datos['h_index'] = val_i
                    elif datos['i10_index'] == 0:
                        datos['i10_index'] = val_i
                        break

            # Número de publicaciones listadas
            works_count = len(soup2.select('.gsc_a_tr'))
            datos['publicaciones'] = max(datos['publicaciones'], works_count)

            # Áreas de investigación
            for btn in soup2.select('.gsc_prf_inta'):
                datos['areas'].append(btn.get_text(strip=True))

        print(f"         [Scholar] encontrado={datos['encontrado']} "
              f"citas={datos['citas_total']} h-index={datos['h_index']}")
    except Exception as ex:
        print(f"   [WEB] Google Scholar error: {ex}")
    return datos


# ──────────────────────────────────────────────────────────────────────────────
#  ESTIMACIÓN DE EDAD
# ──────────────────────────────────────────────────────────────────────────────
def _estimar_edad(texto_total: str, año_primera_actividad: int) -> dict:
    """
    Intenta estimar la edad de la persona a partir del texto web.
    Estrategias:
      1. Fecha de nacimiento explícita
      2. Año de egreso de pregrado (promedio 25 años)
      3. Año primera actividad profesional (promedio 27 años)
    """
    resultado = {'edad_estimada': 0, 'año_nacimiento_estimado': 0, 'metodo': ''}
    t = texto_total

    # Estrategia 1: fecha de nacimiento explícita
    m = re.search(
        r'(?:nacid[ao]|fecha de nacimiento|born)[^\n]{0,40}'
        r'(\d{1,2})[/\-](\d{1,2})[/\-]((?:19|20)\d{2})',
        t, re.I)
    if m:
        año = int(m.group(3))
        if 1940 < año < 2005:
            resultado['año_nacimiento_estimado'] = año
            resultado['edad_estimada'] = _ANO_ACTUAL - año
            resultado['metodo'] = 'fecha_explicita'
            return resultado

    # Estrategia 2: año de egreso de pregrado
    m2 = re.search(
        r'(?:egres[aó]|titulad[ao]|graduad[ao]|licenciad[ao])[^\n]{0,60}'
        r'((?:19[8-9]\d|200[0-5]))',
        t, re.I)
    if m2:
        año_egreso = int(m2.group(1))
        año_nac_est = año_egreso - 24  # promedio egreso pregrado
        if 1950 < año_nac_est < 2000:
            resultado['año_nacimiento_estimado'] = año_nac_est
            resultado['edad_estimada'] = _ANO_ACTUAL - año_nac_est
            resultado['metodo'] = 'año_egreso_pregrado'
            return resultado

    # Estrategia 3: primera actividad profesional
    if año_primera_actividad and año_primera_actividad > 1970:
        año_nac_est = año_primera_actividad - 27  # promedio inicio carrera
        if 1945 < año_nac_est < 2000:
            resultado['año_nacimiento_estimado'] = año_nac_est
            resultado['edad_estimada'] = _ANO_ACTUAL - año_nac_est
            resultado['metodo'] = 'primera_actividad_profesional'
    return resultado


# ──────────────────────────────────────────────────────────────────────────────
#  ALICIA – repositorio nacional de tesis y artículos (CONCYTEC)
# ──────────────────────────────────────────────────────────────────────────────
def _buscar_alicia(partes: dict) -> list:
    """Busca tesis/publicaciones en ALICIA directamente."""
    resultados = []
    try:
        s   = _sesion_http()
        q   = quote_plus(partes['natural'])
        url = f"https://alicia.concytec.gob.pe/vufind/Search/Results?lookfor={q}&type=Author"
        resp = s.get(url, timeout=_TIMEOUT)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.select('.result, .record')[:8]:
            titulo_el  = item.select_one('.title, h2, h3')
            resumen_el = item.select_one('.abstract, .summary, p')
            texto_item = ' '.join(filter(None, [
                titulo_el.get_text(' ')  if titulo_el  else '',
                resumen_el.get_text(' ') if resumen_el else '',
            ]))
            if not texto_item.strip():
                continue
            d = _minar_snippet(texto_item)
            d['url']       = url
            d['fuente']    = 'ALICIA CONCYTEC'
            d['tiene_pub'] = True          # cualquier registro en ALICIA = publicación
            resultados.append(d)
    except Exception as ex:
        print(f"   [WEB] ALICIA error: {ex}")
    return resultados


# ──────────────────────────────────────────────────────────────────────────────
#  BÚSQUEDA DUCKDUCKGO (sin API key)
# ──────────────────────────────────────────────────────────────────────────────
def _buscar_duckduckgo(query: str, max_results: int = 10) -> list:
    """
    Búsqueda en DuckDuckGo HTML (sin API key, sin límite de uso).
    Retorna lista de dicts {titulo, url, snippet}.
    Circuit-breaker: si el host no es alcanzable, salta todas las queries siguientes.
    """
    global _ddg_circuit_open
    if not (REQUESTS_OK and BS4_OK):
        return []
    if _ddg_circuit_open:
        return []  # host inaccesible, no gastar tiempo
    results = []
    try:
        # Sesión SIN reintentos para DDG: un fallo de conexión debe detectarse rápido
        s = requests.Session()
        s.headers.update({
            'User-Agent': _USER_AGENTS[_ua_idx % len(_USER_AGENTS)],
            'Accept-Language': 'es-PE,es;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        url  = 'https://html.duckduckgo.com/html/'
        data = {'q': query, 'kl': 'pe-es', 'df': ''}
        resp = s.post(url, data=data, timeout=_TIMEOUT_DDG)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for r in soup.select('.result')[:max_results]:
            titulo_el  = r.select_one('.result__title a')
            snippet_el = r.select_one('.result__snippet')
            if not titulo_el:
                continue
            href = titulo_el.get('href', '')
            # DuckDuckGo redirige — limpiar uddg= param
            if 'uddg=' in href:
                href = re.search(r'uddg=([^&]+)', href)
                href = requests.utils.unquote(href.group(1)) if href else ''
            results.append({
                'titulo':  titulo_el.get_text(strip=True),
                'url':     href,
                'snippet': snippet_el.get_text(strip=True) if snippet_el else '',
            })
    except Exception as ex:
        err_str = str(ex).lower()
        if 'connecttimeouterror' in err_str or 'connect timeout' in err_str or 'connection timed out' in err_str:
            _ddg_circuit_open = True  # host inaccesible, activar circuit-breaker
            print(f"   [DDG] Host inaccesible (circuit-breaker ON) — saltando queries restantes")
        else:
            print(f"   [WEB] DuckDuckGo error: {ex}")
    return results


# ──────────────────────────────────────────────────────────────────────────────
#  EXTRACCIÓN POR FUENTE
# ──────────────────────────────────────────────────────────────────────────────
def _extraer_linkedin(url: str, partes_nombre: dict) -> dict:
    """Extrae datos del perfil público de LinkedIn."""
    datos = {'fuente': 'LinkedIn', 'url': url, 'cargo': '', 'empresa': '',
             'ubicacion': '', 'resumen': '', 'educacion_lst': [], 'exp_lst': [],
             'skills': []}
    try:
        s    = _sesion_http()
        resp = s.get(url, timeout=_TIMEOUT, allow_redirects=True)
        if resp.status_code in (999, 403, 429):
            # LinkedIn bloquea; intentar con Google Cache
            cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{quote_plus(url)}"
            resp = s.get(cache_url, timeout=_TIMEOUT)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Open Graph meta
        og = {}
        for m in soup.find_all('meta', property=re.compile(r'^og:')):
            og[m.get('property', '')] = m.get('content', '')
        datos['resumen']   = og.get('og:description', '')
        datos['cargo']     = og.get('og:title', '').split(' - ')[0].strip() if og.get('og:title') else ''
        datos['empresa']   = og.get('og:title', '').split(' - ')[1].strip() if og.get('og:title', '').count(' - ') >= 1 else ''
        datos['ubicacion'] = og.get('og:title', '').split(' - ')[-1].strip() if og.get('og:title', '').count(' - ') >= 2 else ''

        # Contenido estructurado (cuando LinkedIn lo expone)
        for section in soup.select('section'):
            h2 = section.find('h2')
            if not h2:
                continue
            h2t = h2.get_text(strip=True).lower()
            items = [li.get_text(' ', strip=True) for li in section.select('li')]
            if 'experienci' in h2t:
                datos['exp_lst'] = items[:8]
            elif 'educaci' in h2t or 'formaci' in h2t:
                datos['educacion_lst'] = items[:6]
            elif 'habilidad' in h2t or 'skill' in h2t:
                datos['skills'] = items[:10]
    except Exception as ex:
        datos['error'] = str(ex)
    return datos


def _extraer_pagina_generica(url: str, partes_nombre: dict) -> dict:
    """Extrae texto libre de cualquier página y detecta entidades relevantes."""
    datos = {'fuente': urlparse(url).netloc, 'url': url,
             'texto': '', 'titulo': '', 'cargos': [], 'instituciones': [],
             'grados': [], 'años': []}
    try:
        s    = _sesion_http()
        resp = s.get(url, timeout=_TIMEOUT)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Remover scripts y estilos
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        datos['titulo'] = soup.title.string.strip() if soup.title else ''
        texto_crudo     = soup.get_text(separator=' ', strip=True)

        # Limitar a 4000 chars centrados en el nombre del candidato
        nom_norm = partes_nombre['natural_norm']
        pos = texto_crudo.lower().find(nom_norm.split()[0] if nom_norm else '')
        if pos > 0:
            texto_crudo = texto_crudo[max(0, pos-500): pos+3500]
        else:
            texto_crudo = texto_crudo[:4000]

        datos['texto'] = re.sub(r'\s{2,}', ' ', texto_crudo).strip()

        # Detectar grados académicos
        grados = re.findall(
            r'\b(?:doctor|ph\.?d|maestr[íi]a|m\.?s\.?c|licenciatura|bachiller|ingenier[íi]a|abog|mdm|mba)\b',
            datos['texto'], re.IGNORECASE)
        datos['grados'] = list(set(g.capitalize() for g in grados))

        # Detectar años (experiencia laboral)
        años = re.findall(r'\b(19[7-9]\d|20[0-2]\d)\b', datos['texto'])
        datos['años'] = sorted(set(años))

        # Detectar instituciones comunes en Perú
        instituciones = re.findall(
            r'\b(?:USIL|UNMSM|PUCP|UPC|UP\b|UTP|UCH|UPCH|UDEP|UCSM|UNFV|UNT|'
            r'INEN|ESSALUD|MINSA|Hospital\s+\w+|Cl[íi]nica\s+\w+|'
            r'Pontificia|Universidad\s+\w+|Instituto\s+\w+)\b',
            datos['texto'], re.IGNORECASE)
        datos['instituciones'] = list(dict.fromkeys(instituciones))[:10]

    except Exception as ex:
        datos['error'] = str(ex)
    return datos


def _extraer_ctivitae(nombre: str, partes: dict) -> dict:
    """Busca directamente en CTI Vitae/CONCYTEC."""
    datos = {'fuente': 'CTI Vitae', 'url': '', 'encontrado': False,
             'investigador': False, 'publicaciones': 0, 'proyectos': 0}
    try:
        s = _sesion_http()
        search_url = (f"https://ctivitae.concytec.gob.pe/appDirectorioCTI/BuscarInvestigador.do"
                      f"?tnombres={quote_plus(partes['nombres'])}"
                      f"&tapellidos={quote_plus(partes['apellidos'])}"
                      f"&tgradoAcademico=&submitBuscar=Buscar")
        resp  = s.get(search_url, timeout=_TIMEOUT)
        soup  = BeautifulSoup(resp.text, 'html.parser')
        filas = soup.select('table tr')
        for fila in filas[1:6]:
            celdas = fila.find_all('td')
            if len(celdas) >= 2:
                nombre_celda = _norm(celdas[0].get_text())
                # Coincidencia flexible: apellido principal
                ape_norm = partes.get('norm_apellido', _norm(partes['apellidos'].split()[0]))
                if ape_norm and ape_norm in nombre_celda:
                    link = fila.find('a', href=True)
                    datos['encontrado']   = True
                    datos['investigador'] = True
                    datos['url']          = 'https://ctivitae.concytec.gob.pe' + link['href'] if link else ''
                    datos['nombre_cti']   = celdas[0].get_text(strip=True)
                    print(f"         [CTI] Encontrado: {datos['nombre_cti']}")
                    break
    except Exception as ex:
        datos['error'] = str(ex)
    return datos


# ──────────────────────────────────────────────────────────────────────────────
#  DIRECTORIOS PROFESIONALES Y DOCUMENTOS INSTITUCIONALES
# ──────────────────────────────────────────────────────────────────────────────
def _buscar_directorios_profesionales(partes: dict, dni: str = '') -> dict:
    """
    Búsqueda en directorios profesionales y documentos institucionales del Estado peruano.
    Cubre:
      - SINARH (Sistema Nacional de Registro de Hardware → Funcionarios)
      - SERVIR (directorio de servidores públicos)
      - Colegio Médico del Perú (verificación CMP)
      - Portal de Transparencia (resoluciones, memorandos)
      - Documentos gob.pe con site: operator
    Retorna dict con datos encontrados.
    """
    datos = {
        'encontrado': False,
        'cargo_institucional': '',
        'institucion_publica': '',
        'colegio_profesional': '',
        'num_colegiatura': '',
        'fuentes': [],
        'snippets': [],
    }
    if not (REQUESTS_OK and BS4_OK):
        return datos

    ape = partes['apellidos'].strip()
    nom = partes['nombres'].strip()
    natural = partes['natural'].strip()
    primer_ape = ape.split()[0] if ape else ''

    # Queries de documentos institucionales
    site_queries = [
        f'site:gob.pe "{natural}"',
        f'site:gob.pe "{nom.split()[0]} {primer_ape}"',
        f'site:inen.sld.pe "{primer_ape}"',
        f'site:essalud.gob.pe "{primer_ape}"',
        f'site:minsa.gob.pe "{primer_ape}"',
        f'site:ins.gob.pe "{primer_ape}"',
        f'"{natural}" resolucion cargo departamento',
        f'"{natural}" medico jefe director departamento hospital',
        f'"{primer_ape}" CMP colegio medico peru',
    ]
    if dni:
        site_queries.insert(0, f'"{natural}" DNI {dni} Peru')

    s = _sesion_http()
    for q in site_queries[:8]:
        try:
            results = _buscar_duckduckgo(q, max_results=5)
            for r in results:
                sn = (r.get('titulo', '') + ' ' + r.get('snippet', '')).strip()
                if not sn or _norm(primer_ape) not in _norm(sn):
                    continue
                datos['encontrado'] = True
                datos['snippets'].append(sn[:300])
                url = r.get('url', '')
                if url and url not in datos['fuentes']:
                    datos['fuentes'].append(url)

                # Extraer cargo / institución del snippet
                sn_l = sn.lower()
                for kw_cargo in ['director', 'jefe', 'médico', 'medico', 'coordinador',
                                  'especialista', 'gerente', 'subdirector', 'encargado']:
                    idx = sn_l.find(kw_cargo)
                    if idx >= 0:
                        frag = sn[idx:idx+80].split('.')[0].strip()
                        if len(frag) > 8 and not datos['cargo_institucional']:
                            datos['cargo_institucional'] = frag
                for kw_inst in ['inen', 'essalud', 'minsa', 'hospital', 'ministerio',
                                 'instituto', 'universidad', 'clínica', 'clinica']:
                    if kw_inst in sn_l and not datos['institucion_publica']:
                        idx2 = sn_l.find(kw_inst)
                        datos['institucion_publica'] = sn[idx2:idx2+60].split('.')[0].strip()
                # Detectar número CMP
                cmp_m = re.search(r'CMP\s*[:\-]?\s*(\d{4,6})', sn, re.I)
                if cmp_m and not datos['num_colegiatura']:
                    datos['colegiatura']     = f"CMP {cmp_m.group(1)}"
                    datos['colegio_profesional'] = 'Colegio Médico del Perú'
            time.sleep(_PAUSA_ENTRE)
        except Exception as ex:
            print(f"   [DIR] error query '{q[:40]}': {ex}")
            continue

    if datos['encontrado']:
        print(f"         [Directorios] cargo={datos['cargo_institucional'][:40]} "
              f"inst={datos['institucion_publica'][:30]} "
              f"snippets={len(datos['snippets'])}")
    return datos


# ──────────────────────────────────────────────────────────────────────────────
#  SCRAPING DIRECTO DE FUENTES INSTITUCIONALES PRIORITARIAS
#  (funciona SIN DuckDuckGo — fallback garantizado)
# ──────────────────────────────────────────────────────────────────────────────
def _buscar_institucional_directo(partes: dict, dni: str = '') -> list:
    """
    Scraping directo de fuentes institucionales peruanas de alta precisión.
    Se ejecuta SIEMPRE como complemento al pipeline estándar, incluso cuando
    DuckDuckGo o CTI Vitae no están disponibles.

    Fuentes cubiertas:
      - portal.inen.sld.pe          (directorio staff médico oncológico)
      - www.gob.pe                  (resoluciones, memorandos, designaciones)
      - essalud.gob.pe              (directorio médico ESSALUD)
      - ins.gob.pe                  (Instituto Nacional de Salud)
      - minsa.gob.pe                (funcionarios MINSA)
      - medicina.cayetano.edu.pe    (UPCH posgrado / especialidades)
      - transparencia.gob.pe        (directorio de funcionarios)
      - cmp.org.pe                  (Colegio Médico del Perú)

    Retorna lista de dicts compatibles con `extracciones` / `snippets_minados`.
    """
    if not (REQUESTS_OK and BS4_OK):
        return []

    apellidos  = partes['apellidos'].strip()
    nombres    = partes['nombres'].strip()
    natural    = partes['natural'].strip()
    primer_ape = apellidos.split()[0] if apellidos else ''
    primer_nom = nombres.split()[0] if nombres else ''
    ape_norm   = partes['norm_apellido']

    resultados = []
    s          = _sesion_http()

    # ── Lista de fuentes directas a consultar ─────────────────────────────────
    fuentes = [
        # INEN – directorio de staff médico
        {'url': f"https://portal.inen.sld.pe/?s={quote_plus(primer_ape)}",
         'tag': 'INEN_STAFF'},
        {'url': f"https://portal.inen.sld.pe/?s={quote_plus(natural)}",
         'tag': 'INEN_STAFF_FULL'},
        # gob.pe – resoluciones de designación / encargatura
        {'url': (f"https://www.gob.pe/busquedas?term={quote_plus(natural)}"
                 f"&contenido[]=resolucion&institucion[]=inen"),
         'tag': 'GOB_PE_INEN'},
        {'url': f"https://www.gob.pe/busquedas?term={quote_plus(natural)}&contenido[]=resolucion",
         'tag': 'GOB_PE_RESOL'},
        {'url': f"https://www.gob.pe/busquedas?term={quote_plus(primer_nom + ' ' + primer_ape)}",
         'tag': 'GOB_PE_GENERAL'},
        # ESSALUD directorio
        {'url': f"https://www.essalud.gob.pe/buscador/?q={quote_plus(primer_ape)}",
         'tag': 'ESSALUD'},
        # Instituto Nacional de Salud
        {'url': f"https://www.ins.gob.pe/buscador/?q={quote_plus(natural)}",
         'tag': 'INS_GOB'},
        # UPCH – posgrado en medicina (para detectar especialidad / maestría)
        {'url': f"https://medicina.cayetano.edu.pe/?s={quote_plus(primer_ape)}",
         'tag': 'UPCH_MEDICINA'},
        # Colegio Médico del Perú
        {'url': (f"https://cmp.org.pe/medicos-colegiados/?apellido={quote_plus(primer_ape)}"
                 f"&nombre={quote_plus(primer_nom)}"),
         'tag': 'CMP_COLEGIADOS'},
        # Transparencia – directorio funcionarios
        {'url': (f"https://www.gob.pe/transparencia-economica/personal-y-proveedores/"
                 f"personal?search={quote_plus(natural)}"),
         'tag': 'TRANSPARENCIA_PERSONAL'},
    ]

    # Si tenemos DNI, agregamos búsqueda directa por documento
    if dni:
        fuentes.insert(0, {
            'url': f"https://www.gob.pe/busquedas?term={quote_plus(dni)}",
            'tag': 'GOB_PE_DNI'
        })

    print(f"   [DIRECTO] Consultando {len(fuentes)} fuentes institucionales...")

    for fuente in fuentes:
        try:
            resp = s.get(fuente['url'], timeout=_TIMEOUT, allow_redirects=True)
            if resp.status_code not in (200, 206):
                continue

            soup        = BeautifulSoup(resp.text, 'html.parser')
            texto_all   = soup.get_text(separator=' ', strip=True)

            # Verificar que el apellido aparezca en la página
            if ape_norm and ape_norm not in _norm(texto_all):
                continue

            # ── Extraer fragmentos centrados en el candidato ──────────────────
            fragmentos = []
            for elem in soup.find_all(string=re.compile(primer_ape, re.I)):
                parent = elem.parent
                if not parent:
                    continue
                ctx = parent.get_text(separator=' ', strip=True)
                if len(ctx) > 15 and ape_norm in _norm(ctx):
                    fragmentos.append(ctx[:600])
                    gp = parent.parent
                    if gp:
                        ctx2 = gp.get_text(separator=' ', strip=True)
                        if len(ctx2) > 20:
                            fragmentos.append(ctx2[:600])

            texto_relevante = ' '.join(list(dict.fromkeys(fragmentos))[:8]) if fragmentos else texto_all[:3000]

            # Minar semánticamente el fragmento
            d = _minar_snippet(texto_relevante)
            d.update({
                'url':         fuente['url'],
                'fuente':      fuente['tag'],
                'texto':       texto_relevante[:3000],
                'snippet_raw': texto_relevante[:600],
            })
            resultados.append(d)

            cargos_log = d.get('cargos', [])[:2]
            inst_log   = d.get('instituciones', [])[:2]
            print(f"         [{fuente['tag']}] OK — {len(texto_relevante)} chars | "
                  f"cargos={cargos_log} | inst={inst_log}")

            # ── Seguir links de perfil individual que contengan el apellido ────
            urls_perfil = set()
            for a in soup.find_all('a', href=True):
                href    = a['href']
                txt_a   = a.get_text(strip=True)
                if (ape_norm in _norm(txt_a)
                        and href.strip().startswith('http')
                        and href not in urls_perfil
                        and len(urls_perfil) < 3):
                    urls_perfil.add(href)
                    try:
                        d2      = _extraer_pagina_generica(href, partes)
                        txt2    = d2.get('texto', '')
                        if txt2 and ape_norm in _norm(txt2):
                            d2m = _minar_snippet(txt2[:3000])
                            d2m.update({
                                'url':         href,
                                'fuente':      fuente['tag'] + '_PERFIL',
                                'texto':       txt2[:3000],
                                'snippet_raw': txt2[:600],
                            })
                            resultados.append(d2m)
                            print(f"           → Perfil individual: {href[:70]}")
                    except Exception:
                        pass

            time.sleep(_PAUSA_ENTRE)

        except Exception as ex:
            print(f"   [DIRECTO] {fuente['tag']}: {ex}")
            continue

    print(f"   [DIRECTO] Total resultados institucionales directos: {len(resultados)}")
    return resultados


# ──────────────────────────────────────────────────────────────────────────────
#  CONSOLIDADOR DE DATOS
# ──────────────────────────────────────────────────────────────────────────────
def _consolidar(partes: dict, resultados_busqueda: list, extracciones: list,
                cti: dict, snippets_minados: list = None,
                alicia: list = None) -> dict:
    """Consolida todos los datos extraídos (páginas + snippets + ALICIA) en un perfil."""

    snippets_minados = snippets_minados or []
    alicia           = alicia or []
    todos            = snippets_minados + extracciones + alicia

    # ── Textos combinados ─────────────────────────────────────────────────────
    texto_total = ' '.join(
        d.get('texto', '') or d.get('resumen', '') or d.get('snippet_raw', '')
        for d in todos
    )

    # ── Educación (page visits + snippets + ALICIA) ───────────────────────────
    edu = {'doctorado': False, 'maestria': False, 'licenciatura': False}
    for d in todos:
        for k in edu:
            if d.get('educacion', {}).get(k):
                edu[k] = True
    # Búsqueda directa en texto visitado
    if not edu['doctorado']:   edu['doctorado']    = bool(re.search(r'\b(doctor(?:ado)?|ph\.?\s*d\.?)\b', texto_total, re.I))
    if not edu['maestria']:    edu['maestria']     = bool(re.search(r'\b(maestr[íi]a|magist|m\.s\.c|mba|mdm|mgp)\b', texto_total, re.I))
    if not edu['licenciatura']:edu['licenciatura'] = bool(re.search(r'\b(licenciat|bachiller|título profesional)\b', texto_total, re.I))

    grados_raw = list(set(
        g for d in todos for g in d.get('grados', [])
    ))[:6]

    # ── Años de experiencia ───────────────────────────────────────────────────
    años_todos = sorted(set(
        int(y) for d in todos for y in d.get('años', []) if int(y) > 1975
    ))
    año_min  = años_todos[0]  if años_todos else 0
    años_exp = min(45, max(0, 2026 - año_min)) if año_min else 0

    # ── Cargo y empresa ───────────────────────────────────────────────────────
    cargo, empresa = '', ''
    for d in todos:
        cargos_d = d.get('cargos', [])
        if cargos_d and not cargo:
            cargo = cargos_d[0].strip().title()
        inst_d = d.get('instituciones', [])
        if inst_d and not empresa:
            empresa = inst_d[0].strip()

    # ── Instituciones ─────────────────────────────────────────────────────────
    instituciones = list(dict.fromkeys(
        i.strip() for d in todos for i in d.get('instituciones', []) if i.strip()
    ))[:10]

    # ── Experiencia laboral (para C3/C4 del motor de evaluación) ─────────────
    _exp_lab_visto: set = set()
    experiencia_laboral: list = []
    for d in todos:
        d_cargos = d.get('cargos', [])
        d_insts  = d.get('instituciones', [])
        for i, c in enumerate(d_cargos):
            if not c:
                continue
            key = c.lower().strip()
            if key not in _exp_lab_visto:
                _exp_lab_visto.add(key)
                inst_d = d_insts[i] if i < len(d_insts) else (d_insts[0] if d_insts else '')
                experiencia_laboral.append({
                    'cargo':   c.strip().title(),
                    'empresa': inst_d.strip(),
                    'anos':    0,
                })
    # Cargo principal al frente si no estaba
    if cargo and cargo.lower().strip() not in _exp_lab_visto:
        experiencia_laboral.insert(0, {'cargo': cargo, 'empresa': empresa, 'anos': 0})
    experiencia_laboral = experiencia_laboral[:8]

    # ── Exp. docente ──────────────────────────────────────────────────────────
    exp_docente = 0
    # Búsqueda literal en cargos
    _CARGOS_DOCENTE_LITERAL = ['docente', 'profesor', 'catedrático', 'catedratico', 'instructor']
    for d in todos:
        for c in d.get('cargos', []):
            if any(x in c.lower() for x in _CARGOS_DOCENTE_LITERAL):
                exp_docente = max(exp_docente, max(1, años_exp // 3))
    for m in re.finditer(r'(?:docente|profesor)[\w\s,]{0,40}?(\d+)\s*a[ñn]os?', texto_total, re.I):
        exp_docente = max(exp_docente, int(m.group(1)))

    # ── Inferencia profesional → docencia implícita ───────────────────────────
    # Un directivo senior en institución médica/académica habitualmente
    # tutela residentes o dicta clases, aunque su cargo formal no diga "docente".
    _CARGOS_DIRECTIVOS = [
        'director', 'jefe de', 'jefatura', 'coordinador', 'decano',
        'subdirector', 'gerente', 'rector', 'vicerrector', 'presidente',
        'superintendente', 'médico jefe', 'medico jefe',
    ]
    _INST_ACADEMICAS = [
        'hospital', 'clínica', 'clinica', 'inen', 'instituto',
        'ministerio', 'essalud', 'universidad', 'escuela', 'facultad',
        'oncosalud', 'ins.gob', 'minsa',
    ]
    _all_cargos_txt = ' '.join(c.lower() for d in todos for c in d.get('cargos', []))
    _all_inst_txt   = ' '.join(i.lower() for i in instituciones)

    _tiene_directivo     = any(x in _all_cargos_txt for x in _CARGOS_DIRECTIVOS)
    _tiene_inst_academica = any(x in _all_inst_txt   for x in _INST_ACADEMICAS)

    if exp_docente == 0:
        if _tiene_directivo and _tiene_inst_academica and años_exp >= 5:
            # Cargo directivo en institución médica/universitaria → docencia implícita
            exp_docente = min(8, max(2, años_exp // 4))
        elif _tiene_directivo and años_exp >= 12:
            # Muy senior sin institución clara → algo de docencia implícita
            exp_docente = 3

    # ── Publicaciones ─────────────────────────────────────────────────────────
    pubs_alicia = sum(1 for d in alicia if d.get('tiene_pub'))
    pubs_cti    = cti.get('publicaciones', 0)
    pubs_texto  = len(re.findall(r'\b(artículo|tesis|publicaci[oó]n|paper|libro)\b', texto_total, re.I))
    publicaciones = max(pubs_alicia, pubs_cti, pubs_texto // 2)

    # ── Idiomas ──────────────────────────────────────────────────────────────
    t_low = texto_total.lower()
    idiomas = []
    for nombre_i, alias in [('Inglés', ['ingles','inglés','english']),
                             ('Francés', ['frances','francés','french']),
                             ('Portugués', ['portugues','portugués']),
                             ('Alemán', ['aleman','alemán']),
                             ('Italiano', ['italiano'])]:
        if any(a in t_low for a in alias):
            idiomas.append(nombre_i)

    # ── URLs de fuentes ───────────────────────────────────────────────────────
    fuentes_urls = []
    if cti.get('url'):  fuentes_urls.append(cti['url'])
    for d in extracciones + snippets_minados:
        u = d.get('url', '')
        if u and u not in fuentes_urls:
            fuentes_urls.append(u)
    fuentes_urls = fuentes_urls[:6]

    # ── Flag de datos insuficientes (distingue "no encontrado" de "valor cero") ──
    datos_insuficientes = (
        len(snippets_minados) == 0
        and len(extracciones) == 0
        and not cti['encontrado']
        and not alicia
    )

    # ── Score de confianza ────────────────────────────────────────────────────
    score = 0
    if datos_insuficientes:
        score = 0   # sin datos = confianza cero, NO inferir valores
    else:
        if edu['doctorado']:      score += 30
        elif edu['maestria']:     score += 20
        elif edu['licenciatura']: score += 15
        if años_exp > 0:          score += min(20, años_exp)
        if cti['encontrado']:     score += 25
        if publicaciones > 0:     score += 10
        if instituciones:         score += 8
        if cargo:                 score += 5
        if len(snippets_minados) >= 3: score += 7
    score = min(100, score)

    # ── Grado máximo consolidado ──────────────────────────────────────────────
    if edu['doctorado']:
        grado_maximo = 'Doctor/PhD'
    elif edu['maestria']:
        grado_maximo = 'Magíster'
    elif edu['licenciatura']:
        grado_maximo = 'Licenciado/Titulado'
    else:
        grado_maximo = 'No determinado'

    return {
        'nombre':          partes['natural'],
        'nombre_original': partes['completo'],
        'dni':             '',
        'educacion': {
            'doctorado':    edu['doctorado'],
            'maestria':     edu['maestria'],
            'licenciatura': edu['licenciatura'],
            'bachiller':    edu['licenciatura'],
            'grados_raw':   grados_raw,
            'grado_maximo': grado_maximo,
        },
        'anos_experiencia':             años_exp,
        'anos_experiencia_profesional': años_exp,
        'experiencia_docente':          exp_docente,
        'experiencia_laboral':          experiencia_laboral,
        'empresas':                     list(dict.fromkeys(
            i for i in ([empresa] + instituciones) if i
        ))[:6],
        'publicaciones':           publicaciones,
        'proyectos_investigacion': cti.get('proyectos', 0),
        'cargo_actual':   cargo,
        'empresa_actual': empresa,
        'idiomas':        idiomas,
        'instituciones':  instituciones,
        'fuente_datos':     'WEB_EXPERIMENTAL',
        'cti_encontrado':   cti['encontrado'],
        'cti_investigador':    cti['investigador'],
        'score_confianza':    score,
        'datos_insuficientes': datos_insuficientes,
        'fuentes_urls':       fuentes_urls,
        'snippets':         [r.get('snippet','') for r in resultados_busqueda if r.get('snippet')][:5],
        'texto_combinado':  texto_total[:5000],
    }


# ──────────────────────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────
def buscar_cv_en_web(nombre: str, dni: str = '', facultad: str = '',
                     carrera: str = '', verbose: bool = True) -> dict:
    """
    Búsqueda EXPERIMENTAL de CV en fuentes web públicas (v2.0).

    Parámetros:
        nombre   : Nombre completo en formato 'APELLIDOS, NOMBRES' o 'NOMBRES APELLIDOS'
        dni      : DNI (opcional, mejora precisión)
        facultad : Facultad/área de la persona (opcional, mejora precisión)
        carrera  : Carrera donde dicta (opcional)
        verbose  : Imprimir progreso

    Retorna:
        Dict con perfil reconstruido detallado + metadata de confianza.
    """
    resultado_base = {
        'encontrado': False,
        'nombre':     nombre,
        'cv_data':    None,
        'mensaje':    '',
        'fuentes':    [],
        'error':      None,
    }

    if not REQUESTS_OK:
        resultado_base['mensaje'] = 'requests no instalado. Ejecuta: pip install requests beautifulsoup4'
        resultado_base['error']   = 'MISSING_DEPS'
        return resultado_base

    if not BS4_OK:
        resultado_base['mensaje'] = 'beautifulsoup4 no instalado. Ejecuta: pip install beautifulsoup4'
        resultado_base['error']   = 'MISSING_DEPS'
        return resultado_base

    global _ddg_circuit_open
    _ddg_circuit_open = False  # resetear circuit-breaker para cada nueva búsqueda

    partes = _nombre_a_partes(nombre)
    ctx    = f'docente universitario Peru {carrera or ""} {facultad or ""}'.strip()
    nq     = f'"{partes["natural"]}"'

    print(f"\n{'='*60}")
    print(f"[WEB v2] Reconstruyendo: {partes['natural']}" + (f"  DNI:{dni}" if dni else ""))
    print(f"{'='*60}")

    # ── FASE 1: CTI Vitae ─────────────────────────────────────────────────────
    print("   [1/8] CTI Vitae...")
    cti = _extraer_ctivitae(nombre, partes)
    time.sleep(_PAUSA_ENTRE)

    # ── FASE 2: ALICIA (repositorio CONCYTEC) ─────────────────────────────────
    print("   [2/8] ALICIA CONCYTEC...")
    alicia = _buscar_alicia(partes)
    print(f"         {len(alicia)} registros ALICIA")
    time.sleep(_PAUSA_ENTRE)

    # ── FASE 3: OpenAlex (publicaciones científicas globales) ─────────────────
    print("   [3/8] OpenAlex (publicaciones globales)...")
    openalex = _buscar_openalex(partes)
    time.sleep(_PAUSA_ENTRE)

    # ── FASE 4: RENATI / SUNEDU (grados académicos oficiales) ────────────────
    print("   [4/8] RENATI / SUNEDU (grados oficiales)...")
    renati = _buscar_renati(partes)
    time.sleep(_PAUSA_ENTRE)

    # ── FASE 5: Google Scholar ─────────────────────────────────────────────────
    print("   [5/8] Google Scholar...")
    scholar = _buscar_google_scholar(partes)
    time.sleep(_PAUSA_ENTRE)

    # ── FASE 6: DuckDuckGo (queries ampliadas con variantes de nombre) ─────────
    variantes = _generar_variantes_nombre(partes)
    # Tomar 4 variantes representativas para no saturar: canonical quoted, short quoted,
    # first+first_surname, without quotes
    v_list = list(variantes)
    # Ordenar por largo descendente para priorizar variantes completas
    v_list.sort(key=len, reverse=True)
    v_canonical = v_list[0]  # nombre completo con comillas
    v_corto = min(v_list, key=len)   # variante más corta

    carrera_ctx = carrera or ''
    facultad_ctx = facultad or ''

    queries: list[str] = []

    # — Queries con DNI (máxima precisión si disponible) ——————————————————
    if dni:
        queries.append(f'{v_canonical} DNI {dni}')
        queries.append(f'DNI {dni} Peru docente universidad')

    # — Queries académicas / docentes ———————————————————————————————————
    queries += [
        f'{v_canonical} {ctx}',
        f'{v_canonical} curriculum vitae Peru',
        f'{v_canonical} docente universidad Peru',
        f'{v_canonical} investigador publicaciones',
        f'{v_canonical} linkedin Peru',
        f'{v_corto} docente universitario Peru {carrera_ctx}'.strip(),
        f'{v_corto} investigador CONCYTEC',
        f'{v_corto} publicaciones revista',
    ]

    # — Queries con facultad / carrera ———————————————————————————————————
    if facultad_ctx:
        queries.append(f'{v_canonical} {facultad_ctx}')
        queries.append(f'{v_corto} {facultad_ctx} Peru')
    if carrera_ctx:
        queries.append(f'{v_canonical} {carrera_ctx} Peru universidad')

    # — Queries con site: operator (documentos institucionales) ——————————
    primer_ape = partes['apellidos'].split()[0] if partes['apellidos'] else ''
    primer_nom = partes['nombres'].split()[0] if partes['nombres'] else ''
    queries += [
        f'site:gob.pe "{partes["natural"]}"',
        f'site:concytec.gob.pe "{primer_nom} {primer_ape}"',
        f'site:inen.sld.pe "{primer_ape}"',
        f'site:essalud.gob.pe "{primer_ape}"',
        f'site:minsa.gob.pe "{primer_ape}"',
        f'site:ins.gob.pe "{primer_ape}"',
        f'site:repositorio.usil.edu.pe "{primer_ape}"',
        f'site:tesis.pucp.edu.pe "{primer_ape}"',
        f'site:revistas.concytec.gob.pe "{partes["natural"]}"',
        f'"{partes["natural"]}" resolucion cargo director Peru',
        f'"{primer_nom} {primer_ape}" medico especialista hospital Peru',
        f'"{primer_nom} {primer_ape}" CMP colegio medico Peru',
    ]

    # Eliminar duplicados manteniendo orden
    seen_q: set[str] = set()
    queries_unicas: list[str] = []
    for q in queries:
        q = q.strip()
        if q and q not in seen_q:
            seen_q.add(q)
            queries_unicas.append(q)
    queries = queries_unicas

    print(f"   [6/8] DuckDuckGo ({len(queries)} queries, {len(variantes)} variantes de nombre)...")
    todos_resultados = []
    vistos = set()
    for q in queries:
        for r in _buscar_duckduckgo(q, max_results=7):
            if r['url'] and r['url'] not in vistos:
                if not any(bl in r['url'].lower() for bl in _URL_BLACKLIST):
                    vistos.add(r['url'])
                    todos_resultados.append(r)
        time.sleep(_PAUSA_ENTRE)
    print(f"         {len(todos_resultados)} URLs únicas")

    # ── FASE 7: Minar snippets directamente (SIN visitar páginas) ────────────
    print(f"   [7/8] Minando {len(todos_resultados)} snippets...")
    snippets_minados = []
    ape_norm = partes['norm_apellido']
    for r in todos_resultados:
        texto_s = (r.get('titulo', '') + ' ' + r.get('snippet', '')).strip()
        if not texto_s:
            continue
        if ape_norm and ape_norm not in _norm(texto_s):
            continue
        d = _minar_snippet(texto_s)
        d['snippet_raw'] = texto_s
        d['url']         = r['url']
        d['fuente']      = urlparse(r['url']).netloc if r['url'] else 'snippet'
        snippets_minados.append(d)
    print(f"         {len(snippets_minados)} snippets relevantes")

    # ── FASE 8: Visitar páginas de alto valor ─────────────────────────────────
    print("   [8/8] Visitando páginas de alto valor...")
    urls_ord = sorted(
        [r for r in todos_resultados if r.get('url','').startswith('http')],
        key=lambda r: next((i for i,d in enumerate(_URL_PRIORITY) if d in r['url'].lower()), 99)
    )
    extracciones = []
    for r in urls_ord[:8]:
        u = r['url']
        if any(s in u.lower() for s in _URL_BLACKLIST):
            continue
        print(f"         {urlparse(u).netloc}")
        if 'linkedin.com/in/' in u:
            datos = _extraer_linkedin(u, partes)
            texto_v = datos.get('resumen', '')
        else:
            datos = _extraer_pagina_generica(u, partes)
            texto_v = datos.get('texto', '')
        if texto_v and (not ape_norm or ape_norm in _norm(texto_v)):
            d_min = _minar_snippet(texto_v)
            d_min.update({'url': u, 'fuente': urlparse(u).netloc,
                          'texto': texto_v[:2000]})
            extracciones.append(d_min)
        time.sleep(_PAUSA_ENTRE)
    print(f"         {len(extracciones)} páginas útiles")

    # ── FASE 6.5: Directorios profesionales (CMP, gob.pe, hospitals) ─────────
    print("   [6.5/8] Directorios profesionales (gob.pe / CMP / hospitales)...")
    directorios = _buscar_directorios_profesionales(partes, dni)
    time.sleep(_PAUSA_ENTRE)

    # ── FASE 9: Fuentes institucionales directas (sin DuckDuckGo) ────────────
    # Siempre se ejecuta: garantiza datos incluso cuando DDG está bloqueado.
    # Cubre INEN, gob.pe resoluciones, ESSALUD, CMP, UPCH, etc.
    print("   [9/9] Fuentes institucionales directas (INEN / gob.pe / CMP)...")
    resultados_directos = _buscar_institucional_directo(partes, dni)
    for rd in resultados_directos:
        texto_rd   = rd.get('texto', '')
        snippet_rd = rd.get('snippet_raw', '')
        # Solo añadir si confirma apellido
        if ape_norm and ape_norm not in _norm(texto_rd + snippet_rd):
            continue
        if len(texto_rd) > 200:
            extracciones.append(rd)      # texto sustancial → extracción completa
        else:
            snippets_minados.append(rd)  # fragmento corto → snippet
    print(f"         {len(resultados_directos)} resultados directos → "
          f"extracciones={len(extracciones)} snippets={len(snippets_minados)}")
    time.sleep(_PAUSA_ENTRE)

    # ── Consolidar datos base ─────────────────────────────────────────────────
    cv_data = _consolidar(partes, todos_resultados, extracciones, cti,
                          snippets_minados=snippets_minados, alicia=alicia)
    cv_data['dni'] = dni

    # ── Enriquecer con directorios institucionales ────────────────────────────
    if directorios['encontrado']:
        # Preferir el cargo del directorio si es más específico (más largo)
        dir_cargo = directorios['cargo_institucional']
        if dir_cargo and len(dir_cargo) > len(cv_data.get('cargo_actual', '') or ''):
            cv_data['cargo_actual'] = dir_cargo
        if directorios['institucion_publica'] and not cv_data.get('empresa_actual'):
            cv_data['empresa_actual'] = directorios['institucion_publica']
        if directorios['colegio_profesional']:
            cv_data['colegio_profesional'] = directorios['colegio_profesional']
            cv_data['num_colegiatura']     = directorios.get('num_colegiatura', '')
        for u in directorios['fuentes']:
            if u not in cv_data['fuentes_urls']:
                cv_data['fuentes_urls'].append(u)
        # Boost de confianza si encontramos en documentos oficiales
        cv_data['score_confianza'] = min(100, cv_data['score_confianza'] + 10)
        cv_data['snippet_directorio'] = directorios['snippets'][:2]

    # ── Enriquecer con resultados directos (Fase 9) ───────────────────────────
    # Cargo, institución y cargo desde las fuentes institucionales directas
    snippets_directos = [
        rd.get('snippet_raw', rd.get('texto', ''))[:300]
        for rd in resultados_directos
        if rd.get('snippet_raw') or rd.get('texto')
    ]
    if snippets_directos:
        cv_data.setdefault('snippet_directorio', [])
        cv_data['snippet_directorio'] = list(dict.fromkeys(
            cv_data['snippet_directorio'] + snippets_directos
        ))[:5]
    # Cargo desde resultados directos (si aún no tenemos)
    for rd in resultados_directos:
        cargos_rd = rd.get('cargos', [])
        if cargos_rd and not cv_data.get('cargo_actual'):
            cv_data['cargo_actual'] = cargos_rd[0].strip().title()
        inst_rd = rd.get('instituciones', [])
        if inst_rd and not cv_data.get('empresa_actual'):
            cv_data['empresa_actual'] = inst_rd[0].strip()
        for inst in inst_rd:
            if inst and inst not in cv_data.get('instituciones', []):
                cv_data.setdefault('instituciones', []).append(inst)
        for u in [rd.get('url', '')]:
            if u and u not in cv_data.get('fuentes_urls', []):
                cv_data.setdefault('fuentes_urls', []).append(u)
    # Boost de confianza si fuentes directas aportaron datos
    if resultados_directos:
        boost_directo = min(15, len(resultados_directos) * 4)
        cv_data['score_confianza'] = min(100, cv_data['score_confianza'] + boost_directo)
        print(f"   [DIRECTO] Confianza +{boost_directo}% → {cv_data['score_confianza']}%")

    # ── Enriquecer con OpenAlex ───────────────────────────────────────────────
    if openalex['encontrado']:
        # Publicaciones: tomar el máximo entre todas las fuentes
        cv_data['publicaciones'] = max(
            cv_data['publicaciones'],
            openalex['publicaciones']
        )
        cv_data['citas_total']       = openalex['citas_total']
        cv_data['orcid']             = openalex['orcid']
        cv_data['obras_destacadas']  = openalex['obras_sample']
        # Mejorar años de experiencia con primera publicación OpenAlex
        if openalex['año_primera_pub'] and openalex['año_primera_pub'] > 1980:
            años_exp_oa = _ANO_ACTUAL - openalex['año_primera_pub']
            cv_data['anos_experiencia'] = max(cv_data['anos_experiencia'], años_exp_oa)
        if openalex['afiliaciones']:
            for af in openalex['afiliaciones']:
                if af not in cv_data['instituciones']:
                    cv_data['instituciones'].insert(0, af)
    else:
        cv_data.setdefault('citas_total', 0)
        cv_data.setdefault('orcid', '')
        cv_data.setdefault('obras_destacadas', [])

    # ── Enriquecer con Google Scholar ────────────────────────────────────────
    cv_data['scholar_h_index']   = scholar.get('h_index', 0)
    cv_data['scholar_i10_index'] = scholar.get('i10_index', 0)
    cv_data['scholar_areas']     = scholar.get('areas', [])
    if scholar['encontrado']:
        cv_data['publicaciones'] = max(cv_data['publicaciones'], scholar['publicaciones'])
        cv_data['citas_total']   = max(cv_data.get('citas_total', 0), scholar['citas_total'])
        if scholar.get('url') and scholar['url'] not in cv_data['fuentes_urls']:
            cv_data['fuentes_urls'].append(scholar['url'])

    # ── Enriquecer con RENATI ─────────────────────────────────────────────────
    cv_data['renati_encontrado']  = renati['encontrado']
    cv_data['renati_grado']       = renati['grado_maximo']
    cv_data['renati_universidades']= renati['universidades_grado']
    cv_data['renati_año_grado']   = renati['año_grado']
    # Si RENATI tiene dato de grado, tomarlo como fuente confiable
    if renati['grado_maximo']:
        grado_r = renati['grado_maximo'].lower()
        if 'doctor' in grado_r:
            cv_data['educacion']['doctorado']    = True
        elif 'maest' in grado_r or 'magist' in grado_r:
            cv_data['educacion']['maestria']     = True
        elif 'licenci' in grado_r or 'bachiller' in grado_r or 'título' in grado_r:
            cv_data['educacion']['licenciatura'] = True
        # Recalcular grado máximo
        if cv_data['educacion']['doctorado']:
            cv_data['educacion']['grado_maximo'] = 'Doctor/PhD'
        elif cv_data['educacion']['maestria']:
            cv_data['educacion']['grado_maximo'] = 'Magíster'
        elif cv_data['educacion']['licenciatura']:
            cv_data['educacion']['grado_maximo'] = 'Licenciado/Titulado'

    # ── Estimación de edad ────────────────────────────────────────────────────
    texto_total_completo = cv_data.get('texto_combinado', '')
    año_primera_act = 0
    if openalex.get('año_primera_pub') and openalex['año_primera_pub'] > 1975:
        año_primera_act = openalex['año_primera_pub']
    elif cv_data['anos_experiencia'] > 0:
        año_primera_act = _ANO_ACTUAL - cv_data['anos_experiencia']
    edad_info = _estimar_edad(texto_total_completo, año_primera_act)
    cv_data['edad_estimada']             = edad_info['edad_estimada']
    cv_data['año_nacimiento_estimado']   = edad_info['año_nacimiento_estimado']
    cv_data['metodo_edad']               = edad_info['metodo']

    # ── Resumen legible del perfil reconstruido ───────────────────────────────
    cv_data['resumen_perfil'] = _generar_resumen_perfil(cv_data)

    # ── ¿Encontró algo? ───────────────────────────────────────────────────────
    tiene_datos = (
        cv_data['educacion']['doctorado']    or
        cv_data['educacion']['maestria']     or
        cv_data['educacion']['licenciatura'] or
        cv_data['anos_experiencia'] > 0      or
        cv_data['cti_encontrado']            or
        cv_data['publicaciones'] > 0         or
        len(cv_data['instituciones']) > 0    or
        len(snippets_minados) > 0            or
        len(extracciones) > 0               or
        openalex['encontrado']               or
        renati['encontrado']
    )

    resultado_base['encontrado']  = tiene_datos
    resultado_base['cv_data']     = cv_data
    resultado_base['fuentes']     = [e.get('fuente','') for e in extracciones]
    resultado_base['openalex']    = openalex
    resultado_base['renati']      = renati
    resultado_base['scholar']     = scholar
    resultado_base['mensaje']     = (
        f"Perfil reconstruido — {len(snippets_minados)} snippets, "
        f"{len(extracciones)} páginas, {cv_data['publicaciones']} pubs, "
        f"confianza {cv_data['score_confianza']}%"
        if tiene_datos else
        f"Sin información web para '{partes['natural']}'"
    )
    print(f"\n   [WEB v2] >>> confianza={cv_data['score_confianza']}% | "
          f"grado={cv_data['educacion']['grado_maximo']} | "
          f"exp={cv_data['anos_experiencia']}a | "
          f"pubs={cv_data['publicaciones']} citas={cv_data.get('citas_total',0)} | "
          f"edad≈{cv_data['edad_estimada']} | "
          f"inst={len(cv_data['instituciones'])}")
    print(f"   Resumen: {cv_data['resumen_perfil'][:120]}...")
    return resultado_base


# ──────────────────────────────────────────────────────────────────────────────
#  GENERADOR DE RESUMEN LEGIBLE
# ──────────────────────────────────────────────────────────────────────────────
def _generar_resumen_perfil(cv: dict) -> str:
    """
    Genera un texto legible tipo 'ficha ejecutiva' del perfil reconstruido.
    Usado para mostrar en la UI y para el análisis de la rúbrica.
    """
    partes = []
    nombre = cv.get('nombre', '')
    if nombre:
        partes.append(f"{nombre}")

    grado = cv.get('educacion', {}).get('grado_maximo', '')
    if grado and grado != 'No determinado':
        partes.append(f"con grado de {grado}")

    renati_univs = cv.get('renati_universidades', [])
    if renati_univs:
        partes.append(f"— Grado en {', '.join(renati_univs[:2])}")

    instituciones = cv.get('instituciones', [])
    if instituciones:
        partes.append(f"— Vinculado a: {', '.join(instituciones[:3])}")

    años_exp = cv.get('anos_experiencia', 0)
    if años_exp > 0:
        partes.append(f"— {años_exp} años de experiencia")

    edad = cv.get('edad_estimada', 0)
    if edad > 0:
        partes.append(f"(~{edad} años de edad estimada)")

    pubs = cv.get('publicaciones', 0)
    citas = cv.get('citas_total', 0)
    if pubs > 0:
        pub_str = f"— {pubs} publicación{'es' if pubs != 1 else ''}"
        if citas > 0:
            pub_str += f" ({citas} citas)"
        partes.append(pub_str)

    h_idx = cv.get('scholar_h_index', 0)
    if h_idx > 0:
        partes.append(f"h-index={h_idx}")

    areas = cv.get('scholar_areas', [])
    if areas:
        partes.append(f"— Áreas: {', '.join(areas[:3])}")

    cargo = cv.get('cargo_actual', '')
    if cargo:
        partes.append(f"— Cargo: {cargo}")

    cti = cv.get('cti_investigador', False)
    if cti:
        partes.append("— Investigador registrado en CTI Vitae (CONCYTEC)")

    orcid = cv.get('orcid', '')
    if orcid:
        partes.append(f"— ORCID: {orcid}")

    idiomas = cv.get('idiomas', [])
    if idiomas:
        partes.append(f"— Idiomas: {', '.join(idiomas)}")

    score = cv.get('score_confianza', 0)
    partes.append(f"[Confianza: {score}%]")

    return ' '.join(partes)


# ──────────────────────────────────────────────────────────────────────────────
#  MODO STANDALONE (test rápido)
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    nombre_test = sys.argv[1] if len(sys.argv) > 1 else 'GARCIA PEREZ, JUAN CARLOS'
    dni_test    = sys.argv[2] if len(sys.argv) > 2 else ''
    r = buscar_cv_en_web(nombre_test, dni=dni_test, verbose=True)
    cv = r['cv_data'] or {}
    print('\n' + '='*60)
    print('FICHA ACADÉMICA RECONSTRUIDA')
    print('='*60)
    print(f"Nombre          : {cv.get('nombre','')}")
    print(f"Grado máximo    : {cv.get('educacion',{}).get('grado_maximo','?')}")
    print(f"RENATI grado    : {cv.get('renati_grado','?')} ({cv.get('renati_a\u00f1o_grado','?')})")
    print(f"Universidades   : {', '.join(cv.get('renati_universidades',[]))}")
    print(f"Edad estimada   : {cv.get('edad_estimada','?')} años (~nac {cv.get('a\u00f1o_nacimiento_estimado','?')})")
    print(f"Exp. total      : {cv.get('anos_experiencia','?')} años")
    print(f"Exp. docente    : {cv.get('experiencia_docente','?')} años")
    print(f"Publicaciones   : {cv.get('publicaciones','?')}")
    print(f"Citas totales   : {cv.get('citas_total','?')}")
    print(f"h-index         : {cv.get('scholar_h_index','?')}")
    print(f"ORCID           : {cv.get('orcid','')}")
    print(f"Instituciones   : {', '.join(cv.get('instituciones',[])[:4])}")
    print(f"Áreas Scholar   : {', '.join(cv.get('scholar_areas',[]))}")
    print(f"Idiomas         : {', '.join(cv.get('idiomas',[]))}")
    print(f"CTI Vitae       : {'Sí (investigador registrado)' if cv.get('cti_investigador') else 'No encontrado'}")
    print(f"Score confianza : {cv.get('score_confianza','?')}%")
    print(f"\nRESUMEN: {cv.get('resumen_perfil','')}")
    if '--json' in sys.argv:
        print('\n--- JSON COMPLETO ---')
        print(json.dumps(cv, indent=2, ensure_ascii=False))
