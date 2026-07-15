"""
Generador de Decisiones MEJORADO - Clasificación de perfiles docentes
Versión: 2.0
Fecha: 2026-02-03

MEJORAS:
- Evalúa condiciones específicas por perfil (no solo puntaje)
- Identifica información faltante en el CV
- Genera justificaciones detalladas
- Recomienda acciones para mejorar el perfil
"""
from typing import Dict, List, Tuple
import json
from config import RANGOS_APROBATORIOS


class GeneradorDecisionesMejorado:
    """Clasifica candidatos en perfiles docentes con análisis profundo"""
    
    # Mapeo de criterios a nombres legibles
    NOMBRES_CRITERIOS = {
        "C1_Formacion_Academica": "Formación Académica",
        "C2_Experiencia_Docente": "Experiencia Docente",
        "C3_Experiencia_Profesional": "Experiencia Profesional",
        "C4_Centro_Labores": "Centro de Labores",
        "C5_Produccion_Academica": "Producción Académica"
    }
    
    # Puntajes máximos por criterio
    PUNTAJES_MAXIMOS = {
        "C1_Formacion_Academica": 50,
        "C2_Experiencia_Docente": 40,
        "C3_Experiencia_Profesional": 40,
        "C4_Centro_Labores": 20,
        "C5_Produccion_Academica": 50
    }
    
    def __init__(self, evaluaciones: List[Dict]):
        self.evaluaciones = evaluaciones
        self.clasificaciones = []
    
    def analizar_informacion_faltante(self, evaluacion: Dict) -> Dict:
        """
        Analiza qué información falta o es insuficiente en el CV
        Retorna un diccionario con campos faltantes y recomendaciones
        """
        puntuaciones = evaluacion.get('puntuaciones_por_criterio', {})
        justificaciones = evaluacion.get('justificaciones', {})
        
        informacion_faltante = []
        recomendaciones = []
        campos_con_info = []
        
        # Analizar cada criterio
        for criterio, puntaje in puntuaciones.items():
            max_pts = self.PUNTAJES_MAXIMOS.get(criterio, 50)
            porcentaje = (puntaje / max_pts * 100) if max_pts > 0 else 0
            nombre = self.NOMBRES_CRITERIOS.get(criterio, criterio)
            justificacion = justificaciones.get(criterio, "")
            
            if puntaje == 0:
                informacion_faltante.append({
                    "criterio": nombre,
                    "codigo": criterio,
                    "problema": "Sin información registrada",
                    "impacto": "CRÍTICO",
                    "justificacion": justificacion
                })
                
                # Recomendaciones específicas según criterio
                if "Formacion" in criterio:
                    recomendaciones.append(f"⚠️ {nombre}: Agregar grados académicos (doctorado, maestría, licenciatura)")
                elif "Docente" in criterio:
                    recomendaciones.append(f"⚠️ {nombre}: Documentar experiencia docente universitaria con fechas")
                elif "Profesional" in criterio:
                    recomendaciones.append(f"⚠️ {nombre}: Registrar experiencia laboral con cargos y períodos")
                elif "Centro" in criterio:
                    recomendaciones.append(f"⚠️ {nombre}: Especificar nombres de instituciones/empresas")
                elif "Produccion" in criterio:
                    recomendaciones.append(f"⚠️ {nombre}: Listar publicaciones, artículos o proyectos de investigación")
            
            elif porcentaje < 25:
                informacion_faltante.append({
                    "criterio": nombre,
                    "codigo": criterio,
                    "problema": f"Información mínima ({puntaje}/{max_pts} pts)",
                    "impacto": "ALTO",
                    "justificacion": justificacion
                })
                recomendaciones.append(f"📝 {nombre}: Completar con más detalle ({porcentaje:.0f}% del máximo)")
            
            elif porcentaje < 50:
                campos_con_info.append({
                    "criterio": nombre,
                    "puntaje": puntaje,
                    "maximo": max_pts,
                    "porcentaje": porcentaje,
                    "estado": "PARCIAL"
                })
            else:
                campos_con_info.append({
                    "criterio": nombre,
                    "puntaje": puntaje,
                    "maximo": max_pts,
                    "porcentaje": porcentaje,
                    "estado": "COMPLETO" if porcentaje >= 75 else "ACEPTABLE"
                })
        
        return {
            "informacion_faltante": informacion_faltante,
            "campos_con_info": campos_con_info,
            "recomendaciones": recomendaciones,
            "completitud": len(campos_con_info) / 5 * 100 if puntuaciones else 0
        }
    
    def evaluar_perfil_especifico(self, evaluacion: Dict, perfil: str, datos_perfil: Dict) -> Dict:
        """
        Evalúa si un candidato cumple las condiciones específicas de un perfil
        No solo el puntaje, sino también los requisitos adicionales
        """
        puntuacion_total = evaluacion['puntuacion_total']
        puntuaciones = evaluacion.get('puntuaciones_por_criterio', {})
        minimo = datos_perfil['minimo']
        requisitos = datos_perfil.get('requisitos', {})
        
        # Verificar puntaje mínimo
        cumple_puntaje = puntuacion_total >= minimo
        diferencia_puntaje = puntuacion_total - minimo
        
        # Verificar requisitos específicos
        requisitos_cumplidos = []
        requisitos_no_cumplidos = []
        
        # Formación mínima
        if 'formacion_minima' in requisitos:
            formacion = puntuaciones.get('C1_Formacion_Academica', 0)
            req_min = requisitos['formacion_minima']
            if formacion >= req_min:
                requisitos_cumplidos.append({
                    "requisito": "Formación Académica",
                    "valor_actual": formacion,
                    "valor_requerido": req_min,
                    "detalle": self._describir_nivel_formacion(formacion)
                })
            else:
                requisitos_no_cumplidos.append({
                    "requisito": "Formación Académica",
                    "valor_actual": formacion,
                    "valor_requerido": req_min,
                    "faltante": req_min - formacion,
                    "detalle": f"Requiere {self._describir_nivel_formacion(req_min)}, tiene {self._describir_nivel_formacion(formacion)}"
                })
        
        # Docencia mínima
        if 'docencia_minima' in requisitos:
            docencia = puntuaciones.get('C2_Experiencia_Docente', 0)
            req_min = requisitos['docencia_minima']
            if docencia >= req_min:
                requisitos_cumplidos.append({
                    "requisito": "Experiencia Docente",
                    "valor_actual": docencia,
                    "valor_requerido": req_min,
                    "detalle": f"{docencia} pts en experiencia docente"
                })
            else:
                requisitos_no_cumplidos.append({
                    "requisito": "Experiencia Docente",
                    "valor_actual": docencia,
                    "valor_requerido": req_min,
                    "faltante": req_min - docencia,
                    "detalle": f"Necesita más experiencia docente universitaria"
                })
        
        # Experiencia profesional mínima
        if 'profesional_minima' in requisitos:
            profesional = puntuaciones.get('C3_Experiencia_Profesional', 0)
            req_min = requisitos['profesional_minima']
            if profesional >= req_min:
                requisitos_cumplidos.append({
                    "requisito": "Experiencia Profesional",
                    "valor_actual": profesional,
                    "valor_requerido": req_min,
                    "detalle": f"{profesional} pts en experiencia profesional"
                })
            else:
                requisitos_no_cumplidos.append({
                    "requisito": "Experiencia Profesional",
                    "valor_actual": profesional,
                    "valor_requerido": req_min,
                    "faltante": req_min - profesional,
                    "detalle": f"Requiere más experiencia profesional ({req_min - profesional} pts)"
                })
        
        # Centro de labores mínimo
        if 'centro_labores_minimo' in requisitos:
            centro = puntuaciones.get('C4_Centro_Labores', 0)
            req_min = requisitos['centro_labores_minimo']
            if centro >= req_min:
                requisitos_cumplidos.append({
                    "requisito": "Centro de Labores",
                    "valor_actual": centro,
                    "valor_requerido": req_min,
                    "detalle": f"Centro de labores reconocido"
                })
            else:
                requisitos_no_cumplidos.append({
                    "requisito": "Centro de Labores",
                    "valor_actual": centro,
                    "valor_requerido": req_min,
                    "faltante": req_min - centro,
                    "detalle": f"Centro de labores no identificado como reconocido"
                })
        
        # Producción académica mínima
        if 'produccion_minima' in requisitos:
            produccion = puntuaciones.get('C5_Produccion_Academica', 0)
            req_min = requisitos['produccion_minima']
            if produccion >= req_min:
                requisitos_cumplidos.append({
                    "requisito": "Producción Académica",
                    "valor_actual": produccion,
                    "valor_requerido": req_min,
                    "detalle": self._describir_nivel_produccion(produccion)
                })
            else:
                requisitos_no_cumplidos.append({
                    "requisito": "Producción Académica",
                    "valor_actual": produccion,
                    "valor_requerido": req_min,
                    "faltante": req_min - produccion,
                    "detalle": f"Sin producción académica suficiente" if produccion == 0 else f"Producción insuficiente ({produccion} pts)"
                })
        
        # Requisito especial: requiere indexado (Scopus/WoS)
        if requisitos.get('requiere_indexado'):
            produccion = puntuaciones.get('C5_Produccion_Academica', 0)
            if produccion >= 40:  # 40+ indica Scopus/WoS o libros
                requisitos_cumplidos.append({
                    "requisito": "Publicación Indexada",
                    "valor_actual": produccion,
                    "valor_requerido": 40,
                    "detalle": "Tiene publicaciones de alto impacto"
                })
            else:
                requisitos_no_cumplidos.append({
                    "requisito": "Publicación Indexada",
                    "valor_actual": produccion,
                    "valor_requerido": 40,
                    "faltante": 40 - produccion,
                    "detalle": "Requiere publicaciones Scopus/WoS o libros"
                })
        
        # Determinar si cumple completamente
        cumple_requisitos = len(requisitos_no_cumplidos) == 0
        cumple_total = cumple_puntaje and cumple_requisitos
        
        # Calcular porcentaje de cumplimiento de requisitos
        total_requisitos = len(requisitos_cumplidos) + len(requisitos_no_cumplidos)
        porcentaje_requisitos = (len(requisitos_cumplidos) / total_requisitos * 100) if total_requisitos > 0 else 100
        
        return {
            "perfil": perfil,
            "descripcion": datos_perfil.get('descripcion', perfil),
            "condicion_adicional": datos_perfil.get('condicion_adicional', ''),
            "cumple_total": cumple_total,
            "cumple_puntaje": cumple_puntaje,
            "cumple_requisitos": cumple_requisitos,
            "puntaje_actual": puntuacion_total,
            "puntaje_minimo": minimo,
            "diferencia_puntaje": diferencia_puntaje,
            "requisitos_cumplidos": requisitos_cumplidos,
            "requisitos_no_cumplidos": requisitos_no_cumplidos,
            "porcentaje_requisitos": porcentaje_requisitos,
            "criterios_prioritarios": datos_perfil.get('criterios_prioritarios', [])
        }
    
    def _describir_nivel_formacion(self, puntaje: int) -> str:
        """Describe el nivel de formación según el puntaje"""
        if puntaje >= 50:
            return "Doctorado completo"
        elif puntaje >= 40:
            return "Doctorado en curso"
        elif puntaje >= 30:
            return "Maestría completa"
        elif puntaje >= 25:
            return "Maestría en curso"
        elif puntaje >= 15:
            return "Licenciatura/Bachiller"
        elif puntaje >= 10:
            return "Bachiller/Egresado"
        else:
            return "Sin grado académico"
    
    def _describir_nivel_produccion(self, puntaje: int) -> str:
        """Describe el nivel de producción según el puntaje"""
        if puntaje >= 50:
            return "Publicaciones Scopus/WoS (alto impacto)"
        elif puntaje >= 40:
            return "Libros o revistas indexadas"
        elif puntaje >= 30:
            return "Investigación y proyectos"
        elif puntaje >= 20:
            return "Artículos no indexados"
        elif puntaje >= 10:
            return "Documentos técnicos"
        else:
            return "Sin evidencia de producción"
    
    def clasificar_candidato(self, evaluacion: Dict) -> Dict:
        """
        Clasifica a un candidato evaluando TODOS los perfiles con sus condiciones específicas
        """
        nombre = evaluacion.get('nombre', 'Sin nombre')
        puntuacion = evaluacion['puntuacion_total']
        
        # Analizar información faltante
        info_faltante = self.analizar_informacion_faltante(evaluacion)
        
        # Evaluar cada perfil con sus condiciones específicas
        evaluaciones_perfiles = []
        perfiles_cumplidos = []
        perfiles_parciales = []  # Cumple puntaje pero no todos los requisitos
        perfiles_no_cumplidos = []
        
        for perfil_key, datos_perfil in RANGOS_APROBATORIOS.items():
            eval_perfil = self.evaluar_perfil_especifico(evaluacion, perfil_key, datos_perfil)
            evaluaciones_perfiles.append(eval_perfil)
            
            if eval_perfil['cumple_total']:
                perfiles_cumplidos.append(eval_perfil)
            elif eval_perfil['cumple_puntaje'] and not eval_perfil['cumple_requisitos']:
                perfiles_parciales.append(eval_perfil)
            else:
                perfiles_no_cumplidos.append(eval_perfil)
        
        # Determinar perfil recomendado
        perfil_recomendado = None
        justificacion_recomendacion = ""
        
        if perfiles_cumplidos:
            # Ordenar por puntaje mínimo (más exigente primero)
            perfiles_cumplidos_ordenados = sorted(perfiles_cumplidos, 
                                                  key=lambda x: x['puntaje_minimo'], 
                                                  reverse=True)
            perfil_recomendado = perfiles_cumplidos_ordenados[0]
            justificacion_recomendacion = f"Cumple todos los requisitos para {perfil_recomendado['descripcion']}"
        elif perfiles_parciales:
            # Hay perfiles donde cumple puntaje pero no requisitos
            mejor_parcial = sorted(perfiles_parciales, 
                                   key=lambda x: x['porcentaje_requisitos'], 
                                   reverse=True)[0]
            perfil_recomendado = mejor_parcial
            requisitos_faltantes = [r['requisito'] for r in mejor_parcial['requisitos_no_cumplidos']]
            justificacion_recomendacion = f"Cumple puntaje para {mejor_parcial['descripcion']}, pero falta: {', '.join(requisitos_faltantes)}"
        else:
            # No cumple ningún perfil
            justificacion_recomendacion = "No cumple los requisitos mínimos para ningún perfil docente"
        
        # Generar justificación completa
        justificacion_detallada = self._generar_justificacion_detallada(
            evaluacion, perfil_recomendado, perfiles_cumplidos, 
            perfiles_parciales, perfiles_no_cumplidos, info_faltante
        )
        
        return {
            "nombre": nombre,
            "archivo": evaluacion.get('archivo', ''),
            "puntuacion_total": puntuacion,
            "perfil_recomendado": perfil_recomendado['perfil'] if perfil_recomendado else "No califica",
            "descripcion_perfil": perfil_recomendado['descripcion'] if perfil_recomendado else "N/A",
            "justificacion_recomendacion": justificacion_recomendacion,
            "perfiles_cumplidos": perfiles_cumplidos,
            "perfiles_parciales": perfiles_parciales,
            "perfiles_no_cumplidos": perfiles_no_cumplidos,
            "evaluaciones_perfiles": evaluaciones_perfiles,
            "informacion_faltante": info_faltante,
            "justificacion_detallada": justificacion_detallada,
            "puntuaciones_criterios": evaluacion.get('puntuaciones_por_criterio', {}),
            "justificaciones_criterios": evaluacion.get('justificaciones', {})
        }
    
    def _generar_justificacion_detallada(self, evaluacion: Dict, perfil_recomendado: Dict,
                                         perfiles_cumplidos: List, perfiles_parciales: List,
                                         perfiles_no_cumplidos: List, info_faltante: Dict) -> str:
        """Genera una justificación detallada en texto"""
        nombre = evaluacion.get('nombre', 'Candidato')
        puntuacion = evaluacion['puntuacion_total']
        
        lineas = [
            f"📋 ANÁLISIS DETALLADO: {nombre}",
            f"{'='*60}",
            f"",
            f"📊 PUNTUACIÓN TOTAL: {puntuacion:.0f}/200 puntos",
            f""
        ]
        
        # Desglose por criterio
        lineas.append("📈 DESGLOSE POR CRITERIO:")
        lineas.append("-" * 40)
        
        puntuaciones = evaluacion.get('puntuaciones_por_criterio', {})
        justificaciones = evaluacion.get('justificaciones', {})
        
        for criterio, puntaje in puntuaciones.items():
            max_pts = self.PUNTAJES_MAXIMOS.get(criterio, 50)
            nombre_criterio = self.NOMBRES_CRITERIOS.get(criterio, criterio)
            justif = justificaciones.get(criterio, "")
            porcentaje = (puntaje / max_pts * 100) if max_pts > 0 else 0
            
            if porcentaje >= 75:
                icono = "🟢"
            elif porcentaje >= 50:
                icono = "🟡"
            elif porcentaje > 0:
                icono = "🟠"
            else:
                icono = "🔴"
            
            lineas.append(f"  {icono} {nombre_criterio}: {puntaje}/{max_pts} pts ({porcentaje:.0f}%)")
            if justif:
                lineas.append(f"     └─ {justif}")
        
        lineas.append("")
        
        # Perfiles que cumple
        if perfiles_cumplidos:
            lineas.append("✅ PERFILES QUE CUMPLE COMPLETAMENTE:")
            lineas.append("-" * 40)
            for p in perfiles_cumplidos:
                lineas.append(f"  ✓ {p['descripcion']} ({p['puntaje_minimo']} pts mín)")
                lineas.append(f"    Condición: {p['condicion_adicional']}")
            lineas.append("")
        
        # Perfiles parciales
        if perfiles_parciales:
            lineas.append("⚠️ PERFILES CON CUMPLIMIENTO PARCIAL:")
            lineas.append("-" * 40)
            for p in perfiles_parciales:
                lineas.append(f"  ⚡ {p['descripcion']} - Cumple puntaje ({p['puntaje_actual']:.0f}/{p['puntaje_minimo']})")
                for req in p['requisitos_no_cumplidos']:
                    lineas.append(f"    ❌ Falta: {req['requisito']} - {req['detalle']}")
            lineas.append("")
        
        # Información faltante
        if info_faltante['informacion_faltante']:
            lineas.append("📝 INFORMACIÓN FALTANTE O INSUFICIENTE:")
            lineas.append("-" * 40)
            for falta in info_faltante['informacion_faltante']:
                lineas.append(f"  ⚠️ {falta['criterio']}: {falta['problema']} [{falta['impacto']}]")
            lineas.append("")
        
        # Recomendaciones
        if info_faltante['recomendaciones']:
            lineas.append("💡 RECOMENDACIONES PARA MEJORAR PERFIL:")
            lineas.append("-" * 40)
            for rec in info_faltante['recomendaciones']:
                lineas.append(f"  {rec}")
            lineas.append("")
        
        # Conclusión
        lineas.append("🎯 CONCLUSIÓN:")
        lineas.append("-" * 40)
        if perfil_recomendado:
            if perfiles_cumplidos:
                lineas.append(f"  ✅ APTO para: {perfil_recomendado['descripcion']}")
            else:
                lineas.append(f"  ⚠️ PARCIALMENTE APTO para: {perfil_recomendado['descripcion']}")
                lineas.append(f"     Requiere completar requisitos faltantes")
        else:
            lineas.append(f"  ❌ NO APTO para ningún perfil docente en este momento")
            lineas.append(f"     Se recomienda completar la información del CV")
        
        return "\n".join(lineas)
    
    def generar_clasificacion_completa(self) -> Dict:
        """Genera clasificación completa de todos los candidatos"""
        if not self.evaluaciones:
            return {"error": "No hay evaluaciones disponibles"}
        
        print(f"\n{'='*70}")
        print(f"🎓 CLASIFICACIÓN MEJORADA DE PERFILES DOCENTES")
        print(f"{'='*70}\n")
        
        self.clasificaciones = []
        
        for evaluacion in self.evaluaciones:
            clasificacion = self.clasificar_candidato(evaluacion)
            self.clasificaciones.append(clasificacion)
            
            # Imprimir resumen
            print(f"👤 {clasificacion['nombre']}")
            print(f"   Puntuación: {clasificacion['puntuacion_total']:.0f}/200")
            print(f"   🎯 Perfil: {clasificacion['descripcion_perfil']}")
            print(f"   📝 {clasificacion['justificacion_recomendacion']}")
            
            # Info faltante
            faltante = clasificacion['informacion_faltante']
            if faltante['informacion_faltante']:
                print(f"   ⚠️ Info faltante: {len(faltante['informacion_faltante'])} criterio(s)")
            
            print()
        
        # Resumen por perfil
        resumen = self._generar_resumen_por_perfil()
        
        return {
            "clasificaciones": self.clasificaciones,
            "resumen_por_perfil": resumen,
            "total_candidatos": len(self.clasificaciones),
            "fecha_analisis": "03/02/2026"
        }
    
    def _generar_resumen_por_perfil(self) -> Dict:
        """Genera resumen de candidatos por cada perfil"""
        resumen = {}
        
        for perfil_key, datos in RANGOS_APROBATORIOS.items():
            # Candidatos que cumplen completamente
            candidatos_completos = []
            # Candidatos que cumplen parcialmente (solo puntaje)
            candidatos_parciales = []
            
            for c in self.clasificaciones:
                for p in c['perfiles_cumplidos']:
                    if p['perfil'] == perfil_key:
                        candidatos_completos.append(c['nombre'])
                        break
                else:
                    for p in c['perfiles_parciales']:
                        if p['perfil'] == perfil_key:
                            candidatos_parciales.append(c['nombre'])
                            break
            
            resumen[perfil_key] = {
                "descripcion": datos.get('descripcion', perfil_key),
                "puntaje_minimo": datos['minimo'],
                "condicion_adicional": datos.get('condicion_adicional', ''),
                "candidatos_aptos": candidatos_completos,
                "cantidad_aptos": len(candidatos_completos),
                "candidatos_parciales": candidatos_parciales,
                "cantidad_parciales": len(candidatos_parciales)
            }
        
        return resumen
    
    def generar_reporte_texto(self) -> str:
        """Genera un reporte completo en texto"""
        if not self.clasificaciones:
            self.generar_clasificacion_completa()
        
        lineas = [
            "=" * 80,
            "REPORTE DE CLASIFICACIÓN DOCENTE - USIL 2026",
            "Sistema de Evaluación Mejorado con Condiciones Específicas por Perfil",
            "=" * 80,
            ""
        ]
        
        for c in self.clasificaciones:
            lineas.append(c['justificacion_detallada'])
            lineas.append("")
            lineas.append("=" * 80)
            lineas.append("")
        
        return "\n".join(lineas)


# Función de compatibilidad con el sistema anterior
class GeneradorDecisiones(GeneradorDecisionesMejorado):
    """Alias para mantener compatibilidad con código existente"""
    pass


if __name__ == "__main__":
    # Test del módulo
    print("Módulo de decisiones mejorado cargado correctamente")
    print("Perfiles disponibles:")
    for perfil, datos in RANGOS_APROBATORIOS.items():
        print(f"  - {datos.get('descripcion', perfil)}: {datos['minimo']} pts mín")
        print(f"    Condición: {datos.get('condicion_adicional', 'N/A')}")
