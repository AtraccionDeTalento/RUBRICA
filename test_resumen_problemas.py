#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test de lectura de datos desde Excel y generación de resumen de problemas"""

import sys
import os

# Cambiar al directorio correcto
base_dir = os.path.dirname(os.path.abspath(__file__))
bot_dir = os.path.join(base_dir, 'bot_evaluacion_docente')
os.chdir(bot_dir)
sys.path.insert(0, bot_dir)

from app_web import leer_datos_desde_requerimientos

print("="*70)
print("PRUEBA DE LECTURA DE DATOS Y RESUMEN DE PROBLEMAS")
print("="*70)

urls, datos_excel, resumen_problemas = leer_datos_desde_requerimientos()

print(f"\n✅ URLs válidas encontradas: {len(urls)}")
print(f"✅ Registros en datos_excel: {len(datos_excel)}")

print(f"\n📊 RESUMEN DE PROBLEMAS:")
print(f"   Links inválidos: {len(resumen_problemas.get('links_invalidos', []))}")
print(f"   Datos faltantes: {len(resumen_problemas.get('datos_faltantes', []))}")

print(f"\n📍 DESGLOSE POR FACULTAD:")
for facultad, stats in resumen_problemas.get("resumen_facultades", {}).items():
    total = stats.get('total', 0)
    con_link = stats.get('con_link_valido', 0)
    sin_link = stats.get('sin_link', 0)
    invalido = stats.get('link_invalido', 0)
    
    if sin_link > 0 or invalido > 0:
        print(f"\n🏛️  {facultad}")
        print(f"    Total: {total} | Con link: {con_link} | Sin link: {sin_link} | Inválido: {invalido}")
        
        # Mostrar personas sin link
        for p in stats.get('personas_sin_link', [])[:3]:
            print(f"    ❌ {p.get('nombre', 'N/A')} (DNI: {p.get('dni', 'N/A')}) - {p.get('motivo', '')}")
        
        for p in stats.get('personas_link_invalido', [])[:3]:
            print(f"    ⚠️  {p.get('nombre', 'N/A')} (DNI: {p.get('dni', 'N/A')}) - {p.get('motivo', '')}")

print("\n" + "="*70)
print("Datos para el frontend (resumen_problemas):")
print("="*70)
print(f"links_invalidos (primeros 5): {resumen_problemas.get('links_invalidos', [])[:5]}")
