"""
Módulo para analizar y procesar la rúbrica de evaluación desde Excel
"""
import os
import pandas as pd
from typing import Dict, List
from config import RUBRICA_PATH


class AnalizadorRubrica:
    """Analiza la Ficha Individual de Selección Docente"""
    
    def __init__(self, ruta_excel: str = RUBRICA_PATH):
        self.ruta_excel = ruta_excel
        self.criterios = {}
        self.ponderaciones = {}
        self.rangos_puntuacion = {}
        
    def cargar_rubrica(self) -> bool:
        """Carga el archivo Excel de la rúbrica"""
        try:
            # Intentar leer todas las hojas
            self.excel_file = pd.ExcelFile(self.ruta_excel)
            print(f"📋 Hojas disponibles en la rúbrica: {self.excel_file.sheet_names}")
            return True
        except Exception as e:
            print(f"❌ Error al cargar rúbrica: {e}")
            return False
    
    def extraer_criterios_rubrica_usil(self) -> Dict:
        """
        Extrae criterios oficiales de la Ficha de Evaluación USIL
        Basado en las tablas institucionales de puntuación
        """
        from config import (TABLA_FORMACION_ACADEMICA, TABLA_EXPERIENCIA_DOCENTE,
                           TABLA_EXPERIENCIA_PROFESIONAL, TABLA_CENTRO_LABORES,
                           TABLA_PRODUCCION_ACADEMICA, PESOS_CRITERIOS)
        
        criterios_usil = {
            "formacion_academica": {
                "peso": PESOS_CRITERIOS["formacion_academica"],
                "puntaje_maximo": 80,
                "tabla": TABLA_FORMACION_ACADEMICA
            },
            "experiencia_docente": {
                "peso": PESOS_CRITERIOS["experiencia_docente"],
                "puntaje_maximo": 50,
                "tabla": TABLA_EXPERIENCIA_DOCENTE
            },
            "experiencia_profesional": {
                "peso": PESOS_CRITERIOS["experiencia_profesional"],
                "puntaje_maximo": 40,
                "tabla": TABLA_EXPERIENCIA_PROFESIONAL
            },
            "centro_labores": {
                "peso": PESOS_CRITERIOS["centro_labores"],
                "puntaje_maximo": 20,
                "tabla": TABLA_CENTRO_LABORES
            },
            "produccion_academica": {
                "peso": PESOS_CRITERIOS["produccion_academica"],
                "puntaje_maximo": 40,
                "tabla": TABLA_PRODUCCION_ACADEMICA
            }
        }
        
        self.criterios = criterios_usil
        return criterios_usil
    
    def obtener_estructura_evaluacion(self) -> Dict:
        """Retorna la estructura completa de evaluación"""
        if not self.criterios:
            self.extraer_criterios_rubrica_usil()
        
        from config import RANGOS_APROBATORIOS
        
        return {
            "criterios": self.criterios,
            "puntuacion_maxima": 85,  # Suma de pesos: 30+5+30+20+0
            "puntuacion_minima_aprobacion": 90,  # Mínimo para Practitioner
            "rangos_aprobatorios": RANGOS_APROBATORIOS,
            "descripcion": "Ficha de Evaluación Perfil - Selección Docente USIL 2026"
        }
    
    def calcular_pesos_totales(self) -> Dict[str, float]:
        """Calcula y valida que los pesos sumen 100%"""
        pesos = {}
        for criterio, datos in self.criterios.items():
            pesos[criterio] = datos.get("peso", 0)
        
        total = sum(pesos.values())
        print(f"\n📊 Pesos totales: {total}%")
        
        if total != 100:
            print(f"⚠️  Advertencia: Los pesos suman {total}%, se normalizarán a 100%")
            # Normalizar
            factor = 100 / total
            pesos = {k: v * factor for k, v in pesos.items()}
        
        return pesos


def analizar_rubrica_completa() -> Dict:
    """Función principal para analizar la rúbrica"""
    print(f"\n{'='*60}")
    print(f"ANALIZANDO RÚBRICA DE EVALUACIÓN")
    print(f"{'='*60}\n")
    
    analizador = AnalizadorRubrica()
    
    if analizador.cargar_rubrica():
        print("✅ Rúbrica cargada exitosamente")
    else:
        print("⚠️  Usando criterios genéricos de evaluación")
    
    estructura = analizador.obtener_estructura_evaluacion()
    pesos = analizador.calcular_pesos_totales()
    
    print("\n📋 Criterios de evaluación:")
    for criterio, peso in pesos.items():
        print(f"   • {criterio.replace('_', ' ').title()}: {peso:.1f}%")
    
    return {
        "estructura": estructura,
        "pesos": pesos,
        "analizador": analizador
    }


if __name__ == "__main__":
    # Test del módulo
    resultado = analizar_rubrica_completa()
    print(f"\n✅ Análisis de rúbrica completado")
