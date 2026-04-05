import streamlit as st
import requests
import os
import io
import json
import uuid
import tempfile
from datetime import datetime, timedelta
import time
import locale
import re
import math
from pathlib import Path
from utils.pdf_generator import generate_pdf
from utils.supabase_db import (
    save_itinerary_v2,
    get_last_itinerary_by_phone,
    get_available_tours,
    get_available_packages,
    get_vendedores,
    save_custom_package,
    get_custom_packages,
    delete_custom_package,
    get_service_templates
)
from utils.translator import translate_itinerary

def get_image_folders_ventas():
    base_path = os.path.join("assets", "img", "tours")
    folders = ["general"]
    if os.path.exists(base_path):
        found = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
        for f in sorted(found):
            if f != "general":
                folders.append(f)
    return folders

# --- ELIMINADAS FUNCIONES DE PERSISTENCIA LOCAL (AHORA ES CLOUD) ---

# --- DICCIONARIO DE ICONOS SVG ---
ICON_MAP = {
    'transporte': '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-1.1 0-2 .9-2 2v7c0 1.1.9 2 2 2h2"></path><circle cx="7" cy="17" r="2"></circle><path d="M9 17h6"></path><circle cx="17" cy="17" r="2"></circle>',
    'traslado': '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-1.1 0-2 .9-2 2v7c0 1.1.9 2 2 2h2"></path><circle cx="7" cy="17" r="2"></circle><path d="M9 17h6"></path><circle cx="17" cy="17" r="2"></circle>',
    'guía': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>',
    'asistencia': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle>',
    'almuerzo': '<path d="M3 2v7c0 1.1.9 2 2 2h4V2"></path><path d="M7 2v20"></path><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"></path>',
    'alimentación': '<path d="M3 2v7c0 1.1.9 2 2 2h4V2"></path><path d="M7 2v20"></path><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"></path>',
    'ingreso': '<path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"></path><path d="M13 5v2"></path><path d="M13 17v2"></path><path d="M13 11v2"></path>',
    'boleto': '<path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"></path><path d="M13 5v2"></path><path d="M13 17v2"></path><path d="M13 11v2"></path>',
    'vuelo': '<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"></path>',
    'botiquín': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M9 12h6"/><path d="M12 9v6"/>',
    'oxígeno': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M9 12h6"/><path d="M12 9v6"/>',
    'propinas': '<line x1="12" y1="2" x2="12" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    'default_in': '<polyline points="20 6 9 17 4 12"></polyline>',
    'default_out': '<line x1="5" y1="12" x2="19" y2="12"></line>'
}

def get_svg_icon(text, default_key='default_in'):
    text_lower = text.lower()
    for key, svg in ICON_MAP.items():
        if key in text_lower:
            return svg
    return ICON_MAP[default_key]

def get_opciones_portadas():
    """Establece las portadas leyendo dinámicamente la carpeta assets/images/covers"""
    base_dir = os.getcwd()
    covers_path = os.path.join(base_dir, "assets", "images", "covers")
    
    opciones = {}
    if os.path.exists(covers_path):
        for file in os.listdir(covers_path):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Nombre amigable: "mi_portada_cusco.jpg" -> "Mi Portada Cusco"
                display_name = file.rsplit('.', 1)[0].replace('_', ' ').title()
                opciones[display_name] = (file, "TU PRÓXIMA", "AVENTURA")
    
    if not opciones:
        opciones["Portada Genérica"] = ("fallback_cover.jpg", "TU PRÓXIMA", "AVENTURA")
        
    return opciones

def format_tour_time(raw_time):
    """Convierte un string de tiempo técnico (ej. 08:00:00) a un formato amigable (ej. 08:00 AM)"""
    if not raw_time:
        return "08:00 AM"
    
    raw_str = str(raw_time).strip()
    if ':' in raw_str:
        try:
            parts = raw_str.split(':')
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            
            # Si ya tiene AM o PM, lo dejamos tal cual
            if 'AM' in raw_str.upper() or 'PM' in raw_str.upper():
                return raw_str
                
            if h >= 12:
                h_12 = h - 12 if h > 12 else 12
                return f"{h_12:02d}:{m:02d} PM"
            else:
                h_12 = h if h > 0 else 12
                return f"{h_12:02d}:{m:02d} AM"
        except:
            return raw_str
    return raw_str

def obtener_imagenes_tour(nombre_carpeta):
    """Obtiene las imágenes de un tour desde la carpeta assets/img/tours/"""
    base_path = Path(os.getcwd()) / 'assets' / 'img' / 'tours' / nombre_carpeta
    
    if not base_path.exists():
        # Fallback a carpeta general si existe
        general_path = Path(os.getcwd()) / 'assets' / 'img' / 'tours' / 'general'
        if general_path.exists():
            base_path = general_path
        else:
            return ["https://via.placeholder.com/400x300?text=Foto+Tour"] * 5
    
    imagenes = []
    if base_path.exists():
        for f in base_path.iterdir():
            if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
                imagenes.append(str(f.absolute()))
    
    while len(imagenes) < 5:
        imagenes.append("https://via.placeholder.com/400x300?text=Foto+Tour")
        
    return imagenes[:5]

def crear_dia_base(titulo="Día Personalizado", desc="", servicios=None, icons=None):
    """Crea la estructura base para un día manual o personalizado."""
    return {
        "id": str(uuid.uuid4()),
        "titulo": titulo,
        "descripcion": desc,
        "highlights": [titulo],
        "servicios": servicios if servicios else ["Asistencia personalizada"],
        "servicios_no_incluye": ["Gastos extras", "Propinas"],
        "costo_nac": 0.0,
        "costo_ext": 0.0,
        "costo_can": 0.0,
        "hora_inicio": "08:00 AM",
        "carpeta_img": "general"
    }

