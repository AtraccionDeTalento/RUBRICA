# -*- coding: utf-8 -*-
"""
Servidor wrapper para iniciar el app_web de evaluacion docente desde el root (requerido por Electron)
"""
import os
import sys

# Forzar UTF-8 en stdout/stderr para evitar UnicodeEncodeError en Windows con emojis
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Cambiar el directorio de trabajo a 'bot_evaluacion_docente' para que todas las rutas relativas funcionen
base_dir = os.path.dirname(os.path.abspath(__file__))
bot_dir = os.path.join(base_dir, 'bot_evaluacion_docente')
os.chdir(bot_dir)

# Agregar la carpeta 'bot_evaluacion_docente' al path para poder importar sus modulos
sys.path.insert(0, bot_dir)

# Ejecutar el app de flask
import app_web
import subprocess

def liberar_puerto(puerto):
    try:
        # Encontrar PID usando netstat en Windows
        salida = subprocess.check_output(f"netstat -ano | findstr :{puerto}", shell=True, text=True)
        for linea in salida.strip().split('\n'):
            if 'LISTENING' in linea or 'ESCUCHANDO' in linea:
                partes = linea.split()
                pid = partes[-1]
                if pid != '0':
                    print(f"[!] Matando proceso zombie {pid} ocupando el puerto {puerto}")
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        pass

if __name__ == '__main__':
    # Liberar puerto antes de arrancar para evitar conflictos con instancias anteriores (zombies)
    liberar_puerto(5000)
    app_web.app.run(host='127.0.0.1', debug=False, port=5000, use_reloader=False, threaded=True)
