# -*- coding: utf-8 -*-
"""
Test completo del sistema de evaluación docente
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, "bot_evaluacion_docente")

print("=== TEST COMPLETO DEL SISTEMA ===")

# 1. Test de imports
try:
    from extractor_web_cvs import ExtractorWebCVs, procesar_excel_links
    from motor_evaluacion import MotorEvaluacion, TOTAL_MAXIMO
    print("[OK] Imports correctos")
except Exception as e:
    print(f"[ERROR] Imports: {e}")
    sys.exit(1)

# 2. Test extraccion de múltiples CVs
print("\n=== Probando extraccion de MULTIPLES CVs ===")
extractor = ExtractorWebCVs()
motor = MotorEvaluacion()

urls_test = [
    "https://ctivitae.concytec.gob.pe/appDirectorioCTI/VerDatosInvestigador.do?id_investigador=107798",  # Dennis Arias
    "https://ctivitae.concytec.gob.pe/appDirectorioCTI/VerDatosInvestigador.do?id_investigador=440291",  
    "https://ctivitae.concytec.gob.pe/appDirectorioCTI/VerDatosInvestigador.do?id_investigador=472410",
]

resultados = []
for url in urls_test:
    try:
        cv = extractor.extraer_cv_desde_url(url)
        evaluacion = motor.evaluar_cv_completo(cv)
        
        resultados.append({
            'nombre': cv.get('nombre'),
            'educacion': cv.get('educacion'),
            'exp_docente': cv.get('experiencia_docente'),
            'publicaciones': cv.get('publicaciones'),
            'perfil_vacio': cv.get('perfil_vacio'),
            'total': evaluacion['total'],
            'clasificacion': evaluacion['clasificacion'],
            'puntajes': evaluacion['puntajes']
        })
    except Exception as e:
        resultados.append({
            'nombre': 'ERROR',
            'error': str(e)
        })

print("\n" + "="*80)
print("RESUMEN DE EVALUACIONES")
print("="*80)

for r in resultados:
    if 'error' in r:
        print(f"\n{r['nombre']}: ERROR - {r['error']}")
    else:
        print(f"\n{r['nombre']}:")
        print(f"  Educacion: {r['educacion']}")
        print(f"  Exp. Docente: {r['exp_docente']} años")
        print(f"  Publicaciones: {r['publicaciones']}")
        print(f"  Perfil vacío: {r['perfil_vacio']}")
        print(f"  TOTAL: {r['total']}/170")
        print(f"  CLASIFICACION: {r['clasificacion']}")
        print(f"  Puntajes: C1={r['puntajes']['C1']}, C2={r['puntajes']['C2']}, C3={r['puntajes']['C3']}, C4={r['puntajes']['C4']}, C5={r['puntajes']['C5']}")

print("\n=== TEST COMPLETADO ===")

