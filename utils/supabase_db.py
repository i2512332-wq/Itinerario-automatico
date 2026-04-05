import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

# Cargar variables de entorno
load_dotenv()

# Configuración de Supabase
# Prioridad: st.secrets (Streamlit Cloud) > os.getenv (Local .env)
def get_config_var(name, default=None):
    # Intentar en st.secrets (formato jerárquico como en la imagen del usuario [supabase])
    try:
        if name == "SUPABASE_URL":
            return st.secrets["supabase"].get("URL") or st.secrets.get("SUPABASE_URL")
        if name == "SUPABASE_KEY":
            # Soporta tanto SUPABASE_KEY como ANON_KEY (que es lo que puso el usuario)
            return st.secrets["supabase"].get("ANON_KEY") or st.secrets["supabase"].get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
    except:
        pass
    return os.getenv(name, default)

SUPABASE_URL = get_config_var("SUPABASE_URL")
SUPABASE_KEY = get_config_var("SUPABASE_KEY")

def get_supabase_client() -> Client:
    """Inicializa y retorna el cliente de Supabase."""
    if not SUPABASE_URL or "your-project" in str(SUPABASE_URL) or not SUPABASE_KEY or "your-anon-key" in str(SUPABASE_KEY):
        if hasattr(st, "warning"):
            st.warning("⚠️ Configuración de Supabase incompleta (SUPABASE_URL o KEY).")
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        if hasattr(st, "error"):
            st.error(f"❌ Error al conectar con Supabase: {e}")
        return None

def save_itinerary_v2(itinerary_data):
    """
    Guarda un itinerario en 'itinerario_digital' y sincroniza con 'lead'.
    Versión adaptada al ESQUEMA MAESTRO FINAL.
    """
    supabase = get_supabase_client()
    if not supabase: return None
    
    try:
        # 1. Resolver el id_vendedor por nombre
        vendedor_nombre = itinerary_data.get("vendedor", "Vendedor General")
        vendedor_res = supabase.table("vendedor").select("id_vendedor").ilike("nombre", f"%{vendedor_nombre}%").limit(1).execute()
        
        vendedor_id = None # Cambiado de 1 a None para evitar errores si 1 no existe
        if vendedor_res.data:
            vendedor_id = vendedor_res.data[0]["id_vendedor"]
        else:
            # Si no existe, creamos el vendedor para no romper la llave foránea
            try:
                new_vend = {"nombre": vendedor_nombre}
                res_v = supabase.table("vendedor").insert(new_vend).execute()
                if res_v.data:
                    vendedor_id = res_v.data[0]["id_vendedor"]
            except Exception as e_v:
                print(f"No se pudo crear/encontrar vendedor '{vendedor_nombre}': {e_v}")
                # Si falla, se queda en None, que es permitido en lead e itinerario_digital

        # 2. Manejar el Lead (SOLO SI ES B2C)
        id_lead = None
        es_b2b = itinerary_data.get("canal") == "B2B"
        nombre = itinerary_data.get("pasajero")
        
        if not es_b2b:
            celular = itinerary_data.get("celular_cliente")
            fuente = itinerary_data.get("fuente")
            estado = itinerary_data.get("estado")
            
            # Buscar lead existente
            lead_res = supabase.table("lead").select("id_lead").eq("numero_celular", celular).execute()
            
            if lead_res.data:
                id_lead = lead_res.data[0]["id_lead"]
                # Actualizamos el lead existente (se quita estado_lead)
                supabase.table("lead").update({
                    "id_vendedor": vendedor_id,
                    "nombre_pasajero": nombre
                }).eq("id_lead", id_lead).execute()
            else:
                # Crear nuevo lead (se quita estado_lead y whatsapp)
                new_lead = {
                    "numero_celular": celular,
                    "nombre_pasajero": nombre,
                    "id_vendedor": vendedor_id,
                    "red_social": fuente
                }
                res_nl = supabase.table("lead").insert(new_lead).execute()
                if res_nl.data:
                    id_lead = res_nl.data[0]["id_lead"]

        # 3. Guardar en itinerario_digital
        it_digital = {
            "id_lead": id_lead,
            "id_vendedor": vendedor_id,
            "nombre_pasajero_itinerario": nombre,
            "datos_render": itinerary_data
        }
        
        res_it = supabase.table("itinerario_digital").insert(it_digital).execute()
        
        if res_it.data:
            it_id = res_it.data[0]["id_itinerario_digital"]
            
            # 4. Actualizar el último itinerario en el Lead para seguimiento rápido
            if id_lead:
                try:
                    supabase.table("lead").update({"ultimo_itinerario_id": it_id}).eq("id_lead", id_lead).execute()
                except Exception as e_lead:
                    print(f"Error actualizando ultimo_itinerario_id: {e_lead}")
                
            return it_id
        else:
            print(f"Error: No se recibió data al insertar en itinerario_digital. Response: {res_it}")
            if hasattr(st, "error"):
                st.error(f"Error DB: No se pudo crear el registro del itinerario. Verifique permisos.")
            
        return None
    except Exception as e:
        import traceback
        error_msg = f"Error en Cerebro Supabase: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        if hasattr(st, "error"):
            st.error(f"DEBUG: {error_msg}")
        return None


