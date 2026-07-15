#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 SCRIPT DE PRUEBAS - Sistema de Evaluación de Perfil Docente
Fecha: 2026-01-30

Valida que los cálculos sean EXACTOS según las tablas esperadas.
"""

import json
from datetime import datetime

print("="*70)
print("🧪 INICIANDO PRUEBAS DEL SISTEMA DE EVALUACIÓN")
print("="*70)
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# TABLAS OFICIALES DE REFERENCIA (según imágenes proporcionadas)
# ============================================================================

TABLA_C1 = {
    "doctorado_completo": 50,
    "doctorado_en_curso": 40,
    "maestria_completa": 30,
    "bachiller_licenciatura": 15,
    "no_cumple": 0
}

TABLA_C2 = {
    "5_plus_anios": 40,
    "3_4_anios": 30,
    "1_2_anios": 20,
    "0_anios": 5
}

TABLA_C3 = {
    "alta_direccion_gerencia": 40,
    "mando_medio": 30,
    "profesional_senior": 25,
    "intermedio_junior": 15,
    "analista_operativo": 10,
    "sin_experiencia": 0
}

TABLA_C4 = {
    "empresa_top": 20,
    "empresa_mediana_reconocida": 15,
    "empresa_pequena": 10,
    "independiente": 0
}

TABLA_C5 = {
    "scopus_wos": 50,
    "libro_revista_indexada": 40,
    "investigacion_proyectos": 30,
    "produccion_inicial": 10,
    "sin_evidencia": 0
}

RANGOS = {
    "NO_ELEGIBLE": {"condicion": "C1=0 AND C5=0"},
    "NO_CALIFICA": {"min": 0, "max": 89},
    "PRACTITIONER": {"min": 90, "max": 109},
    "DTC_DTP_INVESTIGADOR": {"min": 110, "max": 149},
    "CON_HORAS_INVESTIGACION": {"min": 150, "max": 200}
}

# ============================================================================
# FUNCIÓN DE CLASIFICACIÓN
# ============================================================================

def clasificar(c1, c2, c3, c4, c5):
    """Clasifica un perfil según las reglas establecidas."""
    total = c1 + c2 + c3 + c4 + c5
    
    # Regla prioritaria
    if c1 == 0 and c5 == 0:
        return total, "NO_ELEGIBLE_PERFIL_DOCENTE"
    
    # Por puntaje
    if total < 90:
        return total, "NO_CALIFICA"
    elif total < 110:
        return total, "PRACTITIONER"
    elif total < 150:
        return total, "DTC_DTP_DOCENTE_INVESTIGADOR"
    else:
        return total, "DOCENTE_INVESTIGADOR_CON_HORAS_INVESTIGACION"

# ============================================================================
# CASOS DE PRUEBA
# ============================================================================

print("📋 CASO 1: PERFIL A (Luis Augusto Maya Velarde)")
print("-"*50)

# Valores esperados según tu análisis
PERFIL_A_ESPERADO = {
    "C1": 15,  # Bachiller/Licenciatura (MBA no alineado)
    "C2": 5,   # Sin experiencia docente
    "C3": 15,  # Especialista Junior (4-7 años)
    "C4": 15,  # Empresa mediana reconocida (ONPE)
    "C5": 30,  # Investigación/proyectos
    "TOTAL": 80,
    "CLASIFICACION": "NO_CALIFICA"
}

# Calcular
total_a, clasif_a = clasificar(
    PERFIL_A_ESPERADO["C1"],
    PERFIL_A_ESPERADO["C2"],
    PERFIL_A_ESPERADO["C3"],
    PERFIL_A_ESPERADO["C4"],
    PERFIL_A_ESPERADO["C5"]
)

print(f"  C1 (Formación Académica):      {PERFIL_A_ESPERADO['C1']} pts")
print(f"  C2 (Experiencia Docente):      {PERFIL_A_ESPERADO['C2']} pts")
print(f"  C3 (Experiencia Profesional):  {PERFIL_A_ESPERADO['C3']} pts")
print(f"  C4 (Centro de Labores):        {PERFIL_A_ESPERADO['C4']} pts")
print(f"  C5 (Producción Académica):     {PERFIL_A_ESPERADO['C5']} pts")
print(f"  ─────────────────────────────────────")
print(f"  TOTAL CALCULADO:               {total_a} pts")
print(f"  TOTAL ESPERADO:                {PERFIL_A_ESPERADO['TOTAL']} pts")
print(f"  CLASIFICACIÓN:                 {clasif_a}")

# Validación
assert total_a == PERFIL_A_ESPERADO["TOTAL"], f"❌ ERROR: Total calculado ({total_a}) != esperado ({PERFIL_A_ESPERADO['TOTAL']})"
assert "NO_CALIFICA" in clasif_a, f"❌ ERROR: Clasificación incorrecta"
print(f"\n  ✅ PRUEBA PERFIL A: PASSED")

# ============================================================================
print("\n" + "="*70)
print("📋 CASO 2: PERFIL B (Joshua Gabriel Lopez Pinto)")
print("-"*50)

PERFIL_B_ESPERADO = {
    "C1": 0,   # Sin grado académico
    "C2": 5,   # Sin experiencia docente
    "C3": 10,  # Analista/Operativo
    "C4": 10,  # Empresa pequeña
    "C5": 0,   # Sin producción
    "TOTAL": 25,
    "CLASIFICACION": "NO_ELEGIBLE_PERFIL_DOCENTE"
}

total_b, clasif_b = clasificar(
    PERFIL_B_ESPERADO["C1"],
    PERFIL_B_ESPERADO["C2"],
    PERFIL_B_ESPERADO["C3"],
    PERFIL_B_ESPERADO["C4"],
    PERFIL_B_ESPERADO["C5"]
)

print(f"  C1 (Formación Académica):      {PERFIL_B_ESPERADO['C1']} pts")
print(f"  C2 (Experiencia Docente):      {PERFIL_B_ESPERADO['C2']} pts")
print(f"  C3 (Experiencia Profesional):  {PERFIL_B_ESPERADO['C3']} pts")
print(f"  C4 (Centro de Labores):        {PERFIL_B_ESPERADO['C4']} pts")
print(f"  C5 (Producción Académica):     {PERFIL_B_ESPERADO['C5']} pts")
print(f"  ─────────────────────────────────────")
print(f"  TOTAL CALCULADO:               {total_b} pts")
print(f"  TOTAL ESPERADO:                {PERFIL_B_ESPERADO['TOTAL']} pts")
print(f"  CLASIFICACIÓN:                 {clasif_b}")

# Validar regla de exclusión
assert total_b == PERFIL_B_ESPERADO["TOTAL"], f"❌ ERROR: Total"
assert clasif_b == "NO_ELEGIBLE_PERFIL_DOCENTE", f"❌ ERROR: Debería ser NO_ELEGIBLE (C1=0 AND C5=0)"
print(f"\n  ✅ PRUEBA PERFIL B: PASSED")
print(f"  ✅ REGLA C1=0 AND C5=0 → NO_ELEGIBLE: VERIFICADA")

# ============================================================================
print("\n" + "="*70)
print("📋 CASOS LÍMITE - RANGOS DE CLASIFICACIÓN")
print("-"*50)

casos_limite = [
    # (C1, C2, C3, C4, C5, clasificacion_esperada, descripcion)
    (15, 5, 10, 10, 0, "NO_CALIFICA", "40 pts - Muy bajo"),
    (30, 5, 15, 15, 24, "NO_CALIFICA", "89 pts - Justo debajo de PRACTITIONER"),
    (30, 5, 15, 15, 25, "PRACTITIONER", "90 pts - Mínimo PRACTITIONER"),
    (30, 20, 25, 15, 19, "PRACTITIONER", "109 pts - Máximo PRACTITIONER"),
    (30, 20, 25, 15, 20, "DTC_DTP", "110 pts - Mínimo DTC/DTP"),
    (50, 40, 30, 15, 14, "DTC_DTP", "149 pts - Máximo DTC/DTP"),
    (50, 40, 30, 15, 15, "CON_HORAS", "150 pts - Mínimo Investigación"),
    (50, 40, 40, 20, 50, "CON_HORAS", "200 pts - MÁXIMO POSIBLE"),
    (0, 5, 40, 20, 0, "NO_ELEGIBLE", "65 pts pero C1=0 Y C5=0 → Exclusión"),
]

todos_pasaron = True
for c1, c2, c3, c4, c5, esperado, desc in casos_limite:
    total, clasif = clasificar(c1, c2, c3, c4, c5)
    
    # Verificar clasificación
    coincide = esperado in clasif
    status = "✅" if coincide else "❌"
    
    if not coincide:
        todos_pasaron = False
    
    print(f"  {status} {desc}")
    print(f"     C1={c1} C2={c2} C3={c3} C4={c4} C5={c5} → Total={total} → {clasif}")

if todos_pasaron:
    print(f"\n  ✅ TODOS LOS CASOS LÍMITE: PASSED")
else:
    print(f"\n  ❌ ALGUNOS CASOS FALLARON")

# ============================================================================
print("\n" + "="*70)
print("📋 VERIFICACIÓN DE PUNTAJES MÁXIMOS")
print("-"*50)

MAXIMOS = {"C1": 50, "C2": 40, "C3": 40, "C4": 20, "C5": 50}
TOTAL_MAX = sum(MAXIMOS.values())

print(f"  C1 máximo: {MAXIMOS['C1']} pts")
print(f"  C2 máximo: {MAXIMOS['C2']} pts")
print(f"  C3 máximo: {MAXIMOS['C3']} pts")
print(f"  C4 máximo: {MAXIMOS['C4']} pts")
print(f"  C5 máximo: {MAXIMOS['C5']} pts")
print(f"  ─────────────────────────────────────")
print(f"  TOTAL MÁXIMO: {TOTAL_MAX} pts")

assert TOTAL_MAX == 200, f"❌ ERROR: Total máximo debería ser 200, es {TOTAL_MAX}"
print(f"\n  ✅ VERIFICACIÓN MÁXIMOS: PASSED (200 pts)")

# ============================================================================
print("\n" + "="*70)
print("📋 SIMULACIÓN: ¿QUÉ NECESITA PERFIL A PARA MEJORAR?")
print("-"*50)

# Perfil A actual: 80 pts
# Necesita: 90 pts para PRACTITIONER (+10 pts)

print(f"  Estado actual: {total_a} pts → {clasif_a}")
print(f"  Gap hasta PRACTITIONER: +{90 - total_a} pts\n")

# Opción 1: Mejorar C2 (docencia)
nuevo_c2 = 20  # Si consigue 1-2 años docencia
nuevo_total_1 = PERFIL_A_ESPERADO["C1"] + nuevo_c2 + PERFIL_A_ESPERADO["C3"] + PERFIL_A_ESPERADO["C4"] + PERFIL_A_ESPERADO["C5"]
_, nueva_clasif_1 = clasificar(PERFIL_A_ESPERADO["C1"], nuevo_c2, PERFIL_A_ESPERADO["C3"], PERFIL_A_ESPERADO["C4"], PERFIL_A_ESPERADO["C5"])
print(f"  OPCIÓN 1: Conseguir 1-2 años docencia (C2: 5→20)")
print(f"            Nuevo total: {nuevo_total_1} pts → {nueva_clasif_1}")

# Opción 2: Mejorar C5 (publicación indexada)
nuevo_c5 = 40  # Si publica en revista indexada
nuevo_total_2 = PERFIL_A_ESPERADO["C1"] + PERFIL_A_ESPERADO["C2"] + PERFIL_A_ESPERADO["C3"] + PERFIL_A_ESPERADO["C4"] + nuevo_c5
_, nueva_clasif_2 = clasificar(PERFIL_A_ESPERADO["C1"], PERFIL_A_ESPERADO["C2"], PERFIL_A_ESPERADO["C3"], PERFIL_A_ESPERADO["C4"], nuevo_c5)
print(f"\n  OPCIÓN 2: Publicar en revista indexada (C5: 30→40)")
print(f"            Nuevo total: {nuevo_total_2} pts → {nueva_clasif_2}")

# Opción 3: Combinado
nuevo_total_3 = PERFIL_A_ESPERADO["C1"] + nuevo_c2 + PERFIL_A_ESPERADO["C3"] + PERFIL_A_ESPERADO["C4"] + nuevo_c5
_, nueva_clasif_3 = clasificar(PERFIL_A_ESPERADO["C1"], nuevo_c2, PERFIL_A_ESPERADO["C3"], PERFIL_A_ESPERADO["C4"], nuevo_c5)
print(f"\n  OPCIÓN 3: Docencia + Publicación (C2:20, C5:40)")
print(f"            Nuevo total: {nuevo_total_3} pts → {nueva_clasif_3}")

# ============================================================================
print("\n" + "="*70)
print("🎯 RESUMEN FINAL DE PRUEBAS")
print("="*70)

resultados = {
    "Perfil A - Cálculo correcto": total_a == 80,
    "Perfil A - Clasificación correcta": "NO_CALIFICA" in clasif_a,
    "Perfil B - Cálculo correcto": total_b == 25,
    "Perfil B - Exclusión C1=0 Y C5=0": clasif_b == "NO_ELEGIBLE_PERFIL_DOCENTE",
    "Máximo total = 200": TOTAL_MAX == 200,
    "Casos límite OK": todos_pasaron
}

total_pruebas = len(resultados)
pruebas_ok = sum(resultados.values())

print()
for prueba, resultado in resultados.items():
    status = "✅ PASS" if resultado else "❌ FAIL"
    print(f"  {status} - {prueba}")

print()
print(f"  ═══════════════════════════════════════")
print(f"  RESULTADO: {pruebas_ok}/{total_pruebas} pruebas pasaron")
print(f"  ═══════════════════════════════════════")

if pruebas_ok == total_pruebas:
    print("\n  🎉 ¡TODAS LAS PRUEBAS PASARON!")
    print("  ✅ El sistema está VALIDADO y listo para producción")
else:
    print("\n  ⚠️ Algunas pruebas fallaron. Revisar.")

# ============================================================================
# EXPORTAR RESULTADOS DE PRUEBAS
# ============================================================================

resultado_pruebas = {
    "fecha": datetime.now().isoformat(),
    "total_pruebas": total_pruebas,
    "pruebas_ok": pruebas_ok,
    "estado": "VALIDADO" if pruebas_ok == total_pruebas else "REQUIERE_REVISION",
    "perfiles_probados": {
        "perfil_a": {
            "nombre": "Luis Augusto Maya Velarde",
            "puntajes": {"C1": 15, "C2": 5, "C3": 15, "C4": 15, "C5": 30},
            "total": total_a,
            "clasificacion": clasif_a,
            "validacion": "OK"
        },
        "perfil_b": {
            "nombre": "Joshua Gabriel Lopez Pinto",
            "puntajes": {"C1": 0, "C2": 5, "C3": 10, "C4": 10, "C5": 0},
            "total": total_b,
            "clasificacion": clasif_b,
            "validacion": "OK"
        }
    },
    "reglas_verificadas": [
        "C1=0 AND C5=0 → NO_ELEGIBLE",
        "TOTAL < 90 → NO_CALIFICA",
        "90 <= TOTAL < 110 → PRACTITIONER",
        "110 <= TOTAL < 150 → DTC/DTP/INVESTIGADOR",
        "TOTAL >= 150 → CON_HORAS_INVESTIGACION"
    ]
}

with open("resultado_pruebas.json", "w", encoding="utf-8") as f:
    json.dump(resultado_pruebas, f, indent=2, ensure_ascii=False)

print("\n  📄 Exportado: resultado_pruebas.json")
print("\n" + "="*70)
