"""Analizar estructura de archivos en LINKS"""
import pandas as pd

# Archivo 1: INFORMACION DE VALIDACION (links en columna J)
print('='*60)
print('ARCHIVO 1: INFORMACION DE VALIDACION.xlsx')
print('='*60)
path1 = r'C:\Users\jlopezp\OneDrive - Universidad San Ignacio de Loyola\PROYECTO RUBRICA\LINKS\INFORMACION DE VALIDACION.xlsx'
xl1 = pd.ExcelFile(path1)
print(f'Hojas: {xl1.sheet_names}')

# Probar la primera hoja
df1 = pd.read_excel(path1, sheet_name=0, header=0)
print(f'Filas: {len(df1)}')
print(f'Columnas: {list(df1.columns)}')

# Ver columna J (indice 9)
if len(df1.columns) > 9:
    print(f'\nColumna J (indice 9): {df1.columns[9]}')

# Mostrar primeras filas de columnas clave
print('\nPrimeras 10 filas (Nombre y Link):')
for i in range(min(10, len(df1))):
    row = df1.iloc[i]
    nombre = str(row.iloc[0])[:40] if len(df1.columns) > 0 else 'N/A'
    link = str(row.iloc[9])[:60] if len(df1.columns) > 9 else 'N/A'
    print(f'  {i+1}. {nombre} | {link}')

# Archivo 2: Requerimiento docentes
print('\n' + '='*60)
print('ARCHIVO 2: Requerimiento docentes 2026-1 300126.xlsx')
print('='*60)
path2 = r'C:\Users\jlopezp\OneDrive - Universidad San Ignacio de Loyola\PROYECTO RUBRICA\LINKS\Requerimiento docentes 2026-1 300126.xlsx'
xl2 = pd.ExcelFile(path2)
print(f'Hojas: {xl2.sheet_names}')

# Buscar hoja con datos
for hoja in xl2.sheet_names:
    try:
        df2 = pd.read_excel(path2, sheet_name=hoja, header=1)
        if len(df2) > 5:
            cols = [str(c).upper() for c in df2.columns]
            if any('CANDIDATO' in c or 'DNI' in c for c in cols):
                print(f'\nHoja con datos: {hoja}')
                print(f'Filas: {len(df2)}')
                print(f'Columnas: {list(df2.columns)[:12]}')
                
                # Buscar columnas clave
                for j, col in enumerate(df2.columns):
                    col_upper = str(col).upper()
                    if 'CANDIDATO' in col_upper or 'DNI' in col_upper or 'FACULTAD' in col_upper:
                        print(f'  Columna {j}: {col}')
                break
    except:
        continue
