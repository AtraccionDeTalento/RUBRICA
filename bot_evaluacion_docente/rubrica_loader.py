"""
Cargador de Rúbrica (única fuente de verdad)
============================================
Lee los archivos JSON de la carpeta Rubrica/ y expone los criterios,
puntajes, perfiles y diccionarios al motor de evaluación.

A diferencia de las tablas hardcodeadas de config.py (que estaban
desactualizadas respecto a la rúbrica institucional), este módulo
hace que el motor "visite la rúbrica" en cada ejecución.

Archivos consumidos (en RUBRICA_DIR):
  - Criterios de evaluacion.json   → criterios C1..C5 + perfiles + lógica de aprobación
  - empresas_top500.json           → C4 (lista de 500 empresas Top Perú)
  - diccionario_c2_docencia.json   → cargos que cuentan como docencia universitaria
  - diccionario_c3_profesional.json→ cargos de gestión/dirección (C3)

Autor: Sistema Bot Evaluación Docente
"""
import os
import json
import unicodedata
from typing import Dict, List, Optional

from config import RUBRICA_DIR

# Nombres de archivo de la rúbrica por defecto
ARCHIVO_CRITERIOS = "Criterios 2025.json"
ARCHIVO_EMPRESAS = "empresas_top500.json"
ARCHIVO_DICC_C2 = "diccionario_c2_docencia.json"
ARCHIVO_DICC_C3 = "diccionario_c3_profesional.json"


def normalizar(texto: str) -> str:
    """
    Normaliza un texto para comparaciones robustas:
    minúsculas, sin acentos/diacríticos y con espacios colapsados.
    Esto permite emparejar 'Científica' == 'cientifica', 'Católica' == 'catolica'.
    """
    if not texto:
        return ""
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split())


def _leer_json(nombre: str) -> Optional[dict]:
    ruta = os.path.join(RUBRICA_DIR, nombre)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"   [rubrica_loader] AVISO: no se encontró {ruta}")
        return None
    except Exception as e:
        print(f"   [rubrica_loader] ERROR leyendo {ruta}: {e}")
        return None


