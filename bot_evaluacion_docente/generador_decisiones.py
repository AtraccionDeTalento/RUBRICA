"""
Generador de clasificación de perfiles docentes
Clasifica a cada candidato según su puntaje en las categorías USIL
"""
from typing import Dict, List
import json
from config import RANGOS_APROBATORIOS


class GeneradorDecisiones:
    """Clasifica candidatos en perfiles docentes según puntaje"""
    
    def __init__(self, evaluaciones: List[Dict]):
        self.evaluaciones = evaluaciones
        self.decision = {}
        self.clasificaciones = []
    
    def clasificar_candidato(self, evaluacion: Dict) -> Dict:
        """
        Clasifica a un candidato en los perfiles docentes según su puntaje
        Retorna todos los perfiles que cumple y el perfil recomendado
        """
        puntuacion = evaluacion['puntuacion_total']
        
        perfiles_cumplidos = []
        perfiles_no_cumplidos = []
        
        for perfil, datos in RANGOS_APROBATORIOS.items():
            minimo = datos['minimo']
            cumple = puntuacion >= minimo
            
            info_perfil = {
                'perfil': perfil.replace('_', ' '),
                'minimo_requerido': minimo,
                'cumple': cumple,
                'diferencia': puntuacion - minimo
            }
            
            if cumple:
                perfiles_cumplidos.append(info_perfil)
            else:
                perfiles_no_cumplidos.append(info_perfil)
        
        # Determinar perfil recomendado (el de mayor exigencia que cumple)
        if perfiles_cumplidos:
            # Ordenar por mínimo requerido (descendente) para obtener el más exigente
            perfiles_cumplidos_ordenados = sorted(perfiles_cumplidos, 
                                                  key=lambda x: x['minimo_requerido'], 
                                                  reverse=True)
            perfil_recomendado = perfiles_cumplidos_ordenados[0]['perfil']
        else:
            perfil_recomendado = "No califica para ningún perfil"
        
        return {
            'nombre': evaluacion['nombre'],
            'archivo': evaluacion['archivo'],
            'puntuacion_total': evaluacion['puntuacion_total'],
            'perfil_recomendado': perfil_recomendado,
            'perfiles_cumplidos': perfiles_cumplidos,
            'perfiles_no_cumplidos': perfiles_no_cumplidos,
            'puntuaciones_criterios': evaluacion['puntuaciones_por_criterio'],
            'puntajes_maximos': evaluacion['puntajes_maximos']
        }
    
    def analizar_disponibilidad(self, evaluacion: Dict) -> Dict:
        """
        Analiza qué tipo de contratación puede tener según su perfil
        """
        puntuacion = evaluacion['puntuacion_total']
        nombre = evaluacion['nombre']
        
        # Analizar experiencia docente y producción académica
        exp_docente = evaluacion['puntuaciones_por_criterio'].get('C2_Experiencia_Docente', 0)
        prod_academica = evaluacion['puntuaciones_por_criterio'].get('C5_Produccion_Academica', 0)
        formacion = evaluacion['puntuaciones_por_criterio'].get('C1_Formacion_Academica', 0)
        
        disponibilidades = []
        
        # Tiempo Completo (DTC) - Requiere equilibrio académico
        if puntuacion >= 110 and formacion >= 30:
            disponibilidades.append({
                'tipo': 'Tiempo Completo (DTC)',
                'descripcion': 'Dedicación exclusiva con investigación',
                'prioridad': 1
            })
        
        # Tiempo Parcial (DTP) - Profesionales con equilibrio
        if puntuacion >= 110:
            disponibilidades.append({
                'tipo': 'Tiempo Parcial (DTP)',
                'descripcion': 'Combinación docencia-profesión',
                'prioridad': 2
            })
        
        # Medio Tiempo - Practitioner con experiencia profesional fuerte
        if puntuacion >= 90:
            disponibilidades.append({
                'tipo': 'Medio Tiempo (Practitioner)',
                'descripcion': 'Énfasis en experiencia profesional',
                'prioridad': 3
            })
        
        # Por Horas - Si tiene producción académica pero bajo score
        if prod_academica > 10:
            disponibilidades.append({
                'tipo': 'Por Horas (Investigación)',
                'descripcion': 'Horas específicas de investigación',
                'prioridad': 4
            })
        
        return {
            'nombre': nombre,
            'disponibilidades_posibles': disponibilidades,
            'recomendacion_principal': disponibilidades[0] if disponibilidades else None
        }
    
    def generar_clasificacion_completa(self) -> Dict:
        """Genera clasificación completa de todos los candidatos"""
        if not self.evaluaciones:
            return {"error": "No hay evaluaciones disponibles"}
        
        print(f"\n{'='*70}")
        print(f"CLASIFICACIÓN DE PERFILES DOCENTES")
        print(f"{'='*70}\n")
        
        self.clasificaciones = []
        
        for evaluacion in self.evaluaciones:
            clasificacion = self.clasificar_candidato(evaluacion)
            disponibilidad = self.analizar_disponibilidad(evaluacion)
            
            # Combinar información
            clasificacion['disponibilidad'] = disponibilidad
            self.clasificaciones.append(clasificacion)
            
            # Imprimir clasificación
            print(f"👤 {clasificacion['nombre']}")
            print(f"   Puntuación: {clasificacion['puntuacion_total']:.2f}/230")
            print(f"   🎯 Perfil Recomendado: {clasificacion['perfil_recomendado']}")
            print(f"   ⏰ Disponibilidad: {disponibilidad['recomendacion_principal']['tipo'] if disponibilidad['recomendacion_principal'] else 'No aplica'}")
            print(f"   ✅ Cumple {len(clasificacion['perfiles_cumplidos'])} perfiles")
            print()
        
        # Generar resumen por perfil
        resumen_por_perfil = self._generar_resumen_por_perfil()
        
        self.decision = {
            "clasificaciones": self.clasificaciones,
            "resumen_por_perfil": resumen_por_perfil,
            "total_candidatos": len(self.clasificaciones),
            "fecha_analisis": "29/01/2026"
        }
        
        return self.decision
    
    def _generar_resumen_por_perfil(self) -> Dict:
        """Genera resumen de cuántos candidatos califican para cada perfil"""
        resumen = {}
        
        for perfil_key in RANGOS_APROBATORIOS.keys():
            perfil_nombre = perfil_key.replace('_', ' ')
            candidatos_que_cumplen = [
                c for c in self.clasificaciones 
                if any(p['perfil'] == perfil_nombre for p in c['perfiles_cumplidos'])
            ]
            
            resumen[perfil_nombre] = {
                'cantidad': len(candidatos_que_cumplen),
                'candidatos': [c['nombre'] for c in candidatos_que_cumplen],
                'puntaje_minimo': RANGOS_APROBATORIOS[perfil_key]['minimo']
            }
        
        return resumen
    
    def generar_tabla_consolidada(self) -> str:
        """Genera tabla consolidada en formato texto"""
        if not self.clasificaciones:
            self.generar_clasificacion_completa()
        
        tabla = f"\n{'='*120}\n"
        tabla += "TABLA CONSOLIDADA DE CLASIFICACIÓN DOCENTE\n"
        tabla += f"{'='*120}\n\n"
        
        # Encabezados
        tabla += f"{'Candidato':<30} | {'Puntaje':<10} | {'Perfil Asignado':<25} | {'Disponibilidad':<30}\n"
        tabla += f"{'-'*30}-+-{'-'*10}-+-{'-'*25}-+-{'-'*30}\n"
        
        # Datos
        for clasificacion in self.clasificaciones:
            nombre = clasificacion['nombre'][:28]
            puntaje = f"{clasificacion['puntuacion_total']:.0f}/230"
            perfil = clasificacion['perfil_recomendado'][:23]
            disp = clasificacion['disponibilidad']['recomendacion_principal']
            disponibilidad = disp['tipo'][:28] if disp else 'N/A'
            
            tabla += f"{nombre:<30} | {puntaje:<10} | {perfil:<25} | {disponibilidad:<30}\n"
        
        tabla += f"\n{'='*120}\n"
        
        # Resumen por perfil
        tabla += "\nRESUMEN POR PERFIL:\n"
        tabla += f"{'-'*120}\n"
        
        for perfil, datos in self.decision['resumen_por_perfil'].items():
            if datos['cantidad'] > 0:
                tabla += f"\n{perfil} ({datos['puntaje_minimo']} pts mínimo): {datos['cantidad']} candidato(s)\n"
                for candidato in datos['candidatos']:
                    tabla += f"  • {candidato}\n"
        
        return tabla
    
    def imprimir_clasificacion(self):
        """Imprime la clasificación de forma legible"""
        if not self.decision:
            self.generar_clasificacion_completa()
        
        print(self.generar_tabla_consolidada())
        """Genera justificación textual de la decisión"""
        nombre = mejor_candidato['candidato_seleccionado']
        puntuacion = mejor_candidato['puntuacion_total']
        puntajes_max = mejor_candidato['puntajes_maximos']
        
        from config import RANGOS_APROBATORIOS
        
        justificacion = f"""
DECISIÓN DE SELECCIÓN DOCENTE - USIL 2026
==========================================

CANDIDATO SELECCIONADO: {nombre}
PUNTUACIÓN TOTAL: {puntuacion:.2f}/230 puntos

JUSTIFICACIÓN:
--------------

El candidato {nombre} ha sido seleccionado como el más apto para la posición docente 
basándose en la Ficha de Evaluación Perfil - Selección Docente USIL 2026-1.

EVALUACIÓN POR CRITERIO:
------------------------

"""
        
        puntuaciones = mejor_candidato['puntuaciones_detalladas']
        
        # Mostrar cada criterio con su puntaje
        for criterio, puntaje in puntuaciones.items():
            criterio_num = criterio.split('_')[0]
            max_pts = puntajes_max[criterio_num]
            nombre_criterio = criterio.replace('_', ' ')
            porcentaje = (puntaje / max_pts * 100) if max_pts > 0 else 0
            
            if porcentaje >= 75:
                nivel = "⭐ EXCELENTE"
            elif porcentaje >= 50:
                nivel = "✓ BUENO"
            elif porcentaje >= 25:
                nivel = "• ACEPTABLE"
            else:
                nivel = "⚠ BAJO"
            
            justificacion += f"{criterio}: {puntaje:.0f}/{max_pts} puntos ({porcentaje:.0f}%) {nivel}\n"
        
        # Evaluar para qué tipo de docente califica
        justificacion += f"\n\nCLASIFICACIÓN POR TIPO DE DOCENTE:\n"
        justificacion += f"-----------------------------------\n"
        
        for tipo, datos in RANGOS_APROBATORIOS.items():
            min_requerido = datos['minimo']
            cumple = "✅ CUMPLE" if puntuacion >= min_requerido else "❌ NO CUMPLE"
            justificacion += f"{tipo.replace('_', ' ')}: {min_requerido} pts mínimo → {cumple}\n"
        
        # Comparación con otros candidatos
        if len(self.evaluaciones) > 1:
            justificacion += f"\n\nCOMPARACIÓN CON OTROS CANDIDATOS:\n"
            justificacion += f"---------------------------------\n"
            
            for i, eval in enumerate(self.evaluaciones[1:], 2):
                diferencia = puntuacion - eval['puntuacion_total']
                justificacion += f"\n{i}. {eval['nombre']}: {eval['puntuacion_total']:.2f}/230 "
                justificacion += f"(Diferencia: -{diferencia:.2f} puntos)\n"
        
        justificacion += f"""

CONCLUSIÓN:
-----------

Se recomienda la contratación de {nombre} para la posición docente, sujeto a:
1. Verificación de documentos académicos y certificados
2. Validación de experiencia laboral y referencias
3. Entrevista personal con el comité académico
4. Verificación de publicaciones e investigaciones declaradas

Esta decisión se basa en criterios objetivos establecidos en la rúbrica institucional
de la Universidad San Ignacio de Loyola.

Fecha: 29 de enero de 2026
"""
        
        return justificacion
    
    def generar_analisis_comparativo(self) -> Dict:
        """Genera análisis comparativo de todos los candidatos"""
        if len(self.evaluaciones) < 2:
            return {"mensaje": "Se requieren al menos 2 candidatos para comparación"}
        
        analisis = {
            "total_candidatos": len(self.evaluaciones),
            "puntuacion_promedio": sum(e['puntuacion_total'] for e in self.evaluaciones) / len(self.evaluaciones),
            "puntuacion_maxima": self.evaluaciones[0]['puntuacion_total'],
            "puntuacion_minima": self.evaluaciones[-1]['puntuacion_total'],
            "diferencia_max_min": self.evaluaciones[0]['puntuacion_total'] - self.evaluaciones[-1]['puntuacion_total']
        }
        
        # Análisis por criterio
        criterios_analisis = {}
        primer_eval = self.evaluaciones[0]
        
        for criterio in primer_eval['puntuaciones_por_criterio'].keys():
            puntuaciones_criterio = [e['puntuaciones_por_criterio'][criterio] for e in self.evaluaciones]
            criterios_analisis[criterio] = {
                "promedio": sum(puntuaciones_criterio) / len(puntuaciones_criterio),
                "maximo": max(puntuaciones_criterio),
                "minimo": min(puntuaciones_criterio)
            }
        
        analisis["analisis_por_criterio"] = criterios_analisis
        
        return analisis
    
    def generar_decision_completa(self) -> Dict:
        """Genera la decisión completa con toda la información"""
        mejor = self.seleccionar_mejor_candidato()
        justificacion = self.generar_justificacion(mejor)
        analisis = self.generar_analisis_comparativo()
        
        self.decision = {
            "candidato_seleccionado": mejor,
            "justificacion": justificacion,
            "analisis_comparativo": analisis,
            "ranking_completo": [
                {
                    "posicion": i+1,
                    "nombre": e['nombre'],
                    "puntuacion": e['puntuacion_total']
                }
                for i, e in enumerate(self.evaluaciones)
            ]
        }
        
        return self.decision
    
    def imprimir_decision(self):
        """Imprime la decisión de forma legible"""
        if not self.decision:
            self.generar_decision_completa()
        
        print(f"\n{'='*70}")
        print(self.decision['justificacion'])
        print(f"{'='*70}\n")
        
        # Mostrar análisis comparativo
        analisis = self.decision['analisis_comparativo']
        print(f"\nANÁLISIS ESTADÍSTICO:")
        print(f"{'='*70}")
        print(f"Total de candidatos evaluados: {analisis.get('total_candidatos', 0)}")
        print(f"Puntuación promedio: {analisis.get('puntuacion_promedio', 0):.2f}")
        print(f"Rango de puntuaciones: {analisis.get('puntuacion_minima', 0):.2f} - {analisis.get('puntuacion_maxima', 0):.2f}")


if __name__ == "__main__":
    # Test del módulo
    from motor_evaluacion import ejecutar_evaluacion_completa
    
    resultado = ejecutar_evaluacion_completa()
    
    if resultado:
        generador = GeneradorDecisiones(resultado['evaluaciones'])
        decision = generador.generar_decision_completa()
        generador.imprimir_decision()
