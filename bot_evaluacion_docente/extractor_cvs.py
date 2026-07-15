"""
Módulo para extraer información de CVs en formato PDF
"""
import os
import re
from typing import Dict, List
from datetime import datetime
import PyPDF2
import pdfplumber
from config import CVS_DIR, KEYWORDS_EDUCACION, KEYWORDS_EXPERIENCIA, KEYWORDS_INVESTIGACION


class ExtractorCV:
    """Extrae y estructura información de CVs en PDF"""
    
    def __init__(self, cv_path: str):
        self.cv_path = cv_path
        self.nombre_archivo = os.path.basename(cv_path)
        self.texto_completo = ""
        self.datos = {}
        
    def extraer_texto(self) -> str:
        """Extrae todo el texto del PDF"""
        try:
            with pdfplumber.open(self.cv_path) as pdf:
                texto = ""
                for pagina in pdf.pages:
                    texto += pagina.extract_text() + "\n"
                self.texto_completo = texto
                return texto
        except Exception as e:
            print(f"Error extrayendo texto de {self.nombre_archivo}: {e}")
            # Fallback a PyPDF2
            try:
                with open(self.cv_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    texto = ""
                    for pagina in reader.pages:
                        texto += pagina.extract_text() + "\n"
                    self.texto_completo = texto
                    return texto
            except Exception as e2:
                print(f"Error con PyPDF2: {e2}")
                return ""
    
    def extraer_nombre(self) -> str:
        """Extrae el nombre del candidato"""
        # Primero intenta desde el nombre del archivo
        nombre = self.nombre_archivo.replace("CV", "").replace(".pdf", "").strip()
        nombre = nombre.replace("_", " ")
        
        # Buscar en las primeras líneas del CV
        lineas = self.texto_completo.split("\n")[:5]
        for linea in lineas:
            if linea.strip() and len(linea.strip()) > 5 and len(linea.strip()) < 50:
                # Probable que sea el nombre
                if not any(char.isdigit() for char in linea[:20]):
                    nombre = linea.strip()
                    break
        
        return nombre
    
    def contar_keywords(self, keywords: List[str]) -> int:
        """Cuenta la frecuencia de palabras clave en el CV"""
        texto_lower = self.texto_completo.lower()
        contador = 0
        for keyword in keywords:
            contador += texto_lower.count(keyword.lower())
        return contador
    
    def extraer_anos_experiencia(self) -> int:
        """
        Extrae años de experiencia del CV con mejor manejo de períodos
        Detecta solapamientos y diferencia entre meses y años
        """
        texto_lower = self.texto_completo.lower()
        
        # Buscar patrones como "X años de experiencia"
        patrones = [
            r'(\d+)\s*años?\s*de\s*experiencia',
            r'experiencia\s*de\s*(\d+)\s*años?',
            r'(\d+)\s*years?\s*of\s*experience',
            r'experience\s*of\s*(\d+)\s*years?'
        ]
        
        max_anos = 0
        for patron in patrones:
            matches = re.findall(patron, texto_lower)
            for match in matches:
                anos = int(match)
                if anos > max_anos and anos < 50:  # Validación básica
                    max_anos = anos
        
        # Si se encontró experiencia explícita, usarla
        if max_anos > 0:
            return max_anos
        
        # Si no, estimar por fechas con lógica mejorada
        return self._estimar_experiencia_por_fechas()
    
    def _estimar_experiencia_por_fechas(self) -> int:
        """
        Estima experiencia buscando rangos de años en el CV
        Maneja solapamientos y calcula correctamente los períodos
        Soporta formatos: "Mes AAAA - Mes AAAA", "AAAA-AAAA", "Mes AAAA - Actualidad"
        """
        periodos = []
        ano_actual = datetime.now().year
        
        # Patrón 1: "Mes AAAA - Mes AAAA" (ej: "Setiembre 2017 - Febrero 2020")
        patron_mes_completo = r'([A-Za-zñáéíóú]+)\s+(\d{4})\s*[-–—a]\s*([A-Za-zñáéíóú]+)\s+(\d{4})'
        matches_mes = re.findall(patron_mes_completo, self.texto_completo, re.IGNORECASE)
        
        for match in matches_mes:
            try:
                _, ano_inicio_txt, _, ano_fin_txt = match
                ano_inicio = int(ano_inicio_txt)
                ano_fin = int(ano_fin_txt)
                
                if 1980 <= ano_inicio <= ano_actual and ano_inicio <= ano_fin <= ano_actual:
                    periodos.append((ano_inicio, ano_fin))
            except:
                continue
        
        # Patrón 2: "Mes AAAA - Actualidad/Presente"
        patron_presente = r'([A-Za-zñáéíóú]+)\s+(\d{4})\s*[-–—]\s*(actualidad|presente|actual|hoy|today)'
        matches_presente = re.findall(patron_presente, self.texto_completo, re.IGNORECASE)
        
        for match in matches_presente:
            try:
                _, ano_inicio_txt, _ = match
                ano_inicio = int(ano_inicio_txt)
                
                if 1980 <= ano_inicio <= ano_actual:
                    periodos.append((ano_inicio, ano_actual))
            except:
                continue
        
        # Patrón 3: Rangos simples "AAAA-AAAA" o "AAAA - presente"
        patron_rango = r'(\d{4})\s*[-–—]\s*(\d{4}|presente|actual|hoy|today|present)'
        matches_rango = re.findall(patron_rango, self.texto_completo, re.IGNORECASE)
        
        for match in matches_rango:
            try:
                ano_inicio = int(match[0])
                
                # Manejar fecha fin
                if match[1].lower() in ['presente', 'actual', 'hoy', 'today', 'present', 'actualidad']:
                    ano_fin = ano_actual
                else:
                    ano_fin = int(match[1])
                
                # Validar que sean años razonables
                if 1980 <= ano_inicio <= ano_actual and ano_inicio <= ano_fin <= ano_actual:
                    periodos.append((ano_inicio, ano_fin))
            except:
                continue
        
        # Si no se encontraron rangos, buscar todos los años mencionados (fallback)
        if not periodos:
            anos_encontrados = re.findall(r'\b(19\d{2}|20\d{2})\b', self.texto_completo)
            
            if anos_encontrados:
                anos_numeros = [int(ano) for ano in anos_encontrados if 1980 <= int(ano) <= ano_actual]
                
                if anos_numeros:
                    min_ano = min(anos_numeros)
                    max_ano = max(anos_numeros)
                    
                    # Estimar experiencia
                    experiencia_estimada = ano_actual - min_ano
                    
                    # Validación: no más de 40 años de experiencia
                    if experiencia_estimada > 40:
                        experiencia_estimada = max_ano - min_ano
                    
                    return min(experiencia_estimada, 40)
            
            return 0
        
        # Eliminar solapamientos y calcular total
        experiencia_total = self._calcular_anos_sin_solapes(periodos)
        return min(experiencia_total, 40)
    
    def _calcular_anos_sin_solapes(self, periodos: list) -> int:
        """
        Calcula años totales eliminando solapamientos entre períodos
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
                periodo_actual = (periodo_actual[0], max(periodo_actual[1], siguiente[1]))
            else:
                # No hay solapamiento, guardar período actual
                periodos_unidos.append(periodo_actual)
                periodo_actual = siguiente
        
        # Agregar último período
        periodos_unidos.append(periodo_actual)
        
        # Calcular total de años
        total_anos = sum(fin - inicio for inicio, fin in periodos_unidos)
        return total_anos
    
    def extraer_nivel_educacion(self) -> Dict[str, bool]:
        """
        Identifica niveles educativos presentes en el CV
        Diferencia entre estudiante, grado en curso y grado completo
        """
        texto_lower = self.texto_completo.lower()
        
        # Inicializar resultado
        resultado = {
            "doctorado": False,
            "doctorado_completo": False,
            "maestria": False,
            "maestria_completa": False,
            "licenciatura": False
        }
        
        # VERIFICAR SI ES ESTUDIANTE (sin grado completo)
        keywords_estudiante = [
            "estudiante de", "alumno de", "cursando", "en curso",
            "candidato a", "pursuing", "student", "tesista"
        ]
        
        # Buscar ciclo académico (fuerte indicador de estudiante)
        import re
        match_ciclo = re.search(r'\b(\d+)\s*(er|do|to|vo|mo)?\s*ciclo\b', texto_lower)
        es_estudiante = match_ciclo is not None or any(kw in texto_lower for kw in keywords_estudiante)
        
        # Si es estudiante sin grado, retornar sin títulos
        if es_estudiante and match_ciclo:
            # Es estudiante en proceso, marca licenciatura pero sin completar
            resultado["licenciatura"] = True  # En proceso
            return resultado
        
        # KEYWORDS que indican GRADO COMPLETO
        keywords_grado_completo = [
            "titulado", "graduado", "grado obtenido", "título obtenido",
            "egresado con título", "graduated", "degree obtained",
            "colegiado", "licenciado", "ingeniero", "abogado"
        ]
        
        tiene_grado_completo = any(kw in texto_lower for kw in keywords_grado_completo)
        
        # Detección de DOCTORADO
        # 1) Señales de doctorado EN CURSO (doctorando/a, egresado, candidato):
        #    cuentan como doctorado pero NUNCA como completo.
        keywords_doctorado_en_curso = [
            "doctorando", "doctoranda", "doctorado en curso",
            "candidato a doctor", "candidata a doctor", "phd candidate",
            "doctorado (c)", "estudios de doctorado", "estudiante de doctorado",
            "cursando el doctorado", "egresado del doctorado", "egresada del doctorado",
            "egresado de doctorado", "egresada de doctorado", "tesis doctoral en curso",
        ]
        doctorado_en_curso = any(kw in texto_lower for kw in keywords_doctorado_en_curso)

        # 2) Señales de GRADO DOCTORAL OBTENIDO: deben ser explícitas del grado,
        #    con límite de palabra para no confundir "doctoranda en" con "doctora en".
        #    OJO: antes el título de licenciatura ("titulado", "licenciado") marcaba
        #    doctorado_completo=True — un licenciado doctorando salía como doctor.
        patrones_doctorado_completo = [
            r'\bdoctor\s+en\b', r'\bdoctora\s+en\b', r'\bdoctor\s+of\b',
            r'\bphd\s+in\b', r'\bph\.d\.?\s+in\b', r'\bdba\b',
            r'\bdoctor\s+of\s+business\b', r'\bdoctor\s+of\s+philosophy\b',
            r'\bdoctor\s+of\s+education\b', r'\bdoctor\s+of\s+science\b',
            r'\bdoctor\s+of\s+medicine\b', r'\bdoctor\s+of\s+public\b',
            r'\bed\.?d\.?\b', r'\bd\.sc\.?\b',
            r'\bgrado\s+(?:academico\s+)?de\s+doctora?\b',
            r'\btitulo\s+de\s+doctora?\b',
            r'\bdoctorado\s+(?:completo|concluido|culminado|obtenido)\b',
        ]
        doctorado_obtenido = (not doctorado_en_curso) and any(
            re.search(p, texto_lower) for p in patrones_doctorado_completo)

        # 3) Mención genérica ("doctorado", "phd") sin negación → doctorado (no completo)
        tiene_doctorado = doctorado_en_curso or doctorado_obtenido
        if not tiene_doctorado:
            for keyword in ["doctorado", "phd", "ph.d", "doctorate"]:
                if keyword in texto_lower:
                    contexto = texto_lower[max(0, texto_lower.find(keyword)-50):texto_lower.find(keyword)+50]
                    if not any(neg in contexto for neg in ["sin", "no tiene", "no posee", "without", "no phd"]):
                        tiene_doctorado = True
                        break

        if tiene_doctorado:
            resultado["doctorado"] = True
            resultado["doctorado_completo"] = doctorado_obtenido
        
        # Detección de MAESTRÍA
        keywords_maestria = [
            "maestría", "maestria", "magister", "magíster",
            "mba", "m.sc", "msc", "m.a", "postgrado"
        ]
        tiene_maestria = any(keyword in texto_lower for keyword in keywords_maestria)
        # 'master' needs word-boundary check to avoid matching 'mastering'
        if not tiene_maestria:
            tiene_maestria = bool(re.search(r'\bmaster\b', texto_lower))
        
        # Señales de maestría EN CURSO (invalidan maestria_completa)
        maestria_en_curso = any(kw in texto_lower for kw in [
            "maestría en curso", "maestria en curso", "cursando maestría",
            "cursando maestria", "candidato a magister", "candidata a magister",
            "estudiante de maestría", "estudiante de maestria",
            "master in progress", "currently pursuing master",
            "currently enrolled", "expected graduation", "expected completion",
            "en progreso", "en proceso",
        ])
        
        if tiene_maestria:
            resultado["maestria"] = True
            # Maestría completa solo si hay evidencia de grado o mención explícita
            # Y NO hay señales de "en curso"
            if not maestria_en_curso:
                resultado["maestria_completa"] = tiene_grado_completo or any(kw in texto_lower for kw in [
                    "magíster en", "magister en", "maestría en", "mba",
                    "master of business", "master of science", "master of arts",
                    "master in ", "master's in", "master's degree"
                ])
                resultado["maestria_en_curso"] = False
            else:
                resultado["maestria_completa"] = False
                resultado["maestria_en_curso"] = True
        else:
            resultado["maestria_en_curso"] = False
        
        # Detección de LICENCIATURA/BACHILLER
        keywords_licenciatura = [
            "licenciatura", "licenciado", "licenciada",
            "bachiller", "bachelor", "ingeniero", "ingeniera",
            "título profesional", "título universitario",
            # English equivalents
            "industrial engineer", "civil engineer", "mechanical engineer",
            "electrical engineer", "chemical engineer", "systems engineer",
            "certified public accountant", "bachelor of", "bachelor's",
        ]
        tiene_licenciatura = any(keyword in texto_lower for keyword in keywords_licenciatura)
        
        if tiene_licenciatura:
            resultado["licenciatura"] = True
        
        return resultado
    
    def extraer_publicaciones(self) -> int:
        """Cuenta referencias a publicaciones"""
        texto_lower = self.texto_completo.lower()
        
        # Contar menciones de publicaciones
        contador = 0
        keywords_pub = ["publicación", "publication", "paper", "artículo", "article", 
                       "scopus", "scielo", "ieee", "springer", "journal"]
        
        for keyword in keywords_pub:
            contador += texto_lower.count(keyword)
        
        # Buscar patrones de referencias bibliográficas
        # Ej: (2023), [1], et al.
        referencias = len(re.findall(r'\(\d{4}\)|et\s+al\.|\[\d+\]', self.texto_completo))
        
        return contador + referencias
    
    def analizar_experiencia_estructurada(self) -> Dict:
        """Analiza periodos laborales/docentes con analizador_experiencia.
        Devuelve {anos_docencia, anos_totales, experiencia_laboral, evidencias_docencia}."""
        try:
            from analizador_experiencia import analizar_experiencia_texto
            return analizar_experiencia_texto(self.texto_completo)
        except Exception as e:
            print(f"   [!] analizador_experiencia fallo: {e}")
            return {"anos_docencia": 0.0, "anos_totales": 0.0,
                    "experiencia_laboral": [], "evidencias_docencia": []}

    def analizar_cv(self) -> Dict:
        """Realiza análisis completo del CV y retorna datos estructurados"""
        self.extraer_texto()

        exp_estructurada = self.analizar_experiencia_estructurada()
        anos_exp = max(self.extraer_anos_experiencia(), exp_estructurada["anos_totales"])

        self.datos = {
            "nombre": self.extraer_nombre(),
            "archivo": self.nombre_archivo,
            "nombre_completo_cv": self.extraer_nombre(),
            "anos_experiencia": anos_exp,
            "experiencia_docente": exp_estructurada["anos_docencia"],
            "experiencia_laboral": exp_estructurada["experiencia_laboral"],
            "evidencias_docencia": exp_estructurada["evidencias_docencia"],
            "educacion": self.extraer_nivel_educacion(),
            "publicaciones": self.extraer_publicaciones(),
            "keywords_educacion": self.contar_keywords(KEYWORDS_EDUCACION),
            "keywords_experiencia": self.contar_keywords(KEYWORDS_EXPERIENCIA),
            "keywords_investigacion": self.contar_keywords(KEYWORDS_INVESTIGACION),
            "texto_completo": self.texto_completo,
            "longitud_cv": len(self.texto_completo)
        }
        
        return self.datos


def procesar_todos_cvs(carpeta_cvs: str = None, callback_progreso=None) -> List[Dict]:
    """Procesa todos los CVs en la carpeta especificada o en la carpeta por defecto"""
    cvs_procesados = []
    
    # Usar la carpeta especificada o la predeterminada
    directorio = carpeta_cvs if carpeta_cvs else CVS_DIR
    
    if not os.path.exists(directorio):
        print(f"Error: No se encuentra el directorio {directorio}")
        return []
    
    archivos_pdf = [f for f in os.listdir(directorio) if f.endswith('.pdf')]
    total_archivos = len(archivos_pdf)
    
    print(f"\n{'='*60}")
    print(f"EXTRAYENDO INFORMACIÓN DE {total_archivos} CVs")
    print(f"Carpeta: {directorio}")
    print(f"{'='*60}\n")
    
    for i, archivo in enumerate(archivos_pdf):
        ruta_completa = os.path.join(directorio, archivo)
        print(f"📄 Procesando: {archivo}")
        
        if callback_progreso:
            try:
                callback_progreso(archivo, i + 1, total_archivos)
            except Exception as cb_err:
                print(f"Error en callback de progreso: {cb_err}")
        
        extractor = ExtractorCV(ruta_completa)
        datos = extractor.analizar_cv()
        cvs_procesados.append(datos)
        
        print(f"   ✓ Nombre: {datos['nombre']}")
        print(f"   ✓ Experiencia: {datos['anos_experiencia']} años")
        print(f"   ✓ Educación: {datos['educacion']}")
        print(f"   ✓ Publicaciones detectadas: {datos['publicaciones']}\n")
    
    return cvs_procesados


if __name__ == "__main__":
    # Test del módulo
    cvs = procesar_todos_cvs()
    print(f"\n✅ Total de CVs procesados: {len(cvs)}")