def get_last_itinerary_by_phone(phone: str):
    """Busca el historial usando el número de celular."""
    supabase = get_supabase_client()
    if not supabase or not phone: return None
    
    # Limpiar el teléfono de espacios para la búsqueda
    phone_clean = phone.strip()
    
    try:
        # 1. Buscar en itinerario_digital (datos_render -> celular_cliente)
        response = supabase.table("itinerario_digital")\
            .select("*")\
            .ilike("datos_render->>celular_cliente", f"%{phone_clean}%")\
            .order("fecha_generacion", desc=True)\
            .limit(1)\
            .execute()
        
        if response.data:
            return response.data[0]
            
        # Limpiar aún más para fallbacks (solo dígitos)
        phone_digits = "".join(filter(str.isdigit, phone_clean))
        search_term = f"%{phone_digits}%" if len(phone_digits) > 5 else f"%{phone_clean}%"

        # Fallback 1: Buscar en la tabla 'lead'
        res_lead = supabase.table("lead")\
            .select("*")\
            .or_(f"numero_celular.ilike.{search_term},numero_celular.ilike.%{phone_clean}%")\
            .order("fecha_creacion", desc=True)\
            .limit(1)\
            .execute()
            
        if res_lead.data:
            lead = res_lead.data[0]
            return {
                "datos_render": {
                    "pasajero": lead.get("nombre_pasajero", ""),
                    "celular_cliente": lead.get("numero_celular", ""),
                    "fuente": lead.get("red_social", "Desconocido")
                }
            }
            
        # Doble Fallback: Buscar en 'cliente' (algunos tienen el número en su perfil)
        res_cliente = supabase.table("cliente")\
            .select("*")\
            .ilike("nombre", f"%{phone_clean}%")\
            .limit(1)\
            .execute()
            
        if res_cliente.data:
            # st.toast("✅ Cliente encontrado en DB Interna")
            client = res_cliente.data[0]
            pais = str(client.get("pais", "")).upper()
            categoria = "Nacional" if "PERU" in pais or "PERÚ" in pais else "Extranjero"
            
            return {
                "datos_render": {
                    "pasajero": client.get("nombre", ""),
                    "celular_cliente": "", # Cliente no tiene cel en esta tabla
                    "fuente": "Base de Datos",
                    "estado": "Cliente",
                    "categoria": categoria,
                    "tipo_cliente": client.get("tipo_cliente", "B2C")
                }
            }
        else:
            # st.error(f"⚠️ Cliente '{name}' no encontrado en tabla 'cliente'")
            pass
            
        return None
    except Exception as e:
        print(f"Error consultando Cerebro: {e}")
        return None

