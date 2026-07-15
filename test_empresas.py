#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test de reconocimiento de empresas"""

import sys
sys.path.insert(0, 'bot_evaluacion_docente')

from motor_evaluacion import MotorEvaluacion
motor = MotorEvaluacion()

# Prueba con diferentes experiencias laborales
pruebas = [
    {'experiencia_laboral': [{'institucion': 'BCP - Banco de Crédito del Perú', 'cargo': 'Analista'}]},
    {'experiencia_laboral': [{'institucion': 'Clínica Ricardo Palma', 'cargo': 'Médico'}]},
    {'experiencia_laboral': [{'institucion': 'Ministerio de Educación', 'cargo': 'Especialista'}]},
    {'experiencia_laboral': [{'institucion': 'Antamina', 'cargo': 'Ingeniero'}]},
    {'experiencia_laboral': [{'institucion': 'Universidad San Ignacio de Loyola', 'cargo': 'Docente'}]},
    {'experiencia_laboral': [{'institucion': 'Alicorp S.A.', 'cargo': 'Jefe de producción'}]},
    {'experiencia_laboral': [{'institucion': 'Hospital Rebagliati', 'cargo': 'Cirujano'}]},
    {'experiencia_laboral': [{'institucion': 'SUNAT', 'cargo': 'Fiscalizador'}]},
    {'experiencia_laboral': [{'institucion': 'Ferreyros', 'cargo': 'Vendedor'}]},
    {'experiencia_laboral': [{'institucion': 'Empresa pequeña SAC', 'cargo': 'Gerente'}], 'anos_experiencia': 5},
    {'experiencia_laboral': [{'institucion': 'Tienda de barrio', 'cargo': 'Dueño'}]},
]

print('PRUEBAS DE RECONOCIMIENTO DE EMPRESAS (200 Top Perú):')
print('='*70)
for i, p in enumerate(pruebas, 1):
    resultado = motor.evaluar_centro_labores(p)
    inst = p['experiencia_laboral'][0]['institucion']
    print(f'{i}. {inst}')
    print(f'   Puntaje: {resultado["puntaje"]} pts - Categoría: {resultado["categoria"]}')
    print(f'   Justificación: {resultado["justificacion"]}')
    print()