class Rubrica:
    """
    Representa la rúbrica institucional cargada desde los JSON.
    Expone helpers para obtener puntajes por categoría y perfiles.
    """

    def __init__(self, archivo_criterios=ARCHIVO_CRITERIOS, 
                 archivo_empresas=ARCHIVO_EMPRESAS,
                 archivo_dicc_c2=ARCHIVO_DICC_C2,
                 archivo_dicc_c3=ARCHIVO_DICC_C3):
        self._criterios_raw = _leer_json(archivo_criterios) or {}
        self._empresas_raw = _leer_json(archivo_empresas) or {}
        self._dicc_c2 = _leer_json(archivo_dicc_c2) or {}
        self._dicc_c3 = _leer_json(archivo_dicc_c3) or {}

        # --- Índice de categorías: {category_id: {score, name, keywords...}} ---
        self.categorias: Dict[str, dict] = {}
        self.criterios: Dict[str, dict] = {}
        
        criterios_data = self._criterios_raw.get("criterios", self._criterios_raw.get("criteria", []))
        
        if isinstance(criterios_data, dict):
            # Formato de Criterios 2025.json
            for cid, crit in criterios_data.items():
                self.criterios[cid] = crit
                niveles = crit.get("niveles", [])
                for i, n in enumerate(niveles):
                    cat_id = f"{cid}_{i+1}"
                    self.categorias[cat_id] = {
                        "category_id": cat_id,
                        "score": n.get("puntaje", 0),
                        "name": n.get("categoria", "")
                    }
        elif isinstance(criterios_data, list):
            # Formato de PRACTITIONER DOCENTE.json o legacy criteria
            for crit in criterios_data:
                cid = crit.get("id") or crit.get("criterion_id")
                if not cid: continue
                self.criterios[cid] = crit
                niveles = crit.get("categorias", crit.get("categories", []))
                for i, n in enumerate(niveles):
                    cat_id = n.get("category_id", f"{cid}_{i+1}")
                    self.categorias[cat_id] = {
                        "category_id": cat_id,
                        "score": n.get("puntaje", n.get("score", 0)),
                        "name": n.get("nivel", n.get("categoria", n.get("name", "")))
                    }

        # --- Perfiles y su lógica de aprobación ---
        raw_perfiles = self._criterios_raw.get("perfiles", self._criterios_raw.get("profiles", []))
        self.perfiles: List[dict] = []
        if isinstance(raw_perfiles, dict):
            for k, v in raw_perfiles.items():
                v["profile_id"] = v.get("codigo", v.get("profile_id", k))
                self.perfiles.append(v)
        elif isinstance(raw_perfiles, list):
            for p in raw_perfiles:
                p["profile_id"] = p.get("codigo", p.get("perfil", p.get("profile_id", "")))
                self.perfiles.append(p)

        # --- Empresas Top 500 (normalizadas, descartando basura) ---
        self.empresas_top: List[str] = []
        for item in self._empresas_raw.get("empresas", []):
            nombre = item.get("empresa", "") if isinstance(item, dict) else str(item)
            norm = normalizar(nombre)
            # Descartar entradas vacías o ruido tipo 'nan' que generaban
            # falsos positivos por coincidencia de subcadena.
            if norm and norm != "nan" and len(norm) >= 4:
                self.empresas_top.append(norm)
        self.empresas_top = sorted(set(self.empresas_top), key=len, reverse=True)

        # --- Diccionarios de cargos (normalizados) ---
        self.cargos_docencia: List[str] = [
            normalizar(c) for c in self._dicc_c2.get("cargos", [])
        ]
        self.cargos_profesional: List[str] = [
            normalizar(c) for c in self._dicc_c3.get("cargos", [])
        ]

    # ------------------------------------------------------------------ #
    #  Helpers de puntaje                                                  #
    # ------------------------------------------------------------------ #
    def score(self, category_id: str, default: float = 0) -> float:
        """Devuelve el puntaje de una categoría de la rúbrica (ej: 'C5_1')."""
        cat = self.categorias.get(category_id)
        if cat is None:
            return default
        return cat.get("score", default)

    def nombre_categoria(self, category_id: str) -> str:
        cat = self.categorias.get(category_id)
        return cat.get("name", category_id) if cat else category_id

    def max_criterio(self, criterion_id: str) -> float:
        """Puntaje máximo posible de un criterio (mayor score entre sus categorías)."""
        crit = self.criterios.get(criterion_id, {})
        niveles = crit.get("niveles", crit.get("categorias", crit.get("categories", [])))
        scores = [
            c.get("puntaje", c.get("score", 0))
            for c in niveles
        ]
        return max(scores) if scores else 0

    @property
    def total_maximo(self) -> float:
        """Suma de los máximos de C1..C5 según la rúbrica (= 200)."""
        return sum(self.max_criterio(c) for c in ["C1", "C2", "C3", "C4", "C5"])

    # ------------------------------------------------------------------ #
    #  Emparejamiento                                                      #
    # ------------------------------------------------------------------ #
    def es_empresa_top(self, texto_norm: str) -> Optional[str]:
        """
        Devuelve el nombre de la primera empresa Top 500 encontrada como
        subcadena dentro de texto_norm (ya normalizado), o None.
        """
        for emp in self.empresas_top:
            if emp in texto_norm:
                return emp
        return None

    def es_cargo_docencia(self, texto_norm: str) -> bool:
        return any(c and c in texto_norm for c in self.cargos_docencia)

    def es_cargo_profesional(self, texto_norm: str) -> bool:
        return any(c and c in texto_norm for c in self.cargos_profesional)


# Singleton perezoso para no recargar los JSON en cada CV
_RUBRICA_CACHE: Optional[Rubrica] = None


def cargar_rubrica(recargar: bool = False, archivo_criterios=ARCHIVO_CRITERIOS,
                   archivo_empresas=ARCHIVO_EMPRESAS, archivo_dicc_c2=ARCHIVO_DICC_C2,
                   archivo_dicc_c3=ARCHIVO_DICC_C3) -> Rubrica:
    """Devuelve la instancia de la rúbrica."""
    # Si se pasan parámetros personalizados, creamos una nueva instancia en lugar de usar la caché global
    if (archivo_criterios != ARCHIVO_CRITERIOS or 
        archivo_dicc_c2 != ARCHIVO_DICC_C2 or 
        archivo_dicc_c3 != ARCHIVO_DICC_C3):
        return Rubrica(archivo_criterios, archivo_empresas, archivo_dicc_c2, archivo_dicc_c3)
        
    global _RUBRICA_CACHE
    if _RUBRICA_CACHE is None or recargar:
        _RUBRICA_CACHE = Rubrica(ARCHIVO_CRITERIOS, ARCHIVO_EMPRESAS, ARCHIVO_DICC_C2, ARCHIVO_DICC_C3)
    return _RUBRICA_CACHE


if __name__ == "__main__":
    r = cargar_rubrica()
    print("Categorías cargadas:", len(r.categorias))
    print("Perfiles:", [p.get("profile_id", p.get("codigo", "?")) for p in r.perfiles])
    print("Empresas Top:", len(r.empresas_top))
    print("Cargos docencia:", len(r.cargos_docencia))
    print("Cargos profesional:", len(r.cargos_profesional))
    print("TOTAL MÁXIMO:", r.total_maximo)
    print("C5_1 (Scopus):", r.score("C5_1"))
    print("C2_1 (5+ años):", r.score("C2_1"))