def extract_json_list(data, keys_priority):
    """Helper para extraer listas de estructuras JSON variadas."""
    if not data: return []
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for k in keys_priority:
            if k in data and isinstance(data[k], list):
                return data[k]
        # Si no hay lista en las claves, pero el dict tiene valores, ver si hay alguna otra lista
        for val in data.values():
            if isinstance(val, list): return val
        return []
    if isinstance(data, str):
        # Si es un string con comas, convertir a lista
        if "," in data: return [i.strip() for i in data.split(",") if i.strip()]
        return [data.strip()]
    return []

def get_available_tours():
    """Obtiene el catálogo de tours desde Supabase."""
    supabase = get_supabase_client()
    if not supabase: return []
    try:
        res = supabase.table("tour").select("*").order("nombre").execute()
    except Exception as e:
        print(f"Error fetching tours: {e}")
        return []

    tours = []
    if res.data:
        for t in res.data:
            try:
                # 1. Parsear Highlights (UI highlights) desde 'highlights'
                raw_highlights_db = t.get("highlights")
                
                final_highlights = []
                # Buscar dentro de highlights
                if raw_highlights_db:
                    final_highlights = extract_json_list(raw_highlights_db, ["itinerario_lista", "lugares", "atractivos", "highlights", "puntos", "Lo que visitarás"])
                
                # 2. Parsear Servicios
                servicios_in = extract_json_list(t.get("servicios_incluidos"), ["incluye", "servicios"])
                servicios_out = extract_json_list(t.get("servicios_no_incluidos"), ["no_incluye", "no_incluidos"])

                # 3. Enriquecer descripción con 'itinerario' si existe
                desc = t.get("descripcion", "")
                rich_itinerary = ""
                
                # Intentar sacar el texto del itinerario/experiencia de los JSONs
                if isinstance(raw_highlights_db, dict):
                    if "itinerario" in raw_highlights_db:
                        rich_itinerary = raw_highlights_db["itinerario"]
                    elif "itinerario_texto" in raw_highlights_db:
                        rich_itinerary = raw_highlights_db["itinerario_texto"]
                elif isinstance(raw_highlights_db, str) and raw_highlights_db.strip():
                    # Si ya es un texto plano, lo usamos directamente
                    rich_itinerary = raw_highlights_db
                
                # Si encontramos texto enriquecido, lo usamos
                if rich_itinerary:
                    import re
                    # 1. Limpieza básica de caracteres
                    cleaned = rich_itinerary.replace("\\n", "\n").replace('""', '"').strip()
                    # 2. Eliminar el título entre corchetes ej: [Titulo]
                    cleaned = re.sub(r'^\[.*?\]\s*', '', cleaned)
                    # 3. Eliminar prefix común "La Experiencia:" o "The Experience:"
                    cleaned = re.sub(r'^(La Experiencia|The Experience):\s*', '', cleaned, flags=re.IGNORECASE)
                    # 4. Eliminar comillas envolventes si quedaron (ej: "Texto")
                    cleaned = cleaned.strip('"').strip()
                    
                    desc = cleaned

                # 4. Formatear Hora (Normalizar a 24h HH:MM:SS para SQL)
                raw_hora = t.get("hora_inicio")
                formatted_hora = "08:00:00"
                if raw_hora:
                    try:
                        # Si viene como timestamp ISO o tiene zona horaria
                        if "T" in str(raw_hora) or "-" in str(raw_hora):
                            from dateutil import parser
                            dt = parser.parse(str(raw_hora))
                            formatted_hora = dt.strftime("%H:%M:%S")
                        else:
                            # Asegurar que sea HH:MM:SS (truncar o completar)
                            s_hora = str(raw_hora).strip()
                            if len(s_hora) == 5: # HH:MM
                                formatted_hora = f"{s_hora}:00"
                            else:
                                formatted_hora = s_hora[:8]
                    except:
                        formatted_hora = str(raw_hora)[:8]

                tours.append({
                    "id_tour": t.get("id_tour"),
                    "nombre": t.get("nombre", "Sin Nombre"),
                    "itinerario_texto": desc, # Descripción virtual desde highlights
                    "highlights": final_highlights,
                    "servicios_incluidos": servicios_in,
                    "servicios_no_incluidos": servicios_out,
                    
                    # Matriz 12 Precios (Nombres exactos SQL)
                    "precio_adulto_nacional": float(t.get("precio_adulto_nacional") or 0),
                    "precio_adulto_extranjero": float(t.get("precio_adulto_extranjero") or 0),
                    "precio_adulto_can": float(t.get("precio_adulto_can") or 0),
                    
                    "precio_nino_nacional": float(t.get("precio_nino_nacional") or 0),
                    "precio_nino_extranjero": float(t.get("precio_nino_extranjero") or 0),
                    "precio_nino_can": float(t.get("precio_nino_can") or 0),
                    
                    "precio_estudiante_nacional": float(t.get("precio_estudiante_nacional") or 0),
                    "precio_estudiante_extranjero": float(t.get("precio_estudiante_extranjero") or 0),
                    "precio_estudiante_can": float(t.get("precio_estudiante_can") or 0),
                    
                    "precio_pcd_nacional": float(t.get("precio_pcd_nacional") or 0),
                    "precio_pcd_extranjero": float(t.get("precio_pcd_extranjero") or 0),
                    "precio_pcd_can": float(t.get("precio_pcd_can") or 0),

                    # Metadatos
                    "duracion_dias": t.get("duracion_dias") or 1,
                    "duracion_horas": t.get("duracion_horas") or 0,
                    "carpeta_img": t.get("carpeta_img") or "general",
                    "hora_inicio": formatted_hora,
                    "dificultad": t.get("dificultad") or "FACIL",
                    "categoria": t.get("categoria") or "General"
                })
            except Exception as e_row:
                print(f"Error procesando fila de tour {t.get('nombre')}: {e_row}")
                continue
    return tours


