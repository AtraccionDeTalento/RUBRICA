import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'bot_evaluacion_docente')
from extractor_cvs import ExtractorCV
from motor_evaluacion import MotorEvaluacion

cv_path = r'C:\Users\jlopezp\OneDrive - Universidad San Ignacio de Loyola (1)\Desktop\OKA\C_Karla_Salazar.pdf'
e = ExtractorCV(cv_path)
datos = e.analizar_cv()

print('=== DATOS EXTRAIDOS ===')
print('Nombre:', datos['nombre'])
print('Educacion:', json.dumps(datos['educacion'], ensure_ascii=False, indent=2))
print('Anos exp:', datos['anos_experiencia'])
print('Exp docente:', datos.get('experiencia_docente', 'N/A'))
print('Evidencias docencia:', datos.get('evidencias_docencia', []))
print('Publicaciones:', datos['publicaciones'])

motor = MotorEvaluacion()
resultado = motor.evaluar_cv_completo(datos)

print()
print('=== EVALUACION ===')
print('C1:', resultado['puntajes']['C1'], 'pts')
print('  categoria:', resultado['detalles']['formacion_academica']['categoria'])
print('  justificacion:', resultado['detalles']['formacion_academica']['justificacion'])
print('  evidencia:', resultado['detalles']['formacion_academica']['evidencia'])
print()
print('C2:', resultado['puntajes']['C2'], 'pts')
print('  categoria:', resultado['detalles']['experiencia_docente']['categoria'])
print('  justificacion:', resultado['detalles']['experiencia_docente']['justificacion'])
print('  evidencia:', resultado['detalles']['experiencia_docente']['evidencia'])
print()
print('C3:', resultado['puntajes']['C3'], 'pts -', resultado['detalles']['experiencia_profesional']['justificacion'])
print('C4:', resultado['puntajes']['C4'], 'pts -', resultado['detalles']['centro_labores']['justificacion'])
print('C5:', resultado['puntajes']['C5'], 'pts -', resultado['detalles']['produccion_academica']['justificacion'])
print()
print('TOTAL:', resultado['total'], 'pts')
print('Clasificacion:', resultado['clasificacion'])
