import os
import subprocess
import sys
import base64
import json
try:
    import markdown
except ImportError:
    markdown = None
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# --- CONFIGURACIÓN ---
BASE_DIR = Path(__file__).parent.parent
TEMPLATE_DIR = BASE_DIR / "assets" / "templates"
CSS_FILE = BASE_DIR / "assets" / "css" / "report.css"
OUTPUT_FILENAME = "Itinerario_Ventas.pdf"

def find_image(path):
    """Busca la imagen en la ruta dada o en carpetas comunes si no se encuentra."""
    if not path: return None
    path_str = str(path)
    p = Path(path_str)
    
    # 1. Probar ruta tal cual
    if p.exists(): return p
    
    # 2. Probar ruta relativa al BASE_DIR
    # Limpiamos la ruta de posibles prefijos de Windows si estamos en Linux
    clean_filename = path_str.replace('\\', '/').split('/')[-1]
    p_rel = BASE_DIR / clean_filename
    if p_rel.exists(): return p_rel
    
    # 3. Buscar en todo el proyecto por nombre de archivo
    for root, dirs, files in os.walk(BASE_DIR):
        if clean_filename in files:
            return Path(root) / clean_filename
            
    return None

def get_image_as_base64(path):
    """Convierte imagen a Base64 asegurando compatibilidad total."""
    img_path = find_image(path)
    if not img_path:
        # Si no es un archivo local pero es una URL, devolverla tal cual
        if isinstance(path, str) and (path.startswith('http://') or path.startswith('https://')):
            return path
        return ""
    try:
        ext = img_path.suffix[1:].lower()
        mime = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            return f"data:{mime};base64,{b64}"
    except Exception as e:
        print(f"Error procesando {path}: {e}")
        return ""

def ensure_playwright_installed():
    """Asegura que Playwright y Chromium estén instalados en el entorno actual."""
    try:
        # Intentar ejecutar playwright para ver si está instalado
        subprocess.run(["playwright", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Playwright no encontrado. Instalando...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
    
    # Intentar instalar chromium si no existe
    try:
        print("Asegurando Chromium para Playwright...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        # En Linux (Streamlit Cloud), a veces se necesitan dependencias del sistema
        if sys.platform == "linux":
            subprocess.run([sys.executable, "-m", "playwright", "install-deps", "chromium"], check=False)
    except Exception as e:
        print(f"Aviso en instalación de Playwright: {e}")

def generate_pdf(itinerary_data, output_filename=OUTPUT_FILENAME):
    # Asegurar entorno Playwright
    ensure_playwright_installed()
    
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("report.html")
    
    # Cargar CSS
    css_content = ""
    if CSS_FILE.exists():
        with open(CSS_FILE, 'r', encoding='utf-8') as f:
            css_content = f.read()

    # Convertir TODAS las imágenes a Base64
    itinerary_data['logo_url'] = get_image_as_base64(itinerary_data.get('logo_url'))
    itinerary_data['logo_cover_url'] = get_image_as_base64(itinerary_data.get('logo_cover_url'))
    itinerary_data['cover_url'] = get_image_as_base64(itinerary_data.get('cover_url'))
    itinerary_data['llama_img'] = get_image_as_base64(itinerary_data.get('llama_img'))
    itinerary_data['llama_purchase_img'] = get_image_as_base64(itinerary_data.get('llama_purchase_img'))
    itinerary_data['train_exp_img'] = get_image_as_base64(itinerary_data.get('train_exp_img'))
    itinerary_data['train_vis_img'] = get_image_as_base64(itinerary_data.get('train_vis_img'))
    itinerary_data['train_obs_img'] = get_image_as_base64(itinerary_data.get('train_obs_img'))

    # Intentar importar markdown aquí por si se instaló después del arranque
    global markdown
    if markdown is None:
        try:
            import markdown as md
            markdown = md
        except ImportError:
            pass

    for day in itinerary_data.get('days', []):
        day['images'] = [get_image_as_base64(img) for img in day.get('images', [])]
        # Convertir descripción de Markdown a HTML si el import fue exitoso
        if markdown and day.get('descripcion'):
            # Usamos una conversión más robusta
            day['descripcion'] = markdown.markdown(str(day['descripcion']), extensions=['nl2br', 'sane_lists'])

    html_content = template.render(**itinerary_data)
    
    temp_html_path = BASE_DIR / "temp_report.html"
    with open(temp_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    output_path = BASE_DIR / output_filename
    script_path = BASE_DIR / "temp_pdf_script.py"
    
    # Usamos json.dumps para pasar el CSS de forma segura al script
    css_json = json.dumps(css_content)
    
    # Script Playwright
    script_content = f'''
import asyncio
import sys
import json
from playwright.async_api import async_playwright

async def main():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            html_file = r"{str(temp_html_path).replace(chr(92), '/')}"
            await page.goto(f"file://{{html_file}}", wait_until='load', timeout=60000)
            
            # Inyectar CSS de forma segura
            css_content = {css_json}
            await page.add_style_tag(content=css_content)
            
            # Forzamos estilos de iconos y pines
            extra_css = ".service-icon, .service-icon svg {{ width: 35px !important; height: 35px !important; }} .pin-icon {{ width: 45px !important; height: 45px !important; }}"
            await page.add_style_tag(content=extra_css)
            
            await asyncio.sleep(2)
            
            await page.pdf(
                path=r"{str(output_path).replace(chr(92), '/')}",
                format='A4',
                print_background=True,
                margin={{'top': '0', 'right': '0', 'bottom': '0', 'left': '0'}},
                prefer_css_page_size=True
            )
            await browser.close()
            print("PDF generado con éxito")
    except Exception as e:
        print(f"ERROR EN SCRIPT: {{e}}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
'''
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    try:
        # Ejecutar capturando errores
        result = subprocess.run(
            [sys.executable, str(script_path)], 
            capture_output=True, 
            text=True, 
            timeout=180
        )
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            raise Exception(f"Playwright falló: {error_msg}")
            
    finally:
        if temp_html_path.exists(): temp_html_path.unlink()
        if script_path.exists(): script_path.unlink()

    return str(output_path)