def get_available_packages():
    """Obtiene el catálogo de paquetes desde Supabase."""
    supabase = get_supabase_client()
    if not supabase: return []
    try:
        # Recuperamos 'orden' además del nombre del tour para poder ordenar
        # Filtramos solo paquetes activos
        res = supabase.table("paquete").select("*, paquete_tour(orden, tour(nombre))").eq("activo", True).order("nombre").execute()
        packages = []
        for p in res.data:
            # Obtenemos la lista cruda de relaciones
            raw_tours = p.get("paquete_tour", [])
            # Ordenamos por la columna 'orden' para respetar la secuencia del itinerario
            raw_tours.sort(key=lambda x: x.get("orden", 999))
            
            # Extraemos solo los nombres ya ordenados
            tours_names = [pt["tour"]["nombre"] for pt in raw_tours if pt.get("tour")]
            
            packages.append({
                "nombre": p["nombre"],
                "tours": tours_names,
                "destino": p.get("destino_principal") or "Otros",
                "carpeta_img": p.get("carpeta_img") or "general"
            })
        return packages
    except Exception as e:
        st.error(f"❌ Error de conexión al cargar Paquetes: {e}")
        return []

def get_vendedores():
    """Obtiene la lista de vendedores activos desde Supabase."""
    supabase = get_supabase_client()
    if not supabase: return []
    try:
        res = supabase.table("vendedor").select("nombre").eq("estado", "ACTIVO").order("nombre").execute()
        return [v["nombre"] for v in res.data]
    except Exception as e:
        print(f"Error cargando vendedores: {e}")
        return []

