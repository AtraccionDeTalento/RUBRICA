"""
Script para ejecutar el servidor Flask - Compatible con PyInstaller
Abre automáticamente el navegador con la interfaz web
"""
import sys
import os

# Forzar UTF-8 en stdout/stderr para evitar UnicodeEncodeError en Windows (cp1252)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

import webbrowser
import threading
import time
import traceback
import socket

# Para mostrar errores en ventana cuando se ejecuta como .exe
def mostrar_error(mensaje):
    """Muestra un error en una ventana emergente (para .exe sin consola)"""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, str(mensaje), "Error - Evaluación Docente USIL", 0x10)
    except:
        print(f"ERROR: {mensaje}")

def puerto_disponible(puerto):
    """Verifica si un puerto está disponible"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', puerto))
            return True
    except:
        return False

def abrir_navegador(puerto=5000):
    """Espera a que el servidor acepte conexiones y recién abre el navegador
    (un sleep fijo abría el navegador antes de que Flask estuviera listo)."""
    inicio = time.time()
    while time.time() - inicio < 180:
        try:
            with socket.create_connection(('127.0.0.1', puerto), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    try:
        url = f'http://127.0.0.1:{puerto}'
        print(f"🌐 Abriendo navegador en: {url}")
        webbrowser.open(url)
    except Exception as e:
        print(f"⚠️ No se pudo abrir el navegador automáticamente: {e}")
        print(f"   Por favor abre manualmente: http://127.0.0.1:{puerto}")

# Configurar rutas según el entorno
if getattr(sys, 'frozen', False):
    # Ejecutando como .exe (PyInstaller)
    base_path = sys._MEIPASS
    exe_dir = os.path.dirname(sys.executable)
    os.chdir(base_path)
    # Establecer variable de entorno para rutas de datos
    os.environ['EVALUACION_DOCENTE_EXE_DIR'] = exe_dir
else:
    # Ejecutando como script Python
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)

# Redirigir stderr a un archivo de log cuando es .exe
log_file = None
if getattr(sys, 'frozen', False):
    try:
        log_path = os.path.join(os.path.dirname(sys.executable), 'evaluacion_docente_log.txt')
        log_file = open(log_path, 'w', encoding='utf-8')
        # Solo redirigir errores, no stdout para ver mensajes en consola
    except:
        pass

try:
    from app_web import app
except Exception as e:
    error_msg = f"Error al importar app_web:\n{traceback.format_exc()}"
    mostrar_error(error_msg)
    if log_file:
        log_file.write(error_msg)
        log_file.close()
    sys.exit(1)

if __name__ == '__main__':
    PUERTO = 5000
    
    print("\n" + "="*70)
    print("🎓 PEOPLE ANALYTICS - EVALUACIÓN DOCENTE USIL")
    print("   Sistema de Análisis Inteligente de Perfiles")
    print("="*70)
    
    # Verificar si el puerto está disponible
    if not puerto_disponible(PUERTO):
        print(f"\n⚠️ El puerto {PUERTO} está en uso.")
        print("   Por favor cierra otras instancias del programa.")
        if getattr(sys, 'frozen', False):
            input("\nPresiona Enter para cerrar...")
        sys.exit(1)
    
    print(f"\n📱 El navegador se abrirá automáticamente en: http://localhost:{PUERTO}")
    print("\n💡 Para detener el servidor:")
    print("   - Cierra esta ventana, o")
    print("   - Presiona Ctrl+C")
    print("\n" + "-"*70 + "\n")
    
    try:
        # Iniciar hilo para abrir navegador automáticamente
        # (omitir si se pasa --no-browser, p.ej. cuando lo lanza la plataforma PA)
        if '--no-browser' not in sys.argv:
            hilo_navegador = threading.Thread(target=abrir_navegador, args=(PUERTO,), daemon=True)
            hilo_navegador.start()
        else:
            print("🔇 Modo --no-browser: navegador no se abrirá automáticamente.")
        
        # Iniciar servidor Flask
        app.run(host='127.0.0.1', port=PUERTO, debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\n✅ Servidor detenido correctamente")
    except Exception as e:
        error_msg = f"Error al iniciar servidor:\n{traceback.format_exc()}"
        print(f"\n❌ {error_msg}")
        mostrar_error(error_msg)
        if log_file:
            log_file.write(error_msg)
        if getattr(sys, 'frozen', False):
            input("\nPresiona Enter para cerrar...")
    finally:
        if log_file:
            log_file.close()