# --- UI PRINCIPAL ---
def render_ventas_ui():
    """Renderiza la interfaz de ventas"""
    
    # Helper para conversión de moneda (PEN/USD)
    def convert_val(monto, is_already_usd):
        # Tomar TC del session state o default 3.75
        tc_local = st.session_state.get('f_tc', 3.75)
        moneda_target = st.session_state.get('f_moneda_pdf', 'Mix')
        
        if moneda_target == "USD":
            return monto if is_already_usd else (monto / tc_local if tc_local > 0 else 0)
        elif moneda_target == "PEN":
            return (monto * tc_local) if is_already_usd else monto
        return monto

    image_folders = get_image_folders_ventas()
    
    # Esconder elementos de Streamlit (Header, Menu, Footer)
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .stAppDeployButton {display: none;}
            [data-testid="stStatusWidget"] {visibility: hidden;}
            #stDecoration {display:none;}
        </style>
    """, unsafe_allow_html=True)
    
    # Estado de sesión
    if 'itinerario' not in st.session_state:
        st.session_state.itinerario = []
    if 'origen_previo' not in st.session_state:
        st.session_state.origen_previo = "Nacional"
    
    # Inicialización explícita en cero para todo el grupo
    pax_keys_init = [
        'n_adultos_nac', 'n_estud_nac', 'n_pcd_nac', 'n_ninos_nac',
        'n_adultos_ext', 'n_estud_ext', 'n_pcd_ext', 'n_ninos_ext',
        'n_adultos_can', 'n_estud_can', 'n_pcd_can', 'n_ninos_can',
        'an_nac_uni', 'es_nac_uni', 'pcd_nac_uni', 'ni_nac_uni',
        'an_ext_uni', 'es_ext_uni', 'pcd_ext_uni', 'ni_ext_uni',
        'an_can_uni', 'es_can_uni', 'pcd_can_uni', 'ni_can_uni',
        'an_nac_mix', 'es_nac_mix', 'pcd_nac_mix', 'ni_nac_mix',
        'an_ext_mix', 'es_ext_mix', 'pcd_ext_mix', 'ni_ext_mix',
        'an_can_mix', 'es_can_mix', 'pcd_can_mix', 'ni_can_mix'
    ]
    for k in pax_keys_init:
        if k not in st.session_state:
            st.session_state[k] = 0

    # Campos del formulario controlados
    if 'f_vendedor' not in st.session_state: st.session_state.f_vendedor = ""
    if 'f_celular' not in st.session_state: st.session_state.f_celular = ""
    if 'f_fuente' not in st.session_state: st.session_state.f_fuente = "WhatsApp"
    if 'f_estado' not in st.session_state: st.session_state.f_estado = "Frío"
    if 'f_origen' not in st.session_state: st.session_state.f_origen = "Nacional"
    if 'f_categoria' not in st.session_state: st.session_state.f_categoria = "Cusco Tradicional"
    if 'f_tipo_cliente' not in st.session_state: st.session_state.f_tipo_cliente = "B2C"
    if 'f_nota_precio' not in st.session_state: st.session_state.f_nota_precio = "INCLUYE TOUR"
    if 'f_monto_adelanto' not in st.session_state: st.session_state.f_monto_adelanto = 0.0
    if 'f_monto_pendiente' not in st.session_state: st.session_state.f_monto_pendiente = 0.0
    if 'f_margen_porcentaje' not in st.session_state: st.session_state.f_margen_porcentaje = 30.0
    if 'f_margen_antes' not in st.session_state: st.session_state.f_margen_antes = 40.0
    if 'f_estrategia' not in st.session_state: st.session_state.f_estrategia = "Opciones"
    if 'u_h2' not in st.session_state: st.session_state.u_h2 = 40.0
    if 'u_h3' not in st.session_state: st.session_state.u_h3 = 70.0
    if 'u_h4' not in st.session_state: st.session_state.u_h4 = 110.0
    if 'u_h2_sol' not in st.session_state: st.session_state.u_h2_sol = 150.0
    if 'u_h3_sol' not in st.session_state: st.session_state.u_h3_sol = 260.0
    if 'u_h4_sol' not in st.session_state: st.session_state.u_h4_sol = 410.0

    if 'u_t_v' not in st.session_state: st.session_state.u_t_v = 90.0
    if 'u_t_o' not in st.session_state: st.session_state.u_t_o = 140.0
    if 'u_t_v_sol' not in st.session_state: st.session_state.u_t_v_sol = 340.0
    if 'u_t_o_sol' not in st.session_state: st.session_state.u_t_o_sol = 530.0
    if 'u_t_local' not in st.session_state: st.session_state.u_t_local = 0.0
    # Inicialización de Ajuste Global
    if 'f_extra_nac' not in st.session_state: st.session_state.f_extra_nac = 0.0
    if 'f_extra_ext' not in st.session_state: st.session_state.f_extra_ext = 0.0
    if 'f_extra_can' not in st.session_state: st.session_state.f_extra_can = 0.0
    if 'f_num_noches' not in st.session_state: st.session_state.f_num_noches = 0
    if 'f_nota_precio' not in st.session_state: st.session_state.f_nota_precio = "INCLUYE TOUR"
    # Verificar Conexión
    from utils.supabase_db import get_supabase_client
    if get_supabase_client() is None:
        st.warning("⚠️ El sistema no está conectado a Supabase (El Cerebro). Configura el archivo .env para habilitar el seguimiento de leads.")

    st.markdown("""
        <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
            <img src='data:image/x-icon;base64,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' style='width: 45px; margin-right: 15px;'>
            <h1 style='margin: 0;'>Constructor de Itinerarios Premium</h1>
        </div>
    """, unsafe_allow_html=True)
    st.write("Interfaz exclusiva para el equipo de ventas de Viajes Cusco Perú.")
    
    # 0. Cargar Catálogo desde Supabase (Cacheado en sesión)
    if not st.session_state.get('catalogo_tours') or not st.session_state.get('catalogo_paquetes') or not st.session_state.get('lista_vendedores') or st.sidebar.button("🔄 Refrescar Catálogo"):
        with st.spinner("Cargando catálogo desde el Cerebro..."):
            st.session_state.catalogo_tours = get_available_tours()
            st.session_state.catalogo_paquetes = get_available_packages()
            st.session_state.lista_vendedores = get_vendedores()
            
            nt = len(st.session_state.catalogo_tours) if st.session_state.catalogo_tours else 0
            np = len(st.session_state.catalogo_paquetes) if st.session_state.catalogo_paquetes else 0
            nv = len(st.session_state.lista_vendedores) if st.session_state.lista_vendedores else 0
            
            if nt == 0:
                st.sidebar.error("⚠️ No hay tours en Supabase.")
            else:
                st.sidebar.success(f"✅ {nt} tours, {np} paquetes y {nv} vendedores listos.")
    
    tours_db = st.session_state.get('catalogo_tours', [])
    paquetes_db = st.session_state.get('catalogo_paquetes', [])
    vendedores_db = st.session_state.get('lista_vendedores', [])

    # SIDEBAR: PAQUETES CLOUD (Mejorado y Visible)
    with st.sidebar:
        st.header("☁️ Mis Paquetes en la Nube")
        
        with st.expander("✨ Guardar Itinerario Actual", expanded=True):
            nombre_p = st.text_input("Nombre del paquete", key="cloud_pkg_name", placeholder="Ej: Machu Picchu VIP 3D")
            es_pub = st.toggle("Compartir con el equipo", value=True, help="Si se activa, otros vendedores podrán ver y usar este paquete.")
            if st.button("💾 Guardar en la Nube", use_container_width=True):
                if nombre_p and st.session_state.itinerario:
                    with st.spinner("Guardando..."):
                        success = save_custom_package(nombre_p, st.session_state.itinerario, st.session_state.get("user_email"), es_pub)
                        if success:
                            st.success(f"¡'{nombre_p}' guardado exitosamente!")
                            st.rerun()
                        else:
                            st.error("Hubo un error al guardar en la nube.")
                else:
                    st.warning("Escribe un nombre y agrega tours primero.")
        
        st.divider()
        
        cloud_pkgs = get_custom_packages(st.session_state.get("user_email"))
        if cloud_pkgs:
            st.subheader("📂 Paquetes del Equipo")
            for cp in cloud_pkgs:
                with st.container(border=True):
                    col_p1, col_p2 = st.columns([4, 1])
                    with col_p1:
                        badge = "🔒 **[Privado]** " if not cp.get('es_publico') else ""
                        st.markdown(f"{badge}**{cp['nombre']}**")
                        st.caption(f"Por: {cp['creado_por'].split('@')[0] if cp['creado_por'] else 'Anon'}")
                    with col_p2:
                        # Botón cargar
                        if st.button("🚀", key=f"load_{cp['id_paquete_personalizado']}", help="Cargar este paquete"):
                            st.session_state.itinerario = cp['itinerario']
                            st.success(f"Cargado: {cp['nombre']}")
                            st.rerun()
                        # Botón eliminar (solo si es el creador o admin)
                        is_owner = cp['creado_por'] == st.session_state.get("user_email")
                        is_admin = st.session_state.get("user_rol") == "ADMIN"
                        if is_owner or is_admin:
                            if st.button("🗑️", key=f"del_{cp['id_paquete_personalizado']}", help="Eliminar paquete"):
                                if delete_custom_package(cp['id_paquete_personalizado']):
                                    st.success("Paquete eliminado.")
                                    st.rerun()
        else:
            st.caption("No hay paquetes guardados en la nube aún.")
        
        st.divider()

    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("👤 Datos del Pasajero")
        
        nombre = st.text_input("Nombre Completo del Cliente", value=st.session_state.get('f_nombre', ''), placeholder="Ej: Juan Pérez")
        st.session_state.f_nombre = nombre

        ld_col1, ld_col2 = st.columns([1, 1])
        
        with ld_col1:
            # Canal
            idx_t = 0 if st.session_state.f_tipo_cliente == "B2C" else 1
            tipo_c = st.selectbox("Canal de Venta", ["B2C (Directo)", "B2B (Agencia)"], index=idx_t)
            st.session_state.f_tipo_cliente = "B2C" if "B2C" in tipo_c else "B2B"

            # Fuente
            fuente_list = ["WhatsApp", "Facebook Ads", "Instagram Ads", "Google Ads", "Web Site", "Recomendado", "Otros"]
            idx_f = fuente_list.index(st.session_state.f_fuente) if st.session_state.f_fuente in fuente_list else 0
            origen_lead = st.selectbox("Fuente del Lead", fuente_list, index=idx_f)
            
        with ld_col2:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True) # Espaciado 
            estrategias = ["Opciones", "Matriz", "General"]
            idx_e = estrategias.index(st.session_state.f_estrategia) if st.session_state.f_estrategia in estrategias else 0
            estrategia_v = st.radio("Estrategia de Venta", estrategias, index=idx_e, horizontal=True)
            st.session_state.f_estrategia = estrategia_v

            # --- SELECTOR DE MONEDA GLOBAL ---
            currency_display = st.selectbox("🌐 Moneda de Presentación", ["Soles (S/)", "Dólares ($)", "Moneda Original (S/ y $)"], 
                                          index=0 if st.session_state.get('f_moneda_pdf') == "Soles (S/)" else (1 if st.session_state.get('f_moneda_pdf') == "Dólares ($)" else 2),
                                          key="sel_curr_global",
                                          help="Elija la moneda en la que se mostrarán los precios en el PDF. 'Original' mantiene S/ para nacionales y $ para extranjeros.")
            st.session_state.f_moneda_pdf = currency_display

            if estrategia_v == "Matriz":
                # Inyectar CSS para asegurar visibilidad del texto en multiselect
                st.markdown("""
                    <style>
                    span[data-baseweb="tag"] {
                        background-color: #e63946 !important;
                        color: white !important;
                    }
                    span[data-baseweb="tag"] span {
                        color: white !important;
                    }
                    </style>
                """, unsafe_allow_html=True)

                options_h = ["Sin Hotel", "Hotel 2*", "Hotel 3*", "Hotel 4*"]
                options_t = ["Tren Local", "Expedition", "Vistadome", "Observatory"]
                
                # Forzar inicialización limpia si hay inconsistencias
                if 'cats_activas' not in st.session_state or not st.session_state.cats_activas:
                    st.session_state.cats_activas = options_h
                if 'trenes_activos' not in st.session_state or not st.session_state.trenes_activos:
                    st.session_state.trenes_activos = options_t
                
                # Usar columnas más anchas o quitarlas si persiste el problema
                cats_activas = st.multiselect("Hoteles en PDF", options_h, default=[x for x in st.session_state.cats_activas if x in options_h], key="ms_cats_v2")
                trenes_activos = st.multiselect("Trenes en PDF", options_t, default=[x for x in st.session_state.trenes_activos if x in options_t], key="ms_trenes_v2")
                
                st.session_state.cats_activas = cats_activas
                st.session_state.trenes_activos = trenes_activos

        # El vendedor se obtiene automáticamente de la sesión
        vendedor = st.session_state.get("vendedor_name", "Anonimo")
        
        cel1, cel2 = st.columns([4, 1])
        celular = cel1.text_input("Celular del Cliente *", value=st.session_state.f_celular, placeholder="Ej: 9XX XXX XXX")
        st.session_state.f_celular = celular
        
        cel2.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if cel2.button("🔍", key="search_phone"):
            if celular:
                with st.spinner("Buscando por celular..."):
                    last_data = get_last_itinerary_by_phone(celular)
                    if last_data:
                        datos_completos = last_data.get("datos_render", {})
                        st.session_state.f_nombre = datos_completos.get("pasajero", "")
                        st.session_state.f_vendedor = datos_completos.get("vendedor", "")
                        st.session_state.f_fuente = datos_completos.get("fuente", "WhatsApp")
                        st.session_state.f_estrategia = datos_completos.get("estrategia", "Opciones")
                        st.session_state.f_origen = datos_completos.get("categoria", "Nacional")
                        
                        if datos_completos and 'days' in datos_completos:
                             new_it = []
                             for d in datos_completos['days']:
                                 # 1. Intentar buscar metadatos en el catálogo oficial (como la carpeta_img)
                                 t_catalog = next((t for t in tours_db if t.get('titulo') == d.get('titulo')), None)
                                 
                                 # 2. Reconstruir con PRIORIDAD a lo guardado en el PDF (lo que el vendedor editó)
                                 tour_obj = {
                                     "id": d.get('id_original', str(uuid.uuid4())),
                                     "titulo": d.get('titulo', 'Día Cargado'),
                                     "descripcion": d.get('descripcion', ''),
                                     # Convertir servicios de [{texto, svg}] a lista simple de textos
                                     "servicios": [s['texto'] for s in d.get('servicios', [])] if isinstance(d.get('servicios'), list) and d.get('servicios') and isinstance(d.get('servicios')[0], dict) else d.get('servicios', []),
                                     "servicios_no_incluye": d.get('servicios_no_incluye', [s['texto'] for s in d.get('servicios_no', [])] if d.get('servicios_no') else []),
                                     "costo_nac": float(d.get('costo_nac', 0)),
                                     "costo_ext": float(d.get('costo_ext', 0)),
                                     "costo_can": float(d.get('costo_can', 0)),
                                     "costo_nac_est": float(d.get('costo_nac_est', float(d.get('costo_nac', 0))-70)),
                                     "costo_nac_nino": float(d.get('costo_nac_nino', float(d.get('costo_nac', 0))-40)),
                                     "costo_ext_est": float(d.get('costo_ext_est', float(d.get('costo_ext', 0))-20)),
                                     "costo_ext_nino": float(d.get('costo_ext_nino', float(d.get('costo_ext', 0))-15)),
                                     "costo_can_est": float(d.get('costo_can_est', float(d.get('costo_can', 0))-20)),
                                     "costo_can_nino": float(d.get('costo_can_nino', float(d.get('costo_can', 0))-15)),
                                     "hora_inicio": d.get('hora_inicio', '08:00 AM'),
                                     "carpeta_img": t_catalog.get('carpeta_img', 'general') if t_catalog else 'general'
                                 }
                                 new_it.append(tour_obj)
                                     
                             st.session_state.itinerario = new_it
                        
                        st.success(f"¡Datos de {st.session_state.f_nombre} cargados!")
                        st.rerun()
                    else:
                        st.warning("No se encontraron registros previos.")
        
        t_col1, t_col2 = st.columns(2)
        idx_o = 0
        if "Extranjero" in st.session_state.f_origen: idx_o = 1
        elif "Mixto" in st.session_state.f_origen: idx_o = 2
        
        tipo_t = t_col1.radio("Origen", ["Nacional", "Extranjero", "Mixto"], index=idx_o)
        st.session_state.f_origen = tipo_t
        modo_s = "Sistema Pool" # Definimos por defecto para evitar errores en el PDF
        # es_pool = (modo_s == "Sistema Pool") # Mantenemos modo_edicion individual
        
        # Actualizar precios al cambiar origen
        if tipo_t != st.session_state.origen_previo:
            for tour in st.session_state.itinerario:
                # Sincronizar con catálogo si ha cambiado el precio maestro
                t_base = next((t for t in tours_db if t['nombre'] == tour.get('titulo', tour.get('nombre'))), None)
                if t_base:
                    tour['costo'] = t_base['precio_adulto_nacional'] if "Nacional" in tipo_t else t_base['precio_adulto_extranjero']
            st.session_state.origen_previo = tipo_t
            st.rerun()
        
        st.markdown("#### 👥 Composición del Grupo")
        
        if tipo_t == "Nacional":
            # Caso simple: Solo nacionales
            p_col_n = st.columns([1, 2])[0]
            with p_col_n:
                st.caption("🇵🇪 NACIONALES")
                n_adultos_nac = st.number_input("👤 Adultos", min_value=0, step=1, key="an_nac_uni")
                n_estud_nac = st.number_input("🎓 Estudiantes", min_value=0, step=1, key="es_nac_uni")
                n_pcd_nac = st.number_input("♿ PcD", min_value=0, step=1, key="pcd_nac_uni")
                n_ninos_nac = st.number_input("👶 Niños", min_value=0, step=1, key="ni_nac_uni")
            
            # Los otros se quedan con lo que tenían en la sesión o en 0 si no existen
            n_adultos_ext = int(st.session_state.get('n_adultos_ext', 0))
            n_estud_ext = int(st.session_state.get('n_estud_ext', 0))
            n_pcd_ext = int(st.session_state.get('n_pcd_ext', 0))
            n_ninos_ext = int(st.session_state.get('n_ninos_ext', 0))
            
            n_adultos_can = int(st.session_state.get('n_adultos_can', 0))
            n_estud_can = int(st.session_state.get('n_estud_can', 0))
            n_pcd_can = int(st.session_state.get('n_pcd_can', 0))
            n_ninos_can = int(st.session_state.get('n_ninos_can', 0))
            
        elif tipo_t == "Extranjero":
            # Caso "Extranjero": Muestra solo Extranjeros y CAN
            p_col1, p_col2 = st.columns(2)
            
            with p_col1:
                st.caption("🌎 EXTRANJEROS")
                n_adultos_ext = st.number_input("👤 Adultos", min_value=0, step=1, key="an_ext_uni")
                n_estud_ext = st.number_input("🎓 Estudiantes", min_value=0, step=1, key="es_ext_uni")
                n_pcd_ext = st.number_input("♿ PcD", min_value=0, step=1, key="pcd_ext_uni")
                n_ninos_ext = st.number_input("👶 Niños", min_value=0, step=1, key="ni_ext_uni")

            with p_col2:
                st.caption("🤝 CAN")
                n_adultos_can = st.number_input("👤 Adultos ", min_value=0, step=1, key="an_can_uni")
                n_estud_can = st.number_input("🎓 Estudiantes ", min_value=0, step=1, key="es_can_uni")
                n_pcd_can = st.number_input("♿ PcD ", min_value=0, step=1, key="pcd_can_uni")
                n_ninos_can = st.number_input("👶 Niños ", min_value=0, step=1, key="ni_can_uni")
            
            # Los nacionales se quedan con lo que tenían en la sesión
            n_adultos_nac = int(st.session_state.get('n_adultos_nac', 0))
            n_estud_nac = int(st.session_state.get('n_estud_nac', 0))
            n_pcd_nac = int(st.session_state.get('n_pcd_nac', 0))
            n_ninos_nac = int(st.session_state.get('n_ninos_nac', 0))
        else:
            # Caso "Mixto": Muestra todos
            p_col_m1, p_col_m2, p_col_m3 = st.columns(3)
            with p_col_m1:
                st.caption("🇵🇪 NACIONALES")
                n_adultos_nac = st.number_input("👤 Adultos", min_value=0, step=1, key="an_nac_mix")
                n_estud_nac = st.number_input("🎓 Estudiantes", min_value=0, step=1, key="es_nac_mix")
                n_pcd_nac = st.number_input("♿ PcD", min_value=0, step=1, key="pcd_nac_mix")
                n_ninos_nac = st.number_input("👶 Niños", min_value=0, step=1, key="ni_nac_mix")
            with p_col_m2:
                st.caption("🌎 EXTRANJEROS")
                n_adultos_ext = st.number_input("👤 Adultos", min_value=0, step=1, key="an_ext_mix")
                n_estud_ext = st.number_input("🎓 Estudiantes", min_value=0, step=1, key="es_ext_mix")
                n_pcd_ext = st.number_input("♿ PcD", min_value=0, step=1, key="pcd_ext_mix")
                n_ninos_ext = st.number_input("👶 Niños", min_value=0, step=1, key="ni_ext_mix")
            with p_col_m3:
                st.caption("🤝 CAN")
                n_adultos_can = st.number_input("👤 Adultos ", min_value=0, step=1, key="an_can_mix")
                n_estud_can = st.number_input("🎓 Estudiantes ", min_value=0, step=1, key="es_can_mix")
                n_pcd_can = st.number_input("♿ PcD ", min_value=0, step=1, key="pcd_can_mix")
                n_ninos_can = st.number_input("👶 Niños ", min_value=0, step=1, key="ni_can_mix")

        # Persistencia obligatoria de todos los valores para el cálculo en página
        st.session_state.n_adultos_nac = n_adultos_nac
        st.session_state.n_estud_nac = n_estud_nac
        st.session_state.n_pcd_nac = n_pcd_nac
        st.session_state.n_ninos_nac = n_ninos_nac
        
        st.session_state.n_adultos_ext = n_adultos_ext
        st.session_state.n_estud_ext = n_estud_ext
        st.session_state.n_pcd_ext = n_pcd_ext
        st.session_state.n_ninos_ext = n_ninos_ext
        
        st.session_state.n_adultos_can = n_adultos_can
        st.session_state.n_estud_can = n_estud_can
        st.session_state.n_pcd_can = n_pcd_can
        st.session_state.n_ninos_can = n_ninos_can

        
        total_pasajeros = (n_adultos_nac + n_estud_nac + n_pcd_nac + n_ninos_nac + 
                           n_adultos_ext + n_estud_ext + n_pcd_ext + n_ninos_ext + 
                           n_adultos_can + n_estud_can + n_pcd_can + n_ninos_can)
        st.info(f"Total personas: {total_pasajeros}")
        
        # --- NUEVA SECCIÓN: DISTRIBUCIÓN DE HABITACIONES ---
        with st.expander("🛏️ Distribución de Habitaciones", expanded=total_pasajeros > 0):
            st.caption("Define cómo se distribuirá el grupo en las habitaciones.")
            rdr1_1, rdr1_2, rdr1_3 = st.columns(3)
            n_sgl = rdr1_1.number_input("Simple (1p)", min_value=0, step=1, key="f_n_sgl")
            n_dbl = rdr1_2.number_input("Doble Twin (2p)", min_value=0, step=1, key="f_n_dbl")
            n_mat = rdr1_3.number_input("Matrimonial (2p)", min_value=0, step=1, key="f_n_mat")
            
            rdr2_1, rdr2_2, _ = st.columns(3)
            n_tpl = rdr2_1.number_input("Triple (3p)", min_value=0, step=1, key="f_n_tpl")
            n_cua = rdr2_2.number_input("Cuádruple (4p)", min_value=0, step=1, key="f_n_cua")
            
            pax_en_habitaciones = (n_sgl * 1) + (n_dbl * 2) + (n_mat * 2) + (n_tpl * 3) + (n_cua * 4)
            if pax_en_habitaciones != total_pasajeros:
                st.warning(f"⚠️ La distribución ({pax_en_habitaciones} pax) no coincide con el total de pasajeros ({total_pasajeros} pax).")
            else:
                st.success(f"✅ Distribución correcta para {total_pasajeros} pasajeros.")
        
        
        col_date1, col_date2 = st.columns([2, 1])
        fecha_inicio = col_date1.date_input("📅 Fecha de Inicio del Viaje", datetime.now())
        usa_fechas = col_date2.checkbox("¿Ver fechas?", value=st.session_state.get('f_usa_fechas', True), key="f_usa_fechas", help="Si se desactiva, el PDF dirá 'DÍA 1' en lugar de fechas exactas.")
        
        # Calculamos la fecha fin automáticamente basada en el número de días
        num_dias = len(st.session_state.itinerario)
        fecha_fin = fecha_inicio + timedelta(days=max(0, num_dias - 1))
        # Rango para la portada
        if usa_fechas:
            rango_fechas = f"{fecha_inicio.strftime('%d/%m')} al {fecha_fin.strftime('%d/%m, %Y')}"
        else:
            if num_dias == 1:
                rango_fechas = "1 DÍA"
            else:
                rango_fechas = f"{num_dias} DÍAS / {max(0, num_dias-1)} NOCHES"

        # --- ELIMINADA SECCIÓN ANTIGUA DE PAQUETES LOCALES ---
        
        st.divider()
        
        st.subheader("🎁 Cargar Paquete Sugerido")
        
        # --- SELECTOR DE PORTADA (Global) ---
        opciones_portadas = get_opciones_portadas()

        portada_sel = st.selectbox(
            "🖼️ Elija Portada para el PDF",
            list(opciones_portadas.keys()),
            key="user_selected_cover" # Streamlit recordará automáticamente esta selección
        )
        
        # Eliminar lógica de Línea de Producto, cargar todos los paquetes directamente
        if paquetes_db:
            opciones_pkg = {p['nombre']: p for p in paquetes_db}
            pkg_name_sel = st.selectbox("📦 Seleccione el Paquete", list(opciones_pkg.keys()))
            
            if st.button("🚀 Cargar Itinerario", use_container_width=True):
                pkg_final = opciones_pkg.get(pkg_name_sel)
                if pkg_final:
                    # Guardar la imagen de portada asignada al paquete
                    st.session_state.f_package_img = pkg_final.get('carpeta_img', 'general')
                    found_tours = []
                    missing_tours = []
                    for t_n in pkg_final['tours']:
                        # Búsqueda robusta (sin espacios, sin mayúsculas/minúsculas)
                        t_f = next((t for t in tours_db if t['nombre'].strip().upper() == t_n.strip().upper()), None)
                        if t_f:
                            nuevo_t = t_f.copy()
                            # Mapeo de paridad: SQL -> Sesión de ventas
                            nuevo_t['titulo'] = t_f.get('nombre')
                            cn = float(t_f.get('precio_adulto_nacional', 0))
                            ce = float(t_f.get('precio_adulto_extranjero', 0))
                            nuevo_t['costo_nac'] = cn
                            nuevo_t['costo_nac_est'] = float(t_f.get('precio_estudiante_nacional', cn - 70.0))
                            nuevo_t['costo_nac_pcd'] = float(t_f.get('precio_pcd_nacional', cn - 70.0))
                            nuevo_t['costo_nac_nino'] = float(t_f.get('precio_nino_nacional', cn - 40.0))
                            
                            nuevo_t['costo_ext'] = ce
                            nuevo_t['costo_ext_est'] = float(t_f.get('precio_estudiante_extranjero', ce - 20.0))
                            nuevo_t['costo_ext_pcd'] = float(t_f.get('precio_pcd_extranjero', ce - 20.0))
                            nuevo_t['costo_ext_nino'] = float(t_f.get('precio_nino_extranjero', ce - 15.0))

                            if "MACHU PICCHU" in t_f['nombre'].upper():
                                cc = float(t_f.get('precio_adulto_can', ce - 20.0))
                            else:
                                cc = float(t_f.get('precio_adulto_can', ce))
                            
                            nuevo_t['costo_can'] = cc
                            nuevo_t['costo_can_est'] = float(t_f.get('precio_estudiante_can', cc - 20.0))
                            nuevo_t['costo_can_pcd'] = float(t_f.get('precio_pcd_can', cc - 20.0))
                            nuevo_t['costo_can_nino'] = float(t_f.get('precio_nino_can', cc - 15.0))
                            
                            # MAPEO DE TEXTOS (SQL -> Ventas Session)
                            nuevo_t['descripcion'] = t_f.get('itinerario_texto', '')
                            nuevo_t['servicios'] = t_f.get('servicios_incluidos', [])
                            nuevo_t['servicios_no_incluye'] = t_f.get('servicios_no_incluidos', [])
                            nuevo_t['hora_inicio'] = t_f.get('hora_inicio', '08:00 AM')
                            
                            # ID único para persistencia de widgets
                            if 'id' not in nuevo_t:
                                nuevo_t['id'] = str(uuid.uuid4())
                                
                            found_tours.append(nuevo_t)
                        else:
                            missing_tours.append(t_n)
                    
                    if found_tours:
                        st.session_state.itinerario = found_tours
                        # st.session_state.f_categoria ya no se actualiza porque "Línea de Producto" no existe
                        if missing_tours:
                            st.warning(f"⚠️ Algunos tours no se encontraron en el catálogo general: {', '.join(missing_tours)}")
                        st.success(f"✅ Paquete '{pkg_final['nombre']}' cargado con {len(found_tours)} tours.")
                        st.rerun()
                    else:
                        st.error(f"❌ Error: El paquete '{pkg_final['nombre']}' quiere cargar estos tours: {pkg_final['tours']}, pero ninguno coincide con los {len(tours_db)} tours que hay en la base de datos.")
                        if st.button("🔧 Forzar Sincronización"):
                            st.session_state.catalogo_tours = None
                            st.rerun()
                else:
                    st.error("❌ Error al identificar el paquete seleccionado.")
        
        st.subheader("📍 Agregar Tour Individual")
        tour_nombres = [t['nombre'] for t in tours_db]
        tour_sel = st.selectbox("Seleccione un tour", ["-- Seleccione --"] + tour_nombres)
        if tour_sel != "-- Seleccione --" and st.button("Agregar Tour"):
            t_data = next((t for t in tours_db if t['nombre'] == tour_sel), None)
            if t_data:
                nuevo_t = t_data.copy()
                nuevo_t['titulo'] = t_data.get('nombre')
                cn = float(t_data.get('precio_adulto_nacional', 0))
                ce = float(t_data.get('precio_adulto_extranjero', 0))
                nuevo_t['costo_nac'] = cn
                nuevo_t['costo_nac_est'] = float(t_data.get('precio_estudiante_nacional') or (cn - 70.0))
                nuevo_t['costo_nac_pcd'] = float(t_data.get('precio_pcd_nacional') or (cn - 70.0))
                nuevo_t['costo_nac_nino'] = float(t_data.get('precio_nino_nacional') or (cn - 40.0))
                nuevo_t['costo_ext'] = ce
                nuevo_t['costo_ext_est'] = float(t_data.get('precio_estudiante_extranjero') or (ce - 20.0))
                nuevo_t['costo_ext_pcd'] = float(t_data.get('precio_pcd_extranjero') or (ce - 20.0))
                nuevo_t['costo_ext_nino'] = float(t_data.get('precio_nino_extranjero') or (ce - 15.0))

                if "MACHU PICCHU" in t_data['nombre'].upper():
                    cc = float(t_data.get('precio_adulto_can') or (ce - 20.0))
                else:
                    cc = float(t_data.get('precio_adulto_can') or ce)
                
                nuevo_t['costo_can'] = cc
                nuevo_t['costo_can_est'] = float(t_data.get('precio_estudiante_can') or (cc - 20.0))
                nuevo_t['costo_can_pcd'] = float(t_data.get('precio_pcd_can') or (cc - 20.0))
                nuevo_t['costo_can_nino'] = float(t_data.get('precio_nino_can') or (cc - 15.0))
                
                # MAPEO DE TEXTOS (SQL -> Ventas Session)
                nuevo_t['descripcion'] = t_data.get('itinerario_texto', '')
                nuevo_t['servicios'] = t_data.get('servicios_incluidos', [])
                nuevo_t['servicios_no_incluye'] = t_data.get('servicios_no_incluidos', [])
                nuevo_t['hora_inicio'] = t_data.get('hora_inicio', '08:00 AM')
                
                # ID único para persistencia de widgets
                nuevo_t['id'] = str(uuid.uuid4())
                
                st.session_state.itinerario.append(nuevo_t)
                st.rerun()
        
        st.subheader("✨ Servicios Rápidos / Personalizados")
        
        c_p1, c_p2 = st.columns([1, 1])
        
        with c_p1:
            if st.button("➕ Agregar Día en Blanco", use_container_width=True, help="Añade un día vacío para que escribas lo que quieras."):
                nuevo_d = crear_dia_base()
                st.session_state.itinerario.append(nuevo_d)
                # Activar edición para el nuevo día
                st.session_state[f"mod_edit_{nuevo_d['id']}"] = True
                st.rerun()
        
        with c_p2:
            db_templates = get_service_templates()
            quick_opt_map = {t['titulo']: t for t in db_templates}
            quick_names = ["-- Seleccione Plantilla --"] + list(quick_opt_map.keys())
            
            q_sel = st.selectbox("Plantillas Rápidas", quick_names, label_visibility="collapsed")
            
            if q_sel != "-- Seleccione Plantilla --":
                if st.button("⚡ Aplicar Plantilla", use_container_width=True):
                    template_data = quick_opt_map[q_sel]
                    
                    nuevo_d = crear_dia_base(
                        titulo=template_data['titulo'],
                        desc=template_data.get('descripcion', "")
                    )
                    # Opcional: Si la plantilla tiene precios, podrías asignarlos aquí
                    nuevo_d['costo_nac'] = float(template_data.get('costo_nac', 0.0))
                    nuevo_d['costo_ext'] = float(template_data.get('costo_ext', 0.0))
                    
                    st.session_state.itinerario.append(nuevo_d)
                    st.session_state[f"mod_edit_{nuevo_d['id']}"] = True
                    st.rerun()
    
    with col2:
        st.subheader("📋 Plan de Viaje Actual")
        
        total_nac_pp = 0
        total_ext_pp = 0
        total_can_pp = 0
        
        # El modo de edición ahora es individual por cada tour
        
        if not st.session_state.itinerario:
            st.info("El itinerario está vacío. Comienza cargando un paquete o un tour individual.")
        else:
            # Obtener factores de margen para visualización
            m_pct_view = st.session_state.get('f_margen_porcentaje', 0.0)
            f_m_view = 1 + (m_pct_view / 100)
            
            m_antes_view = st.session_state.get('f_margen_antes', 0.0)
            f_m_antes_view = 1 + (m_antes_view / 100)

            for i, tour in enumerate(st.session_state.itinerario):
                total_nac_pp += tour.get('costo_nac', 0)
                total_ext_pp += tour.get('costo_ext', 0)
                total_can_pp += tour.get('costo_can', 0)
                
                tour_id = tour.get('id', str(uuid.uuid4()))
                tour['id'] = tour_id # Asegurar que esté guardado
                
                c_content, c_btns = st.columns([0.88, 0.12])
                
                with c_content:
                    es_mp = "MACHU PICCHU" in tour.get('titulo', '').upper()
                    
                    current_date = fecha_inicio + timedelta(days=i)
                    date_str = current_date.strftime('%d/%m/%Y')
                    header_icon = "⭐" if modo_s == "B2B" else "📍" 
                    
                    # Precios marginados para el encabezado (Redondeo solicitado)
                    p_nac_m = math.ceil(tour.get('costo_nac', 0) * f_m_view)
                    p_ext_m = math.ceil(tour.get('costo_ext', 0) * f_m_view)
                    p_can_m = math.ceil(tour.get('costo_can', 0) * f_m_view)
                    
                    # Precios "Antes" para visualización (Redondeo solicitado)
                    p_nac_a = math.ceil(tour.get('costo_nac', 0) * f_m_antes_view)
                    p_ext_a = math.ceil(tour.get('costo_ext', 0) * f_m_antes_view)
                    
                    show_antes = m_antes_view > m_pct_view
                    
                    p_nac_str = f"S/ {p_nac_m:,.2f}"
                    if show_antes: p_nac_str = f"~~S/ {p_nac_a:,.2f}~~ {p_nac_str}"
                    
                    p_ext_str = f"$ {p_ext_m:,.2f}"
                    if show_antes: p_ext_str = f"~~$ {p_ext_a:,.2f}~~ {p_ext_str}"

                    header_text = f"✨ {date_str} - DÍA {i+1}: {tour['titulo']} - ({p_nac_str} | {p_ext_str})"
                    if es_mp:
                        p_can_str = f"CAN $ {p_can_m:,.2f}"
                        # Para CAN no solemos mostrar antes para no saturar, pero si es necesario se añade
                        header_text = f"✨ {date_str} - DÍA {i+1}: {tour['titulo']} - ({p_nac_str} | {p_ext_str} | {p_can_str})"
                    
                    with st.expander(header_text, expanded=False):
                        # Control de edición manual para este día específico
                        modo_edicion = st.toggle("🔧 Modificar datos de este día", key=f"mod_edit_{tour_id}")
                        is_disabled = not modo_edicion
                        
                        if es_mp:
                            col_t1, col_n, col_e, col_c, col_h = st.columns([1.5, 0.6, 0.6, 0.6, 0.6])
                            tour['titulo'] = col_t1.text_input(f"Título día {i+1}", tour['titulo'], key=f"title_{tour_id}", disabled=is_disabled)
                            tour['hora_inicio'] = col_h.text_input(f"⏰ Hora", value=tour.get('hora_inicio', '08:00 AM'), key=f"hi_{tour_id}", disabled=is_disabled)
                            # Control de visibilidad de hora
                            tour['mostrar_hora'] = st.toggle("👁️ Mostrar hora en PDF", value=tour.get('mostrar_hora', True), key=f"v_h_{tour_id}", disabled=is_disabled)
                            
                            tour['costo_nac'] = col_n.number_input(f"Nac (S/)", value=float(tour.get('costo_nac', 0)), key=f"cn_{tour_id}", disabled=is_disabled)
                            tour['costo_ext'] = col_e.number_input(f"Ext ($)", value=float(tour.get('costo_ext', 0)), key=f"ce_{tour_id}", disabled=is_disabled)
                            tour['costo_can'] = col_c.number_input(f"CAN ($)", value=float(tour.get('costo_can', 0)), key=f"cc_{tour_id}", disabled=is_disabled)
                            
                            # Margen individual por tour opcional
                            tour['usar_margen_propio'] = col_h.checkbox("Activar Margen", value=tour.get('usar_margen_propio', False), key=f"use_m_{tour_id}", disabled=is_disabled)
                            tour['margen_individual'] = col_h.number_input(f"% Margen", value=float(tour.get('margen_individual', m_pct_view)), step=1.0, key=f"margen_{tour_id}", disabled=not tour.get('usar_margen_propio') or is_disabled, help="Si está activado, usa este margen. Si no, usa el global.")
                            
                            st.markdown("---")
                            # Campo movido a la sección de resumen global abajo
                            
                            # --- Suplementos de Tren (Localizados en MP) ---
                            st.markdown("🚅 **Suplementos de Tren (Manual)**")
                            
                            # Layout con columnas para Soles y Dólares
                            ct_labels, ct_sol, ct_usd = st.columns([1, 1.5, 1.5])
                            
                            ct_labels.markdown("<div style='height: 35px;'></div>Vistadome<br><div style='height: 15px;'></div>Observatory", unsafe_allow_html=True)
                            
                            with ct_sol:
                                val_v_sol = st.number_input("Vistadome (S/)", value=float(st.session_state.get('u_t_v_sol', 340.0)), key=f"utv_sol_{tour_id}", disabled=is_disabled)
                                val_o_sol = st.number_input("Observatory (S/)", value=float(st.session_state.get('u_t_o_sol', 530.0)), key=f"uto_sol_{tour_id}", disabled=is_disabled)
                                st.session_state.u_t_v_sol = val_v_sol
                                st.session_state.u_t_o_sol = val_o_sol
                                
                                # Tren Local (Solo Nacionales)
                                if tipo_t == "Nacional" or tipo_t == "Mixto":
                                    val_l = st.number_input("Tren Local (S/)", value=float(st.session_state.get('u_t_local', 0.0)), key=f"utl_{tour_id}", disabled=is_disabled)
                                    st.session_state.u_t_local = val_l

                            with ct_usd:
                                val_v_usd = st.number_input("Vistadome ($)", value=float(st.session_state.get('u_t_v', 90.0)), key=f"utv_usd_{tour_id}", disabled=is_disabled)
                                val_o_usd = st.number_input("Observatory ($)", value=float(st.session_state.get('u_t_o', 140.0)), key=f"uto_usd_{tour_id}", disabled=is_disabled)
                                st.session_state.u_t_v = val_v_usd
                                st.session_state.u_t_o = val_o_usd
                        else:
                            col_t1, col_n, col_e, col_h = st.columns([2, 0.8, 0.8, 0.8])
                            tour['titulo'] = col_t1.text_input(f"Título día {i+1}", tour['titulo'], key=f"title_{tour_id}", disabled=is_disabled)
                            tour['hora_inicio'] = col_h.text_input(f"⏰ Hora", value=tour.get('hora_inicio', '08:00 AM'), key=f"hi_{tour_id}", disabled=is_disabled)
                            # Control de visibilidad de hora
                            tour['mostrar_hora'] = st.toggle("👁️ Mostrar hora en PDF", value=tour.get('mostrar_hora', True), key=f"v_h_{tour_id}", disabled=is_disabled)
                            
                            tour['costo_nac'] = col_n.number_input(f"Nac (S/)", value=float(tour.get('costo_nac', 0)), key=f"cn_{tour_id}", disabled=is_disabled)
                            tour['costo_ext'] = col_e.number_input(f"Ext ($)", value=float(tour.get('costo_ext', 0)), key=f"ce_{tour_id}", disabled=is_disabled)
                            tour['costo_can'] = tour['costo_ext']
                            
                            # Margen individual por tour opcional
                            tour['usar_margen_propio'] = col_h.checkbox("Activar Margen", value=tour.get('usar_margen_propio', False), key=f"use_m_{tour_id}", disabled=is_disabled)
                            tour['margen_individual'] = col_h.number_input(f"% Margen", value=float(tour.get('margen_individual', m_pct_view)), step=1.0, key=f"margen_{tour_id}", disabled=not tour.get('usar_margen_propio') or is_disabled, help="Si está activado, usa este margen. Si no, usa el global.")
                            
                            if modo_edicion:
                                current_folder = tour.get('carpeta_img', 'general')
                                opts_folder = image_folders + [current_folder] if current_folder not in image_folders else image_folders
                                tour['carpeta_img'] = st.selectbox("📁 Carpeta Imágenes (Assets)", options=opts_folder, index=opts_folder.index(current_folder) if current_folder in opts_folder else 0, key=f"img_folder_{tour_id}", help="Selecciona la carpeta de imágenes para este día.")
                        
                        # --- MEJORA: Tarifas por Categoría (Ahora más visible) ---
                        if modo_edicion:
                            with st.container(border=True):
                                st.markdown("##### 👥 Edición de Tarifas por Categoría (Estudiantes/Niños)")
                                ec1, ec2, ec3 = st.columns(3)
                                # Nacionales
                                ec1.markdown("**🇵🇪 Nac**")
                                tour['costo_nac_est'] = ec1.number_input(f"Estud/PcD (S/)", value=float(tour.get('costo_nac_est', tour['costo_nac']-70)), key=f"cn_e_{tour_id}")
                                tour['costo_nac_nino'] = ec1.number_input(f"Niño (S/)", value=float(tour.get('costo_nac_nino', tour['costo_nac']-40)), key=f"cn_n_{tour_id}")
                                # Extranjeros
                                ec2.markdown("**🌎 Ext**")
                                tour['costo_ext_est'] = ec2.number_input(f"Estud/PcD ($)", value=float(tour.get('costo_ext_est', tour['costo_ext']-20)), key=f"ce_e_{tour_id}")
                                tour['costo_ext_nino'] = ec2.number_input(f"Niño ($)", value=float(tour.get('costo_ext_nino', tour['costo_ext']-15)), key=f"ce_n_{tour_id}")
                                # CAN
                                ec3.markdown("**🤝 CAN**")
                                tour['costo_can_est'] = ec3.number_input(f"Estud/PcD ($)", value=float(tour.get('costo_can_est', tour['costo_can']-20)), key=f"cc_e_{tour_id}")
                                tour['costo_can_nino'] = ec3.number_input(f"Niño ($)", value=float(tour.get('costo_can_nino', tour['costo_can']-15)), key=f"cc_n_{tour_id}")
                        else:
                            with st.expander("👥 Ver Tarifas por Categoría"):
                                st.write(f"**Nac:** Estud S/ {tour.get('costo_nac_est',0)} | Niño S/ {tour.get('costo_nac_nino',0)}")
                                st.write(f"**Ext:** Estud $ {tour.get('costo_ext_est',0)} | Niño $ {tour.get('costo_ext_nino',0)}")

                        st.divider()
                        
                        desc_key = f"desc_{tour_id}"
                        raw_desc = st.text_area(f"Descripción día {i+1}", tour.get('descripcion', ""), key=desc_key, height=100, disabled=is_disabled)
                        tour['descripcion'] = raw_desc
                        st.caption("💡 **Tips:** `**Negrita**`, `*Cursiva*`, `[Enter]` para nuevo párrafo.")
                        words_count = len(raw_desc.split())
                        st.caption(f"📝 {words_count} palabras")
                        
                        # Atractivos eliminados por pedido del usuario - Simplificación
                        
                        s_text = st.text_area(f"✅ Incluye", "\n".join(tour.get('servicios', [])), key=f"s_{tour_id}", height=120, disabled=is_disabled)
                        tour['servicios'] = [line.strip() for line in s_text.split("\n") if line.strip()]

                        sn_text = st.text_area(f"❌ No Incluye", "\n".join(tour.get('servicios_no_incluye', [])), key=f"sn_{tour_id}", height=80, disabled=is_disabled)
                        tour['servicios_no_incluye'] = [line.strip() for line in sn_text.split("\n") if line.strip()]
                        
                        if is_disabled:
                            st.caption("💡 Haz clic en 'Modificar datos de este día' arriba para editar precios o textos.")
                
                with c_btns:
                    st.write('<div style="margin-top: 4px;"></div>', unsafe_allow_html=True)
                    # Usamos el ID único para que los botones sean estables al moverse
                    tour_id = tour.get('id', str(i))
                    b1, b2, b3 = st.columns(3)
                    
                    if b1.button("🔼", key=f"up_{tour_id}"):
                        if i > 0:
                            item = st.session_state.itinerario.pop(i)
                            st.session_state.itinerario.insert(i-1, item)
                            st.rerun()
                            
                    if b2.button("🔽", key=f"down_{tour_id}"):
                        if i < len(st.session_state.itinerario)-1:
                            item = st.session_state.itinerario.pop(i)
                            st.session_state.itinerario.insert(i+1, item)
                            st.rerun()
                            
                    if b3.button("🗑️", key=f"del_{tour_id}"):
                        st.session_state.itinerario.pop(i)
                        st.rerun()
                
                st.markdown('<div style="margin-top: -15px;"></div>', unsafe_allow_html=True)
            
            st.divider()
            
            
            st.markdown("#### 💰 Margen Extra / Ajuste Global (Opcional)")
            ma1, ma2, ma3, ma4 = st.columns(4)
            # Usar keys permite que el valor se mantenga estable aunque la app se refresque por otras razones
            extra_nac = ma1.number_input("S/ Extra (Nac)", step=10.0, key="f_extra_nac")
            extra_ext = ma2.number_input("$ Extra (Ext)", step=5.0, key="f_extra_ext")
            extra_can = ma3.number_input("$ Extra (CAN)", step=5.0, key="f_extra_can")
            margen_pct = ma4.number_input("% Margen (Venta)", value=float(st.session_state.get('f_margen_porcentaje', 30.0)), step=1.0, key="f_margen_porcentaje", help="Aumenta los precios de los tours en este porcentaje.")
            
            ma5, ma6, ma7, ma8 = st.columns(4)
            margen_antes_pct = ma5.number_input("% Margen (Antes)", value=float(st.session_state.get('f_margen_antes', 40.0)), step=1.0, key="f_margen_antes", help="Margen para el precio tachado (efecto de oferta).")
            
            st.markdown('<div style="margin-top: -10px;"></div>', unsafe_allow_html=True)

            # Cálculo automático base de noches si el valor es 0 o el estado no existe
            auto_noches = max(0, len(st.session_state.itinerario) - 1)
            # Solo forzar auto_noches si el usuario no ha tocado el campo (valor en 0)
            if st.session_state.f_num_noches == 0 and auto_noches > 0:
                st.session_state.f_num_noches = auto_noches

            ma_n1, ma_n2 = st.columns(2)
            num_noches = ma_n1.number_input("🌙 Noches Hotel", min_value=0, step=1, key="f_num_noches")

            # --- CONFIGURACIÓN DE UPGRADES (HOTEL Y TREN) ---
            u_h2, u_h3, u_h4 = 0, 0, 0
            u_t_v, u_t_o = 0, 0
            precio_cierre_over = 0.0

            with st.expander("🏨 Configuración de Costos de Upgrades", expanded=(estrategia_v in ["Matriz", "Opciones"])):
                st.caption("Define el costo por persona/noche según el tipo de habitación para cada categoría. **Carga manual de precios (Sin conversiones automáticas).**")
                
                # Definir Pestañas por Categoría
                tab2, tab3, tab4 = st.tabs(["Hotel 2*", "Hotel 3*", "Hotel 4*"])
                
                def render_hotel_inputs(cat_key, sign, state_prefix):
                    cc1, cc2, cc3 = st.columns(3)
                    sgl = cc1.number_input(f"Simple ({sign})", value=float(st.session_state.get(f'u_h{cat_key}_sgl_{state_prefix}', 60.0 if state_prefix == "usd" else 220.0)), key=f"uh{cat_key}_sgl_{state_prefix}")
                    dbl = cc2.number_input(f"Doble ({sign})", value=float(st.session_state.get(f'u_h{cat_key}_dbl_{state_prefix}', 40.0 if state_prefix == "usd" else 150.0)), key=f"uh{cat_key}_dbl_{state_prefix}")
                    mat = cc3.number_input(f"Matrim. ({sign})", value=float(st.session_state.get(f'u_h{cat_key}_mat_{state_prefix}', 40.0 if state_prefix == "usd" else 150.0)), key=f"uh{cat_key}_mat_{state_prefix}")
                    cc4, cc5, _ = st.columns(3)
                    tpl = cc4.number_input(f"Triple ({sign})", value=float(st.session_state.get(f'u_h{cat_key}_tpl_{state_prefix}', 35.0 if state_prefix == "usd" else 130.0)), key=f"uh{cat_key}_tpl_{state_prefix}")
                    cua = cc5.number_input(f"Cuádruple ({sign})", value=float(st.session_state.get(f'u_h{cat_key}_cua_{state_prefix}', 30.0 if state_prefix == "usd" else 110.0)), key=f"uh{cat_key}_cua_{state_prefix}")
                    return sgl, dbl, mat, tpl, cua

                # Hotel 2*
                with tab2:
                    st.markdown("🇵🇪 **Nacionales (Soles)**")
                    u_h2_sgl_sol, u_h2_dbl_sol, u_h2_mat_sol, u_h2_tpl_sol, u_h2_cua_sol = render_hotel_inputs("2", "S/", "sol")
                    st.markdown("🌎 **Extranjeros (USD)**")
                    u_h2_sgl_usd, u_h2_dbl_usd, u_h2_mat_usd, u_h2_tpl_usd, u_h2_cua_usd = render_hotel_inputs("2", "$", "usd")
                
                # Hotel 3*
                with tab3:
                    st.markdown("🇵🇪 **Nacionales (Soles)**")
                    u_h3_sgl_sol, u_h3_dbl_sol, u_h3_mat_sol, u_h3_tpl_sol, u_h3_cua_sol = render_hotel_inputs("3", "S/", "sol")
                    st.markdown("🌎 **Extranjeros (USD)**")
                    u_h3_sgl_usd, u_h3_dbl_usd, u_h3_mat_usd, u_h3_tpl_usd, u_h3_cua_usd = render_hotel_inputs("3", "$", "usd")

                # Hotel 4*
                with tab4:
                    st.markdown("🇵🇪 **Nacionales (Soles)**")
                    u_h4_sgl_sol, u_h4_dbl_sol, u_h4_mat_sol, u_h4_tpl_sol, u_h4_cua_sol = render_hotel_inputs("4", "S/", "sol")
                    st.markdown("🌎 **Extranjeros (USD)**")
                    u_h4_sgl_usd, u_h4_dbl_usd, u_h4_mat_usd, u_h4_tpl_usd, u_h4_cua_usd = render_hotel_inputs("4", "$", "usd")

                # Guardar en session state (Soles)
                st.session_state.u_h2_sgl_sol = u_h2_sgl_sol; st.session_state.u_h2_dbl_sol = u_h2_dbl_sol; st.session_state.u_h2_mat_sol = u_h2_mat_sol; st.session_state.u_h2_tpl_sol = u_h2_tpl_sol; st.session_state.u_h2_cua_sol = u_h2_cua_sol
                st.session_state.u_h3_sgl_sol = u_h3_sgl_sol; st.session_state.u_h3_dbl_sol = u_h3_dbl_sol; st.session_state.u_h3_mat_sol = u_h3_mat_sol; st.session_state.u_h3_tpl_sol = u_h3_tpl_sol; st.session_state.u_h3_cua_sol = u_h3_cua_sol
                st.session_state.u_h4_sgl_sol = u_h4_sgl_sol; st.session_state.u_h4_dbl_sol = u_h4_dbl_sol; st.session_state.u_h4_mat_sol = u_h4_mat_sol; st.session_state.u_h4_tpl_sol = u_h4_tpl_sol; st.session_state.u_h4_cua_sol = u_h4_cua_sol

                # Guardar en session state (USD) - Mapeamos a las keys originales para compatibilidad si es necesario, 
                # pero idealmente usaremos las específicas. Por ahora usaremos las específicas.
                st.session_state.u_h2_sgl_usd = u_h2_sgl_usd; st.session_state.u_h2_dbl_usd = u_h2_dbl_usd; st.session_state.u_h2_mat_usd = u_h2_mat_usd; st.session_state.u_h2_tpl_usd = u_h2_tpl_usd; st.session_state.u_h2_cua_usd = u_h2_cua_usd
                st.session_state.u_h3_sgl_usd = u_h3_sgl_usd; st.session_state.u_h3_dbl_usd = u_h3_dbl_usd; st.session_state.u_h3_mat_usd = u_h3_mat_usd; st.session_state.u_h3_tpl_usd = u_h3_tpl_usd; st.session_state.u_h3_cua_usd = u_h3_cua_usd
                st.session_state.u_h4_sgl_usd = u_h4_sgl_usd; st.session_state.u_h4_dbl_usd = u_h4_dbl_usd; st.session_state.u_h4_mat_usd = u_h4_mat_usd; st.session_state.u_h4_tpl_usd = u_h4_tpl_usd; st.session_state.u_h4_cua_usd = u_h4_cua_usd
                # Suplementos de Tren movidos a la tarjeta de MP

            sel_hotel_gen = "Sin Hotel"
            sel_tren_gen = "Expedition"

            # Verificar si existe MP en el itinerario de forma global (usado por métricas y General)
            has_mp = any("MACHU PICCHU" in t.get('titulo', t.get('nombre', '')).upper() for t in st.session_state.itinerario)

            if estrategia_v == "General":
                with st.container(border=True):
                    st.markdown("🎯 **Configuración del Paquete (Modo General)**")
                    cg1, cg2 = st.columns(2)
                    sel_hotel_gen = cg1.selectbox("Categoría de Hotel", ["Sin Hotel", "Hotel 2*", "Hotel 3*", "Hotel 4*"], key="sel_h_gen")
                    
                    sel_tren_gen = "Expedition" # Valor por defecto seguro
                    
                    if has_mp:
                        opciones_tren = ["Expedition", "Vistadome", "Observatory"]
                        if tipo_t == "Nacional":
                            opciones_tren.insert(0, "Tren Local")
                        
                        sel_tren_gen = cg2.selectbox("Tipo de Tren", opciones_tren, key="sel_t_gen")

                    


            st.divider()
            
            # FILTRAR PASAJEROS Y MÁRGENES SEGÚN ORIGEN (Para evitar filtraciones de data oculta en la sesión)
            # Definimos variables locales de conteo para la lógica de cálculo
            c_ad_nac = n_adultos_nac; c_es_nac = n_estud_nac; c_pc_nac = n_pcd_nac; c_ni_nac = n_ninos_nac
            c_ad_ext = n_adultos_ext; c_es_ext = n_estud_ext; c_pc_ext = n_pcd_ext; c_ni_ext = n_ninos_ext
            c_ad_can = n_adultos_can; c_es_can = n_estud_can; c_pc_can = n_pcd_can; c_ni_can = n_ninos_can
            
            # Margen local para cálculo
            m_extra_nac = extra_nac
            m_extra_ext = extra_ext
            m_extra_can = extra_can

            if tipo_t == "Nacional":
                pasajeros_nac = c_ad_nac + c_es_nac + c_pc_nac + c_ni_nac
                pasajeros_ext = 0; pasajeros_can = 0
                # Zero out foreigners for calculation
                c_ad_ext = 0; c_es_ext = 0; c_pc_ext = 0; c_ni_ext = 0
                c_ad_can = 0; c_es_can = 0; c_pc_can = 0; c_ni_can = 0
                m_extra_ext = 0.0; m_extra_can = 0.0
            elif tipo_t == "Extranjero":
                pasajeros_nac = 0
                pasajeros_ext = c_ad_ext + c_es_ext + c_pc_ext + c_ni_ext
                pasajeros_can = c_ad_can + c_es_can + c_pc_can + c_ni_can
                # Zero out nationals for calculation
                c_ad_nac = 0; c_es_nac = 0; c_pc_nac = 0; c_ni_nac = 0
                m_extra_nac = 0.0
            else: # Mixto
                pasajeros_nac = c_ad_nac + c_es_nac + c_pc_nac + c_ni_nac
                pasajeros_ext = c_ad_ext + c_es_ext + c_pc_ext + c_ni_ext
                pasajeros_can = c_ad_can + c_es_can + c_pc_can + c_ni_can
                # Keep all category counts as they are

            # Recuperar suplementos de tren (Manual)
            u_t_v_sol = st.session_state.get('u_t_v_sol', 0.0)
            u_t_o_sol = st.session_state.get('u_t_o_sol', 0.0)
            u_t_local = st.session_state.get('u_t_local', 0.0)
            u_t_v_usd = st.session_state.get('u_t_v', 0.0)
            u_t_o_usd = st.session_state.get('u_t_o', 0.0)

            # Pre-calcular upgrades (SIEMPRE ambos para evitar conversiones raras en Mixto)
            calc_upgrades_sol = 0.0
            calc_upgrades_usd = 0.0
            calc_tren_sol = 0.0
            calc_tren_usd = 0.0
            tc = 3.8 # Tipo de cambio base para el sistema

            if estrategia_v == "General":
                total_pax_safe = max(1, total_pasajeros)
                # 🏨 Hotel
                if sel_hotel_gen != "Sin Hotel":
                    cat_code = sel_hotel_gen.split(" ")[1].replace("*", "") # "2", "3" o "4"
                    
                    # Soles
                    t_sgl_s = st.session_state.get(f'u_h{cat_code}_sgl_sol', 0.0)
                    t_dbl_s = st.session_state.get(f'u_h{cat_code}_dbl_sol', 0.0)
                    t_mat_s = st.session_state.get(f'u_h{cat_code}_mat_sol', 0.0)
                    t_tpl_s = st.session_state.get(f'u_h{cat_code}_tpl_sol', 0.0)
                    t_cua_s = st.session_state.get(f'u_h{cat_code}_cua_sol', 0.0)
                    total_hotel_sol = (n_sgl*1*t_sgl_s + n_dbl*2*t_dbl_s + n_mat*2*t_mat_s + n_tpl*3*t_tpl_s + n_cua*4*t_cua_s) * num_noches
                    calc_upgrades_sol = total_hotel_sol / total_pax_safe
                    
                    # Dólares
                    t_sgl_u = st.session_state.get(f'u_h{cat_code}_sgl_usd', 0.0)
                    t_dbl_u = st.session_state.get(f'u_h{cat_code}_dbl_usd', 0.0)
                    t_mat_u = st.session_state.get(f'u_h{cat_code}_mat_usd', 0.0)
                    t_tpl_u = st.session_state.get(f'u_h{cat_code}_tpl_usd', 0.0)
                    t_cua_u = st.session_state.get(f'u_h{cat_code}_cua_usd', 0.0)
                    total_hotel_usd = (n_sgl*1*t_sgl_u + n_dbl*2*t_dbl_u + n_mat*2*t_mat_u + n_tpl*3*t_tpl_u + n_cua*4*t_cua_u) * num_noches
                    calc_upgrades_usd = total_hotel_usd / total_pax_safe
                
                # 🚂 Tren
                if has_mp:
                    if sel_tren_gen == "Tren Local":
                        calc_tren_sol = u_t_local
                        calc_tren_usd = 0.0
                    elif sel_tren_gen == "Vistadome":
                        calc_tren_sol = u_t_v_sol
                        calc_tren_usd = u_t_v_usd
                    elif sel_tren_gen == "Observatory":
                        calc_tren_sol = u_t_o_sol
                        calc_tren_usd = u_t_o_usd
                    else:
                        calc_tren_sol = 0.0
                        calc_tren_usd = 0.0
            
            # --- CÁLCULO DE PRECIOS OPTIMIZADO (VIA FASTAPI) ---
            pricing_data = {
                "itinerario": st.session_state.itinerario,
                "pax_counts": {
                    "ad_nac": c_ad_nac, "es_nac": c_es_nac, "pc_nac": c_pc_nac, "ni_nac": c_ni_nac,
                    "ad_ext": c_ad_ext, "es_ext": c_es_ext, "pc_ext": c_pc_ext, "ni_ext": c_ni_ext,
                    "ad_can": c_ad_can, "es_can": c_es_can, "pc_can": c_pc_can, "ni_can": c_ni_can
                },
                "margen_pct": margen_pct,
                "margen_antes_pct": margen_antes_pct,
                "adj_global": {
                    "extra_nac": m_extra_nac, "extra_ext": m_extra_ext, "extra_can": m_extra_can
                },
                "upgrades": {
                    "up_nac": calc_upgrades_sol + calc_tren_sol,
                    "up_ext": calc_upgrades_usd + calc_tren_usd
                }
            }

            try:
                # Intentar llamar al motor de lógica asíncrono
                response = requests.post("http://127.0.0.1:8000/pricing", json=pricing_data, timeout=2)
                if response.status_code == 200:
                    api_res = response.json()
                    # Mapear resultados para compatibilidad con el resto de la UI
                    avg_nac_pp = api_res["avg_nac_pp"]
                    real_nac = api_res["real_nac"]
                    avg_ext_pp = api_res["avg_ext_pp"]
                    real_ext = api_res["real_ext"]
                    avg_can_pp = api_res["avg_can_pp"]
                    real_can = api_res["real_can"]
                    
                    # Nuevos campos para compatibilidad con PDF
                    total_nac_pp = api_res["total_nac_pp"]
                    total_ext_pp = api_res["total_ext_pp"]
                    total_can_pp = api_res["total_can_pp"]
                    avg_nac_antes_pp = api_res["avg_nac_antes_pp"]
                    avg_ext_antes_pp = api_res["avg_ext_antes_pp"]
                    avg_can_antes_pp = api_res["avg_can_antes_pp"]
                    total_nac_a_pp = api_res["total_nac_a_pp"]
                    
                    # --- VALORES RECUPERADOS ---
                    real_nac = api_res["real_nac"]
                    real_ext = api_res["real_ext"]
                    real_can = api_res["real_can"]
                    
                    # Totales para compatibilidad
                    total_nac_pp = api_res["total_nac_pp"]
                    total_ext_pp = api_res["total_ext_pp"]
                    total_can_pp = api_res["total_can_pp"]
                    
                    det_nac = api_res["det_nac"]
                    det_ext = api_res["det_ext"]
                    det_can = api_res["det_can"]
                    
                    precios = {
                        'nac': {'total': f"{avg_nac_pp:,.2f}", 'lista_det': det_nac} if pasajeros_nac > 0 else None,
                        'ext': {'total': f"{avg_ext_pp:,.2f}", 'lista_det': det_ext} if pasajeros_ext > 0 else None,
                        'can': {'total': f"{avg_can_pp:,.2f}", 'lista_det': det_can} if pasajeros_can > 0 else None
                    }
                else:
                    st.error("Error en el Motor de Lógica (FastAPI).")
                    st.stop()
            except Exception as e:
                st.warning(f"⚠️ Motor FastAPI no detectado en localhost:8000. El sistema no puede calcular precios.")
                st.info("Por favor, ejecuta 'uvicorn app_api:app --reload' en una terminal.")
                st.stop()

            # Define target currency settings globally
            mode_curr = st.session_state.get('f_moneda_pdf', "Soles (S/)")
            target_is_usd = (mode_curr == "Dólares ($)")
            target_is_mixed = (mode_curr == "Moneda Original (S/ y $)")
            sym_target = "$" if target_is_usd else "S/"

            col_res1, col_res2, col_res3 = st.columns(3)
            
            def render_col_breakdown(title, pax_total, val_total, p_dict, counts_dict, icon, is_ext=False):
                st.markdown(f"### {icon} {title}")
                sym_col = sym_target
                if target_is_mixed: sym_col = "$" if is_ext else "S/"
                
                if pax_total > 0:
                    st.markdown(f"## {sym_col} {val_total:,.2f}")
                    st.caption(f"**Total {title}** ({pax_total} pax)")
                    if p_dict and 'lista_det' in p_dict:
                        for label, monto_str in p_dict['lista_det'].items():
                            q = counts_dict.get(label, 0)
                            if q and q > 0:
                                st.write(f"{q} x {label}: **{sym_col} {monto_str}**")
                else:
                    st.write("---")
                    st.caption("Sin pasajeros")

            with col_res1:
                render_col_breakdown("Nacional", pasajeros_nac, real_nac, precios.get('nac'), 
                                     {'Adulto': c_ad_nac, 'Estudiante': c_es_nac, 'PCD': c_pc_nac, 'Niño': c_ni_nac}, "🇵🇪")
            with col_res2:
                render_col_breakdown("Extranjero", pasajeros_ext, real_ext, precios.get('ext'), 
                                     {'Adulto': c_ad_ext, 'Estudiante': c_es_ext, 'PCD': c_pc_ext, 'Niño': c_ni_ext}, "🌎", is_ext=True)
            with col_res3:
                render_col_breakdown("CAN", pasajeros_can, real_can, precios.get('can'), 
                                     {'Adulto': c_ad_can, 'Estudiante': c_es_can, 'PCD': c_pc_can, 'Niño': c_ni_can}, "🤝", is_ext=True)

            # TOTAL GENERAL (Consolidado)
            st.markdown("---")
            if target_is_mixed:
                tot_s = convert_val(real_nac, False)
                tot_d = convert_val(real_ext, True) + convert_val(real_can, True)
                st.markdown(f"## 💰 Inversión Total: S/ {tot_s:,.2f} + $ {tot_d:,.2f}")
            else:
                total_general_conv = convert_val(real_nac, False) + convert_val(real_ext, True) + convert_val(real_can, True)
                st.markdown(f"## 💰 Inversión Total: {sym_target} {total_general_conv:,.2f}")
            
            st.caption(f"Suma de todos los pasajeros ({pasajeros_nac+pasajeros_ext+pasajeros_can} pax) en {st.session_state.f_moneda_pdf}")
            
            # El monto de referencia es la suma de TODOS los reales (Nac + Ext + CAN)
            # El monto de referencia para la base de datos se guarda en la moneda principal (Soles si hay nac, USD sino)
            if pasajeros_nac > 0:
                monto_t_ref = real_nac + (real_ext + real_can) * tc
            else:
                monto_t_ref = real_ext + real_can
            
            st.divider()
            
            # --- NUEVA SECCIÓN: NOTA DE PRECIO GLOBAL ---
            st.session_state.f_nota_precio = st.text_input(
                "📝 Nota de Precio (Sección de Precios)", 
                value=st.session_state.get('f_nota_precio', "INCLUYE TOUR"),
                help="Ej: INCLUYE TOUR, No incluye vuelos, etc. Aparece junto a los montos."
            )
            
            st.session_state.f_notas_finales = st.text_area(
                "✍️ Notas Finales / Especificaciones (Última Hoja)", 
                value=st.session_state.get('f_notas_finales', ''), 
                key="global_notas_finales", 
                height=120, 
                help="Escriba aquí las indicaciones breves que irán en la última hoja del PDF."
            )
            
            st.divider()
            
            c_btn1, c_btn2 = st.columns(2)
            if c_btn2.button("🧹 Limpiar Todo"):
                # Resetear itinerario
                st.session_state.itinerario = []
                # Resetear nota de precio global
                st.session_state.f_nota_precio = "INCLUYE TOUR"
                # Resetear datos del pasajero
                st.session_state.f_nombre = ""
                st.session_state.f_celular = ""
                # Resetear composición del grupo
                keys_to_reset = [
                    'n_adultos_nac', 'n_estud_nac', 'n_pcd_nac', 'n_ninos_nac',
                    'n_adultos_ext', 'n_estud_ext', 'n_pcd_ext', 'n_ninos_ext',
                    'n_adultos_can', 'n_estud_can', 'n_pcd_can', 'n_ninos_can',
                    'an_nac_uni', 'es_nac_uni', 'pcd_nac_uni', 'ni_nac_uni',
                    'an_ext_uni', 'es_ext_uni', 'pcd_ext_uni', 'ni_ext_uni',
                    'an_can_uni', 'es_can_uni', 'pcd_can_uni', 'ni_can_uni',
                    'an_nac_mix', 'es_nac_mix', 'pcd_nac_mix', 'ni_nac_mix',
                    'an_ext_mix', 'es_ext_mix', 'pcd_ext_mix', 'ni_ext_mix',
                    'an_can_mix', 'es_can_mix', 'pcd_can_mix', 'ni_can_mix',
                    'v_nombre', 'v_celular', 'f_usa_fechas', 'global_notas_finales'
                ]
                for k in keys_to_reset:
                    if k in st.session_state:
                        del st.session_state[k]
                
                # Resetear distribución de habitaciones
                room_keys = ['f_n_sgl', 'f_n_dbl', 'f_n_mat', 'f_n_tpl', 'f_n_cua']
                for rk in room_keys:
                    if rk in st.session_state:
                        del st.session_state[rk]

                # Reiniciar otros campos opcionales
                for fk in ['f_extra_nac', 'f_extra_ext', 'f_extra_can', 'f_margen_porcentaje', 'f_margen_antes']:
                    if fk in st.session_state:
                        del st.session_state[fk]
                
                st.success("¡Formulario limpiado por completo!")
                st.rerun()
            
            # --- SELECTOR DE IDIOMA PARA EL PDF ---
            st.markdown("🌐 **Idioma del Itinerario**")
            idioma_pdf = st.selectbox(
                "Soporta traducción automática con IA", 
                ["Español", "English", "Français", "Deutsch", "Português", "Italiano", "日本語 (Japonés)"],
                key="f_idioma_itinerario"
            )

            st.markdown("👁️ **Visualización en PDF**")
            ocultar_total = st.checkbox("Ocultar Precios Totales (Solo mostrar precios por persona)", value=False, key="f_ocultar_total")
            
            # (La selección de portada ahora se encuentra en el panel superior, al elegir el paquete)
            
            # Obtener el valor actual del selector global vía session_state
            portada_sel = st.session_state.get('user_selected_cover', 'Cusco Tradicional')
            
            # Catálogo de portadas dinámico
            opciones_portadas = get_opciones_portadas()

            st.markdown("---")
            st.markdown("### 🎒 Recomendaciones y Equipaje")
            st.caption("Puedes editar libremente las listas antes de generar el PDF. Coloca cada ítem en una línea nueva.")
            
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                recomendacion_salud = st.text_area(
                    "🌿 Salud y Protección", 
                    value="BLOQUEADOR SOLAR SPF 50+\nREPELENTE DE INSECTOS\nMEDICACIÓN PERSONAL\nTOALLITAS HÚMEDAS",
                    height=150
                )
            with col_r2:
                recomendacion_ropa = st.text_area(
                    "👕 Ropa y Equipo", 
                    value="CAMISAS DE MANGA LARGA\nPANTALONES CÓMODOS\nCHAQUETA DE LLUVIA / PONCHO\nMOCHILA LIGERA",
                    height=150
                )
            st.markdown("---")

            if c_btn1.button("🔥 GENERAR ITINERARIO PDF"):
                if celular and st.session_state.itinerario:
                    with st.spinner("Generando PDF con Edge..."):
                        base_dir = os.getcwd()
                        target_cat = st.session_state.get('f_categoria', 'Cusco Tradicional')
                        package_img_folder = st.session_state.get('f_package_img', '')
                        fallback_cover = os.path.join(base_dir, "assets", "images", "fallback_cover.jpg")
                        
                        # Buscar la tupla exacta en el catálogo mapeado
                        datos_portada = opciones_portadas.get(portada_sel)
                        if datos_portada:
                            archivo_img, _t1_dummy, _t2_dummy = datos_portada
                        else:
                            archivo_img = "cusco_tradicional.jpg"
                            
                        # Limpiar el nombre del paquete para usarlo de título: 
                        # Remover cosas como "8D/7N" o "08D/07N" usando Expresiones Regulares
                        nombre_limpio = pkg_name_sel if 'pkg_name_sel' in locals() else "TU PRÓXIMA AVENTURA"
                        nombre_limpio = re.sub(r'\b\d{1,2}D(?:/|-)?\d{1,2}N\b', '', nombre_limpio, flags=re.IGNORECASE).strip()
                        
                        # Dividir el nombre limpio en dos líneas si es muy largo, priorizando T1
                        palabras = nombre_limpio.split()
                        if len(palabras) > 2:
                            mitad = len(palabras) // 2
                            t1 = " ".join(palabras[:mitad]).upper()
                            t2 = " ".join(palabras[mitad:]).upper()
                        elif len(palabras) == 2:
                            t1, t2 = palabras[0].upper(), palabras[1].upper()
                        else:
                            t1, t2 = nombre_limpio.upper(), ""
                            
                        cover_img = os.path.join(base_dir, "assets", "images", "covers", archivo_img)
                        
                        # Si por alguna razón los archivos de portada no existen, usar el respaldo (fallback)
                        if not os.path.exists(cover_img):
                            cover_img = fallback_cover
                        
                        # --- PROCESAMIENTO DE TEXTOS Y ETIQUETAS ---
                        labels_pdf = {
                            "preparado_para": "PREPARADO PARA", "dia_label": "DÍA", "inicia_label": "INICIA:",
                            "servicios_incluye": "SERVICIOS QUE INCLUYE:", "servicios_no_incluye": "SERVICIOS QUE NO INCLUYE:",
                            "categorias": {"ADULTO": "ADULTO", "NIÑO": "NIÑO", "ESTUDIANTE": "ESTUDIANTE", "PcD": "PcD"},
                            "cada_uno": "c/u", "confirmacion_titulo": "CONFIRMACIÓN FINAL",
                            "confirmacion_subtitulo": "DOCUMENTO DE CIERRE DE RESERVA", "total_acordado": "TOTAL ACORDADO",
                            "monto_final_cierre": "Monto Final de Cierre", "desglose_pasajero": "Desglose por Pasajero",
                            "inversion_persona": "Inversión por persona:", "observaciones": "Observaciones:",
                            "nota_inversion": "Nota sobre la inversión:", "propuesta_inversion": "Propuesta de Inversión",
                            "seleccione_nivel": "Seleccione su nivel de experiencia", "experiencia_label": "EXPERIENCIA",
                            "mas_elegido": "MÁS ELEGIDO", "garantia_titulo": "GARANTÍA DE RESERVA",
                            "garantia_texto": "Confirmación con el 50% del total. El saldo se cancela al llegar a Cusco.",
                            "oferta_lanzamiento": "OFERTA DE LANZAMIENTO", "tarifas_preferenciales": "TARIFAS PREFERENCIALES",
                            "super_precio": "¡SÚPER PRECIO!", "tarifa_nacional": "TARIFA NACIONAL",
                            "tarifa_internacional": "TARIFA INTERNACIONAL / CAN", "total_por_pasajero": "TOTAL POR PASAJERO",
                            "extranjero_label": "Extranjero", "can_label": "Comunidad Andina (CAN)",
                            "disponibilidad_titulo": "DISPONIBILIDAD", "disponibilidad_texto": "Sujeto a cambios según espacios.",
                            "validez_titulo": "VALIDEZ", "validez_texto": "Válido por 48 horas.", "nota_experto": "Nota del Experto:",
                            "terminos_titulo": "Términos y Condiciones", "terminos_subtitulo": "RESUMEN DE POLÍTICAS",
                            "terminos_disclaimer": "Al confirmar, acepta los términos descritos.",
                            "guia_titulo": "Guía del Viajero", "guia_subtitulo": "PREPARA TU AVENTURA",
                            "recomendaciones_titulo": "RECOMENDACIONES", "equipaje_titulo": "EQUIPAJE",
                            "mensaje_final_1": "¡Prepárate para vivir una experiencia inolvidable!",
                            "mensaje_final_2": "Nos vemos pronto en Cusco.", "notas_adicionales": "Notas Adicionales:"
                        }

                        itinerario_a_procesar = st.session_state.itinerario
                        notas_a_procesar = st.session_state.get('f_notas_finales', '')

                        if idioma_pdf != "Español":
                            target_lang = idioma_pdf
                            with st.status(f"Traduciendo a {target_lang}...", expanded=False) as status:
                                try:
                                    translate_req = {
                                        "itinerario": {"days": itinerario_a_procesar}, 
                                        "notas_finales": notas_a_procesar,
                                        "target_lang": target_lang
                                    }
                                    res_tr = requests.post("http://127.0.0.1:8000/translate", json=translate_req, timeout=60)
                                    if res_tr.status_code == 200:
                                        translated_data = res_tr.json()
                                        itinerario_a_procesar = translated_data['days']
                                        notas_a_procesar = translated_data['notas_finales']
                                        if 'labels' in translated_data:
                                            labels_pdf = translated_data['labels']
                                        st.success("¡Traducción completada!")
                                    else:
                                        st.error(f"Error en Traducción: {res_tr.text}")
                                        st.stop()
                                except Exception as e:
                                    st.error(f"Error llamando a la API de Traducción: {e}")
                                    st.stop()
                                status.update(label="Traducción lista ✅", state="complete")

                        # Preparar días con imágenes (Local)
                        days_data = []
                        for i, tour in enumerate(itinerario_a_procesar):
                            titulo_actual = tour.get('titulo', '').upper()
                            carpeta = tour.get('carpeta_img', 'general')
                            if (carpeta == 'general' or not carpeta) and tours_db:
                                match_t = next((t for t in tours_db if t['nombre'].upper().strip() == titulo_actual.strip()), None)
                                if match_t: carpeta = match_t.get('carpeta_img', 'general')

                            imgs = obtener_imagenes_tour(carpeta)
                            servs_in = [{'texto': s, 'svg': get_svg_icon(s, 'default_in')} for s in tour.get('servicios', [])]
                            servs_out = [{'texto': s, 'svg': get_svg_icon(s, 'default_out')} for s in tour.get('servicios_no_incluye', [])]
                            
                            current_date = fecha_inicio + timedelta(days=i)
                            days_data.append({
                                'numero': i + 1,
                                'fecha': current_date.strftime('%d / %m / %Y') if usa_fechas else "",
                                'titulo': tour['titulo'],
                                'hora_inicio': format_tour_time(tour.get('hora_inicio', '08:00 AM')),
                                'mostrar_hora': tour.get('mostrar_hora', True),
                                'descripcion': tour.get('descripcion', ''),
                                'servicios': servs_in,
                                'servicios_no': servs_out,
                                'images': imgs
                            })
                        
                        # Data para PDF
                        num_noches = st.session_state.get('f_num_noches', len(st.session_state.itinerario))

                        # --- DATA PARA EL PDF (JINJA2) ---
                        # Precios Actuales
                        precios_pdf = {
                            'nac': {'total': f"{avg_nac_pp:,.2f}", 'lista_det': det_nac} if pasajeros_nac > 0 else None,
                            'ext': {'total': f"{avg_ext_pp:,.2f}", 'lista_det': det_ext} if pasajeros_ext > 0 else None,
                            'can': {'total': f"{avg_can_pp:,.2f}", 'lista_det': det_can} if pasajeros_can > 0 else None
                        }
                        
                        # Precios Antes (Oferta)
                        precios_antes_pdf = {
                            'nac': {'total': f"{avg_nac_antes_pp:,.2f}"} if avg_nac_antes_pp > 0 else None,
                            'ext': {'total': f"{avg_ext_antes_pp:,.2f}"} if avg_ext_antes_pp > 0 else None,
                            'can': {'total': f"{avg_can_antes_pp:,.2f}"} if avg_can_antes_pp > 0 else None
                        }

                        # Estructura de Políticas (Por defecto)
                        politicas_base = {
                            "titulo_principal": "RESUMEN DE TÉRMINOS Y CONDICIONES",
                            "secciones": [
                                {"titulo": "1. Reservas y Pagos", "icon": "💳", "contenido": "Se requiere el 50% para confirmar."},
                                {"titulo": "2. Anulaciones", "icon": "🕒", "contenido": "Gastos administrativos aplican si se anula con menos de 15 días."},
                                {"titulo": "3. Condiciones", "icon": "📋", "contenido": "Es obligatorio DNI/Pasaporte vigente."},
                                {"titulo": "4. Visita", "icon": "🏛️", "contenido": "Boletos válidos para un solo ingreso."},
                                {"titulo": "5. Responsabilidades", "icon": "🛡️", "contenido": "La agencia no responde por retrasos externos."},
                                {"titulo": "6. Atención", "icon": "📱", "contenido": "Atención virtual vía WhatsApp/Email."}
                            ]
                        }

                        # Estructura de Guía del Viajero (Recomendaciones y Equipaje)
                        guia_viajero_pdf = {
                            "secciones": [
                                {"nombre": labels_pdf.get("recomendaciones_titulo", "RECOMENDACIONES"), "lista": [item.strip() for item in recomendacion_salud.split('\n') if item.strip()]}
                            ],
                            "secciones_extra": [
                                {"nombre": labels_pdf.get("equipaje_titulo", "EQUIPAJE"), "lista": [item.strip() for item in recomendacion_ropa.split('\n') if item.strip()]}
                            ]
                        }

                        full_itinerary_data = {
                            'title_1': t1,
                            'title_2': t2,
                            'pasajero': st.session_state.f_nombre.upper(),
                            'fechas': rango_fechas.upper(),
                            'usa_fechas': usa_fechas,
                            'origen': tipo_t,
                            'es_nacional': (pasajeros_nac > 0),
                            'simbolo_moneda': sym_target,
                            'duracion': f"{len(st.session_state.itinerario)}D / {num_noches}N",
                            'vendedor': st.session_state.get('v_nombre', 'Vendedor'),
                            'celular_cliente': st.session_state.f_celular,
                            'days': days_data,
                            'precios': precios_pdf,
                            'precios_antes': precios_antes_pdf,
                            'show_antes_pdf': True, 
                            'nota_p': st.session_state.get('f_nota_precio', 'INCLUYE TOUR'),
                            'notas_finales': notas_a_procesar,
                            'labels': labels_pdf,
                            'politicas': politicas_base,
                            'guia_viajero': guia_viajero_pdf,
                            'header_img': "assets/img/logos/header_pdf.png",
                            'header_img': "assets/img/logos/header_pdf.png",
                            'logo_url': os.path.abspath(os.path.join("assets", "images", "logo_background.png")),
                            'logo_cover_url': os.path.abspath(os.path.join("assets", "images", "logo_background.png")),
                            'llama_img': os.path.abspath(os.path.join("assets", "images", "llama_purchase.png")),
                            'llama_purchase_img': os.path.abspath(os.path.join("assets", "images", "llama_purchase.png")),
                            'train_exp_img': os.path.abspath(os.path.join("assets", "images", "train_expedition.png")),
                            'train_vis_img': os.path.abspath(os.path.join("assets", "images", "train_vistadome.png")),
                            'train_obs_img': os.path.abspath(os.path.join("assets", "images", "train_observatory.png")),
                            'cover_url': os.path.abspath(cover_img)
                        }

                        # Limpiar nulos (Si fuera necesario para el nuevo formato de diccionario, se haría aquí, pero no es vital)
                        with st.spinner("Generando y Sincronizando..."):
                            try:
                                # 1. Guardar en Supabase
                                it_id = save_itinerary_v2(full_itinerary_data)
                                if it_id:
                                    st.toast(f"✅ Sincronizado (ID: {it_id})")
                                
                                # 2. Generar PDF via API (Con timeout extendido a 120s para la nube)
                                res_pdf = requests.post("http://127.0.0.1:8000/generate-pdf", json=full_itinerary_data, timeout=120)
                                if res_pdf.status_code == 200:
                                    pdf_path = res_pdf.json()["pdf_path"]
                                    with open(pdf_path, "rb") as f:
                                        st.download_button(
                                            label="⬇️ Descargar Itinerario PDF",
                                            data=f.read(),
                                            file_name=f"Itinerario_{st.session_state.f_nombre}.pdf",
                                            mime="application/pdf"
                                        )
                                else:
                                    err_detail = res_pdf.json().get('detail', 'Error Desconocido')
                                    st.error(f"Error en el Motor de PDF (FastAPI): {err_detail}")
                            except Exception as e:
                                st.error(f"Error final: {e}")
                else:
                    st.warning("⚠️ Asegúrate de poner el Celular y tener al menos un tour en el plan.")
    
    # Pie de página
    st.markdown("---")
    st.caption("v2.0 - Sistema de Gestión de Itinerarios con Edge PDF | Viajes Cusco Perú")
