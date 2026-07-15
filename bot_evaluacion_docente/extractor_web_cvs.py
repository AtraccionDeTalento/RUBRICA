"""
Extractor de CVs desde CTI Vitae (CONCYTEC)
Extrae información de hojas de vida en línea
Con procesamiento paralelo para mayor velocidad
"""
import os
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import Dict, List, Callable, Optional
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# Variable global para tracking de progreso en tiempo real
_progress_lock = threading.Lock()
_progress_state = {
    "total": 0,
    "completados": 0,
    "exitosos": 0,
    "errores": 0,
    "tiempo_inicio": None,
    "tiempos_individuales": [],
    "registros_con_error": []
}


def get_extraction_progress():
    """Obtiene el estado actual del progreso de extracción"""
    with _progress_lock:
        return _progress_state.copy()


def reset_extraction_progress():
    """Reinicia el estado de progreso"""
    global _progress_state
    with _progress_lock:
        _progress_state = {
            "total": 0,
            "completados": 0,
            "exitosos": 0,
            "errores": 0,
            "tiempo_inicio": None,
            "tiempos_individuales": [],
            "registros_con_error": []
        }


class ExtractorWebCVs:
    """Extrae información de CVs desde páginas web de CTI Vitae"""
    
    # Configuración de reintentos y timeouts
    MAX_REINTENTOS = 3
    TIMEOUT_INICIAL = 35  # segundos
    TIMEOUT_INCREMENTO = 20  # segundos adicionales por cada reintento
    ESPERA_ENTRE_REINTENTOS = 2  # segundos
    
    # Timeout especial para re-análisis (perfiles problemáticos)
    TIMEOUT_REANALISIS = 180  # 3 minutos
    
    def __init__(self):
        self.session = requests.Session()
        # Headers más completos para simular un navegador real
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-PE,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
    
    def _hacer_peticion_con_reintentos(self, url: str) -> requests.Response:
        """
        Realiza petición HTTP con sistema de reintentos
        
        Args:
            url: URL a solicitar
            
        Returns:
            Response de requests
            
        Raises:
            requests.RequestException: Si fallan todos los reintentos
        """
        ultimo_error = None
        
        for intento in range(1, self.MAX_REINTENTOS + 1):
            try:
                timeout = self.TIMEOUT_INICIAL + (intento - 1) * self.TIMEOUT_INCREMENTO
                print(f"   📡 Intento {intento}/{self.MAX_REINTENTOS} (timeout={timeout}s)...")
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                return response
                
            except requests.Timeout as e:
                ultimo_error = e
                print(f"   ⏱️ Timeout en intento {intento}/{self.MAX_REINTENTOS} (timeout={timeout}s)")
                if intento < self.MAX_REINTENTOS:
                    print(f"   ⏳ Esperando {self.ESPERA_ENTRE_REINTENTOS}s antes de reintentar...")
                    time.sleep(self.ESPERA_ENTRE_REINTENTOS)
                    
            except requests.RequestException as e:
                ultimo_error = e
                print(f"   ⚠️ Error en intento {intento}/{self.MAX_REINTENTOS}: {type(e).__name__}")
                if intento < self.MAX_REINTENTOS:
                    time.sleep(self.ESPERA_ENTRE_REINTENTOS)
        
        # Si llegamos aquí, fallaron todos los reintentos
        raise ultimo_error
    
    def _hacer_peticion_reanalisis(self, url: str) -> requests.Response:
        """
        Petición especial para RE-ANÁLISIS con timeout extendido.
        TIEMPO TOTAL MÁXIMO: 5 minutos (300 segundos).
        Diseñado para perfiles problemáticos o con mucha información.
        
        Args:
            url: URL a solicitar
            
        Returns:
            Response de requests
        """
        TIEMPO_MAXIMO_TOTAL = 300  # 5 minutos máximo TOTAL
        TIMEOUT_POR_INTENTO = 90   # 1.5 minutos por intento
        
        tiempo_inicio = time.time()
        ultimo_error = None
        intento = 0
        
        while True:
            intento += 1
            tiempo_transcurrido = time.time() - tiempo_inicio
            tiempo_restante = TIEMPO_MAXIMO_TOTAL - tiempo_transcurrido
            
            # Si ya no queda tiempo, terminar
            if tiempo_restante <= 10:
                print(f"   ⏱️ Tiempo máximo alcanzado ({TIEMPO_MAXIMO_TOTAL}s)")
                break
            
            # Calcular timeout para este intento (máximo el tiempo restante)
            timeout = min(TIMEOUT_POR_INTENTO, tiempo_restante - 5)
            
            try:
                print(f"   🔄 Re-análisis intento {intento} (timeout={int(timeout)}s, restante={int(tiempo_restante)}s)...")
                
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                print(f"   ✅ Conexión exitosa en intento {intento} ({int(time.time() - tiempo_inicio)}s total)")
                return response
                
            except requests.Timeout as e:
                ultimo_error = e
                print(f"   ⏱️ Timeout en intento {intento}")
                # Pequeña pausa antes de reintentar
                if tiempo_restante > 15:
                    time.sleep(3)
                    
            except requests.RequestException as e:
                ultimo_error = e
                print(f"   ⚠️ Error de conexión en intento {intento}: {type(e).__name__}")
                if tiempo_restante > 15:
                    time.sleep(3)
        
        raise ultimo_error
    
    def _extraer_datos_desde_html(self, soup: BeautifulSoup, url: str) -> Dict:
        """
        Extrae datos estructurados del CV desde un soup ya parseado.
        Método interno usado por extraer_cv_desde_url y reanalizar_cv_individual.
        
        Args:
            soup: BeautifulSoup ya parseado del HTML
            url: URL original (para incluir en los datos)
            
        Returns:
            Diccionario con datos estructurados del CV
        """
        try:
            # CRÍTICO: Extraer texto completo para que el motor pueda analizarlo
            texto_completo = soup.get_text(separator=' ', strip=True)
            
            # Extraer datos estructurados
            publicaciones_data = self._extraer_publicaciones(soup)
            experiencia_laboral = self._extraer_experiencia_laboral(soup)
            
            # NUEVO: Extraer fecha de última actualización del perfil
            fecha_actualizacion, meses_sin_actualizar, perfil_desactualizado = self._extraer_fecha_actualizacion(soup, texto_completo)
            
            # NUEVO: Detectar si el perfil está vacío o en construcción
            perfil_vacio = self._detectar_perfil_vacio(soup, texto_completo)
            
            cv_data = {
                'nombre': self._extraer_nombre(soup),
                'anos_experiencia': self._extraer_experiencia(soup),
                'educacion': self._extraer_educacion(soup),
                'publicaciones': publicaciones_data.get('total', 0),
                'publicaciones_detalle': publicaciones_data,
                'proyectos': publicaciones_data.get('proyectos', 0),
                'experiencia_laboral': experiencia_laboral,
                'experiencia_docente': self._extraer_experiencia_docente(soup),
                'idiomas': self._extraer_idiomas(soup),
                'premios': self._extraer_premios(soup),
                'url': url,
                # CRÍTICO: Incluir texto completo para análisis del motor
                'texto_completo': texto_completo,
                'fuente': 'CTI_VITAE',
                # NUEVO: Información de estado del perfil
                'fecha_actualizacion': fecha_actualizacion,
                'meses_sin_actualizar': meses_sin_actualizar,
                'perfil_desactualizado': perfil_desactualizado,
                'perfil_vacio': perfil_vacio
            }
            
            return cv_data
            
        except Exception as e:
            print(f"   ❌ Error extrayendo datos del HTML: {e}")
            return self._cv_vacio(url)
    
    def extraer_cv_desde_url(self, url: str) -> Dict:
        """
        Extrae información completa de un CV desde CTI Vitae
        
        Args:
            url: URL del perfil de CTI Vitae
            
        Returns:
            Diccionario con datos estructurados del CV
        """
        try:
            print(f"\n🌐 Extrayendo CV desde: {url}")
            
            response = self._hacer_peticion_con_reintentos(url)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Usar método común de extracción
            cv_data = self._extraer_datos_desde_html(soup, url)
            
            # Mostrar resumen
            print(f"   ✓ Nombre: {cv_data['nombre']}")
            print(f"   ✓ Experiencia total: {cv_data['anos_experiencia']} años")
            print(f"   ✓ Experiencia docente: {cv_data['experiencia_docente']} años")
            print(f"   ✓ Educación: {cv_data['educacion']}")
            print(f"   ✓ Publicaciones: {cv_data.get('publicaciones_detalle', {})}")
            print(f"   ✓ Experiencia laboral: {len(cv_data.get('experiencia_laboral', []))} registros")
            if cv_data.get('fecha_actualizacion'):
                print(f"   📅 Última actualización: {cv_data['fecha_actualizacion']} ({cv_data.get('meses_sin_actualizar', 0)} meses)")
                if cv_data.get('perfil_desactualizado'):
                    print(f"   ⚠️ PERFIL DESACTUALIZADO (más de 6 meses)")
            if cv_data.get('perfil_vacio'):
                print(f"   ⚠️ PERFIL VACÍO/EN CONSTRUCCIÓN")
            
            return cv_data
            
        except requests.RequestException as e:
            print(f"   ❌ Error al acceder a URL: {e}")
            return self._cv_vacio(url)
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")
            return self._cv_vacio(url)
    
    def _extraer_nombre(self, soup: BeautifulSoup) -> str:
        """Extrae el nombre completo del investigador"""
        try:
            # Método 1: Buscar en el título H1 con clases específicas
            titulo = soup.find('h1', class_='tituloNombre')
            if titulo:
                nombre = titulo.get_text(strip=True)
                if nombre and len(nombre) > 2:
                    return nombre
            
            # Método 2: Buscar en tabla de datos personales
            tabla_personal = soup.find('table', {'class': 'tablaPersonal'})
            if tabla_personal:
                # Buscar apellidos
                apellidos_td = tabla_personal.find('td', string=re.compile(r'Apellidos?\s*:', re.IGNORECASE))
                nombres_td = tabla_personal.find('td', string=re.compile(r'Nombres?\s*:', re.IGNORECASE))
                
                if apellidos_td and nombres_td:
                    apellido_val = apellidos_td.find_next_sibling('td')
                    nombre_val = nombres_td.find_next_sibling('td')
                    
                    if apellido_val and nombre_val:
                        return f"{nombre_val.get_text(strip=True)} {apellido_val.get_text(strip=True)}"
            
            # Método 3: Buscar en secciones con texto "Apellidos" y "Nombres"
            todas_celdas = soup.find_all('td')
            apellidos_val = None
            nombres_val = None
            
            for i, celda in enumerate(todas_celdas):
                texto = celda.get_text(strip=True)
                
                if re.match(r'^Apellidos?\s*:?$', texto, re.IGNORECASE) and i + 1 < len(todas_celdas):
                    apellidos_val = todas_celdas[i + 1].get_text(strip=True)
                
                if re.match(r'^Nombres?\s*:?$', texto, re.IGNORECASE) and i + 1 < len(todas_celdas):
                    nombres_val = todas_celdas[i + 1].get_text(strip=True)
            
            if apellidos_val and nombres_val:
                nombre_completo = f"{nombres_val} {apellidos_val}"
                # Limpiar espacios múltiples y saltos de línea
                nombre_completo = ' '.join(nombre_completo.split())
                return nombre_completo
            
            # Método 4: Buscar en metadatos
            meta_title = soup.find('meta', {'property': 'og:title'})
            if meta_title and meta_title.get('content'):
                return meta_title['content']
            
            # Método 5: Buscar en el title de la página
            title = soup.find('title')
            if title:
                titulo_texto = title.get_text(strip=True)
                # Extraer nombre del título si tiene formato "Nombre - CTI Vitae"
                if '-' in titulo_texto:
                    nombre = titulo_texto.split('-')[0].strip()
                    if len(nombre) > 2:
                        print(f"   📛 Nombre extraído del título de página")
                        return nombre
            
            # Método 6: Buscar en spans o divs con estilos de nombre
            for tag in ['span', 'div', 'p']:
                elementos = soup.find_all(tag)
                for elem in elementos:
                    texto = elem.get_text(strip=True)
                    # Buscar patrones de nombre completo (2-4 palabras con mayúsculas)
                    if re.match(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,4}$', texto):
                        if 5 < len(texto) < 60:  # Longitud razonable para un nombre
                            print(f"   📛 Nombre extraído de elemento {tag}")
                            return texto
            
            print(f"   ⚠️ No se pudo extraer nombre con ningún método")
            return "Nombre no encontrado"
            
        except Exception as e:
            print(f"   ❌ Error extrayendo nombre: {e}")
            return "Nombre no encontrado"
    
    def _extraer_experiencia(self, soup: BeautifulSoup) -> int:
        """
        Calcula años de experiencia total basado en experiencia laboral
        Maneja correctamente períodos, solapamientos y meses
        """
        try:
            periodos = []  # Lista de tuplas (ano_inicio, ano_fin, meses_duracion)
            
            # Buscar tabla de experiencia laboral o experiencia profesional
            experiencia_section = soup.find(string=re.compile(r'EXPERIENCIA (LABORAL|PROFESIONAL)', re.IGNORECASE))
            if experiencia_section:
                tabla = experiencia_section.find_parent('table') or experiencia_section.find_next('table')
                
                if tabla:
                    filas = tabla.find_all('tr')
                    
                    for fila in filas:
                        celdas = fila.find_all('td')
                        
                        # Buscar fechas (Fecha Inicio / Fecha Fin)
                        for i, celda in enumerate(celdas):
                            texto = celda.get_text(strip=True)
                            
                            if 'Fecha Inicio' in texto and i + 1 < len(celdas):
                                try:
                                    fecha_inicio_texto = celdas[i + 1].get_text(strip=True)
                                    fecha_fin_texto = celdas[i + 3].get_text(strip=True) if i + 3 < len(celdas) else ''
                                    
                                    # Extraer información completa de fecha
                                    info_inicio = self._extraer_fecha_completa(fecha_inicio_texto)
                                    info_fin = self._extraer_fecha_completa(fecha_fin_texto) if fecha_fin_texto else None
                                    
                                    if info_inicio:
                                        ano_inicio = info_inicio['ano']
                                        mes_inicio = info_inicio['mes']
                                        
                                        # Si no hay fecha fin, asumir hasta ahora
                                        if not info_fin:
                                            ano_fin = datetime.now().year
                                            mes_fin = datetime.now().month
                                        else:
                                            ano_fin = info_fin['ano']
                                            mes_fin = info_fin['mes']
                                        
                                        # Calcular duración en meses
                                        meses_totales = (ano_fin - ano_inicio) * 12 + (mes_fin - mes_inicio)
                                        
                                        if meses_totales > 0 and meses_totales < 600:  # Máximo 50 años
                                            periodos.append((ano_inicio, ano_fin, meses_totales))
                                        
                                except Exception as e:
                                    continue
            
            # Si no se encontraron períodos específicos, buscar rangos de fechas en el texto
            if not periodos:
                texto_completo = soup.get_text()
                
                # Buscar patrones: "Mes AAAA - Mes AAAA" o "Mes AAAA – Mes AAAA"
                # Ejemplos: "Setiembre 2017 - Febrero 2020", "Enero 2022 – Octubre 2022"
                patron_mes_completo = r'([A-Za-zñáéíóú]+)\s+(\d{4})\s*[-–—a]\s*([A-Za-zñáéíóú]+)\s+(\d{4})'
                matches_mes = re.findall(patron_mes_completo, texto_completo, re.IGNORECASE)
                
                for match in matches_mes:
                    try:
                        mes_inicio_txt, ano_inicio_txt, mes_fin_txt, ano_fin_txt = match
                        
                        info_inicio = self._extraer_fecha_completa(f"{mes_inicio_txt} {ano_inicio_txt}")
                        info_fin = self._extraer_fecha_completa(f"{mes_fin_txt} {ano_fin_txt}")
                        
                        if info_inicio and info_fin:
                            ano_inicio = info_inicio['ano']
                            mes_inicio = info_inicio['mes']
                            ano_fin = info_fin['ano']
                            mes_fin = info_fin['mes']
                            
                            meses_totales = (ano_fin - ano_inicio) * 12 + (mes_fin - mes_inicio)
                            
                            if 0 < meses_totales < 600:
                                periodos.append((ano_inicio, ano_fin, meses_totales))
                    except:
                        continue
                
                # Buscar patrones: "Mes AAAA - Actualidad/Presente"
                patron_presente = r'([A-Za-zñáéíóú]+)\s+(\d{4})\s*[-–—]\s*(actualidad|presente|actual|hoy|today)'
                matches_presente = re.findall(patron_presente, texto_completo, re.IGNORECASE)
                
                for match in matches_presente:
                    try:
                        mes_inicio_txt, ano_inicio_txt, _ = match
                        info_inicio = self._extraer_fecha_completa(f"{mes_inicio_txt} {ano_inicio_txt}")
                        
                        if info_inicio:
                            ano_inicio = info_inicio['ano']
                            mes_inicio = info_inicio['mes']
                            ano_fin = datetime.now().year
                            mes_fin = datetime.now().month
                            
                            meses_totales = (ano_fin - ano_inicio) * 12 + (mes_fin - mes_inicio)
                            
                            if 0 < meses_totales < 600:
                                periodos.append((ano_inicio, ano_fin, meses_totales))
                    except:
                        continue
                
                # Fallback: buscar solo años (AAAA - AAAA)
                if not periodos:
                    matches_anos = re.findall(r'(\d{4})\s*[-–—]\s*(\d{4}|presente|actual)', texto_completo, re.IGNORECASE)
                    
                    for match in matches_anos:
                        ano_inicio = int(match[0])
                        ano_fin = datetime.now().year if match[1].lower() in ['presente', 'actual', 'actualidad'] else int(match[1])
                        
                        if 1980 <= ano_inicio <= datetime.now().year and ano_inicio <= ano_fin:
                            meses_totales = (ano_fin - ano_inicio) * 12
                            periodos.append((ano_inicio, ano_fin, meses_totales))
            
            # Eliminar solapamientos y calcular experiencia total
            if periodos:
                experiencia_total_meses = self._calcular_experiencia_sin_solapes(periodos)
                return min(experiencia_total_meses / 12, 50)  # Convertir a años, máximo 50
            
            return 0
            
        except Exception as e:
            print(f"   Error calculando experiencia: {e}")
            return 0
    
    def _extraer_fecha_completa(self, texto: str) -> Dict:
        """
        Extrae año y mes de un texto de fecha en español o inglés
        Soporta: "Setiembre 2017", "Febrero 2020", "09/2017", etc.
        Retorna: {'ano': int, 'mes': int} o None si no puede parsear
        """
        try:
            # Mapeo completo de meses en español e inglés (incluye setiembre y septiembre)
            meses_map = {
                # Español
                'enero': 1, 'ene': 1,
                'febrero': 2, 'feb': 2,
                'marzo': 3, 'mar': 3,
                'abril': 4, 'abr': 4,
                'mayo': 5,
                'junio': 6, 'jun': 6,
                'julio': 7, 'jul': 7,
                'agosto': 8, 'ago': 8,
                'septiembre': 9, 'setiembre': 9, 'sep': 9, 'set': 9, 'sept': 9,
                'octubre': 10, 'oct': 10,
                'noviembre': 11, 'nov': 11,
                'diciembre': 12, 'dic': 12,
                # Inglés
                'january': 1, 'jan': 1,
                'february': 2,
                'march': 3,
                'april': 4, 'apr': 4,
                'may': 5,
                'june': 6,
                'july': 7,
                'august': 8, 'aug': 8,
                'september': 9,
                'october': 10,
                'november': 11,
                'december': 12, 'dec': 12
            }
            
            texto_lower = texto.lower().strip()
            
            # Si dice "actualidad" o "presente", devolver fecha actual
            if any(palabra in texto_lower for palabra in ['actualidad', 'presente', 'actual', 'hoy', 'today']):
                return {'ano': datetime.now().year, 'mes': datetime.now().month}
            
            # Buscar año (formato YYYY)
            match_ano = re.search(r'(19\d{2}|20\d{2})', texto)
            if not match_ano:
                return None
            
            ano = int(match_ano.group(1))
            
            # Buscar mes en texto (priorizar coincidencias más largas primero)
            mes = 1  # Default: enero si no se encuentra
            mes_encontrado = False
            
            # Ordenar por longitud descendente para priorizar "septiembre" sobre "sep"
            meses_ordenados = sorted(meses_map.items(), key=lambda x: len(x[0]), reverse=True)
            
            for mes_nombre, mes_num in meses_ordenados:
                if mes_nombre in texto_lower:
                    mes = mes_num
                    mes_encontrado = True
                    break
            
            # También buscar formato numérico (MM/YYYY o DD/MM/YYYY)
            match_mes = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', texto)
            if match_mes:
                mes = int(match_mes.group(2))
                mes_encontrado = True
            elif re.search(r'(\d{1,2})/(\d{4})', texto):
                match_mes = re.search(r'(\d{1,2})/(\d{4})', texto)
                mes = int(match_mes.group(1))
            
            return {'ano': ano, 'mes': max(1, min(12, mes))}
            
        except Exception as e:
            return None
    
    def _calcular_experiencia_sin_solapes(self, periodos: List[tuple]) -> int:
        """
        Calcula experiencia total en meses eliminando solapamientos
        periodos: lista de tuplas (ano_inicio, ano_fin, meses_duracion)
        """
        if not periodos:
            return 0
        
        # Ordenar períodos por fecha de inicio
        periodos_ordenados = sorted(periodos, key=lambda x: x[0])
        
        # Unir períodos solapados
        periodos_unidos = []
        periodo_actual = periodos_ordenados[0]
        
        for i in range(1, len(periodos_ordenados)):
            siguiente = periodos_ordenados[i]
            
            # Si hay solapamiento, extender el período actual
            if siguiente[0] <= periodo_actual[1]:
                periodo_actual = (periodo_actual[0], max(periodo_actual[1], siguiente[1]), 0)
            else:
                # No hay solapamiento, guardar periodo actual y empezar uno nuevo
                periodos_unidos.append(periodo_actual)
                periodo_actual = siguiente
        
        # Agregar el último período
        periodos_unidos.append(periodo_actual)
        
        # Calcular total de meses
        total_meses = 0
        for periodo in periodos_unidos:
            meses = (periodo[1] - periodo[0]) * 12
            total_meses += meses
        
        return total_meses
    
    def _extraer_ano(self, texto: str) -> int:
        """Extrae año de un texto de fecha"""
        try:
            match = re.search(r'(\d{4})', texto)
            return int(match.group(1)) if match else None
        except:
            return None
    
    def _extraer_educacion(self, soup: BeautifulSoup) -> Dict:
        """
        Extrae nivel máximo de educación desde tablas estructuradas de CTI Vitae
        REGLA CRÍTICA: Solo cuenta grados OBTENIDOS y verificables
        
        Busca en AMBAS secciones:
        - FORMACIÓN ACADÉMICA (FUENTE: SUNEDU) - Grados verificados oficialmente
        - FORMACIÓN ACADÉMICA (FUENTE: MANUAL) - Grados autodeclarados (usados para grados extranjeros)
        """
        educacion = {
            'doctorado': False,
            'doctorado_completo': False,
            'maestria': False,
            'maestria_completa': False,
            'licenciatura': False
        }
        
        try:
            grados_obtenidos = []
            grados_en_curso = []
            fuentes_encontradas = []
            
            # ============================================================
            # MÉTODO 1: Buscar en todas las tablas de la página
            # Esto incluye tanto SUNEDU como MANUAL
            # ============================================================
            all_tables = soup.find_all('table')
            print(f"   📊 Analizando {len(all_tables)} tablas para educación...")
            
            for tabla in all_tables:
                filas = tabla.find_all('tr')
                
                for fila in filas:
                    celdas = fila.find_all('td')
                    if len(celdas) >= 2:
                        celda_grado = celdas[0].get_text(strip=True).upper()
                        celda_titulo = celdas[1].get_text(strip=True).upper() if len(celdas) > 1 else ""
                        fila_completa = fila.get_text(strip=True).upper()
                        
                        # DETECTAR DOCTORADO
                        if 'DOCTOR' in celda_grado or 'DOCTORADO' in celda_grado or 'PHD' in celda_grado or 'PH.D' in celda_grado:
                            # Verificar que NO sea "en curso" o "candidato"
                            if '(C)' not in celda_titulo and 'CANDIDATO' not in celda_titulo and 'EN CURSO' not in fila_completa:
                                educacion['doctorado'] = True
                                educacion['doctorado_completo'] = True
                                institucion = celdas[2].get_text(strip=True) if len(celdas) > 2 else ""
                                grados_obtenidos.append(f'DOCTORADO ({institucion[:30]}...)')
                            else:
                                grados_en_curso.append('DOCTORADO_EN_CURSO')
                        
                        # DETECTAR MAESTRÍA
                        elif any(x in celda_grado for x in ['MAGISTER', 'MAESTR', 'MÁSTER', 'MASTER', 'MBA', 'M.SC', 'MSC']):
                            # Verificar que NO sea "en curso" o "candidato"
                            if '(C)' not in celda_titulo and 'CANDIDATO' not in celda_titulo and 'EN CURSO' not in fila_completa:
                                # Verificar fecha fin si está disponible
                                fecha_fin = celdas[-1].get_text(strip=True) if len(celdas) >= 5 else ""
                                
                                if fecha_fin or len(celdas) <= 5:  # Tabla de obtenidos tiene menos columnas
                                    educacion['maestria'] = True
                                    educacion['maestria_completa'] = True
                                    institucion = celdas[2].get_text(strip=True) if len(celdas) > 2 else ""
                                    grados_obtenidos.append(f'MAESTRIA ({institucion[:30]}...)')
                            else:
                                grados_en_curso.append('MAESTRIA_EN_CURSO')
                        
                        # DETECTAR LICENCIATURA/TITULO
                        elif any(x in celda_grado for x in ['LICENCIADO', 'BACHILLER', 'INGENIER', 'TÍTULO', 'TITULO']):
                            educacion['licenciatura'] = True
                            grados_obtenidos.append('LICENCIATURA')
            
            # ============================================================
            # MÉTODO 2 (FALLBACK): Buscar en texto completo si no se encontró nada
            # Esto ayuda cuando el HTML tiene formato diferente
            # ============================================================
            if not educacion['doctorado'] and not educacion['maestria']:
                texto_completo = soup.get_text().upper()
                
                # Buscar patrones de doctorado en texto
                patrones_doctorado = [
                    r'DOCTOR\s+(EN|DE|IN)\s+\w+',
                    r'DOCTORADO\s+(EN|DE)\s+\w+',
                    r'PH\.?D\.?\s+',
                    r'GRADO\s+DE\s+DOCTOR'
                ]
                
                for patron in patrones_doctorado:
                    if re.search(patron, texto_completo):
                        # Verificar que no sea candidato
                        if 'CANDIDATO A DOCTOR' not in texto_completo and 'DOCTORADO (C)' not in texto_completo:
                            educacion['doctorado'] = True
                            educacion['doctorado_completo'] = True
                            grados_obtenidos.append('DOCTORADO (detectado en texto)')
                            break
                
                # Buscar patrones de maestría en texto
                patrones_maestria = [
                    r'MAGIST[EÉ]?R\s+(EN|DE|IN)\s+\w+',
                    r'MAESTR[IÍ]A\s+(EN|DE)\s+\w+',
                    r'MASTER\s+(EN|OF|IN|DE)\s+\w+',
                    r'M\.?SC\.?\s+',
                    r'MBA\s+'
                ]
                
                for patron in patrones_maestria:
                    if re.search(patron, texto_completo):
                        # Verificar que no sea candidato
                        if 'CANDIDATO A MAGISTER' not in texto_completo and 'MAESTRIA (C)' not in texto_completo:
                            educacion['maestria'] = True
                            educacion['maestria_completa'] = True
                            grados_obtenidos.append('MAESTRIA (detectado en texto)')
                            break
            
            # Si solo tiene maestría/doctorado en curso pero no completa
            if 'MAESTRIA_EN_CURSO' in grados_en_curso and not educacion['maestria_completa']:
                educacion['maestria'] = True
            
            if 'DOCTORADO_EN_CURSO' in grados_en_curso and not educacion['doctorado_completo']:
                educacion['doctorado'] = True
            
            print(f"   ✓ Grados obtenidos: {grados_obtenidos if grados_obtenidos else 'Ninguno'}")
            if grados_en_curso:
                print(f"   ⏳ Grados en curso: {grados_en_curso}")
            
        except Exception as e:
            print(f"   ❌ Error extrayendo educación: {e}")
            import traceback
            traceback.print_exc()
        
        return educacion
    
    def _extraer_publicaciones(self, soup: BeautifulSoup) -> Dict:
        """
        Cuenta publicaciones científicas detalladamente
        Retorna diccionario con conteos por tipo
        """
        try:
            resultado = {
                'total': 0,
                'libros': 0,
                'articulos': 0,
                'articulos_indexados': 0,
                'proyectos': 0,
                'tiene_scopus': False,
                'tiene_wos': False
            }
            
            texto_completo = soup.get_text().upper()
            
            # ============================================================
            # MÉTODO 1: Buscar sección "PRODUCCIÓN CIENTÍFICA"
            # ============================================================
            all_tables = soup.find_all('table')
            
            for tabla in all_tables:
                tabla_text = tabla.get_text().upper()
                
                # Buscar elementos anteriores para contexto
                prev_text = ""
                for prev in tabla.previous_siblings:
                    if hasattr(prev, 'get_text'):
                        prev_text += prev.get_text().upper() + " "
                    if len(prev_text) > 500:
                        break
                
                # PRODUCCIÓN CIENTÍFICA (Scopus, WoS)
                if 'PRODUCCIÓN CIENTÍFICA' in prev_text or 'PRODUCCION CIENTIFICA' in prev_text:
                    filas = tabla.find_all('tr')
                    for fila in filas[1:]:
                        celdas = fila.find_all('td')
                        if celdas:
                            tipo = celdas[0].get_text(strip=True).upper() if len(celdas) > 0 else ""
                            fila_text = fila.get_text().upper()
                            
                            if 'ARTÍCULO' in tipo or 'ARTICULO' in tipo or 'REVIEW' in tipo:
                                resultado['articulos_indexados'] += 1
                                resultado['total'] += 1
                            
                            # Detectar Scopus/WoS
                            if 'SCOPUS' in fila_text:
                                resultado['tiene_scopus'] = True
                            if 'WOS' in fila_text or 'WEB OF SCIENCE' in fila_text:
                                resultado['tiene_wos'] = True
                            if 'Q1' in fila_text or 'Q2' in fila_text:
                                resultado['tiene_scopus'] = True
                
                # OTRAS PRODUCCIONES (libros, artículos no indexados)
                if 'OTRAS PRODUCCIONES' in prev_text:
                    filas = tabla.find_all('tr')
                    for fila in filas[1:]:
                        celdas = fila.find_all('td')
                        if celdas:
                            tipo = celdas[0].get_text(strip=True).upper() if len(celdas) > 0 else ""
                            
                            if 'LIBRO' in tipo:
                                resultado['libros'] += 1
                                resultado['total'] += 1
                                print(f"   📖 Libro encontrado")
                            elif 'ARTÍCULO' in tipo or 'ARTICULO' in tipo:
                                resultado['articulos'] += 1
                                resultado['total'] += 1
                                print(f"   📄 Artículo encontrado")
                
                # PROYECTOS DE INVESTIGACIÓN
                if 'PROYECTOS DE INVESTIGACIÓN' in prev_text or 'PROYECTOS DE INVESTIGACION' in prev_text:
                    filas = tabla.find_all('tr')
                    count_proyectos = max(0, len(filas) - 1)
                    resultado['proyectos'] = count_proyectos
                    if count_proyectos > 0:
                        print(f"   🔬 {count_proyectos} proyecto(s) de investigación")
            
            # ============================================================
            # MÉTODO 2: Conteo por palabras clave en texto completo
            # SOLO si hay filas con datos reales en las tablas
            # ============================================================
            # NO buscar por palabras clave genéricas ya que "SCOPUS", "WOS", etc.
            # aparecen en los encabezados de tablas vacías de CTI Vitae
            
            # IMPORTANTE: Solo marcar Scopus/WoS si se encontraron artículos indexados REALES
            # Las palabras "SCOPUS" y "WOS" aparecen en encabezados de tablas vacías
            if resultado['articulos_indexados'] == 0:
                resultado['tiene_scopus'] = False
                resultado['tiene_wos'] = False
            
            print(f"   ✓ Publicaciones: {resultado['total']} (Libros: {resultado['libros']}, Artículos: {resultado['articulos']}, Indexados: {resultado['articulos_indexados']})")
            
            return resultado
            
        except Exception as e:
            print(f"   Error extrayendo publicaciones: {e}")
            return {'total': 0, 'libros': 0, 'articulos': 0, 'articulos_indexados': 0, 'proyectos': 0, 'tiene_scopus': False, 'tiene_wos': False}
    
    def _extraer_proyectos(self, soup: BeautifulSoup) -> int:
        """Cuenta proyectos de investigación"""
        try:
            count = 0
            
            # Buscar sección de proyectos
            proyectos_section = soup.find(string=re.compile(r'PROYECTOS?', re.IGNORECASE))
            
            if proyectos_section:
                tabla = proyectos_section.find_parent('table') or proyectos_section.find_next('table')
                
                if tabla:
                    filas = tabla.find_all('tr')
                    count = max(0, len(filas) - 1)
            
            return count
            
        except Exception as e:
            return 0
    
    def _extraer_experiencia_laboral(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrae lista de experiencias laborales"""
        experiencias = []
        
        try:
            experiencia_section = soup.find(string=re.compile(r'EXPERIENCIA LABORAL', re.IGNORECASE))
            
            if experiencia_section:
                tabla = experiencia_section.find_parent('table') or experiencia_section.find_next('table')
                
                if tabla:
                    filas = tabla.find_all('tr')
                    
                    experiencia_actual = {}
                    for fila in filas:
                        celdas = fila.find_all('td')
                        
                        if len(celdas) >= 2:
                            campo = celdas[0].get_text(strip=True)
                            valor = celdas[1].get_text(strip=True)
                            
                            if 'Institución' in campo:
                                if experiencia_actual:
                                    experiencias.append(experiencia_actual)
                                experiencia_actual = {'institucion': valor}
                            elif 'Cargo' in campo:
                                experiencia_actual['cargo'] = valor
                            elif 'Fecha Inicio' in campo:
                                experiencia_actual['fecha_inicio'] = valor
                            elif 'Fecha Fin' in campo:
                                experiencia_actual['fecha_fin'] = valor
                    
                    if experiencia_actual:
                        experiencias.append(experiencia_actual)
        
        except Exception as e:
            pass
        
        return experiencias
    
    def _extraer_experiencia_docente(self, soup: BeautifulSoup) -> int:
        """
        Calcula años de experiencia docente específicamente
        Busca PRIMERO en 'EXPERIENCIA LABORAL COMO DOCENTE' (sección específica de CTI Vitae)
        y luego en 'Experiencia Laboral' general si tiene cargos docentes
        """
        try:
            periodos_docentes = []
            texto_completo = soup.get_text()
            
            # ============================================================
            # MÉTODO 1: Buscar sección específica "EXPERIENCIA LABORAL COMO DOCENTE"
            # Esta es la sección principal en CTI Vitae para experiencia docente
            # ============================================================
            
            # Buscar todas las tablas y analizar su contexto
            all_tables = soup.find_all('table')
            
            for tabla in all_tables:
                # Verificar si esta tabla está después del título "EXPERIENCIA LABORAL COMO DOCENTE"
                tabla_text = tabla.get_text().upper()
                
                # Buscar el encabezado anterior a la tabla
                prev_elements = []
                for prev in tabla.previous_siblings:
                    if hasattr(prev, 'get_text'):
                        prev_elements.append(prev.get_text())
                    if len(prev_elements) > 5:
                        break
                
                prev_text = ' '.join(prev_elements).upper()
                
                # Si encontramos la sección de docencia
                if 'EXPERIENCIA LABORAL COMO DOCENTE' in prev_text or 'EXPERIENCIA LABORAL COMO DOCENTE' in tabla_text:
                    filas = tabla.find_all('tr')
                    
                    for fila in filas[1:]:  # Saltar encabezado
                        celdas = fila.find_all('td')
                        
                        if len(celdas) >= 5:
                            # Formato típico: Institución | Tipo | Tipo Docente | Descripción | Fecha Inicio | Fecha Fin
                            fecha_inicio_texto = celdas[-2].get_text(strip=True) if len(celdas) >= 2 else ""
                            fecha_fin_texto = celdas[-1].get_text(strip=True) if len(celdas) >= 1 else ""
                            
                            info_inicio = self._extraer_fecha_completa(fecha_inicio_texto)
                            info_fin = self._extraer_fecha_completa(fecha_fin_texto) if fecha_fin_texto else None
                            
                            if info_inicio:
                                ano_inicio = info_inicio['ano']
                                mes_inicio = info_inicio['mes']
                                
                                # Si dice "actualidad" o no tiene fecha fin
                                if not info_fin or 'actual' in fecha_fin_texto.lower():
                                    ano_fin = datetime.now().year
                                    mes_fin = datetime.now().month
                                else:
                                    ano_fin = info_fin['ano']
                                    mes_fin = info_fin['mes']
                                
                                meses_totales = (ano_fin - ano_inicio) * 12 + (mes_fin - mes_inicio)
                                
                                if meses_totales > 0 and meses_totales < 1200:  # Máximo 100 años
                                    periodos_docentes.append((ano_inicio, ano_fin, meses_totales))
                                    print(f"   📚 Exp. Docente encontrada: {ano_inicio} - {ano_fin} ({meses_totales} meses)")
            
            # ============================================================
            # MÉTODO 2: Buscar patrones de fechas en texto para docencia
            # Ejemplo: "Junio 1985" hasta "A la actualidad"
            # ============================================================
            
            if not periodos_docentes:
                # Buscar patrones como "Junio 1985" o "1985" en contexto docente
                patron_docente_fecha = r'(docente|profesor|catedr[aá]tico|investigador)[^\d]*(\w+\s+)?(\d{4})\s*[-–]\s*(\w+\s+)?(\d{4}|actualidad|actual|presente)'
                matches = re.findall(patron_docente_fecha, texto_completo, re.IGNORECASE)
                
                for match in matches:
                    try:
                        ano_inicio = int(match[2])
                        if match[4].lower() in ['actualidad', 'actual', 'presente']:
                            ano_fin = datetime.now().year
                        else:
                            ano_fin = int(match[4])
                        
                        meses_totales = (ano_fin - ano_inicio) * 12
                        if 0 < meses_totales < 1200:
                            periodos_docentes.append((ano_inicio, ano_fin, meses_totales))
                    except:
                        continue
            
            # ============================================================
            # MÉTODO 3: Extraer de la tabla de experiencia laboral general
            # ============================================================
            
            if not periodos_docentes:
                experiencia_section = soup.find(string=re.compile(r'EXPERIENCIA LABORAL$', re.IGNORECASE))
                
                if experiencia_section:
                    tabla = experiencia_section.find_parent('table') or experiencia_section.find_next('table')
                    
                    if tabla:
                        filas = tabla.find_all('tr')
                        
                        for fila in filas[1:]:  # Saltar encabezado
                            celdas = fila.find_all('td')
                            texto_fila = fila.get_text().lower()
                            
                            # Verificar si es cargo docente
                            keywords_docente = ['docente', 'profesor', 'catedrático', 'catedratico',
                                               'instructor', 'maestro', 'teaching', 'lecturer',
                                               'investigador', 'investigadora', 'editora', 'editor',
                                               'asesora', 'asesor']
                            es_universidad_fila = 'universidad' in texto_fila or 'universidade' in texto_fila
                            es_docente = any(kw in texto_fila for kw in keywords_docente) or \
                                         (es_universidad_fila and any(kw in texto_fila for kw in [
                                             'director', 'directora', 'coordinador', 'coordinadora',
                                             'apoyo', 'encargado', 'responsable',
                                         ]))
                            
                            if es_docente and len(celdas) >= 5:
                                fecha_inicio_texto = celdas[-2].get_text(strip=True)
                                fecha_fin_texto = celdas[-1].get_text(strip=True)
                                
                                info_inicio = self._extraer_fecha_completa(fecha_inicio_texto)
                                info_fin = self._extraer_fecha_completa(fecha_fin_texto) if fecha_fin_texto else None
                                
                                if info_inicio:
                                    ano_inicio = info_inicio['ano']
                                    mes_inicio = info_inicio['mes']
                                    
                                    if not info_fin or 'actual' in fecha_fin_texto.lower():
                                        ano_fin = datetime.now().year
                                        mes_fin = datetime.now().month
                                    else:
                                        ano_fin = info_fin['ano']
                                        mes_fin = info_fin['mes']
                                    
                                    meses_totales = (ano_fin - ano_inicio) * 12 + (mes_fin - mes_inicio)
                                    
                                    if 0 < meses_totales < 1200:
                                        periodos_docentes.append((ano_inicio, ano_fin, meses_totales))
            
            # Calcular total sin solapamientos
            if periodos_docentes:
                meses_totales = self._calcular_experiencia_sin_solapes(periodos_docentes)
                # FIX: usar round() en vez de int() para no truncar meses parciales.
                # Ej: 7 meses = 0.58 años con round(), pero 0 con int() → puntaje incorrecto.
                anos = round(meses_totales / 12, 2)
                print(f"   ✓ Total experiencia docente: {anos} años ({meses_totales} meses)")
                return min(anos, 50)  # Máximo 50 años
            
            return 0
            
        except Exception as e:
            print(f"   Error calculando experiencia docente: {e}")
            return 0
    
    def _extraer_idiomas(self, soup: BeautifulSoup) -> List[str]:
        """Extrae idiomas que domina"""
        idiomas = []
        
        try:
            texto = soup.get_text().lower()
            
            idiomas_comunes = ['inglés', 'ingles', 'portugués', 'portugues', 'francés', 'frances', 
                              'alemán', 'aleman', 'italiano', 'chino', 'japonés', 'japones']
            
            for idioma in idiomas_comunes:
                if idioma in texto:
                    idiomas.append(idioma.capitalize())
            
            # Eliminar duplicados
            idiomas = list(set(idiomas))
            
        except Exception as e:
            pass
        
        return idiomas
    
    def _extraer_premios(self, soup: BeautifulSoup) -> List[str]:
        """Extrae premios y reconocimientos"""
        premios = []
        
        try:
            premios_section = soup.find(string=re.compile(r'PREMIOS?|RECONOCIMIENTOS?|DISTINCIONES?', re.IGNORECASE))
            
            if premios_section:
                tabla = premios_section.find_parent('table') or premios_section.find_next('table')
                
                if tabla:
                    filas = tabla.find_all('tr')
                    
                    for fila in filas[1:]:  # Saltar encabezado
                        celdas = fila.find_all('td')
                        if celdas:
                            premio = ' '.join([c.get_text(strip=True) for c in celdas])
                            if premio:
                                premios.append(premio)
        
        except Exception as e:
            pass
        
        return premios
    
    def _extraer_fecha_actualizacion(self, soup: BeautifulSoup, texto_completo: str) -> tuple:
        """
        Extrae la fecha de última actualización del perfil CTI Vitae
        
        Returns:
            tuple: (fecha_str, meses_sin_actualizar, perfil_desactualizado)
        """
        try:
            # Buscar patrones de fecha de actualización en el HTML
            # CTI Vitae suele mostrar "Última actualización: DD/MM/YYYY" o similar
            
            # Método 1: Buscar texto de última actualización
            patrones_actualizacion = [
                r'[Úú]ltima\s+(?:actualizaci[oó]n|modificaci[oó]n)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(?:Actualizado|Modificado)\s+(?:el)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'Fecha\s+(?:de\s+)?(?:actualizaci[oó]n|modificaci[oó]n)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*(?:\(?\s*[Úú]ltima\s+actualizaci[oó]n\s*\)?)',
            ]
            
            fecha_encontrada = None
            for patron in patrones_actualizacion:
                match = re.search(patron, texto_completo, re.IGNORECASE)
                if match:
                    fecha_encontrada = match.group(1)
                    break
            
            # Método 2: Buscar en elementos específicos del HTML
            if not fecha_encontrada:
                elementos_fecha = soup.find_all(string=re.compile(r'actualizaci[oó]n|modificaci[oó]n', re.IGNORECASE))
                for elem in elementos_fecha:
                    texto_elem = elem.get_text() if hasattr(elem, 'get_text') else str(elem)
                    match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', texto_elem)
                    if match:
                        fecha_encontrada = match.group(1)
                        break
            
            # Método 3: Buscar la fecha más reciente en secciones relevantes
            if not fecha_encontrada:
                # Buscar todas las fechas en formato DD/MM/YYYY o DD-MM-YYYY
                todas_fechas = re.findall(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto_completo)
                if todas_fechas:
                    fechas_parseadas = []
                    for f in todas_fechas:
                        try:
                            separador = '/' if '/' in f else '-'
                            partes = f.split(separador)
                            if len(partes) == 3:
                                dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
                                if 1 <= mes <= 12 and 1 <= dia <= 31 and 2000 <= ano <= 2030:
                                    fechas_parseadas.append((datetime(ano, mes, dia), f))
                        except:
                            continue
                    
                    if fechas_parseadas:
                        # Tomar la fecha más reciente
                        fechas_parseadas.sort(key=lambda x: x[0], reverse=True)
                        fecha_encontrada = fechas_parseadas[0][1]
            
            if fecha_encontrada:
                # Calcular meses sin actualizar
                try:
                    separador = '/' if '/' in fecha_encontrada else '-'
                    partes = fecha_encontrada.split(separador)
                    dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
                    if ano < 100:
                        ano += 2000
                    fecha_obj = datetime(ano, mes, dia)
                    
                    # Calcular diferencia en meses
                    hoy = datetime.now()
                    meses_diferencia = (hoy.year - fecha_obj.year) * 12 + (hoy.month - fecha_obj.month)
                    
                    perfil_desactualizado = meses_diferencia > 6
                    
                    return fecha_encontrada, meses_diferencia, perfil_desactualizado
                    
                except Exception as e:
                    return fecha_encontrada, None, False
            
            return None, None, False
            
        except Exception as e:
            return None, None, False
    
    def _detectar_perfil_vacio(self, soup: BeautifulSoup, texto_completo: str) -> bool:
        """
        Detecta si el perfil está vacío o en construcción
        
        Returns:
            bool: True si el perfil está vacío/en construcción
        """
        try:
            texto_lower = texto_completo.lower()
            
            # Indicadores de perfil vacío o en construcción
            indicadores_vacio = [
                'perfil en construcci',
                'no hay informaci[oó]n registrada',
                'sin informaci[oó]n registrada',
                'próximamente',
                'coming soon',
                'perfil vacío',
                'no disponible',
                'pendiente de registro'
            ]
            
            for indicador in indicadores_vacio:
                if re.search(indicador, texto_lower, re.IGNORECASE):
                    # Verificar si a pesar del indicador tiene datos reales
                    # (algunos perfiles dicen "en construcción" pero tienen datos)
                    if self._tiene_datos_reales(soup, texto_completo):
                        return False
                    return True
            
            # Verificar si tiene muy poco contenido
            # Eliminar etiquetas comunes y espacios
            texto_limpio = re.sub(r'\s+', ' ', texto_lower)
            texto_limpio = re.sub(r'cti\s*vitae|concytec|investigador|curriculum|directorio|nacional', '', texto_limpio)
            
            # Si después de limpiar tiene menos de 200 caracteres Y no hay datos reales
            if len(texto_limpio.strip()) < 200:
                if not self._tiene_datos_reales(soup, texto_completo):
                    return True
            
            return False
            
        except Exception as e:
            return False
    
    def _tiene_datos_reales(self, soup: BeautifulSoup, texto_completo: str) -> bool:
        """
        Verifica si el perfil tiene datos reales extraíbles.
        
        Returns:
            bool: True si tiene al menos algún dato real
        """
        texto_lower = texto_completo.lower()
        
        # Verificar indicadores de contenido real
        tiene_educacion = any(kw in texto_lower for kw in ['doctorado', 'maestría', 'licenciatura', 'magister', 'bachiller', 'ingeniero'])
        tiene_experiencia = any(kw in texto_lower for kw in ['experiencia', 'docente', 'profesor', 'universidad', 'empresa'])
        tiene_publicaciones = any(kw in texto_lower for kw in ['publicación', 'artículo', 'libro', 'revista', 'scopus', 'proyecto'])
        
        # Si tiene al menos 2 de estos indicadores, tiene datos reales
        indicadores = [tiene_educacion, tiene_experiencia, tiene_publicaciones]
        return sum(indicadores) >= 1  # Al menos un indicador de datos reales
    
    def _cv_vacio(self, url: str) -> Dict:
        """Retorna estructura de CV vacía en caso de error"""
        return {
            'nombre': 'Error al extraer',
            'anos_experiencia': 0,
            'educacion': {'doctorado': False, 'maestria': False, 'licenciatura': False},
            'publicaciones': 0,
            'proyectos': 0,
            'experiencia_laboral': [],
            'experiencia_docente': 0,
            'idiomas': [],
            'premios': [],
            'url': url,
            'fecha_actualizacion': None,
            'meses_sin_actualizar': None,
            'perfil_desactualizado': False,
            'perfil_vacio': True,  # CV vacío siempre se marca como perfil vacío
            'error_extraccion': True,
            'error_mensaje': 'Error al extraer CV'
        }
    
    def _extraer_cv_con_datos_excel(self, url: str, lookup_excel: dict, indice: int, total: int) -> Dict:
        """
        Extrae un CV individual con datos del Excel y tracking de progreso.
        Diseñado para ejecución paralela.
        """
        global _progress_state
        tiempo_inicio_cv = time.time()
        
        try:
            cv_data = self.extraer_cv_desde_url(url)
            
            # Si el nombre no se encontró, usar el del Excel
            if cv_data['nombre'] in ['Nombre no encontrado', 'Error al extraer', '']:
                datos_lookup = lookup_excel.get(url.strip(), {})
                if datos_lookup.get('nombre'):
                    cv_data['nombre'] = datos_lookup['nombre']
            
            # Agregar DNI, Facultad y Carrera del Excel si están disponibles
            datos_lookup = lookup_excel.get(url.strip(), {})
            cv_data['dni'] = datos_lookup.get('dni', '')
            cv_data['facultad'] = datos_lookup.get('facultad', '')
            cv_data['carrera'] = datos_lookup.get('carrera', '')
            cv_data['tipo_candidato'] = datos_lookup.get('tipo_candidato', '')
            cv_data['puesto'] = datos_lookup.get('puesto', '')
            cv_data['categoria_practitioner'] = datos_lookup.get('categoria_practitioner', '')
            cv_data['error_extraccion'] = False
            cv_data['indice_original'] = indice
            
            tiempo_cv = time.time() - tiempo_inicio_cv
            
            # Actualizar progreso
            with _progress_lock:
                _progress_state["completados"] += 1
                _progress_state["exitosos"] += 1
                _progress_state["tiempos_individuales"].append(tiempo_cv)
            
            print(f"   ✅ [{indice}/{total}] {cv_data['nombre'][:40]}... ({tiempo_cv:.1f}s)")
            return cv_data
            
        except Exception as e:
            cv_vacio = self._cv_vacio(url)
            
            # Intentar usar datos del Excel para CV vacío
            datos_lookup = lookup_excel.get(url.strip(), {})
            if datos_lookup.get('nombre'):
                cv_vacio['nombre'] = datos_lookup['nombre']
            cv_vacio['dni'] = datos_lookup.get('dni', '')
            cv_vacio['facultad'] = datos_lookup.get('facultad', '')
            cv_vacio['carrera'] = datos_lookup.get('carrera', '')
            cv_vacio['tipo_candidato'] = datos_lookup.get('tipo_candidato', '')
            cv_vacio['puesto'] = datos_lookup.get('puesto', '')
            cv_vacio['categoria_practitioner'] = datos_lookup.get('categoria_practitioner', '')
            cv_vacio['error_extraccion'] = True
            cv_vacio['error_mensaje'] = str(e)
            cv_vacio['indice_original'] = indice
            
            tiempo_cv = time.time() - tiempo_inicio_cv
            
            # Actualizar progreso
            with _progress_lock:
                _progress_state["completados"] += 1
                _progress_state["errores"] += 1
                _progress_state["tiempos_individuales"].append(tiempo_cv)
                _progress_state["registros_con_error"].append({
                    "indice": indice,
                    "url": url,
                    "nombre": cv_vacio['nombre'],
                    "dni": cv_vacio['dni'],
                    "facultad": cv_vacio.get('facultad', ''),
                    "carrera": cv_vacio.get('carrera', ''),
                    "tipo_candidato": cv_vacio.get('tipo_candidato', ''),
                    "puesto": cv_vacio.get('puesto', ''),
                    "categoria_practitioner": cv_vacio.get('categoria_practitioner', ''),
                    "error": str(e)
                })
            
            print(f"   ❌ [{indice}/{total}] Error: {str(e)[:50]}...")
            return cv_vacio
    
    def extraer_multiples_cvs(self, urls: List[str], datos_excel: List[Dict] = None, 
                              max_workers: int = 5, callback_progreso: Callable = None) -> List[Dict]:
        """
        Extrae información de múltiples CVs usando procesamiento paralelo.
        
        Args:
            urls: Lista de URLs de CTI Vitae
            datos_excel: Lista opcional de diccionarios con {url, dni, nombre, facultad, carrera} del Excel
            max_workers: Número máximo de hilos paralelos (default: 5 para no saturar el servidor)
            callback_progreso: Función opcional para reportar progreso
            
        Returns:
            Lista de diccionarios con datos de CVs
        """
        global _progress_state
        
        print(f"\n{'='*60}")
        print(f"⚡ EXTRACCIÓN PARALELA: {len(urls)} CVs")
        print(f"   Hilos paralelos: {max_workers}")
        print(f"{'='*60}")
        
        # Reiniciar estado de progreso
        reset_extraction_progress()
        with _progress_lock:
            _progress_state["total"] = len(urls)
            _progress_state["tiempo_inicio"] = time.time()
        
        # Crear diccionario de lookup por URL si hay datos del Excel
        lookup_excel = {}
        if datos_excel:
            for dato in datos_excel:
                if dato.get('url'):
                    lookup_excel[dato['url'].strip()] = {
                        'dni': dato.get('dni', ''),
                        'nombre': dato.get('nombre', ''),
                        'facultad': dato.get('facultad', ''),
                        'carrera': dato.get('carrera', ''),
                        'tipo_candidato': dato.get('tipo_candidato', ''),
                        'puesto': dato.get('puesto', ''),
                        'categoria_practitioner': dato.get('categoria_practitioner', '')
                    }
        
        cvs_extraidos = []
        total = len(urls)
        
        # Usar ThreadPoolExecutor para paralelismo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Enviar todas las tareas
            futuros = {}
            for i, url in enumerate(urls, 1):
                futuro = executor.submit(
                    self._extraer_cv_con_datos_excel, 
                    url, 
                    lookup_excel, 
                    i, 
                    total
                )
                futuros[futuro] = i
                # Pequeña pausa entre envíos para no saturar
                time.sleep(0.1)
            
            # Recolectar resultados a medida que completan
            for futuro in as_completed(futuros):
                try:
                    cv_data = futuro.result()
                    cvs_extraidos.append(cv_data)
                    
                    # Callback de progreso si existe
                    if callback_progreso:
                        progreso = get_extraction_progress()
                        callback_progreso(progreso)
                        
                except Exception as e:
                    print(f"   ⚠️ Error en futuro: {e}")
        
        # Ordenar por índice original para mantener orden
        cvs_extraidos.sort(key=lambda x: x.get('indice_original', 0))
        
        # Calcular estadísticas finales
        tiempo_total = time.time() - _progress_state["tiempo_inicio"]
        tiempos = _progress_state["tiempos_individuales"]
        tiempo_promedio = sum(tiempos) / len(tiempos) if tiempos else 0
        
        print(f"\n{'='*60}")
        print(f"✅ EXTRACCIÓN PARALELA COMPLETADA")
        print(f"   Total procesados: {len(cvs_extraidos)}")
        print(f"   Exitosos: {_progress_state['exitosos']}")
        print(f"   Con errores: {_progress_state['errores']}")
        print(f"   Tiempo total: {tiempo_total:.1f}s")
        print(f"   Tiempo promedio/CV: {tiempo_promedio:.1f}s")
        print(f"   Velocidad: {len(cvs_extraidos)/tiempo_total:.1f} CVs/segundo")
        print(f"{'='*60}")
        
        return cvs_extraidos
    
    def reanalizar_cv_individual(self, url: str, datos_extra: Dict = None) -> Dict:
        """
        Re-analiza un CV individual de forma detallada.
        Útil para reintentar cuando hubo un error.
        USA TIMEOUT EXTENDIDO (hasta 5 minutos) para perfiles con mucha información.
        
        Args:
            url: URL del CV a re-analizar
            datos_extra: Diccionario con {dni, nombre, facultad} adicionales
            
        Returns:
            Diccionario con datos del CV y diagnóstico detallado
        """
        print(f"\n🔄 RE-ANALIZANDO CV: {url}")
        print(f"   ⏱️ Usando timeout extendido (hasta 5 minutos por intento)")
        tiempo_inicio = time.time()
        
        resultado = {
            "exito": False,
            "cv_data": None,
            "diagnostico": {
                "url_accesible": False,
                "contenido_parseado": False,
                "datos_encontrados": [],
                "datos_faltantes": [],
                "errores": [],
                "warnings": []
            },
            "tiempo_proceso": 0
        }
        
        try:
            # Paso 1: Verificar accesibilidad de URL con TIMEOUT EXTENDIDO
            response = self._hacer_peticion_reanalisis(url)
            resultado["diagnostico"]["url_accesible"] = True
            resultado["diagnostico"]["codigo_http"] = response.status_code
            
            # Paso 2: Parsear contenido
            soup = BeautifulSoup(response.content, 'html.parser')
            resultado["diagnostico"]["contenido_parseado"] = True
            resultado["diagnostico"]["tamano_html"] = len(response.content)
            
            # Paso 3: Extraer datos con diagnóstico
            print(f"   📝 Extrayendo datos del perfil...")
            cv_data = self._extraer_datos_desde_html(soup, url)
            
            # Diagnóstico de datos encontrados
            if cv_data.get('nombre') and cv_data['nombre'] not in ['Nombre no encontrado', 'Error al extraer']:
                resultado["diagnostico"]["datos_encontrados"].append("nombre")
            else:
                resultado["diagnostico"]["datos_faltantes"].append("nombre")
                
            if cv_data.get('educacion', {}).get('doctorado') or cv_data.get('educacion', {}).get('maestria'):
                resultado["diagnostico"]["datos_encontrados"].append("educacion")
            else:
                resultado["diagnostico"]["datos_faltantes"].append("educacion")
                
            if cv_data.get('anos_experiencia', 0) > 0:
                resultado["diagnostico"]["datos_encontrados"].append("experiencia")
            else:
                resultado["diagnostico"]["datos_faltantes"].append("experiencia")
                
            if cv_data.get('publicaciones', 0) > 0:
                resultado["diagnostico"]["datos_encontrados"].append("publicaciones")
            else:
                resultado["diagnostico"]["warnings"].append("Sin publicaciones detectadas")
            
            # Agregar datos extra si se proporcionan
            if datos_extra:
                cv_data['dni'] = datos_extra.get('dni', cv_data.get('dni', ''))
                cv_data['nombre'] = datos_extra.get('nombre', cv_data.get('nombre', ''))
                cv_data['facultad'] = datos_extra.get('facultad', cv_data.get('facultad', ''))
                cv_data['carrera'] = datos_extra.get('carrera', cv_data.get('carrera', ''))
            
            cv_data['reanalizado'] = True
            cv_data['fecha_reanalisis'] = datetime.now().isoformat()
            
            resultado["exito"] = True
            resultado["cv_data"] = cv_data
            
        except requests.Timeout as e:
            resultado["diagnostico"]["errores"].append(f"Timeout: El servidor no respondió a tiempo ({e})")
        except requests.ConnectionError as e:
            resultado["diagnostico"]["errores"].append(f"Error de conexión: No se pudo conectar al servidor ({e})")
        except requests.HTTPError as e:
            resultado["diagnostico"]["errores"].append(f"Error HTTP: {e}")
        except Exception as e:
            resultado["diagnostico"]["errores"].append(f"Error inesperado: {type(e).__name__}: {e}")
        
        resultado["tiempo_proceso"] = time.time() - tiempo_inicio
        
        print(f"   Resultado: {'✅ Éxito' if resultado['exito'] else '❌ Error'}")
        print(f"   Tiempo: {resultado['tiempo_proceso']:.1f}s")
        if resultado["diagnostico"]["errores"]:
            print(f"   Errores: {resultado['diagnostico']['errores']}")
        
        return resultado


def procesar_excel_links(ruta_excel: str = None, max_workers: int = 5) -> list:
    """
    Función principal para procesar links de CTI Vitae desde un archivo Excel.
    Lee el archivo de configuración si no se especifica ruta.
    
    Args:
        ruta_excel: Ruta opcional del archivo Excel con links
        max_workers: Número de hilos paralelos para extracción
        
    Returns:
        Lista de diccionarios con datos de CVs procesados
    """
    import pandas as pd
    from config import INFORMACION_VALIDACION_PATH, LINKS_DIR
    
    # Si no se especifica ruta, usar el archivo configurado
    if ruta_excel is None:
        ruta_excel = INFORMACION_VALIDACION_PATH
    
    print(f"\n{'='*60}")
    print("📊 PROCESANDO LINKS DE CTI VITAE DESDE EXCEL")
    print(f"{'='*60}")
    
    # Verificar si existe el archivo
    if not os.path.exists(ruta_excel):
        # Buscar cualquier Excel en la carpeta LINKS
        if os.path.exists(LINKS_DIR):
            archivos_excel = [f for f in os.listdir(LINKS_DIR) if f.endswith('.xlsx') or f.endswith('.xls')]
            if archivos_excel:
                ruta_excel = os.path.join(LINKS_DIR, archivos_excel[0])
                print(f"   📁 Usando archivo encontrado: {archivos_excel[0]}")
            else:
                print(f"   ⚠️ No se encontraron archivos Excel en {LINKS_DIR}")
                print(f"   📁 Por favor, coloca el archivo Excel con links en: {LINKS_DIR}")
                return []
        else:
            print(f"   ⚠️ No existe el directorio: {LINKS_DIR}")
            return []
    
    print(f"   📄 Archivo: {os.path.basename(ruta_excel)}")
    
    try:
        # Leer el archivo Excel
        # Intentar leer todas las hojas para encontrar links
        excel_file = pd.ExcelFile(ruta_excel)
        
        urls = []
        datos_excel = []  # Para guardar DNI, nombre, facultad, carrera junto con URL
        
        for sheet_name in excel_file.sheet_names:
            try:
                df = pd.read_excel(ruta_excel, sheet_name=sheet_name, dtype=str)
                print(f"   📋 Hoja '{sheet_name}': {len(df)} filas")
                
                # Buscar columnas que puedan contener URLs
                columnas_url = []
                columnas_datos = {
                    'dni': None, 'nombre': None, 'facultad': None, 'carrera': None,
                    'tipo_candidato': None, 'puesto': None, 'categoria_practitioner': None
                }
                
                for col in df.columns:
                    col_lower = str(col).lower()
                    # Buscar columna de URL
                    if any(kw in col_lower for kw in ['link', 'url', 'cti', 'vitae', 'enlace', 'perfil']):
                        columnas_url.append(col)
                    # Buscar otras columnas importantes
                    if 'dni' in col_lower or 'documento' in col_lower:
                        columnas_datos['dni'] = col
                    if 'nombre' in col_lower or 'apellido' in col_lower:
                        columnas_datos['nombre'] = col
                    if 'facultad' in col_lower:
                        columnas_datos['facultad'] = col
                    if 'carrera' in col_lower or 'programa' in col_lower:
                        columnas_datos['carrera'] = col
                    if 'tipo de candidato' in col_lower:
                        columnas_datos['tipo_candidato'] = col
                    if 'puesto' in col_lower and 'tipo' not in col_lower:
                        columnas_datos['puesto'] = col
                    if 'categoria practitioner' in col_lower or 'categoría practitioner' in col_lower:
                        columnas_datos['categoria_practitioner'] = col
                
                # Si no encontramos columnas por nombre, buscar en todas las columnas
                if not columnas_url:
                    for col in df.columns:
                        muestra = df[col].dropna().head(10)
                        for val in muestra:
                            if isinstance(val, str) and 'ctivitae.concytec' in val:
                                columnas_url.append(col)
                                break
                
                # Extraer URLs y datos asociados
                for col_url in columnas_url:
                    for idx, row in df.iterrows():
                        url = str(row[col_url]).strip() if pd.notna(row[col_url]) else ''
                        
                        if url and 'ctivitae.concytec' in url:
                            # Normalizar URL
                            if not url.startswith('http'):
                                url = 'https://' + url
                                
                            if url not in urls:
                                urls.append(url)
                                
                                # Guardar datos asociados
                                datos_fila = {
                                    'url': url,
                                    'dni': str(row[columnas_datos['dni']]).strip() if columnas_datos['dni'] and pd.notna(row.get(columnas_datos['dni'])) else '',
                                    'nombre': str(row[columnas_datos['nombre']]).strip() if columnas_datos['nombre'] and pd.notna(row.get(columnas_datos['nombre'])) else '',
                                    'facultad': str(row[columnas_datos['facultad']]).strip() if columnas_datos['facultad'] and pd.notna(row.get(columnas_datos['facultad'])) else '',
                                    'carrera': str(row[columnas_datos['carrera']]).strip() if columnas_datos['carrera'] and pd.notna(row.get(columnas_datos['carrera'])) else '',
                                    'tipo_candidato': str(row[columnas_datos['tipo_candidato']]).strip() if columnas_datos['tipo_candidato'] and pd.notna(row.get(columnas_datos['tipo_candidato'])) else '',
                                    'puesto': str(row[columnas_datos['puesto']]).strip() if columnas_datos['puesto'] and pd.notna(row.get(columnas_datos['puesto'])) else '',
                                    'categoria_practitioner': str(row[columnas_datos['categoria_practitioner']]).strip() if columnas_datos['categoria_practitioner'] and pd.notna(row.get(columnas_datos['categoria_practitioner'])) else ''
                                }
                                datos_excel.append(datos_fila)
                
            except Exception as e:
                print(f"   ⚠️ Error leyendo hoja '{sheet_name}': {e}")
                continue
        
        print(f"\n   ✓ URLs de CTI Vitae encontradas: {len(urls)}")
        
        if not urls:
            print("   ⚠️ No se encontraron links de CTI Vitae en el archivo Excel")
            print("   💡 Asegúrate de que el archivo contenga URLs de ctivitae.concytec.gob.pe")
            return []
        
        # Extraer CVs usando el extractor
        extractor = ExtractorWebCVs()
        cvs_extraidos = extractor.extraer_multiples_cvs(
            urls=urls, 
            datos_excel=datos_excel,
            max_workers=max_workers
        )
        
        # Asegurarse de que cada CV tenga la fuente correcta
        for cv in cvs_extraidos:
            cv['fuente'] = 'CTI_VITAE'
            cv['fuente_datos'] = 'CTI_VITAE'
        
        print(f"\n   ✅ Procesados: {len(cvs_extraidos)} perfiles de CTI Vitae")
        
        return cvs_extraidos
        
    except Exception as e:
        print(f"   ❌ Error procesando Excel: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    # Prueba del extractor
    extractor = ExtractorWebCVs()
    
    # URL de ejemplo
    url_test = "https://ctivitae.concytec.gob.pe/appDirectorioCTI/VerDatosInvestigador.do?id_investigador=440291"
    
    cv = extractor.extraer_cv_desde_url(url_test)
    
    print("\n" + "="*60)
    print("RESULTADO DE LA EXTRACCIÓN:")
    print("="*60)
    print(f"Nombre: {cv['nombre']}")
    print(f"Experiencia: {cv['anos_experiencia']} años")
    print(f"Educación: {cv['educacion']}")
    print(f"Publicaciones: {cv['publicaciones']}")
    print(f"Proyectos: {cv['proyectos']}")
    print(f"Experiencia docente: {cv['experiencia_docente']} años")
    print(f"Idiomas: {', '.join(cv['idiomas']) if cv['idiomas'] else 'No especificado'}")