def verify_user(email, password):
    """
    Verifica credenciales usando el sistema de Autenticación OFICIAL de Supabase.
    Luego busca el rol en la tabla usuarios_app.
    """
    supabase = get_supabase_client()
    if not supabase: return None
    
    try:
        # 1. Intentar Login real en Supabase Auth
        res_auth = supabase.auth.sign_in_with_password({"email": email, "password": password})
        
        if res_auth.user:
            # 2. Si el login es exitoso, buscamos su ROL en nuestra tabla blanca
            res_role = supabase.table("usuarios_app").select("rol").eq("email", email).execute()
            rol = "VENTAS" # Rol por defecto
            if res_role.data:
                rol = res_role.data[0]["rol"]

            # 3. Buscamos el NOMBRE real en la tabla vendedor
            res_vendedor = supabase.table("vendedor").select("nombre").eq("email", email).execute()
            nombre = email.split('@')[0].capitalize()
            if res_vendedor.data:
                nombre = res_vendedor.data[0]["nombre"]

            return {
                "email": res_auth.user.email,
                "id": res_auth.user.id,
                "rol": rol,
                "nombre": nombre
            }
        return None
    except Exception as e:
        # Si las credenciales son inválidas, Supabase lanzará una excepción
        print(f"Error de Auth: {e}")
        return None

# --- FUNCIONES DE PAQUETES PERSONALIZADOS (CLOUD) ---

def save_custom_package(nombre: str, itinerario: list, user_email: str, es_publico: bool = True):
    """Guarda un itinerario personalizado en Supabase."""
    supabase = get_supabase_client()
    if not supabase: return False
    
    try:
        data = {
            "nombre": nombre,
            "itinerario": itinerario,
            "creado_por": user_email,
            "es_publico": es_publico
        }
        res = supabase.table("paquete_personalizado").insert(data).execute()
        return len(res.data) > 0
    except Exception as e:
        print(f"Error guardando paquete cloud: {e}")
        return False

def get_custom_packages(user_email: str = None):
    """Obtiene la lista de paquetes personalizados guardados en la nube."""
    supabase = get_supabase_client()
    if not supabase: return []
    
    try:
        if user_email:
            # Traer públicos O los creados por el usuario actual
            res = supabase.table("paquete_personalizado")\
                .select("*")\
                .or_(f"es_publico.eq.true,creado_por.eq.{user_email}")\
                .order("created_at", desc=True)\
                .execute()
        else:
            # Fallback: Solo los públicos
            res = supabase.table("paquete_personalizado").select("*").eq("es_publico", True).order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        print(f"Error listando paquetes cloud: {e}")
        return []

def delete_custom_package(id_paquete: str):
    """Elimina un paquete personalizado de la nube."""
    supabase = get_supabase_client()
    if not supabase: return False
    
    try:
        res = supabase.table("paquete_personalizado").delete().eq("id_paquete_personalizado", id_paquete).execute()
        return len(res.data) > 0
    except Exception as e:
        print(f"Error eliminando paquete cloud: {e}")
        return False

def get_service_templates():
    """Obtiene las plantillas de servicios rápidos desde la base de datos."""
    supabase = get_supabase_client()
    if not supabase: return []
    
    try:
        res = supabase.table("plantilla_servicio").select("*").order("titulo").execute()
        return res.data
    except Exception as e:
        print(f"Error cargando plantillas de servicio: {e}")
        return []

# --- CONFIGURACIÓN MAESTRA ---
def update_tour_master(id_tour, data):
    """
    Actualiza cualquier campo de un tour en la tabla `tour`.
    `data` es un diccionario con los campos a actualizar.
    """
    supabase = get_supabase_client()
    if not supabase: return False, "No client"
    try:
        # Actualización en una sola llamada
        res = supabase.table("tour").update(data).eq("id_tour", id_tour).execute()
        if res.data:
            return True, "Tour actualizado correctamente"
        else:
            return False, "No se encontró el tour para actualizar"
    except Exception as e:
        return False, str(e)


