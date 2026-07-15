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


if __name__ == "__main__":
    # Test del módulo
    from motor_evaluacion import ejecutar_evaluacion_completa
    
    resultado = ejecutar_evaluacion_completa()
    
    if resultado:
        generador = GeneradorDecisiones(resultado['evaluaciones'])
        clasificacion = generador.generar_clasificacion_completa()
        generador.imprimir_clasificacion()
