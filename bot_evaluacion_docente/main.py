"""
Sistema de Evaluación Automática de Docentes - SIMPLIFICADO
============================================

Aplicación principal con lógica funcional validada

Autor: Joshua Lopez
Fecha: Enero 2026
Version: 3.0 - Adaptado de Testear
"""

import sys
import os
from datetime import datetime
import json

# Importar módulos del sistema
from extractor_cvs import procesar_todos_cvs
from extractor_web_cvs import ExtractorWebCVs, procesar_excel_links
from motor_evaluacion import MotorEvaluacion, TOTAL_MAXIMO
from config import RESULTADOS_DIR


def imprimir_banner():
    """Imprime el banner de inicio"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "   SISTEMA DE EVALUACIÓN AUTOMÁTICA DE DOCENTES - V3.0".center(78) + "║")
    print("║" + "   Universidad San Ignacio de Loyola".center(78) + "║")
    print("║" + "   Lógica Funcional Validada".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    print(f"\nFecha de ejecución: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")


def main():
    """Función principal del sistema"""
    try:
        # Mostrar banner
        imprimir_banner()
        
        # PASO 1: Extracción de CVs (PDF + Excel Links)
        print(f"\n{'█'*60}")
        print("█ PASO 1: EXTRACCIÓN DE DATOS")
        print(f"{'█'*60}\n")
        
        # Procesar CVs PDF
        print("📄 Procesando CVs en PDF...")
        cvs_pdf = procesar_todos_cvs()
        print(f"   ✓ {len(cvs_pdf)} CVs PDF procesados")
        
        # Procesar links de Excel
        print("\n🌐 Procesando links de CTI Vitae...")
        cvs_web = procesar_excel_links()
        print(f"   ✓ {len(cvs_web)} perfiles web procesados")
        
        # Combinar todos los CVs
        todos_cvs = cvs_pdf + cvs_web
        
        if not todos_cvs:
            print("\n❌ ERROR: No se encontraron CVs para procesar.")
            print("   Verifique carpeta 'Cvs' y archivo Excel con links\n")
            return 1
        
        print(f"\n✅ Total: {len(todos_cvs)} candidatos para evaluar\n")
        
        # PASO 2: Evaluación con Motor Simplificado
        print(f"\n{'█'*60}")
        print("█ PASO 2: EVALUACIÓN DE CANDIDATOS")
        print(f"{'█'*60}\n")
        
        motor = MotorEvaluacion()
        evaluaciones = motor.evaluar_multiples_cvs(todos_cvs)
        
        print(f"✅ {len(evaluaciones)} candidatos evaluados\n")
        
        # PASO 3: Generar Ranking y Resultados
        print(f"\n{'█'*60}")
        print("█ PASO 3: GENERACIÓN DE RANKING")
        print(f"{'█'*60}\n")
        
        # Guardar JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_json = os.path.join(RESULTADOS_DIR, f"clasificacion_final_{timestamp}.json")
        
        output = {
            "metadata": {
                "version": "3.0_SIMPLIFICADO",
                "fecha": datetime.now().isoformat(),
                "total_candidatos": len(evaluaciones),
                "descripcion": "Sistema con lógica funcional validada"
            },
            "ranking": evaluaciones,
            "reglas": {
                "total_maximo": TOTAL_MAXIMO,
                "exclusion": "C1=0 AND C5=0 → NO_ELEGIBLE",
                "no_califica": "TOTAL < 90",
                "practitioner": "90 <= TOTAL < 110",
                "dtc_dtp": "110 <= TOTAL < 150",
                "investigador_horas": "TOTAL >= 150"
            }
        }
        
        with open(archivo_json, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Guardado: {os.path.basename(archivo_json)}\n")
        
        # Mostrar Ranking
        print(f"\n{'='*70}")
        print("📊 RANKING FINAL DE CANDIDATOS")
        print(f"{'='*70}\n")
        
        print(f"{'#':<4} {'Nombre':<35} {'C1':<5} {'C2':<5} {'C3':<5} {'C4':<5} {'C5':<5} {'Total':<6} {'Perfil'}")
        print("-" * 90)
        
        for i, ev in enumerate(evaluaciones, 1):
            p = ev["puntajes"]
            perfil_corto = ev["clasificacion"][:20] if len(ev["clasificacion"]) > 20 else ev["clasificacion"]
            
            print(f"{i:<4} {ev['nombre']:<35} {p['C1']:<5} {p['C2']:<5} {p['C3']:<5} {p['C4']:<5} {p['C5']:<5} {ev['total']:<6} {perfil_corto}")
        
        # Resumen Final
        print(f"\n{'='*70}")
        print("✅ PROCESO COMPLETADO")
        print(f"{'='*70}\n")
        
        print(f"📊 RESUMEN:")
        print(f"   • Total evaluados: {len(evaluaciones)}")
        print(f"   • Elegibles: {sum(1 for e in evaluaciones if e['es_elegible'])}")
        print(f"   • No elegibles: {sum(1 for e in evaluaciones if not e['es_elegible'])}")
        
        if evaluaciones:
            mejor = evaluaciones[0]
            print(f"\n🏆 MEJOR CANDIDATO:")
            print(f"   • {mejor['nombre']}")
            print(f"   • {mejor['total']}/{TOTAL_MAXIMO} puntos ({mejor['porcentaje']}%)")
            print(f"   • {mejor['clasificacion']}")
        
        print(f"\n📂 Resultados guardados en: {RESULTADOS_DIR}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {str(e)}")
        print(f"   Tipo: {type(e).__name__}")
        import traceback
        print(f"\n   Detalle técnico:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
