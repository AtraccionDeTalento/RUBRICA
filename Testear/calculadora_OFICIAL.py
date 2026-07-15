#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema OFICIAL de Evaluación de Perfil Docente
Version: 2.0 OFICIAL
Fecha: 2026-01-30

CRITERIOS SEGÚN TABLAS OFICIALES PROPORCIONADAS
"""

import json
from datetime import datetime
from typing import Dict, Any


# ============================================================================
# DATOS DE LOS CANDIDATOS CON CRITERIOS OFICIALES
# ============================================================================

candidatos_data = [
    {
        "id": "CANDIDATO_001",
        "nombre_completo": "Luis Augusto Maya Velarde",
        "fuente": "CTI Vitae CONCYTEC (ID: 440291)",
        
        # C1: Formación Académica (Máx: 50)
        "C1": {
            "puntaje": 30,
            "categoria": "maestria_completa",
            "justificacion": "Tiene Magíster MBA obtenido (U. Europea del Atlántico). Maestrías en curso NO cuentan hasta obtención."
        },
        
        # C2: Experiencia Docente Universitaria (Máx: 50)
        "C2": {
            "puntaje": 5,
            "categoria": "sin_experiencia",
            "años": 0,
            "justificacion": "0 años de experiencia docente universitaria directa. Solo tiene formación en docencia (Especialización UBA)."
        },
        
        # C3: Experiencia Profesional (Máx: 40)
        "C3": {
            "puntaje": 10,
            "categoria": "analista_operativo",
            "cargo_mas_alto": "Analista Administrativo (ONPE)",
            "años_total": 5.5,
            "justificacion": "Cargo: Analista/Operativo en ONPE y Migraciones. No alcanza nivel de Jefatura/Coordinación."
        },
        
        # C4: Centro de Labores (Máx: 20)
        "C4": {
            "puntaje": 10,
            "categoria": "empresa_pequena",
            "nombre": "ONPE",
            "justificacion": "ONPE: institución pública de relevancia limitada (no Top 500 empresas)."
        },
        
        # C5: Producción Académica (Máx: 50) - CATEGÓRICO
        "C5": {
            "puntaje": 10,
            "categoria": "produccion_inicial",
            "nivel_mas_alto": "Tesis (documento técnico/informe)",
            "justificacion": "Tiene 3 tesis en repositorios. NO tiene Scopus/WoS (50), ni libro/revista indexada (40), ni proyectos investigación (30). Tesis = Producción inicial (10 pts)."
        }
    },
    
    {
        "id": "CANDIDATO_002",
        "nombre_completo": "Joshua Gabriel Lopez Pinto",
        "fuente": "CV PDF Adjunto",
        
        "C1": {
            "puntaje": 0,
            "categoria": "no_cumple",
            "justificacion": "Sin grado académico obtenido. Estudiante."
        },
        
        "C2": {
            "puntaje": 5,
            "categoria": "sin_experiencia",
            "años": 0,
            "justificacion": "Sin experiencia docente universitaria."
        },
        
        "C3": {
            "puntaje": 10,
            "categoria": "analista_operativo",
            "cargo_mas_alto": "Estimado: Analista",
            "años_total": 2,
            "justificacion": "~2 años experiencia profesional estimada, nivel operativo."
        },
        
        "C4": {
            "puntaje": 10,
            "categoria": "empresa_pequena",
            "nombre": "USIL (como estudiante)",
            "justificacion": "Afiliación a USIL como estudiante."
        },
        
        "C5": {
            "puntaje": 0,
            "categoria": "sin_evidencia",
            "justificacion": "Sin publicaciones académicas identificadas."
        }
    }
]


# ============================================================================
# FUNCIONES DE CÁLCULO
# ============================================================================

def calcular_puntaje_total(candidato: Dict[str, Any]) -> int:
    """Calcula el puntaje total sumando C1 + C2 + C3 + C4 + C5."""
    return (
        candidato["C1"]["puntaje"] +
        candidato["C2"]["puntaje"] +
        candidato["C3"]["puntaje"] +
        candidato["C4"]["puntaje"] +
        candidato["C5"]["puntaje"]
    )


def determinar_clasificacion(c1: int, c5: int, total: int) -> Dict[str, Any]:
    """
    Determina la clasificación según rangos aprobatorios oficiales.
    
    Reglas:
    1. Si C1 = 0 Y C5 = 0 → NO_ELEGIBLE (prioridad 1)
    2. Si TOTAL < 90 → NO_CALIFICA
    3. Si TOTAL >= 90 y < 110 → PRACTITIONER
    4. Si TOTAL >= 110 y < 150 → DTC/DTP/DOCENTE_INVESTIGADOR
    5. Si TOTAL >= 150 → CON_HORAS_INVESTIGACION
    """
    
    # Regla prioritaria: exclusión automática
    if c1 == 0 and c5 == 0:
        return {
            "perfil": "NO_ELEGIBLE_PERFIL_DOCENTE",
            "descripcion": "Sin formación académica Y sin producción académica",
            "es_elegible": False,
            "puntaje_minimo_requerido": None
        }
    
    # Clasificación por puntaje
    if total < 90:
        return {
            "perfil": "NO_CALIFICA",
            "descripcion": "Puntaje insuficiente (< 90 puntos)",
            "es_elegible": False,
            "puntaje_minimo_requerido": 90
        }
    elif total < 110:
        return {
            "perfil": "PRACTITIONER",
            "descripcion": "Profesional de campo (Prioriza experiencia profesional)",
            "es_elegible": True,
            "puntaje_minimo_requerido": 90
        }
    elif total < 150:
        return {
            "perfil": "DTC/DTP/DOCENTE_INVESTIGADOR",
            "descripcion": "Docente Tiempo Completo/Parcial o Docente Investigador",
            "es_elegible": True,
            "puntaje_minimo_requerido": 110
        }
    else:
        return {
            "perfil": "CON_HORAS_INVESTIGACION",
            "descripcion": "Docente con Horas de Investigación (requiere C5 > 0)",
            "es_elegible": True,
            "puntaje_minimo_requerido": 150
        }


def generar_evaluacion_completa(candidato: Dict[str, Any]) -> Dict[str, Any]:
    """Genera la evaluación completa de un candidato."""
    
    total = calcular_puntaje_total(candidato)
    clasificacion = determinar_clasificacion(
        candidato["C1"]["puntaje"],
        candidato["C5"]["puntaje"],
        total
    )
    
    return {
        "id": candidato["id"],
        "nombre_completo": candidato["nombre_completo"],
        "fuente": candidato["fuente"],
        "fecha_evaluacion": datetime.now().isoformat(),
        
        "criterios": {
            "C1": {
                **candidato["C1"],
                "nombre": "Formación Académica",
                "puntaje_maximo": 50
            },
            "C2": {
                **candidato["C2"],
                "nombre": "Experiencia Docente Universitaria",
                "puntaje_maximo": 50
            },
            "C3": {
                **candidato["C3"],
                "nombre": "Experiencia Profesional",
                "puntaje_maximo": 40
            },
            "C4": {
                **candidato["C4"],
                "nombre": "Centro de Labores",
                "puntaje_maximo": 20
            },
            "C5": {
                **candidato["C5"],
                "nombre": "Producción Académica",
                "puntaje_maximo": 50
            }
        },
        
        "puntaje_total": total,
        "puntaje_maximo_posible": 210,
        "porcentaje": round((total / 210) * 100, 2),
        
        "clasificacion": clasificacion["perfil"],
        "descripcion_clasificacion": clasificacion["descripcion"],
        "es_elegible": clasificacion["es_elegible"],
        "puntaje_minimo_requerido": clasificacion.get("puntaje_minimo_requerido")
    }


def generar_ranking(candidatos: list) -> list:
    """Genera el ranking ordenado de candidatos."""
    evaluaciones = [generar_evaluacion_completa(c) for c in candidatos]
    ranking = sorted(evaluaciones, key=lambda x: x["puntaje_total"], reverse=True)
    
    for i, evaluacion in enumerate(ranking, 1):
        evaluacion["posicion_ranking"] = i
    
    return ranking


def generar_tabla_markdown(ranking: list) -> str:
    """Genera tabla markdown con el ranking."""
    lineas = []
    lineas.append("# 🏆 RANKING OFICIAL - CRITERIOS CORRECTOS\n")
    lineas.append(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lineas.append(f"**Total candidatos:** {len(ranking)}")
    lineas.append("**Sistema:** Criterios Oficiales v2.0\n")
    
    lineas.append("| Pos | Nombre | C1 | C2 | C3 | C4 | C5 | **TOTAL** | % | Clasificación |")
    lineas.append("|-----|--------|----|----|----|----|----|-----------|----|--------------")
    
    for ev in ranking:
        lineas.append(
            f"| {ev['posicion_ranking']} | "
            f"{ev['nombre_completo'][:30]} | "
            f"{ev['criterios']['C1']['puntaje']} | "
            f"{ev['criterios']['C2']['puntaje']} | "
            f"{ev['criterios']['C3']['puntaje']} | "
            f"{ev['criterios']['C4']['puntaje']} | "
            f"{ev['criterios']['C5']['puntaje']} | "
            f"**{ev['puntaje_total']}** | "
            f"{ev['porcentaje']}% | "
            f"{ev['clasificacion']} |"
        )
    
    lineas.append("\n## 📊 Puntajes Máximos (OFICIAL)")
    lineas.append("- **C1** Formación Académica: 50 pts")
    lineas.append("- **C2** Experiencia Docente Universitaria: 50 pts")
    lineas.append("- **C3** Experiencia Profesional: 40 pts")
    lineas.append("- **C4** Centro de Labores: 20 pts")
    lineas.append("- **C5** Producción Académica: 50 pts (CATEGÓRICO, no acumulativo)")
    lineas.append("- **TOTAL MÁXIMO: 210 pts**")
    
    lineas.append("\n## ⚠️ CRITERIOS CLAVE")
    lineas.append("1. **C5 es CATEGÓRICO:** Se toma el nivel más alto, NO se suman publicaciones")
    lineas.append("2. **C3 evalúa CARGO:** Prioriza nivel de responsabilidad sobre años")
    lineas.append("3. **Exclusión automática:** Si C1=0 Y C5=0 → NO ELEGIBLE")
    lineas.append("4. **Rangos:** < 90 = NO CALIFICA | 90-109 = PRACTITIONER | 110-149 = DTC/DTP | 150+ = INVESTIGACIÓN")
    
    return "\n".join(lineas)


# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    print("🔄 Generando evaluación con CRITERIOS OFICIALES...\n")
    
    # Generar ranking
    ranking = generar_ranking(candidatos_data)
    
    # Exportar JSON completo
    output_json = {
        "metadata": {
            "version": "2.0_OFICIAL",
            "fecha_generacion": datetime.now().isoformat(),
            "fuente_criterios": "Tablas Oficiales Institucionales",
            "total_candidatos": len(ranking)
        },
        "ranking": ranking
    }
    
    with open("ranking_OFICIAL.json", "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)
    
    print("✅ Exportado: ranking_OFICIAL.json")
    
    # Generar tabla markdown
    tabla = generar_tabla_markdown(ranking)
    
    with open("ranking_OFICIAL.md", "w", encoding="utf-8") as f:
        f.write(tabla)
    
    print("✅ Exportado: ranking_OFICIAL.md\n")
    
    # Mostrar en consola
    print(tabla)
    
    print("\n" + "="*70)
    print("📊 RESUMEN COMPARATIVO")
    print("="*70)
    
    for ev in ranking:
        print(f"\n{ev['posicion_ranking']}. {ev['nombre_completo']}")
        print(f"   Total: {ev['puntaje_total']}/210 pts ({ev['porcentaje']}%)")
        print(f"   Clasificación: {ev['clasificacion']}")
        print(f"   Elegible: {'✅ SÍ' if ev['es_elegible'] else '❌ NO'}")
        
        if not ev['es_elegible'] and ev['puntaje_minimo_requerido']:
            gap = ev['puntaje_minimo_requerido'] - ev['puntaje_total']
            print(f"   Gap hasta PRACTITIONER: +{gap} puntos")
    
    print("\n✅ Proceso completado con criterios oficiales")
