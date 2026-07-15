import pandas as pd

# Verificar archivo subido
archivo = r'bot_evaluacion_docente\archivo_usuario_subido.xlsx'
print(f"Analizando: {archivo}")

xl = pd.ExcelFile(archivo)
print(f"\nHOJAS DISPONIBLES: {xl.sheet_names}")

# Analizar solo la hoja 2026.1 con diferentes headers
hoja = '2026.1'
print(f"\n{'='*60}")
print(f"ANALIZANDO HOJA: {hoja}")

for header_row in [0, 1, 2]:
    df = pd.read_excel(xl, sheet_name=hoja, header=header_row)
    print(f"\n  HEADER={header_row}:")
    print(f"  Filas: {len(df)}")
    print(f"  Columnas: {list(df.columns)}")
    
    # Buscar columna CTI
    urls_encontradas = 0
    for col in df.columns:
        col_str = str(col).upper()
        if 'CTI' in col_str or 'LINK' in col_str:
            urls_validas = df[col].dropna().astype(str)
            urls_cti = urls_validas[urls_validas.str.contains('ctivitae.concytec.gob.pe', na=False)]
            print(f"  Columna '{col}': {len(urls_cti)} URLs válidas")
            urls_encontradas += len(urls_cti)
    
    # Buscar en todas las columnas si no encontró por nombre
    if urls_encontradas == 0:
        for col in df.columns:
            valores = df[col].dropna().astype(str)
            urls_cti = valores[valores.str.contains('ctivitae.concytec.gob.pe', na=False)]
            if len(urls_cti) > 0:
                print(f"  Columna '{col}': {len(urls_cti)} URLs CTI")
