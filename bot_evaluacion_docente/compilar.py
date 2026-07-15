"""
Script para compilar el Sistema de Evaluación Docente USIL a ejecutable .exe
Ejecutar este script para generar el archivo EvaluacionDocente_USIL.exe

USO: python compilar.py
"""
import subprocess
import sys
import os
import shutil


def verificar_pyinstaller():
    try:
        import PyInstaller
        print("✅ PyInstaller ya está instalado")
        return True
    except ImportError:
        print("📦 Instalando PyInstaller...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        print("✅ PyInstaller instalado correctamente")
        return True


def crear_icono(script_dir):
    """Genera un ícono USIL (graduación académica) en múltiples resoluciones."""
    ico_path = os.path.join(script_dir, 'usil_icon.ico')

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("📦 Instalando Pillow para generar el ícono...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pillow'])
        from PIL import Image, ImageDraw

    BLUE  = (30, 58, 138, 255)   # USIL azul
    GOLD  = (255, 215, 0, 255)   # Dorado
    WHITE = (255, 255, 255, 255)

    def draw_icon(size):
        img  = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        s, m = size, max(1, round(size * 0.05))

        # Fondo azul redondeado
        try:
            draw.rounded_rectangle([m, m, s - m - 1, s - m - 1],
                                   radius=round(s * 0.18), fill=BLUE)
        except AttributeError:
            draw.rectangle([m, m, s - m - 1, s - m - 1], fill=BLUE)

        bx = s // 2                    # centro horizontal
        by = round(s * 0.42)           # posición del tablero

        # Tablero del birrete (elipse dorada)
        bw = round(s * 0.70)
        bh = max(2, round(s * 0.08))
        draw.ellipse([bx - bw // 2, by - bh, bx + bw // 2, by + bh], fill=GOLD)

        # Cuerpo del birrete (trapecio blanco)
        tw2 = round(s * 0.22)
        bw2 = round(s * 0.26)
        ty  = by + bh
        bottom_y = round(s * 0.70)
        draw.polygon([
            (bx - tw2, ty), (bx + tw2, ty),
            (bx + bw2, bottom_y), (bx - bw2, bottom_y),
        ], fill=WHITE)

        # Tallo (línea dorada vertical al centro)
        stem_top = round(s * 0.16)
        sw = max(1, round(s * 0.04))
        draw.rectangle([bx - sw // 2, stem_top, bx + sw // 2, by - bh], fill=GOLD)

        # Botón superior (círculo dorado)
        btn_r = max(2, round(s * 0.07))
        draw.ellipse([bx - btn_r, stem_top - btn_r,
                      bx + btn_r, stem_top + btn_r], fill=GOLD)

        # Borla (línea dorada a la derecha del tablero)
        tx  = bx + bw // 2 - max(1, round(s * 0.09))
        tlw = max(1, round(s * 0.03))
        tb  = round(s * 0.78)
        draw.rectangle([tx - tlw // 2, by + bh, tx + tlw // 2, tb], fill=GOLD)
        tr = max(2, round(s * 0.06))
        draw.ellipse([tx - tr, tb, tx + tr, tb + 2 * tr], fill=GOLD)

        return img

    sizes  = [16, 32, 48, 64, 128, 256]
    images = [draw_icon(s) for s in sizes]
    images[0].save(ico_path, format='ICO',
                   sizes=[(s, s) for s in sizes],
                   append_images=images[1:])
    print(f"✅ Ícono generado: {ico_path}")
    return ico_path


def compilar():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    launcher_file = os.path.join(script_dir, 'launcher.py')

    print("\n" + "=" * 70)
    print("🔨 COMPILANDO SISTEMA DE EVALUACIÓN DOCENTE USIL")
    print("=" * 70)
    print(f"\n📁 Directorio: {script_dir}")
    print(f"📄 Archivo principal: {launcher_file}")

    if not os.path.exists(launcher_file):
        print(f"❌ Error: No se encontró el archivo {launcher_file}")
        return False

    dist_dir = os.path.join(script_dir, 'dist')
    sep = ';' if sys.platform == 'win32' else ':'

    # Generar ícono
    print("\n🎨 Generando ícono...")
    ico_path = crear_icono(script_dir)

    print("\n⚙️  Ejecutando PyInstaller...")
    print("   (Esto puede tomar 5-10 minutos)\n")

    comando = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        '--onefile',
        '--windowed',                          # sin consola negra
        '--name', 'EvaluacionDocente_USIL',
        '--icon', ico_path,
        # Recursos web
        '--add-data', f'templates{sep}templates',
        '--add-data', f'static{sep}static',
        # Dependencias Flask
        '--collect-all', 'flask',
        '--collect-all', 'werkzeug',
        '--collect-all', 'jinja2',
        '--collect-all', 'markupsafe',
        '--collect-all', 'itsdangerous',
        '--collect-all', 'click',
        '--collect-all', 'blinker',
        # Dependencias de datos
        '--collect-all', 'pandas',
        '--collect-all', 'openpyxl',
        '--collect-all', 'pdfplumber',
        '--collect-all', 'pdfminer',
        '--collect-all', 'bs4',
        '--collect-all', 'requests',
        # Módulos internos
        '--hidden-import', 'config',
        '--hidden-import', 'app_web',
        '--hidden-import', 'motor_evaluacion',
        '--hidden-import', 'rubrica_loader',
        '--hidden-import', 'extractor_cvs',
        '--hidden-import', 'extractor_web_cvs',
        '--hidden-import', 'analizador_rubrica',
        '--hidden-import', 'generador_decisiones',
        '--hidden-import', 'generador_decisiones_mejorado',
        '--hidden-import', 'generador_decisiones_nuevo',
        '--hidden-import', 'generador_reportes',
        'launcher.py'
    ]

    try:
        subprocess.run(comando, cwd=script_dir, check=True)

        exe_path = os.path.join(dist_dir, 'EvaluacionDocente_USIL.exe')

        if not os.path.exists(exe_path):
            print("\n❌ Error: El ejecutable no se generó correctamente")
            return False

        # Copiar JSON de rúbrica al lado del EXE (los necesita en runtime)
        rubrica_src = os.path.join(os.path.dirname(script_dir), 'Rubrica')
        rubrica_dst = os.path.join(dist_dir, 'Rubrica')
        if os.path.exists(rubrica_src):
            os.makedirs(rubrica_dst, exist_ok=True)
            for f in os.listdir(rubrica_src):
                if f.endswith('.json'):
                    shutil.copy2(os.path.join(rubrica_src, f),
                                 os.path.join(rubrica_dst, f))
            print(f"\n📁 Archivos de rúbrica copiados a: {rubrica_dst}")
        else:
            print(f"\n⚠️  No se encontró carpeta Rubrica en: {rubrica_src}")

        size_mb = os.path.getsize(exe_path) / (1024 * 1024)

        print("\n" + "=" * 70)
        print("✅ ¡COMPILACIÓN EXITOSA!")
        print("=" * 70)
        print(f"\n📦 Ejecutable generado en:")
        print(f"   {exe_path}")
        print(f"\n📏 Tamaño: {size_mb:.1f} MB")
        print("\n📋 INSTRUCCIONES DE USO:")
        print("   1. Copia TODA la carpeta 'dist/' a cualquier equipo")
        print("   2. En la misma carpeta que el .exe, agrega:")
        print("      - LINKS/   (con el Excel INFORMACION DE VALIDACION.xlsx)")
        print("      - Cvs/     (para PDFs de CVs — opcional)")
        print("   3. Haz doble clic en EvaluacionDocente_USIL.exe")
        print("      El navegador se abrirá automáticamente.")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error durante la compilación: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n🚀 Iniciando proceso de compilación...\n")

    if not verificar_pyinstaller():
        print("❌ No se pudo instalar PyInstaller")
        return

    if compilar():
        print("\n✨ Proceso completado exitosamente")
    else:
        print("\n⚠️  El proceso terminó con errores")

    input("\nPresiona Enter para cerrar...")


if __name__ == '__main__':
    main()
