#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Automatizado de Evaluación de Perfil Docente
Version: 1.0
Fecha: 2026-01-30

Este script calcula automáticamente los puntajes según los criterios C1-C5
y genera un ranking preciso de candidatos para perfil docente.
"""

import json
from datetime import datetime
from typing import Dict, List, Any


class EvaluadorPerfilDocente:
    """Clase principal para evaluar perfiles docentes según criterios establecidos."""
    
    def __init__(self, ruta_criterios: str = "criterios_evaluacion.json"):
        """Inicializa el evaluador con los criterios desde archivo JSON."""
        with open(ruta_criterios, 'r', encoding='utf-8') as f:
            self.criterios = json.load(f)
        
        self.puntaje_maximo_total = 200
    
    def calcular_c1_formacion_academica(self, formacion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula puntaje C1 - Formación Académica.
        
        Args:
            formacion: Dict con claves: grado_maximo, grados_obtenidos (lista)
            
        Ejemplo:
            {
                "grado_maximo": "maestria",  # opciones: doctorado, maestria, segunda_especialidad, licenciatura, bachiller, estudiante
                "grados_obtenidos": ["bachiller", "licenciatura", "maestria"],
                "en_curso": ["doctorado"]  # NO se cuentan
            }
        
        Returns:
            Dict con puntaje, justificacion, detalle
        """
        grado = formacion.get("grado_maximo", "estudiante").lower()
        subcategorias = self.criterios["criterios"]["C1"]["subcategorias"]
        
        if grado in subcategorias:
            puntaje = subcategorias[grado]["puntos"]
            descripcion = subcategorias[grado]["descripcion"]
        else:
            puntaje = 0
            descripcion = "Grado no reconocido o sin información"
        
        return {
            "codigo": "C1",
            "criterio": "Formación Académica",
            "puntaje_obtenido": puntaje,
            "puntaje_maximo": 50,
            "grado_evaluado": grado,
            "descripcion": descripcion,
            "grados_verificados": formacion.get("grados_obtenidos", []),
            "grados_en_curso": formacion.get("en_curso", [])
        }
    
    def calcular_c2_experiencia_docente(self, experiencia: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula puntaje C2 - Experiencia Docente Universitaria.
        
        Args:
            experiencia: Dict con años_docencia_universitaria (float)
            
        Ejemplo:
            {
                "años_docencia_universitaria": 3.5,
                "instituciones": ["Universidad X", "Universidad Y"],
                "cursos_formacion_docente": True  # Si solo tiene cursos, se considera < 1 año
            }
        
        Returns:
            Dict con puntaje, justificacion
        """
        años = experiencia.get("años_docencia_universitaria", 0)
        solo_cursos = experiencia.get("cursos_formacion_docente", False)
        
        if solo_cursos and años == 0:
            puntaje = 5
            categoria = "menos_1_anio"
        elif años >= 10:
            puntaje = 40
            categoria = "mas_10_anios"
        elif años >= 6:
            puntaje = 30
            categoria = "6_a_10_anios"
        elif años >= 3:
            puntaje = 20
            categoria = "3_a_5_anios"
        elif años >= 1:
            puntaje = 10
            categoria = "1_a_2_anios"
        elif años > 0:
            puntaje = 5
            categoria = "menos_1_anio"
        else:
            puntaje = 0
            categoria = "sin_experiencia"
        
        return {
            "codigo": "C2",
            "criterio": "Experiencia Docente Universitaria",
            "puntaje_obtenido": puntaje,
            "puntaje_maximo": 40,
            "años_computados": años,
            "categoria": categoria,
            "instituciones": experiencia.get("instituciones", []),
            "observaciones": "Solo cursos de formación docente" if solo_cursos else ""
        }
    
    def calcular_c3_experiencia_profesional(self, experiencia: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula puntaje C3 - Experiencia Profesional.
        
        Args:
            experiencia: Dict con años_experiencia_profesional (float)
            
        Ejemplo:
            {
                "años_experiencia_profesional": 5.5,
                "empleadores": ["Empresa A", "ONPE", "Migraciones"],
                "area_especializacion": "Economía y Gestión Pública"
            }
        
        Returns:
            Dict con puntaje, justificacion
        """
        años = experiencia.get("años_experiencia_profesional", 0)
        
        if años >= 10:
            puntaje = 40
            categoria = "mas_10_anios"
        elif años >= 6:
            puntaje = 30
            categoria = "6_a_10_anios"
        elif años >= 3:
            puntaje = 20
            categoria = "3_a_5_anios"
        elif años >= 1:
            puntaje = 10
            categoria = "1_a_2_anios"
        elif años > 0:
            puntaje = 5
            categoria = "menos_1_anio"
        else:
            puntaje = 0
            categoria = "sin_experiencia"
        
        return {
            "codigo": "C3",
            "criterio": "Experiencia Profesional",
            "puntaje_obtenido": puntaje,
            "puntaje_maximo": 40,
            "años_computados": años,
            "categoria": categoria,
            "empleadores": experiencia.get("empleadores", []),
            "area": experiencia.get("area_especializacion", "")
        }
    
    def calcular_c4_centro_labores(self, centro: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula puntaje C4 - Centro de Labores.
        
        Args:
            centro: Dict con tipo_institucion
            
        Ejemplo:
            {
                "tipo_institucion": "universidad_acreditada",  # opciones ver JSON
                "nombre": "Universidad San Ignacio de Loyola",
                "cargo_actual": "Analista"
            }
        
        Returns:
            Dict con puntaje
        """
        tipo = centro.get("tipo_institucion", "sin_centro").lower()
        subcategorias = self.criterios["criterios"]["C4"]["subcategorias"]
        
        if tipo in subcategorias:
            puntaje = subcategorias[tipo]["puntos"]
            descripcion = subcategorias[tipo]["descripcion"]
        else:
            puntaje = 0
            descripcion = "Sin centro de labores o no especificado"
        
        return {
            "codigo": "C4",
            "criterio": "Centro de Labores",
            "puntaje_obtenido": puntaje,
            "puntaje_maximo": 20,
            "tipo_institucion": tipo,
            "nombre_institucion": centro.get("nombre", ""),
            "descripcion": descripcion
        }
    
    def calcular_c5_produccion_academica(self, produccion: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Calcula puntaje C5 - Producción Académica.
        
        Args:
            produccion: Dict con listas de publicaciones por tipo
            
        Ejemplo:
            {
                "articulos_scopus_q1_q2": [
                    {"titulo": "...", "año": 2023, "revista": "..."}
                ],
                "tesis_maestria_doctorado": [
                    {"titulo": "...", "año": 2024, "repositorio": "..."}
                ],
                ...
            }
        
        Returns:
            Dict con puntaje total (máx 50)
        """
        subcategorias = self.criterios["criterios"]["C5"]["subcategorias"]
        puntaje_total = 0
        detalle_items = []
        
        for tipo_pub, items in produccion.items():
            if tipo_pub in subcategorias and isinstance(items, list):
                puntos_unitario = subcategorias[tipo_pub]["puntos_unitario"]
                cantidad = len(items)
                puntos_categoria = puntos_unitario * cantidad
                puntaje_total += puntos_categoria
                
                detalle_items.append({
                    "tipo": tipo_pub,
                    "cantidad": cantidad,
                    "puntos_unitario": puntos_unitario,
                    "puntos_subtotal": puntos_categoria,
                    "items": items
                })
        
        # Máximo 50 puntos
        puntaje_final = min(puntaje_total, 50)
        
        return {
            "codigo": "C5",
            "criterio": "Producción Académica",
            "puntaje_obtenido": puntaje_final,
            "puntaje_maximo": 50,
            "puntaje_acumulado_bruto": puntaje_total,
            "se_aplico_tope": puntaje_total > 50,
            "detalle_por_tipo": detalle_items,
            "total_publicaciones": sum(len(items) for items in produccion.values() if isinstance(items, list))
        }
    
    def evaluar_candidato(self, candidato: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa un candidato completo y retorna su perfil con puntajes.
        
        Args:
            candidato: Dict con toda la información del candidato
            
        Returns:
            Dict con evaluación completa
        """
        # Calcular cada criterio
        c1 = self.calcular_c1_formacion_academica(candidato.get("formacion_academica", {}))
        c2 = self.calcular_c2_experiencia_docente(candidato.get("experiencia_docente", {}))
        c3 = self.calcular_c3_experiencia_profesional(candidato.get("experiencia_profesional", {}))
        c4 = self.calcular_c4_centro_labores(candidato.get("centro_labores", {}))
        c5 = self.calcular_c5_produccion_academica(candidato.get("produccion_academica", {}))
        
        # Calcular total
        total = c1["puntaje_obtenido"] + c2["puntaje_obtenido"] + c3["puntaje_obtenido"] + \
                c4["puntaje_obtenido"] + c5["puntaje_obtenido"]
        
        # Determinar clasificación
        clasificacion = self._determinar_clasificacion(c1["puntaje_obtenido"], 
                                                        c5["puntaje_obtenido"], 
                                                        total)
        
        return {
            "nombre_completo": candidato.get("nombre_completo", "Sin nombre"),
            "fuente": candidato.get("fuente", ""),
            "fecha_evaluacion": datetime.now().isoformat(),
            "criterios": {
                "C1": c1,
                "C2": c2,
                "C3": c3,
                "C4": c4,
                "C5": c5
            },
            "puntaje_total": total,
            "puntaje_maximo_posible": 200,
            "porcentaje": round((total / 200) * 100, 2),
            "clasificacion": clasificacion["perfil"],
            "descripcion_clasificacion": clasificacion["descripcion"],
            "es_elegible": clasificacion["es_elegible"],
            "observaciones": clasificacion["observaciones"]
        }
    
    def _determinar_clasificacion(self, puntaje_c1: int, puntaje_c5: int, total: int) -> Dict[str, Any]:
        """Determina la clasificación del perfil según reglas."""
        
        # Regla prioritaria: NO ELEGIBLE si C1=0 Y C5=0
        if puntaje_c1 == 0 and puntaje_c5 == 0:
            return {
                "perfil": "NO_ELEGIBLE_PERFIL_DOCENTE",
                "descripcion": "Sin formación académica Y sin producción académica",
                "es_elegible": False,
                "observaciones": "Candidato no cumple requisitos mínimos para perfil docente"
            }
        
        # Clasificación por puntaje total
        if total < 90:
            perfil = "NO_CALIFICA"
            descripcion = "Puntaje total insuficiente (< 90 puntos)"
            elegible = False
        elif total < 110:
            perfil = "PRACTITIONER"
            descripcion = "Profesional con experiencia práctica"
            elegible = True
        elif total < 150:
            perfil = "DTC_DTP_DOCENTE_INVESTIGADOR"
            descripcion = "Docente a Tiempo Completo/Parcial o Docente Investigador"
            elegible = True
        else:
            perfil = "DOCENTE_INVESTIGADOR_CON_HORAS_INVESTIGACION"
            descripcion = "Docente Investigador con dedicación a investigación"
            elegible = True
        
        return {
            "perfil": perfil,
            "descripcion": descripcion,
            "es_elegible": elegible,
            "observaciones": f"Puntaje total: {total}/200"
        }
    
    def generar_ranking(self, candidatos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evalúa múltiples candidatos y genera un ranking ordenado.
        
        Args:
            candidatos: Lista de dicts con información de candidatos
            
        Returns:
            Lista ordenada por puntaje (mayor a menor)
        """
        evaluaciones = []
        
        for candidato in candidatos:
            evaluacion = self.evaluar_candidato(candidato)
            evaluaciones.append(evaluacion)
        
        # Ordenar por puntaje total (descendente)
        ranking = sorted(evaluaciones, key=lambda x: x["puntaje_total"], reverse=True)
        
        # Agregar posición en el ranking
        for i, evaluacion in enumerate(ranking, 1):
            evaluacion["posicion_ranking"] = i
        
        return ranking
    
    def exportar_ranking_json(self, ranking: List[Dict[str, Any]], archivo_salida: str):
        """Exporta el ranking a un archivo JSON."""
        output = {
            "fecha_generacion": datetime.now().isoformat(),
            "total_candidatos": len(ranking),
            "sistema_version": self.criterios["version"],
            "ranking": ranking
        }
        
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Ranking exportado a: {archivo_salida}")
    
    def generar_tabla_resumen(self, ranking: List[Dict[str, Any]]) -> str:
        """Genera una tabla markdown con resumen del ranking."""
        lineas = []
        lineas.append("# 🏆 RANKING DE CANDIDATOS - PERFIL DOCENTE")
        lineas.append(f"\n**Fecha de evaluación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lineas.append(f"**Total de candidatos evaluados:** {len(ranking)}\n")
        lineas.append("| Pos | Nombre | C1 | C2 | C3 | C4 | C5 | **TOTAL** | % | Clasificación |")
        lineas.append("|-----|--------|----|----|----|----|----|-----------|----|---------------|")
        
        for evaluacion in ranking:
            pos = evaluacion["posicion_ranking"]
            nombre = evaluacion["nombre_completo"][:30]  # Limitar longitud
            c1 = evaluacion["criterios"]["C1"]["puntaje_obtenido"]
            c2 = evaluacion["criterios"]["C2"]["puntaje_obtenido"]
            c3 = evaluacion["criterios"]["C3"]["puntaje_obtenido"]
            c4 = evaluacion["criterios"]["C4"]["puntaje_obtenido"]
            c5 = evaluacion["criterios"]["C5"]["puntaje_obtenido"]
            total = evaluacion["puntaje_total"]
            porcentaje = evaluacion["porcentaje"]
            clasificacion = evaluacion["clasificacion"]
            
            lineas.append(f"| {pos} | {nombre} | {c1} | {c2} | {c3} | {c4} | {c5} | **{total}** | {porcentaje}% | {clasificacion} |")
        
        lineas.append("\n## 📊 Puntajes Máximos por Criterio")
        lineas.append("- **C1** Formación Académica: 50 pts")
        lineas.append("- **C2** Experiencia Docente Universitaria: 40 pts")
        lineas.append("- **C3** Experiencia Profesional: 40 pts")
        lineas.append("- **C4** Centro de Labores: 20 pts")
        lineas.append("- **C5** Producción Académica: 50 pts")
        lineas.append("- **TOTAL MÁXIMO: 200 pts**")
        
        return "\n".join(lineas)


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Crear instancia del evaluador
    evaluador = EvaluadorPerfilDocente("criterios_evaluacion.json")
    
    # Ejemplo de candidatos (aquí van los datos extraídos)
    candidatos = [
        {
            "nombre_completo": "Luis Augusto Maya Velarde",
            "fuente": "CTI Vitae CONCYTEC - ID: 440291",
            "formacion_academica": {
                "grado_maximo": "maestria",
                "grados_obtenidos": ["bachiller", "licenciatura", "maestria"],
                "en_curso": ["maestria_gestion_publica", "especialidad_docencia"]
            },
            "experiencia_docente": {
                "años_docencia_universitaria": 0,
                "cursos_formacion_docente": True,
                "instituciones": []
            },
            "experiencia_profesional": {
                "años_experiencia_profesional": 5.5,
                "empleadores": ["ONPE", "Superintendencia Nacional de Migraciones"],
                "area_especializacion": "Economía y Gestión Pública"
            },
            "centro_labores": {
                "tipo_institucion": "institucion_publica",
                "nombre": "ONPE / Migraciones",
                "cargo_actual": "Analista Administrativo"
            },
            "produccion_academica": {
                "tesis_maestria_doctorado": [
                    {
                        "titulo": "Implementación del aprendizaje basado en problemas en la enseñanza de las ciencias económicas",
                        "año": 2025,
                        "repositorio": "UBA"
                    },
                    {
                        "titulo": "Análisis del impacto de la implementación de la gestión por procesos en la emisión del pasaporte electrónico",
                        "año": 2019,
                        "repositorio": "Universidad Europea del Atlántico"
                    }
                ],
                "tesis_pregrado": [
                    {
                        "titulo": "Impacto de las variables que inciden en la tasa de la prevalencia de desnutrición para países en desarrollo durante 1995-2014",
                        "año": 2017,
                        "repositorio": "USIL"
                    }
                ]
            }
        },
        {
            "nombre_completo": "Joshua Gabriel Lopez Pinto",
            "fuente": "CV PDF - Estudiante",
            "formacion_academica": {
                "grado_maximo": "estudiante",
                "grados_obtenidos": [],
                "en_curso": ["bachiller_economia"]
            },
            "experiencia_docente": {
                "años_docencia_universitaria": 0,
                "cursos_formacion_docente": True,
                "instituciones": []
            },
            "experiencia_profesional": {
                "años_experiencia_profesional": 2,
                "empleadores": ["Varios"],
                "area_especializacion": "Economía"
            },
            "centro_labores": {
                "tipo_institucion": "universidad_licenciada",
                "nombre": "Universidad San Ignacio de Loyola",
                "cargo_actual": "Estudiante"
            },
            "produccion_academica": {}
        }
    ]
    
    # Generar ranking
    ranking = evaluador.generar_ranking(candidatos)
    
    # Exportar resultados
    evaluador.exportar_ranking_json(ranking, "ranking_docentes.json")
    
    # Generar y mostrar tabla resumen
    tabla = evaluador.generar_tabla_resumen(ranking)
    print("\n" + tabla)
    
    # Guardar tabla en markdown
    with open("ranking_resumen.md", "w", encoding="utf-8") as f:
        f.write(tabla)
    
    print("\n✅ Proceso completado exitosamente")
    print("📄 Archivos generados:")
    print("   - ranking_docentes.json (datos completos)")
    print("   - ranking_resumen.md (tabla resumen)")