def create_new_tour(
    nombre, descripcion,
    precio_nac, precio_ext, precio_can,
    incluye_text="", no_incluye_text="",
    duracion_dias=1, duracion_horas=0,
    precio_nino_nac=None, precio_nino_ext=None, precio_nino_can=None,
    precio_est_nac=None, precio_est_ext=None, precio_est_can=None,
    precio_pcd_nac=0, precio_pcd_ext=0, precio_pcd_can=0,
    categoria="General", dificultad="FACIL", carpeta_img="general", hora_inicio="08:00:00"
):
    """
    Crea un nuevo tour en la base de datos asegurando que no haya campos Null críticos
    y estructurando las listas de JSON (highlights, servicios).
    """
    supabase = get_supabase_client()
    if not supabase: return False, "No client"

    try:
        # 1. Transformar textos largos a la estructura JSON esperada por UI
        # UI espera { "itinerario": "texto largo" }
        hl_json = {"itinerario": descripcion}
        inc_json = {"incluye": [i.strip() for i in incluye_text.split(",") if i.strip()]}
        no_inc_json = {"no_incluye": [n.strip() for n in no_incluye_text.split(",") if n.strip()]}

        data = {
            "nombre": nombre,
            "duracion_dias": duracion_dias,
            "duracion_horas": duracion_horas,
            
            # Precios Base
            "precio_adulto_nacional": precio_nac,
            "precio_adulto_extranjero": precio_ext,
            "precio_adulto_can": precio_can,
            
            # Precios Derivados o Secundarios (Cálculo automático si no se proveen)
            "precio_nino_nacional": precio_nino_nac if precio_nino_nac is not None else max(0, precio_nac - 40),
            "precio_nino_extranjero": precio_nino_ext if precio_nino_ext is not None else max(0, precio_ext - 15),
            "precio_nino_can": precio_nino_can if precio_nino_can is not None else max(0, precio_can - 15),
            
            "precio_estudiante_nacional": precio_est_nac if precio_est_nac is not None else max(0, precio_nac - 70),
            "precio_estudiante_extranjero": precio_est_ext if precio_est_ext is not None else max(0, precio_ext - 20),
            "precio_estudiante_can": precio_est_can if precio_est_can is not None else max(0, precio_can - 20),
            
            "precio_pcd_nacional": precio_pcd_nac,
            "precio_pcd_extranjero": precio_pcd_ext,
            "precio_pcd_can": precio_pcd_can,
            
            # Textos y Metadatos
            "highlights": hl_json,
            "servicios_incluidos": inc_json,
            "servicios_no_incluidos": no_inc_json,
            
            "categoria": categoria,
            "dificultad": dificultad,
            "carpeta_img": carpeta_img,
            "hora_inicio": hora_inicio,
            "activo": True
        }
        
        res = supabase.table("tour").insert(data).execute()
        
        if res.data:
            return True, "Tour creado con éxito"
        else:
            return False, f"Respuesta vacía de la base de datos: {res}"
    except Exception as e:
        return False, f"Error de excepción: {str(e)}"

def create_master_package(nombre, descripcion, dias, noches, tours_vinculados, precio_sugerido=0, destino="", temporada="", carpeta_img="general"):
    """
    Crea un paquete maestro oficial y lo vincula con los tours del catálogo.
    `tours_vinculados` es una lista de dicts: [{"id_tour": 1, "dia": 1, "orden": 1}, ...]
    """
    supabase = get_supabase_client()
    if not supabase: return False, "No client"
    
    try:
        # 1. Insertar el encabezado del paquete
        pkg_data = {
            "nombre": nombre,
            "descripcion": descripcion,
            "dias": dias,
            "noches": noches,
            "precio_sugerido": precio_sugerido,
            "destino_principal": destino,
            "temporada": temporada,
            "carpeta_img": carpeta_img,
            "activo": True
        }
        res_pkg = supabase.table("paquete").insert(pkg_data).execute()
        
        if not res_pkg.data:
            return False, "Error creando el registro del paquete"
            
        new_pkg_id = res_pkg.data[0]["id_paquete"]
        
        # 2. Insertar las relaciones paquete_tour
        relaciones = []
        for vt in tours_vinculados:
            relaciones.append({
                "id_paquete": new_pkg_id,
                "id_tour": vt["id_tour"],
                "dia_del_paquete": vt["dia"],
                "orden": vt["orden"]
            })
            
        if relaciones:
            supabase.table("paquete_tour").insert(relaciones).execute()
            
        return True, "Paquete maestro creado y vinculado exitosamente"
        
    except Exception as e:
        return False, str(e)


