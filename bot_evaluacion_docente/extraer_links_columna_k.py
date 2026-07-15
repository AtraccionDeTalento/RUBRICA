"""
Script para extraer links de Excel de SharePoint y consolidar en HOJA DE PRUEBA
También identifica registros sin link (DNI + Nombre)

Uso:
1. Descargar el Excel de SharePoint a la carpeta LINKS/
2. Ejecutar: python extraer_links_columna_k.py
"""

import pandas as pd
import os
from datetime import datetime

# Configuración
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKS_DIR = os.path.join(BASE_DIR, "LINKS")

# Archivo de entrada (descargado de SharePoint)
ARCHIVO_ENTRADA = os.path.join(LINKS_DIR, "Requerimiento docentes 2026-1.xlsx")

# Archivo de salida - HOJA DE PRUEBA (sobrescribir)
ARCHIVO_SALIDA = os.path.join(LINKS_DIR, "HOJA DE PRUEBA de Extraccion de LINKs.xlsx")


def extraer_y_consolidar_links():
    """
    Extrae links de columna K y datos de registros sin link
    Actualiza HOJA DE PRUEBA con toda la información
    """
    print("\n" + "="*70)
    print("📊 EXTRACTOR DE LINKS + REGISTROS SIN INFORMACIÓN")
    print("="*70)
    
    # Verificar que existe el archivo
    if not os.path.exists(ARCHIVO_ENTRADA):
        print(f"\n❌ ERROR: No se encontró el archivo")
        print(f"📁 Ruta esperada: {ARCHIVO_ENTRADA}")
        print("\n💡 INSTRUCCIONES:")
        print("   1. Abre el link de SharePoint en tu navegador")
        print("   2. Descarga el Excel 'Requerimiento docentes 2026-1.xlsx'")
        print("   3. Guárdalo en: LINKS/")
        print("   4. Ejecuta este script nuevamente\n")
        return
    
    try:
        print(f"\n📂 Leyendo archivo: {os.path.basename(ARCHIVO_ENTRADA)}")
        
        # Leer todas las hojas del Excel
        excel_file = pd.ExcelFile(ARCHIVO_ENTRADA)
        print(f"📄 Hojas encontradas: {len(excel_file.sheet_names)}")
        
        registros_con_link = []
        registros_sin_link = []
        
        for sheet_name in excel_file.sheet_names:
            print(f"\n🔍 Procesando hoja: '{sheet_name}'...")
            
            try:
                # Leer hoja completa
                df = pd.read_excel(ARCHIVO_ENTRADA, sheet_name=sheet_name)
                
                print(f"   Total de filas: {len(df)}")
                print(f"   Total de columnas: {df.shape[1]}")
                
                # Intentar identificar columnas importantes
                # Buscar DNI (columnas comunes: A, B, C)
                columna_dni = None
                columna_nombre = None
                columna_link = None
                
                for i, col_name in enumerate(df.columns):
                    col_lower = str(col_name).lower()
                    if 'dni' in col_lower or 'documento' in col_lower:
                        columna_dni = i
                    elif 'nombre' in col_lower or 'apellido' in col_lower:
                        columna_nombre = i
                    elif 'link' in col_lower or 'url' in col_lower or 'ctivitae' in col_lower:
                        columna_link = i
                
                # Si no se encontraron por nombre, asumir posiciones
                if columna_link is None and df.shape[1] > 10:
                    columna_link = 10  # Columna K (índice 10)
                
                if columna_link is not None:
                    print(f"   📍 Columna de links: {df.columns[columna_link] if columna_link < len(df.columns) else 'K (índice 10)'}")
                    
                    # Procesar cada fila
                    for idx, row in df.iterrows():
                        # Obtener datos básicos
                        dni = row.iloc[columna_dni] if columna_dni is not None and columna_dni < len(row) else ""
                        nombre = row.iloc[columna_nombre] if columna_nombre is not None and columna_nombre < len(row) else ""
                        link = row.iloc[columna_link] if columna_link < len(row) else ""
                        
                        # Limpiar datos
                        dni_str = str(dni).strip() if pd.notna(dni) else ""
                        nombre_str = str(nombre).strip() if pd.notna(nombre) else ""
                        link_str = str(link).strip() if pd.notna(link) else ""
                        
                        # Clasificar
                        if link_str and (link_str.startswith('http') or link_str.startswith('www')):
                            # Tiene link válido
                            registros_con_link.append({
                                'URL': link_str,
                                'DNI': dni_str,
                                'Nombre': nombre_str,
                                'Hoja': sheet_name,
                                'Estado': 'CON LINK'
                            })
                        elif dni_str or nombre_str:
                            # No tiene link pero tiene datos de persona
                            registros_sin_link.append({
                                'URL': '',
                                'DNI': dni_str,
                                'Nombre': nombre_str,
                                'Hoja': sheet_name,
                                'Estado': 'SIN LINK - REVISAR MANUALMENTE'
                            })
                    
                    print(f"   ✅ Con link: {len([r for r in registros_con_link if r['Hoja'] == sheet_name])}")
                    print(f"   ⚠️ Sin link: {len([r for r in registros_sin_link if r['Hoja'] == sheet_name])}")
                else:
                    print(f"   ⚠️ No se encontró columna de links en esta hoja")
                    
            except Exception as e:
                print(f"   ❌ Error procesando hoja: {e}")
        
        # Consolidar resultados
        print("\n" + "="*70)
        print("📊 RESUMEN DE EXTRACCIÓN")
        print("="*70)
        print(f"✅ Registros CON link: {len(registros_con_link)}")
        print(f"⚠️ Registros SIN link: {len(registros_sin_link)}")
        
        # Crear DataFrame consolidado
        todos_registros = registros_con_link + registros_sin_link
        
        if todos_registros:
            df_consolidado = pd.DataFrame(todos_registros)
            
            # Crear Excel con dos hojas
            with pd.ExcelWriter(ARCHIVO_SALIDA, engine='openpyxl') as writer:
                # Hoja 1: Solo links (para el sistema)
                df_links = df_consolidado[df_consolidado['Estado'] == 'CON LINK'][['URL']]
                df_links.to_excel(writer, sheet_name='Links', index=False)
                
                # Hoja 2: Todos los registros (para revisión)
                df_consolidado.to_excel(writer, sheet_name='Detalle_Completo', index=False)
            
            print(f"\n✅ Archivo actualizado exitosamente:")
            print(f"📁 {ARCHIVO_SALIDA}")
            print(f"\n📋 Hojas creadas:")
            print(f"   1. 'Links' - Solo URLs ({len(registros_con_link)} registros)")
            print(f"   2. 'Detalle_Completo' - Todos los datos ({len(todos_registros)} registros)")
            
            # Preview de registros sin link
            if registros_sin_link:
                print(f"\n⚠️ REGISTROS SIN LINK (primeros 10):")
                for i, reg in enumerate(registros_sin_link[:10], 1):
                    print(f"   {i}. DNI: {reg['DNI']} | Nombre: {reg['Nombre']}")
                if len(registros_sin_link) > 10:
                    print(f"   ... y {len(registros_sin_link) - 10} más")
            
            print("\n✅ El sistema ahora procesará los links automáticamente")
            print("⚠️ Revisa la hoja 'Detalle_Completo' para los registros sin link\n")
        else:
            print("\n⚠️ No se encontraron registros para procesar")
        
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    extraer_y_consolidar_links()
