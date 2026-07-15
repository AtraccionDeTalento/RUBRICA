"""
Launcher para el Sistema de Evaluacion Docente USIL
Este script se usa como punto de entrada para el ejecutable .exe
"""
import sys
import os

# ============================================================================
# INICIO INMEDIATO - Mostrar que el programa esta cargando
# ============================================================================
print("")
print("=" * 70)
print("  SISTEMA DE EVALUACION DOCENTE USIL")
print("  People Analytics - Talento & Cultura")
print("=" * 70)
print("")
print("[INICIO] Verificando componentes del sistema...")
sys.stdout.flush()

# ============================================================================
# VERIFICACION DE LIBRERIAS
# ============================================================================
def verificar_librerias():
    """Verifica que todas las librerias necesarias esten disponibles"""
    librerias_requeridas = [
        ('flask', 'Flask'),
        ('pandas', 'pandas'),
        ('openpyxl', 'openpyxl'),
        ('pdfplumber', 'pdfplumber'),
        ('bs4', 'BeautifulSoup4'),
        ('requests', 'requests'),
        ('jinja2', 'Jinja2'),
        ('werkzeug', 'Werkzeug'),
    ]
    
    errores = []
    for modulo, nombre in librerias_requeridas:
        try:
            __import__(modulo)
            print(f"  [OK] {nombre}")
        except ImportError as e:
            print(f"  [ERROR] {nombre}: {e}")
            errores.append(nombre)
    
    sys.stdout.flush()
    return len(errores) == 0

print("")
print("[INFO] Verificando librerias...")
if not verificar_librerias():
    print("")
    print("[ERROR] Faltan librerias necesarias.")
    print("        El programa no puede continuar.")
    input("\nPresiona Enter para cerrar...")
    sys.exit(1)

print("")
print("[OK] Todas las librerias verificadas correctamente")
sys.stdout.flush()

# ============================================================================
# IMPORTACIONES ADICIONALES
# ============================================================================
try:
    import webbrowser
    import threading
    import time
except ImportError as e:
    print(f"[ERROR] Error al importar modulos basicos: {e}")
    input("\nPresiona Enter para cerrar...")
    sys.exit(1)

# ============================================================================
# CONFIGURACION DE RUTAS
# ============================================================================
def get_base_path():
    """Obtiene la ruta base correcta tanto para desarrollo como para el .exe"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_data_path():
    """Obtiene la ruta a los datos (donde esta el .exe o el proyecto)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_PATH = get_base_path()
DATA_PATH = get_data_path()

# Agregar el directorio base al path de Python
sys.path.insert(0, BASE_PATH)

# Configurar variables de entorno
os.environ['EVALUACION_DOCENTE_BASE'] = DATA_PATH
os.environ['EVALUACION_DOCENTE_APP'] = BASE_PATH

print("")
print(f"[INFO] Directorio de datos: {DATA_PATH}")
print(f"[INFO] Directorio de aplicacion: {BASE_PATH}")
sys.stdout.flush()

# ============================================================================
# VERIFICACION DE CARPETAS
# ============================================================================
print("")
print("[INFO] Verificando carpetas del proyecto...")

carpetas_necesarias = ['Cvs', 'LINKS', 'Rubrica', 'Extraccion de data']
carpetas_faltantes = []

for carpeta in carpetas_necesarias:
    ruta = os.path.join(DATA_PATH, carpeta)
    if os.path.exists(ruta):
        print(f"  [OK] {carpeta}")
    else:
        print(f"  [FALTA] {carpeta}")
        carpetas_faltantes.append(carpeta)

if carpetas_faltantes:
    print("")
    print("[ADVERTENCIA] Algunas carpetas no existen:")
    for c in carpetas_faltantes:
        print(f"  - Crear: {os.path.join(DATA_PATH, c)}")
    print("")
    print("  El programa continuara, pero algunas funciones")
    print("  pueden no estar disponibles.")

# Crear carpeta de resultados si no existe
resultados_dir = os.path.join(DATA_PATH, 'bot_evaluacion_docente', 'resultados')
if not os.path.exists(resultados_dir):
    try:
        os.makedirs(resultados_dir, exist_ok=True)
        print(f"  [CREADA] Carpeta de resultados")
    except Exception as e:
        print(f"  [ERROR] No se pudo crear carpeta de resultados: {e}")

sys.stdout.flush()

# ============================================================================
# FUNCION PARA ABRIR NAVEGADOR
# ============================================================================
def abrir_navegador():
    """Espera a que el servidor Flask responda y recien abre el navegador.

    Antes se usaba un sleep fijo de 2s, pero importar app_web (pandas,
    pdfplumber, etc.) puede tardar mucho mas, sobre todo en el .exe:
    el navegador llegaba antes de que existiera el servidor y mostraba
    una pagina vacia.
    """
    import socket
    inicio = time.time()
    timeout_total = 180  # hasta 3 minutos (primer arranque del .exe es lento)
    while time.time() - inicio < timeout_total:
        try:
            with socket.create_connection(('127.0.0.1', 5000), timeout=1):
                break  # el servidor ya acepta conexiones
        except OSError:
            time.sleep(0.5)
    else:
        print("[AVISO] El servidor tarda en arrancar; abre manualmente: http://127.0.0.1:5000")
        sys.stdout.flush()
        return
    try:
        webbrowser.open('http://127.0.0.1:5000')
        print("[INFO] Navegador abierto en http://127.0.0.1:5000")
    except Exception as e:
        print(f"[AVISO] No se pudo abrir el navegador automaticamente: {e}")
        print("        Abre manualmente: http://127.0.0.1:5000")
    sys.stdout.flush()

# ============================================================================
# INICIO DEL SERVIDOR WEB
# ============================================================================
def main():
    print("")
    print("=" * 70)
    print("[INFO] Iniciando servidor web Flask...")
    print("[INFO] El navegador se abrira automaticamente")
    print("[INFO] URL: http://127.0.0.1:5000")
    print("")
    print("[TIP] Para detener el servidor, cierra esta ventana")
    print("      o presiona Ctrl+C")
    print("=" * 70)
    print("")
    sys.stdout.flush()
    
    # Abrir navegador en segundo plano
    hilo_navegador = threading.Thread(target=abrir_navegador, daemon=True)
    hilo_navegador.start()
    
    try:
        # Importar la aplicacion Flask
        print("[INFO] Cargando aplicacion web...")
        sys.stdout.flush()
        
        from app_web import app
        
        print("[OK] Aplicacion cargada correctamente")
        print("[INFO] Servidor iniciado - esperando conexiones...")
        print("")
        sys.stdout.flush()
        
        # Ejecutar el servidor
        app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("")
        print("[INFO] Servidor detenido por el usuario")
        
    except Exception as e:
        print("")
        print("=" * 70)
        print("[ERROR] Error al iniciar el servidor:")
        print(f"        {e}")
        print("=" * 70)
        print("")
        import traceback
        traceback.print_exc()
        print("")
        input("Presiona Enter para cerrar...")
        sys.exit(1)

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print("")
        print("=" * 70)
        print("[ERROR FATAL] El programa encontro un error inesperado:")
        print(f"              {e}")
        print("=" * 70)
        print("")
        import traceback
        traceback.print_exc()
        print("")
        input("Presiona Enter para cerrar...")
        sys.exit(1)
