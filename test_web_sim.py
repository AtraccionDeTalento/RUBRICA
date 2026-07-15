import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'bot_evaluacion_docente')
from extractor_cvs import procesar_todos_cvs
from motor_evaluacion import MotorEvaluacion

carpeta = r'C:\Users\jlopezp\OneDrive - Universidad San Ignacio de Loyola (1)\Desktop\OKA'
cvs = procesar_todos_cvs(carpeta)

karla_cv = next((cv for cv in cvs if 'Karla' in cv.get('nombre', '')), None)
if not karla_cv:
    print("Karla not found")
else:
    print("=== EXTRACCION ===")
    print(json.dumps(karla_cv.get('educacion', {}), ensure_ascii=False, indent=2))
    
    motor = MotorEvaluacion()
    evals = motor.evaluar_multiples_cvs([karla_cv])
    print("=== EVALUACION ===")
    print("C1:", evals[0]['puntajes']['C1'])
    print("Detalles C1:", json.dumps(evals[0].get('detalles', {}).get('formacion_academica', {}), ensure_ascii=False))
