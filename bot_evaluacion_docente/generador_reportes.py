"""
Generador de reportes en Excel y JSON
"""
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict
from config import RESULTADOS_DIR


class GeneradorReportes:
    """Genera reportes de resultados en múltiples formatos"""
    
    def __init__(self, evaluaciones: list, clasificacion: Dict):
        self.evaluaciones = evaluaciones
        self.clasificacion = clasificacion
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def generar_excel_comparativo(self) -> str:
        """Genera Excel con tabla comparativa de candidatos"""
        # Crear DataFrame principal
        datos = []
        
        for i, eval in enumerate(self.evaluaciones, 1):
            fila = {
                "Ranking": i,
                "Nombre": eval['nombre'],
                "Archivo": eval['archivo'],
                "Puntuación Total": round(eval['puntuacion_total'], 2)
            }
            
            # Añadir puntuaciones por criterio
            for criterio, puntaje in eval['puntuaciones_por_criterio'].items():
                criterio_num = criterio.split('_')[0]
                max_pts = eval['puntajes_maximos'][criterio_num]
                nombre_criterio = criterio.replace('_', ' ')
                fila[nombre_criterio] = f"{puntaje:.0f}/{max_pts}"
            
            # Añadir datos del CV
            cv_data = eval['datos_cv']
            fila['Años Experiencia'] = cv_data.get('anos_experiencia', 0)
            fila['Doctorado'] = "Sí" if cv_data.get('educacion', {}).get('doctorado') else "No"
            fila['Maestría'] = "Sí" if cv_data.get('educacion', {}).get('maestria') else "No"
            fila['Publicaciones'] = cv_data.get('publicaciones', 0)
            
            datos.append(fila)
        
        df = pd.DataFrame(datos)
        
        # Guardar Excel
        nombre_archivo = f"comparativa_candidatos_{self.timestamp}.xlsx"
        ruta_completa = os.path.join(RESULTADOS_DIR, nombre_archivo)
        
        with pd.ExcelWriter(ruta_completa, engine='openpyxl') as writer:
            # Hoja 1: Ranking general
            df.to_excel(writer, sheet_name='Ranking General', index=False)
            
            # Hoja 2: Clasificaciones
            clasificaciones_data = []
            for clas in self.clasificacion['clasificaciones']:
                # Construir lista de perfiles cumplidos
                perfiles = [p['perfil'] for p in clas.get('perfiles_cumplidos', [])]
                perfiles_str = ', '.join(perfiles) if perfiles else 'Ninguno'
                
                # Obtener disponibilidades
                disponibilidades = [d['tipo'] for d in clas.get('disponibilidades_posibles', [])]
                disponibilidad_str = ', '.join(disponibilidades) if disponibilidades else 'N/A'
                
                clasificaciones_data.append({
                    'Nombre': clas['nombre'],
                    'Puntaje Total': clas['puntuacion_total'],
                    'Perfil Recomendado': clas['perfil_recomendado'],
                    'Perfiles Cumplidos': perfiles_str,
                    'Disponibilidad': disponibilidad_str,
                    'C1': clas['puntuaciones_criterios'].get('C1_Formacion_Academica', 0),
                    'C2': clas['puntuaciones_criterios'].get('C2_Experiencia_Docente', 0),
                    'C3': clas['puntuaciones_criterios'].get('C3_Experiencia_Profesional', 0),
                    'C4': clas['puntuaciones_criterios'].get('C4_Centro_Labores', 0),
                    'C5': clas['puntuaciones_criterios'].get('C5_Produccion_Academica', 0)
                })
            
            df_clasificaciones = pd.DataFrame(clasificaciones_data)
            df_clasificaciones.to_excel(writer, sheet_name='Clasificaciones', index=False)
            
            # Hoja 3: Resumen por perfil
            resumen_data = []
            for perfil, candidatos in self.clasificacion['resumen_por_perfil'].items():
                resumen_data.append({
                    'Perfil': perfil,
                    'Cantidad': len(candidatos),
                    'Candidatos': ', '.join(candidatos)
                })
            
            df_resumen = pd.DataFrame(resumen_data)
            df_resumen.to_excel(writer, sheet_name='Resumen por Perfil', index=False)
        
        print(f"✅ Excel generado: {nombre_archivo}")
        return ruta_completa
    
    def generar_json_decision(self) -> str:
        """Genera JSON con la decisión completa"""
        nombre_archivo = f"clasificacion_final_{self.timestamp}.json"
        ruta_completa = os.path.join(RESULTADOS_DIR, nombre_archivo)
        
        # Preparar datos para JSON
        clasificacion_json = {
            "fecha_evaluacion": datetime.now().isoformat(),
            "clasificacion": self.clasificacion,
            "evaluaciones_detalladas": [
                {
                    "nombre": e['nombre'],
                    "archivo": e['archivo'],
                    "puntuacion_total": e['puntuacion_total'],
                    "puntuaciones_por_criterio": e['puntuaciones_por_criterio'],
                    "puntajes_maximos": e['puntajes_maximos'],
                    "experiencia_anos": e['datos_cv'].get('anos_experiencia', 0),
                    "educacion": e['datos_cv'].get('educacion', {}),
                    "publicaciones": e['datos_cv'].get('publicaciones', 0)
                }
                for e in self.evaluaciones
            ]
        }
        
        with open(ruta_completa, 'w', encoding='utf-8') as f:
            json.dump(clasificacion_json, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON generado: {nombre_archivo}")
        return ruta_completa
    
    def generar_reporte_texto(self) -> str:
        """Genera reporte en formato texto"""
        nombre_archivo = f"reporte_detallado_{self.timestamp}.txt"
        ruta_completa = os.path.join(RESULTADOS_DIR, nombre_archivo)
        
        with open(ruta_completa, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("REPORTE DE EVALUACIÓN DOCENTE\n")
            f.write("="*80 + "\n\n")
            f.write(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Candidatos evaluados: {len(self.evaluaciones)}\n\n")
            
            # Escribir justificación
            f.write(self.decision.get('justificacion', ''))
            
            f.write("\n\n")
            f.write("="*80 + "\n")
            f.write("DETALLES DE EVALUACIÓN POR CANDIDATO\n")
            f.write("="*80 + "\n\n")
            
            for i, eval in enumerate(self.evaluaciones, 1):
                f.write(f"\n{i}. {eval['nombre']}\n")
                f.write("-" * 80 + "\n")
                f.write(f"Archivo: {eval['archivo']}\n")
                f.write(f"Puntuación Total: {eval['puntuacion_total']:.2f}/230\n\n")
                f.write("Puntuaciones por Criterio:\n")
                
                for criterio, puntaje in eval['puntuaciones_por_criterio'].items():
                    criterio_num = criterio.split('_')[0]
                    max_pts = eval['puntajes_maximos'][criterio_num]
                    nombre_criterio = criterio.replace('_', ' ')
                    f.write(f"  • {nombre_criterio}: {puntaje:.2f}/{max_pts}\n")
                
                f.write("\nDatos del CV:\n")
                cv = eval['datos_cv']
                f.write(f"  • Años de experiencia: {cv.get('anos_experiencia', 0)}\n")
                f.write(f"  • Educación: {cv.get('educacion', {})}\n")
                f.write(f"  • Publicaciones detectadas: {cv.get('publicaciones', 0)}\n")
                f.write("\n")
        
        print(f"✅ Reporte de texto generado: {nombre_archivo}")
        return ruta_completa
    
    def generar_todos_reportes(self) -> Dict[str, str]:
        """Genera todos los reportes (Excel y JSON solamente)"""
        print(f"\n{'='*60}")
        print(f"GENERANDO REPORTES")
        print(f"{'='*60}\n")
        
        rutas = {
            "excel": self.generar_excel_comparativo(),
            "json": self.generar_json_decision()
            # No se genera TXT - resultados se muestran en la web
        }
        
        print(f"\n📁 Reportes guardados en: {RESULTADOS_DIR}\n")
        
        return rutas


if __name__ == "__main__":
    # Test del módulo
    from motor_evaluacion import ejecutar_evaluacion_completa
    from generador_decisiones import GeneradorDecisiones
    
    resultado = ejecutar_evaluacion_completa()
    
    if resultado:
        generador_dec = GeneradorDecisiones(resultado['evaluaciones'])
        decision = generador_dec.generar_decision_completa()
        
        generador_rep = GeneradorReportes(resultado['evaluaciones'], decision)
        rutas = generador_rep.generar_todos_reportes()
        
        print("\n✅ Reportes generados exitosamente")
