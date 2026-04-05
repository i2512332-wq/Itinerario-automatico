import os
import streamlit as st
from utils.supabase_db import get_available_tours, update_tour_master, create_new_tour

def get_image_folders_admin():
    base_path = os.path.join("assets", "img", "tours")
    folders = ["general"]
    if os.path.exists(base_path):
        found = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
        for f in sorted(found):
            if f != "general":
                folders.append(f)
    return folders

def render_admin_precios_ui():
    image_folders = get_image_folders_admin()

    st.markdown("## ⚙️ Configuración Maestra de Catálogo")
    st.markdown("Gestiona los tours y paquetes. **Los cambios afectarán a todas las nuevas cotizaciones.**")
    st.divider()

    # Obtener tours
    with st.spinner("Cargando catálogo..."):
        tours_db = get_available_tours()

    tab1, tab2 = st.tabs(["✏️ Editar Catálogo Existente", "➕ Crear Nuevo Tour"])

    with tab1:
        if not tours_db:
            st.warning("No hay tours disponibles o hubo un error al cargar el catálogo.")
        else:
            st.markdown("### 🏷️ Gestión de Tours")
            search = st.text_input("🔍 Buscar por nombre", "").lower()

            for idx, t in enumerate(tours_db):
                if search and search not in t['nombre'].lower():
                    continue

                id_tour = t.get('id_tour')
                if not id_tour: continue

                with st.expander(f"📦 {t['nombre']}"):
                    with st.form(f"form_edit_{id_tour}_{idx}"):
                        col_e1, col_e2 = st.columns([2, 1])
                        with col_e1:
                            new_nombre = st.text_input("Nombre del Tour", value=t['nombre'])
                            
                            # Validación de palabras en 'itinerario' (dentro de highlights JSONB)
                            current_desc = t.get('itinerario_texto', "")
                            word_count = len(current_desc.split())
                            desc_label = f"Texto del Itinerario (Highlights) - {word_count}/100 palabras"
                            
                            new_desc = st.text_area(desc_label, value=current_desc, height=150)
                            
                            new_word_count = len(new_desc.split())
                            if new_word_count > 100:
                                st.error(f"⚠️ ¡Atención! La descripción tiene {new_word_count} palabras. El límite para el PDF es de 100.")
                        with col_e2:
                            st.markdown("**💰 Precios Base (Adulto)**")
                            new_p_nac = st.number_input("Nacional (S/)", value=float(t.get('precio_adulto_nacional', 0.0)), step=1.0, key=f"ed_nac_{id_tour}")
                            new_p_ext = st.number_input("Extranjero (USD)", value=float(t.get('precio_adulto_extranjero', 0.0)), step=1.0, key=f"ed_ext_{id_tour}")
                            new_p_can = st.number_input("CAN (USD)", value=float(t.get('precio_adulto_can', 0.0)), step=1.0, key=f"ed_can_{id_tour}")

                        # --- DETALLES AVANZADOS ---
                        c_adv_main1, c_adv_main2 = st.columns(2)
                        with c_adv_main1:
                            with st.expander("⭐ Precios Niños, Estudiantes, PCD"):
                                st.caption("Configuración manual por categoría:")
                                c_adv1, c_adv2, c_adv3 = st.columns(3)
                                with c_adv1:
                                    st.markdown("**Niños**")
                                    n_nino_nac = st.number_input("Nac (S/)", value=float(t.get('precio_nino_nacional', 0.0)), key=f"ed_nnn_{id_tour}")
                                    n_nino_ext = st.number_input("Ext (USD)", value=float(t.get('precio_nino_extranjero', 0.0)), key=f"ed_nne_{id_tour}")
                                    n_nino_can = st.number_input("CAN (USD)", value=float(t.get('precio_nino_can', 0.0)), key=f"ed_nnc_{id_tour}")
                                with c_adv2:
                                    st.markdown("**Estudiantes**")
                                    n_est_nac = st.number_input("Nac (S/)", value=float(t.get('precio_estudiante_nacional', 0.0)), key=f"ed_nen_{id_tour}")
                                    n_est_ext = st.number_input("Ext (USD)", value=float(t.get('precio_estudiante_extranjero', 0.0)), key=f"ed_nee_{id_tour}")
                                    n_est_can = st.number_input("CAN (USD)", value=float(t.get('precio_estudiante_can', 0.0)), key=f"ed_nec_{id_tour}")
                                with c_adv3:
                                    st.markdown("**PCD**")
                                    n_pcd_nac = st.number_input("Nac (S/)", value=float(t.get('precio_pcd_nacional', 0.0)), key=f"ed_npn_{id_tour}")
                                    n_pcd_ext = st.number_input("Ext (USD)", value=float(t.get('precio_pcd_extranjero', 0.0)), key=f"ed_npe_{id_tour}")
                                    n_pcd_can = st.number_input("CAN (USD)", value=float(t.get('precio_pcd_can', 0.0)), key=f"ed_npc_{id_tour}")
                        
                        with c_adv_main2:
                            with st.expander("🛠️ Configuración Técnica"):
                                st.caption("Metadatos y duración:")
                                c_tech1, c_tech2 = st.columns(2)
                                with c_tech1:
                                    n_dias = st.number_input("Días", min_value=1, value=int(t.get('duracion_dias', 1)), key=f"ed_dias_{id_tour}")
                                    n_horas = st.number_input("Horas", min_value=0, value=int(t.get('duracion_horas', 0)), key=f"ed_hr_{id_tour}")
                                with c_tech2:
                                    n_dificultad = st.selectbox("Dificultad", options=["FACIL", "MODERADO", "DIFICIL", "EXTREMO"], index=["FACIL", "MODERADO", "DIFICIL", "EXTREMO"].index(t.get('dificultad', 'FACIL')), key=f"ed_dif_{id_tour}")
                                    n_categoria = st.text_input("Categoría", value=t.get('categoria', 'General'), key=f"ed_cat_{id_tour}")
                                
                                    current_img = t.get('carpeta_img', 'general')
                                    opts_img = image_folders + [current_img] if current_img not in image_folders else image_folders
                                    n_img = st.selectbox("Carpeta Imágenes", options=opts_img, index=opts_img.index(current_img) if current_img in opts_img else 0, key=f"ed_img_{id_tour}")
                                    n_hora = st.text_input("Hora Inicio (HH:MM:SS)", value=t.get('hora_inicio', '08:00:00')[:8], key=f"ed_hora_{id_tour}")


                        st.markdown("**📝 Textos del Itinerario**")
                        
                        raw_i = t.get('servicios_incluidos', []) 
                        inc_str = ", ".join(raw_i) if isinstance(raw_i, list) else ""
                        
                        raw_ni = t.get('servicios_no_incluidos', [])
                        no_inc_str = ", ".join(raw_ni) if isinstance(raw_ni, list) else ""

                        new_inc = st.text_input("Incluye", value=inc_str, key=f"ed_inc_{id_tour}")
                        new_no_inc = st.text_input("No Incluye", value=no_inc_str, key=f"ed_noinc_{id_tour}")

                        if st.form_submit_button("💾 Guardar Cambios Totales", type="primary", use_container_width=True):
                            update_data = {
                                "nombre": new_nombre,
                                "precio_adulto_nacional": new_p_nac,
                                "precio_adulto_extranjero": new_p_ext,
                                "precio_adulto_can": new_p_can,
                                # Precios avanzados
                                "precio_nino_nacional": n_nino_nac,
                                "precio_nino_extranjero": n_nino_ext,
                                "precio_nino_can": n_nino_can,
                                "precio_estudiante_nacional": n_est_nac,
                                "precio_estudiante_extranjero": n_est_ext,
                                "precio_estudiante_can": n_est_can,
                                "precio_pcd_nacional": n_pcd_nac,
                                "precio_pcd_extranjero": n_pcd_ext,
                                "precio_pcd_can": n_pcd_can,
                                "duracion_dias": n_dias,
                                "duracion_horas": n_horas,
                                "dificultad": n_dificultad,
                                "categoria": n_categoria,
                                "carpeta_img": n_img,
                                "hora_inicio": n_hora if ":" in n_hora else f"{n_hora}:00:00", # Asegurar formato TIME
                                "highlights": {"itinerario": new_desc},
                                "servicios_incluidos": {"incluye": [i.strip() for i in new_inc.split(",") if i.strip()]},
                                "servicios_no_incluidos": {"no_incluye": [n.strip() for n in new_no_inc.split(",") if n.strip()]}
                            }
                            
                            with st.spinner("Actualizando base de datos..."):
                                if len(new_desc.split()) > 100:
                                    st.error("❌ No se puede guardar: La descripción excede las 100 palabras.")
                                else:
                                    success, msg = update_tour_master(id_tour, update_data)
                                    if success:
                                        if 'catalogo_tours' in st.session_state:
                                            del st.session_state['catalogo_tours']
                                        st.success(f"✅ '{new_nombre}' actualizado correctamente.")
                                        st.rerun()
                                    else:
                                        st.error(f"Error: {msg}")

    with tab2:
        st.markdown("### ➕ Ingresar Nuevo Tour al Catálogo")
        with st.form("form_crear_tour", clear_on_submit=True):
            col_t1, col_t2 = st.columns([2, 1])
            with col_t1:
                f_nombre = st.text_input("Nombre del Tour *", placeholder="Ej: Full Day Paracas e Ica")
                f_desc = st.text_area("Texto Itinerario (Se guardará en 'highlights') *", placeholder="Escribe el itinerario o resumen...")
                
                f_word_count = len(f_desc.split())
                if f_word_count > 0:
                    st.caption(f"Palabras: {f_word_count}/100")
                if f_word_count > 100:
                    st.error(f"⚠️ Has excedido el límite ({f_word_count}/100).")
            with col_t2:
                f_dias = st.number_input("Días", min_value=1, value=1, step=1)
                f_horas = st.number_input("Horas", min_value=0, value=0, step=1)
            
            st.markdown("**💰 Precios Base (Adultos)**")
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1: f_p_nac = st.number_input("Precio Perú (S/) *", min_value=0.0, value=0.0)
            with col_p2: f_p_ext = st.number_input("Precio Extranjero (USD) *", min_value=0.0, value=0.0)
            with col_p3: f_p_can = st.number_input("Precio CAN (USD)", min_value=0.0, value=0.0)

            c_adv_c1, c_adv_c2 = st.columns(2)
            with c_adv_c1:
                with st.expander("⭐ Precios Niños, Estudiantes, PCD"):
                    st.caption("Opcional: Si dejas 0, el sistema calcula automáticamente.")
                    coa1, coa2, coa3 = st.columns(3)
                    with coa1:
                        st.markdown("**Niños**")
                        f_nnn = st.number_input("Niño Nac (S/)", min_value=0.0, value=0.0)
                        f_nne = st.number_input("Niño Ext (USD)", min_value=0.0, value=0.0)
                        f_nnc = st.number_input("Niño CAN (USD)", min_value=0.0, value=0.0)
                    with coa2:
                        st.markdown("**Estudiantes**")
                        f_nen = st.number_input("Est Nac (S/)", min_value=0.0, value=0.0)
                        f_nee = st.number_input("Est Ext (USD)", min_value=0.0, value=0.0)
                        f_nec = st.number_input("Est CAN (USD)", min_value=0.0, value=0.0)
                    with coa3:
                        st.markdown("**PCD**")
                        f_npn = st.number_input("PCD Nac (S/)", value=0.0)
                        f_npe = st.number_input("PCD Ext (USD)", value=0.0)
                        f_npc = st.number_input("PCD CAN (USD)", value=0.0)
            
            with c_adv_c2:
                with st.expander("🛠️ Información Técnica"):
                    f_dificultad = st.selectbox("Dificultad", options=["FACIL", "MODERADO", "DIFICIL", "EXTREMO"])
                    f_categoria = st.text_input("Categoría", value="General")
                    f_img = st.selectbox("Carpeta Imágenes", options=image_folders)
                    f_hora = st.text_input("Hora Inicio", value="08:00:00")

            st.markdown("**📝 Textos (Separados por comas)**")
            f_inc = st.text_input("Qué incluye")
            f_no_inc = st.text_input("Qué NO incluye")
            
            if st.form_submit_button("🔨 Crear Tour Oficial", type="primary", use_container_width=True):
                if not f_nombre:
                    st.error("❌ El nombre es obligatorio.")
                elif len(f_desc.split()) > 100:
                    st.error(f"❌ La descripción es muy larga ({len(f_desc.split())} palabras). Máximo 100.")
                else:
                    success, msg = create_new_tour(
                        nombre=f_nombre, descripcion=f_desc,
                        precio_nac=f_p_nac, precio_ext=f_p_ext, precio_can=f_p_can,
                        incluye_text=f_inc, no_incluye_text=f_no_inc,
                        duracion_dias=f_dias, duracion_horas=f_horas,
                        precio_nino_nac=f_nnn if f_nnn > 0 else None,
                        precio_nino_ext=f_nne if f_nne > 0 else None,
                        precio_nino_can=f_nnc if f_nnc > 0 else None,
                        precio_est_nac=f_nen if f_nen > 0 else None,
                        precio_est_ext=f_nee if f_nee > 0 else None,
                        precio_est_can=f_nec if f_nec > 0 else None,
                        precio_pcd_nac=f_npn, precio_pcd_ext=f_npe, precio_pcd_can=f_npc,
                        categoria=f_categoria, dificultad=f_dificultad, 
                        carpeta_img=f_img, hora_inicio=f_hora
                    )
                    if success:
                        if 'catalogo_tours' in st.session_state:
                            del st.session_state['catalogo_tours']
                        st.success(f"✅ Tour '{f_nombre}' creado con éxito.")
                        st.rerun()
                    else: 
                        st.error(f"❌ Error al crear: {msg}")
                        with st.expander("Ver detalle del error"):
                            st.code(msg)

