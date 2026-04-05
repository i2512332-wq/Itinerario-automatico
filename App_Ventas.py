import streamlit as st
import sys
import datetime
from pathlib import Path
import subprocess
import socket
import time
import extra_streamlit_components as nsc

# --- AUTO-ARRANQUE DEL MOTOR FASTAPI (CEREBRO) ---
def ensure_backend_running():
    """Verifica si el motor FastAPI en el puerto 8000 está activo, si no, lo arranca."""
    port = 8000
    host = "127.0.0.1"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex((host, port)) == 0:
                return # Ya está corriendo
    except:
        pass
    
    # Si no está corriendo, lanzarlo en segundo plano
    try:
        # Usamos sys.executable para asegurar que use el mismo entorno de Streamlit
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app_api:app", "--host", host, "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2) # Breve espera para inicialización
    except Exception as e:
        st.error(f"Error crítico al arrancar el Motor de Lógica: {e}")

ensure_backend_running()

# Configurar path para imports relativos
sys.path.insert(0, str(Path(__file__).parent))

# Configuración de Página Global (Debe ser lo primero)
st.set_page_config(
    page_title="Constructor de Itinerarios",
    page_icon="assets/images/logo_background.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar Estilos Globales
def load_css():
    css_path = Path("assets/css/app_style.css")
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

# --- GESTIÓN DE COOKIES (PERSISTENCIA REFORZADA) ---
def get_manager():
    return nsc.CookieManager()

cookie_manager = get_manager()

# --- SEGURIDAD Y AUTO-LOGIN ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Solo intentar restaurar si no estamos ya autenticados en el estado actual
if not st.session_state.authenticated:
    # Pequeño buffer para que el componente JS de Cookies cargue
    # Usamos un mensaje sutil
    with st.status("Reconectando sesión...", expanded=False) as status:
        time.sleep(0.8) # Espera necesaria para el CookieManager
        existing_cookie = cookie_manager.get(cookie="latitud_session_token")
        
        if existing_cookie:
            try:
                st.session_state.authenticated = True
                st.session_state.user_email = existing_cookie.get("email")
                st.session_state.user_rol = existing_cookie.get("rol")
                st.session_state.vendedor_name = existing_cookie.get("nombre")
                status.update(label="✅ Sesión restaurada", state="complete")
                st.rerun()
            except Exception:
                status.update(label="⚠️ Error al restaurar", state="error")
        else:
            status.update(label="Pronto para iniciar", state="complete")

if not st.session_state.authenticated:
    from modules.auth.ui import render_login_ui
    render_login_ui(cookie_manager=cookie_manager)
else:
    # Sidebar de Usuario Autenticado
    with st.sidebar:
        user_email = st.session_state.get("user_email", "desconocido")
        user_rol = st.session_state.get("user_rol", "VENTAS")
        st.write(f"👤 **Usuario:** {user_email}")
        st.write(f"🛡️ **Rol:** {user_rol}")
        if st.button("Cerrar Sesión"):
            cookie_manager.delete("latitud_session_token")
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        
        # Módulos Disponibles para Todos
        st.markdown("### ⚙️ Administración")
        active_tab = st.radio("Selector de Módulo:", ["Itinerarios", "Catálogo Maestro"], index=0, help="Elige la herramienta a usar.")
        st.divider()
            
        st.caption("v2.5 - Catálogo Integrado 🚀")

    # Renderizar el módulo seleccionado
    if active_tab == "Catálogo Maestro":
        from modules.admin.ui_precios import render_admin_precios_ui
        render_admin_precios_ui()
    else:
        # Importar y renderizar el módulo de ventas
        from modules.ventas.ui import render_ventas_ui
        render_ventas_ui()
