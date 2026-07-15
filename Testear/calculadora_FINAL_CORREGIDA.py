#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema FINAL de Evaluación de Perfil Docente
Version: 3.0 CORREGIDA
Fecha: 2026-01-30

VALORES VALIDADOS Y CORREGIDOS
"""

import json
from datetime import datetime


# ============================================================================
# DATOS CORREGIDOS DE LOS CANDIDATOS
# ============================================================================

PERFIL_A = {
    "id": "PERFIL_A",
    "nombre": "Luis Augusto Maya Velarde",
    "fuente": "CTI Vitae CONCYTEC",
    "id_concytec": "440291",
    
    "C1": {
        "puntaje": 15,
        "categoria": "bachiller_licenciatura",
        "justificacion": "MBA obtenido pero NO alineado al área de docencia requerida. Se evalúa con Licenciatura = 15 pts"
    },
    "C2": {
        "puntaje": 5,
        "categoria": "sin_experiencia",
        "justificacion": "0 años de experiencia docente universitaria directa. Tiene formación en docencia (no cuenta como experiencia)"
    },
    "C3": {
        "puntaje": 15,
        "categoria": "especialista_junior_4_7_anios",
        "justificacion": "~5.5 años experiencia profesional. Rango 4-7 años = Especialista Junior = 15 pts"
    },
    "C4": {
        "puntaje": 15,
        "categoria": "empresa_mediana_reconocida",
        "justificacion": "ONPE: Institución pública con reconocimiento sectorial = 15 pts"
    },
    "C5": {
        "puntaje": 30,
        "categoria": "investigacion_proyectos",
        "justificacion": "3 tesis en repositorios + líneas de investigación CONCYTEC + participación UNICAMP/CEPAL = 30 pts"
    }
}

PERFIL_B = {
    "id": "PERFIL_B",
    "nombre": "Joshua Gabriel Lopez Pinto",
    "fuente": "CV PDF",
    
    "C1": {
        "puntaje": 0,
        "categoria": "no_cumple",
        "justificacion": "Estudiante sin grado académico obtenido"
    },
    "C2": {
        "puntaje": 5,
        "categoria": "sin_experiencia",
        "justificacion": "Sin experiencia docente universitaria"
    },
    "C3": {
        "puntaje": 10,
        "categoria": "analista_operativo",
        "justificacion": "~2 años experiencia estimada, nivel operativo"
    },
    "C4": {
        "puntaje": 10,
        "categoria": "empresa_pequena",
        "justificacion": "Afiliación como estudiante a USIL"
    },
    "C5": {
        "puntaje": 0,
        "categoria": "sin_evidencia",
        "justificacion": "Sin publicaciones académicas identificadas"
    }
}


# ============================================================================
# CONSTANTES DEL SISTEMA
# ============================================================================

PUNTAJES_MAXIMOS = {
    "C1": 50,  # Formación Académica
    "C2": 50,  # Experiencia Docente Universitaria
    "C3": 40,  # Experiencia Profesional
    "C4": 20,  # Centro de Labores
    "C5": 50   # Producción Académica
}

TOTAL_MAXIMO = sum(PUNTAJES_MAXIMOS.values())  # 210


# ============================================================================
# FUNCIONES
# ============================================================================

def calcular_total(perfil: dict) -> int:
    """Suma los puntajes C1 + C2 + C3 + C4 + C5."""
    return (
        perfil["C1"]["puntaje"] +
        perfil["C2"]["puntaje"] +
        perfil["C3"]["puntaje"] +
        perfil["C4"]["puntaje"] +
        perfil["C5"]["puntaje"]
    )


def clasificar_perfil(c1: int, c5: int, total: int) -> dict:
    """Determina la clasificación según las reglas establecidas."""
    
    # Regla prioritaria: exclusión automática
    if c1 == 0 and c5 == 0:
        return {
            "clasificacion": "NO_ELEGIBLE_PERFIL_DOCENTE",
            "razon": "C1=0 AND C5=0 → Exclusión automática",
            "es_elegible": False,
            "gap_practitioner": None
        }
    
    # Clasificación por puntaje
    if total < 90:
        return {
            "clasificacion": "NO_CALIFICA",
            "razon": f"TOTAL ({total}) < 90",
            "es_elegible": False,
            "gap_practitioner": 90 - total
        }
    elif total < 110:
        return {
            "clasificacion": "PRACTITIONER",
            "razon": f"90 <= TOTAL ({total}) < 110",
            "es_elegible": True,
            "gap_practitioner": 0
        }
    elif total < 150:
        return {
            "clasificacion": "DTC/DTP/DOCENTE_INVESTIGADOR",
            "razon": f"110 <= TOTAL ({total}) < 150",
            "es_elegible": True,
            "gap_practitioner": 0
        }
    else:
        return {
            "clasificacion": "DOCENTE_INVESTIGADOR_CON_HORAS_INVESTIGACION",
            "razon": f"TOTAL ({total}) >= 150",
            "es_elegible": True,
            "gap_practitioner": 0
        }


def evaluar_perfil(perfil: dict) -> dict:
    """Evalúa un perfil completo."""
    total = calcular_total(perfil)
    clasificacion = clasificar_perfil(
        perfil["C1"]["puntaje"],
        perfil["C5"]["puntaje"],
        total
    )
    
    return {
        "id": perfil["id"],
        "nombre": perfil["nombre"],
        "fuente": perfil["fuente"],
        "puntajes": {
            "C1": perfil["C1"]["puntaje"],
            "C2": perfil["C2"]["puntaje"],
            "C3": perfil["C3"]["puntaje"],
            "C4": perfil["C4"]["puntaje"],
            "C5": perfil["C5"]["puntaje"]
        },
        "total": total,
        "maximo": TOTAL_MAXIMO,
        "porcentaje": round((total / TOTAL_MAXIMO) * 100, 1),
        **clasificacion
    }


def generar_tabla_markdown(evaluaciones: list) -> str:
    """Genera tabla markdown del ranking."""
    lineas = [
        "# 📊 TABLAS FINALES - CORREGIDAS Y VALIDADAS\n",
        f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Sistema:** Criterios Oficiales v3.0 CORREGIDA\n",
        "---\n",
        "## 📊 TABLA 1 — PERFIL A\n",
        f"**Fuente:** {evaluaciones[0]['fuente']}",
        f"**Candidato:** {evaluaciones[0]['nombre']}\n",
        "| Criterio | Código | Puntaje | Máx |",
        "|----------|--------|---------|-----|",
    ]
    
    nombres_criterios = {
        "C1": "Formación Académica",
        "C2": "Experiencia Docente Univ.",
        "C3": "Experiencia Profesional",
        "C4": "Centro de Labores",
        "C5": "Producción Académica"
    }
    
    for codigo, nombre in nombres_criterios.items():
        pts = evaluaciones[0]["puntajes"][codigo]
        max_pts = PUNTAJES_MAXIMOS[codigo]
        lineas.append(f"| {nombre} | {codigo} | **{pts}** | {max_pts} |")
    
    lineas.append(f"| **TOTAL** | — | **{evaluaciones[0]['total']}** | **{TOTAL_MAXIMO}** |\n")
    lineas.append(f"**Clasificación:** `{evaluaciones[0]['clasificacion']}`")
    if evaluaciones[0].get("gap_practitioner"):
        lineas.append(f"**Gap hasta PRACTITIONER:** +{evaluaciones[0]['gap_practitioner']} puntos\n")
    
    lineas.append("\n---\n")
    lineas.append("## 📊 TABLA 2 — PERFIL B\n")
    lineas.append(f"**Fuente:** {evaluaciones[1]['fuente']}")
    lineas.append(f"**Candidato:** {evaluaciones[1]['nombre']}\n")
    lineas.append("| Criterio | Código | Puntaje | Máx |")
    lineas.append("|----------|--------|---------|-----|")
    
    for codigo, nombre in nombres_criterios.items():
        pts = evaluaciones[1]["puntajes"][codigo]
        max_pts = PUNTAJES_MAXIMOS[codigo]
        lineas.append(f"| {nombre} | {codigo} | **{pts}** | {max_pts} |")
    
    lineas.append(f"| **TOTAL** | — | **{evaluaciones[1]['total']}** | **{TOTAL_MAXIMO}** |\n")
    lineas.append(f"**Clasificación:** `{evaluaciones[1]['clasificacion']}`")
    lineas.append(f"**Razón:** {evaluaciones[1]['razon']}\n")
    
    # Ranking
    lineas.append("\n---\n")
    lineas.append("## 🏆 RANKING FINAL\n")
    lineas.append("| Pos | Nombre | C1 | C2 | C3 | C4 | C5 | **TOTAL** | Clasificación |")
    lineas.append("|-----|--------|----|----|----|----|----|-----------|--------------| ")
    
    for i, ev in enumerate(evaluaciones, 1):
        p = ev["puntajes"]
        lineas.append(
            f"| **{i}** | {ev['nombre']} | {p['C1']} | {p['C2']} | {p['C3']} | {p['C4']} | {p['C5']} | **{ev['total']}** | {ev['clasificacion']} |"
        )
    
    lineas.append("\n---\n")
    lineas.append("## 🧠 REGLA GLOBAL\n")
    lineas.append("```text")
    lineas.append(f"TOTAL_MAX = {TOTAL_MAXIMO}")
    lineas.append("")
    lineas.append("SI (C1 == 0) AND (C5 == 0):")
    lineas.append("    PERFIL = NO_ELEGIBLE_PERFIL_DOCENTE")
    lineas.append("")
    lineas.append("SI (TOTAL < 90):")
    lineas.append("    PERFIL = NO_CALIFICA")
    lineas.append("")
    lineas.append("SI (TOTAL >= 90) AND (TOTAL < 110):")
    lineas.append("    PERFIL = PRACTITIONER")
    lineas.append("")
    lineas.append("SI (TOTAL >= 110) AND (TOTAL < 150):")
    lineas.append("    PERFIL = DTC / DTP / DOCENTE_INVESTIGADOR")
    lineas.append("")
    lineas.append("SI (TOTAL >= 150):")
    lineas.append("    PERFIL = DOCENTE_INVESTIGADOR_CON_HORAS_INVESTIGACION")
    lineas.append("```")
    lineas.append("\n**✅ Cálculos verificados y corregidos**")
    
    return "\n".join(lineas)


# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    print("🔄 Generando evaluación CORREGIDA...\n")
    
    # Evaluar perfiles
    eval_a = evaluar_perfil(PERFIL_A)
    eval_b = evaluar_perfil(PERFIL_B)
    evaluaciones = [eval_a, eval_b]
    
    # Ordenar por puntaje
    evaluaciones.sort(key=lambda x: x["total"], reverse=True)
    
    # Exportar JSON
    output = {
        "metadata": {
            "version": "3.0_CORREGIDA",
            "fecha": datetime.now().isoformat(),
            "descripcion": "Valores validados y corregidos según criterios oficiales"
        },
        "perfiles": evaluaciones,
        "reglas": {
            "total_maximo": TOTAL_MAXIMO,
            "exclusion": "C1=0 AND C5=0 → NO_ELEGIBLE",
            "no_califica": "TOTAL < 90",
            "practitioner": "90 <= TOTAL < 110",
            "dtc_dtp": "110 <= TOTAL < 150",
            "investigador_horas": "TOTAL >= 150"
        }
    }
    
    with open("ranking_FINAL_CORREGIDO.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print("✅ Exportado: ranking_FINAL_CORREGIDO.json")
    
    # Generar tabla markdown
    tabla = generar_tabla_markdown(evaluaciones)
    with open("ranking_FINAL_CORREGIDO.md", "w", encoding="utf-8") as f:
        f.write(tabla)
    print("✅ Exportado: ranking_FINAL_CORREGIDO.md\n")
    
    # Mostrar resultados
    print("="*70)
    print("📊 RESULTADOS FINALES CORREGIDOS")
    print("="*70)
    
    for i, ev in enumerate(evaluaciones, 1):
        print(f"\n{i}. {ev['nombre']}")
        print(f"   C1={ev['puntajes']['C1']} | C2={ev['puntajes']['C2']} | C3={ev['puntajes']['C3']} | C4={ev['puntajes']['C4']} | C5={ev['puntajes']['C5']}")
        print(f"   TOTAL: {ev['total']}/{TOTAL_MAXIMO} ({ev['porcentaje']}%)")
        print(f"   Clasificación: {ev['clasificacion']}")
        print(f"   Elegible: {'✅ SÍ' if ev['es_elegible'] else '❌ NO'}")
        if ev.get('gap_practitioner') and ev['gap_practitioner'] > 0:
            print(f"   Gap hasta PRACTITIONER: +{ev['gap_practitioner']} puntos")
    
    print("\n" + "="*70)
    print("✅ Proceso completado - Valores corregidos y validados")
    print("="*70)
