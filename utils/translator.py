import os
import json
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def translate_itinerary(itinerary_data, target_lang="English"):
    """
    Traduce los textos de un itinerario (títulos, descripciones, servicios) 
    usando OpenAI GPT-4o-mini.
    """
    try:
        api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    except:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return itinerary_data, "Error: No se encontró la API KEY de OpenAI (configura OPENAI_API_KEY en st.secrets o .env)."

    client = OpenAI(api_key=api_key)
    
    # Preparar el prompt para la IA
    # Solo traducimos los campos de texto para ahorrar tokens y mantener IDs/Precios intactos.
    system_prompt = f"""
    Eres un traductor experto en turismo y viajes. 
    Tu tarea es traducir el contenido de un itinerario de viaje del Español al {target_lang}.
    
    Reglas:
    1. Mantén un tono profesional, elegante y acogedor para una agencia de viajes premium.
    2. TOTALMENTE PROHIBIDO traducir nombres propios de lugares, atractivos turísticos o sitios arqueológicos (ej: 'Machu Picchu', 'Ollantaytambo', 'Sacsayhuaman', 'Qorikancha', 'Pisaq'). Estos deben permanecer EXACTAMENTE igual en el texto traducido.
    3. Solo traduce términos generales como 'Sacred Valley' por 'Valle Sagrado' si es estrictamente necesario para la fluidez, pero prioriza los nombres originales.
    4. Devuelve los resultados en el mismo formato estructurado que recibas (JSON-object).
    5. NO traduzcas bajo ninguna circunstancia números, fechas, horas, ni símbolos de moneda (S/, $, USD).
    """

    # Extraer textos para traducir
    # Para ser eficientes, enviamos todo en un solo bloque si es posible o por partes claras.
    processed_days = []
    
    for day in itinerary_data.get('days', []):
        user_prompt = f"""
        Traduce los siguientes campos al {target_lang}:
        Título: {day.get('titulo')}
        Descripción: {day.get('descripcion')}
        Incluye: {", ".join(day.get('servicios', []))}
        No Incluye: {", ".join(day.get('servicios_no_incluye', []))}
        """
        
        try:
            json_prompt = f"""
            Traduce este JSON al {target_lang} respetando las llaves. Solo traduce los valores.
            {{
                "titulo": "{day.get('titulo')}",
                "descripcion": "{day.get('descripcion')}",
                "servicios": {day.get('servicios', [])},
                "servicios_no_incluye": {day.get('servicios_no_incluye', [])}
            }}
            """
            
            response_json = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json_prompt}
                ]
            )
            
            import json
            translations = json.loads(response_json.choices[0].message.content)
            
            # Crear copia del día con todas las propiedades originales (incluyendo images, numero, fecha, etc.)
            new_day = day.copy()
            
            # Aplicar traducciones sobre la copia
            new_day['titulo'] = translations.get('titulo', day.get('titulo'))
            new_day['descripcion'] = translations.get('descripcion', day.get('descripcion'))
            new_day['servicios'] = translations.get('servicios', day.get('servicios'))
            new_day['servicios_no_incluye'] = translations.get('servicios_no_incluye', day.get('servicios_no_incluye', []))
            
            processed_days.append(new_day)
            
        except Exception as e:
            print(f"Error traduciendo día: {e}")
            processed_days.append(day)

    # ✅ Guardar los días traducidos de vuelta en itinerary_data
    itinerary_data['days'] = processed_days

    # 3. Traducir NOTA DE PRECIO (texto plano - usar JSON wrapper para evitar que la IA lo devuelva como clave JSON)
    if itinerary_data.get('nota_precio'):
        try:
            res_np = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": f"Eres un traductor. Devuelve SOLO un JSON con esta estructura: {{\"resultado\": \"texto traducido\"}}"},
                    {"role": "user", "content": f"Traduce al {target_lang} este texto: {itinerary_data.get('nota_precio')}"}
                ]
            )
            itinerary_data['nota_precio'] = json.loads(res_np.choices[0].message.content).get('resultado', itinerary_data['nota_precio'])
        except: pass

    # 4. Traducir NOTAS FINALES (texto plano - mismo fix JSON wrapper)
    if itinerary_data.get('notas_finales'):
        try:
            res_nf = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": f"Eres un traductor. Devuelve SOLO un JSON con esta estructura: {{\"resultado\": \"texto traducido\"}}"},
                    {"role": "user", "content": f"Traduce al {target_lang} este texto: {itinerary_data.get('notas_finales')}"}
                ]
            )
            itinerary_data['notas_finales'] = json.loads(res_nf.choices[0].message.content).get('resultado', itinerary_data['notas_finales'])
        except: pass

    # 5. Traducir BLOQUES ESTÁTICOS (Guía y Políticas)
    # Definimos los bloques base en español si no vienen en el data
    guia_base = itinerary_data.get('guia_viajero', {
        "titulo": "Guía del Viajero",
        "subtitulo": "PREPARA TU AVENTURA",
        "secciones": [
            {"nombre": "SALUD Y PROTECCIÓN", "lista": ["BLOQUEADOR SOLAR SPF 50+", "REPELENTE DE INSECTOS", "MEDICACIÓN PERSONAL", "TOALLITAS HÚMEDAS"]}
        ],
        "secciones_extra": [
            {"nombre": "ROPA Y EQUIPO", "lista": ["CAMISAS DE MANGA LARGA", "PANTALONES CÓMODOS", "CHAQUETA DE LLUVIA / PONCHO", "MOCHILA LIGERA"]}
        ],
        "mensaje_final": "<p style='margin: 0; font-size: 1.1rem; color: #2d3436; font-weight: 600;'>✨ <strong>¡Prepárate para vivir una experiencia inolvidable!</strong> ✨</p><p style='margin: 10px 0 0 0; font-size: 0.9rem; color: #636e72;'>Cada detalle cuenta para que tu viaje sea perfecto. ¡Nos vemos pronto en Cusco!</p>"
    })

    politicas_base = itinerary_data.get('politicas', {
        "titulo_principal": "RESUMEN DE TÉRMINOS Y CONDICIONES",
        "secciones": [
            {
                "titulo": "1. Reservas y Pagos",
                "icon": "💳",
                "contenido": "<strong>Depósito inicial:</strong> Se requiere el 50% del total para confirmar la reserva del paquete turístico.<br><strong>Saldo restante:</strong> Debe liquidarse a más tardar 48 horas antes del inicio del primer tour o según lo acordado con su asesor.<br><strong>Métodos de pago:</strong> Transferencia bancaria, depósito, efectivo, PayPal y tarjetas (estas últimas con un recargo del 5%).<br><strong>Información requerida:</strong> El cliente debe facilitar datos reales (pasaporte/DNI, edad, restricciones médicas y alimentarias)."
            },
            {
                "titulo": "2. Políticas de Anulación",
                "icon": "🕒",
                "contenido": "<strong>Más de 15 días:</strong> Reembolso del 100% (menos 10% de gastos administrativos).<br><strong>Entre 8 y 14 días:</strong> Reembolso del 50%.<br><strong>Entre 4 y 7 días:</strong> Reembolso del 25%.<br><strong>Menos de 4 días:</strong> No hay devolución.<br><strong>Casos excepcionales:</strong> Ingresos a Machu Picchu o pasajes quedan sujetos a condiciones de los proveedores."
            },
            {
                "titulo": "3. Condiciones del Servicio",
                "icon": "📋",
                "contenido": "<strong>Documentación:</strong> Es obligatorio portar pasaporte o DNI original vigente.<br><strong>Infantes:</strong> Menores de 2 años viajan gratis.<br><strong>Habitaciones:</strong> El alojamiento individual (SGL) conlleva un suplemento adicional.<br><strong>Puntualidad:</strong> El cliente debe presentarse puntualmente en los puntos de encuentro.<br><strong>Seguro:</strong> Se recomienda contar con un seguro de viaje personal."
            },
            {
                "titulo": "4. Reglamento de Visita",
                "icon": "🏛️",
                "contenido": "<strong>Boletos:</strong> Son válidos para un solo ingreso a la Ciudadela de Machu Picchu.<br><strong>Permanencia:</strong> El tiempo promedio permitido es de 2 a 3 horas según circuito.<br><strong>Guía:</strong> El uso de guía oficial es obligatorio para el ingreso."
            },
            {
                "titulo": "5. Responsabilidades",
                "icon": "🛡️",
                "contenido": "<strong>La Agencia:</strong> Se compromete a brindar guías certificados y transporte autorizado.<br><strong>Eximentes:</strong> La agencia no se responsabiliza por robos, accidentes externos o cierres por causas de fuerza mayor (clima, huelgas, desastres).<br><strong>Jurisdicción:</strong> Controversias legales se resolverán bajo los tribunales de Cusco."
            },
            {
                "titulo": "6. Atención y Reclamos",
                "icon": "📱",
                "contenido": "<strong>Atención:</strong> Las consultas y reservas son 100% virtuales (WhatsApp/Email).<br><strong>Reclamos:</strong> Se dispone de un Libro de Reclamaciones (físico y virtual) conforme a la ley de INDECOPI."
            }
        ]
    })

    try:
        # Traducir Guía
        json_guia = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Traduce este objeto de guía al {target_lang}: {json.dumps(guia_base)}"}
            ]
        )
        itinerary_data['guia_viajero'] = json.loads(json_guia.choices[0].message.content)

        # Traducir Políticas
        json_pol = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Traduce este objeto de políticas al {target_lang}: {json.dumps(politicas_base)}"}
            ]
        )
        itinerary_data['politicas'] = json.loads(json_pol.choices[0].message.content)
    except:
        itinerary_data['guia_viajero'] = guia_base
        itinerary_data['politicas'] = politicas_base

    # 6. Traducir ETIQUETAS DE INTERFAZ (textos fijos del template HTML)
    labels_base = {
        # Portada
        "preparado_para": "PREPARADO PARA",
        # Días del itinerario
        "dia_label": "DÍA",
        "inicia_label": "INICIA:",
        "servicios_incluye": "SERVICIOS QUE INCLUYE:",
        "servicios_no_incluye": "SERVICIOS QUE NO INCLUYE:",
        # Categorías dinámicas (pasajeros y totales)
        "categorias": {
            "ADULTO": "ADULTO",
            "NIÑO": "NIÑO",
            "BEBÉ": "BEBÉ",
            "INFANTE": "INFANTE",
            "ESTUDIANTE": "ESTUDIANTE",
            "PcD": "PcD",
            "TOTAL NACIONAL": "TOTAL NACIONAL",
            "TOTAL EXTRANJERO": "TOTAL EXTRANJERO",
            "TOTAL CAN": "TOTAL CAN"
        },
        "cada_uno": "c/u",
        # Precios - Estrategia General
        "confirmacion_titulo": "CONFIRMACIÓN FINAL",
        "confirmacion_subtitulo": "DOCUMENTO DE CIERRE DE RESERVA",
        "total_acordado": "TOTAL ACORDADO",
        "monto_final_cierre": "Monto Final de Cierre",
        "desglose_pasajero": "Desglose por Pasajero",
        "inversion_persona": "Inversión por persona:",
        "observaciones": "Observaciones:",
        "nota_inversion": "Nota sobre la inversión:",
        # Precios - Estrategia Matriz
        "propuesta_inversion": "Propuesta de Inversión",
        "seleccione_nivel": "Seleccione su nivel de experiencia",
        "experiencia_label": "EXPERIENCIA",
        "mas_elegido": "MÁS ELEGIDO",
        "garantia_titulo": "GARANTÍA DE RESERVA",
        "garantia_texto": "Confirmación con el 50% del total. El saldo se cancela al llegar a Cusco. Incluye todos los impuestos bancarios.",
        # Precios - Estrategia Oferta
        "oferta_lanzamiento": "OFERTA DE LANZAMIENTO",
        "tarifas_preferenciales": "TARIFAS PREFERENCIALES POR PERSONA",
        "super_precio": "¡SÚPER PRECIO!",
        "tarifa_nacional": "TARIFA NACIONAL",
        "tarifa_internacional": "TARIFA INTERNACIONAL / CAN",
        "total_por_pasajero": "TOTAL POR PASAJERO",
        "extranjero_label": "Extranjero",
        "can_label": "Comunidad Andina (CAN)",
        "disponibilidad_titulo": "DISPONIBILIDAD",
        "disponibilidad_texto": "Esta tarifa especial está sujeta a cambios según la disponibilidad de espacios al momento de la reserva.",
        "validez_titulo": "VALIDEZ",
        "validez_texto": "Oferta válida para reservas confirmadas en las próximas 48 horas.",
        "nota_experto": "Nota del Experto:",
        # Términos y Condiciones
        "terminos_titulo": "Términos y Condiciones",
        "terminos_subtitulo": "RESUMEN DE POLÍTICAS DE RESERVA",
        "terminos_disclaimer": "Al confirmar su reserva, acepta los términos y condiciones aquí descritos. Para consultas, contáctenos directamente.",
        # Guía del Viajero
        "guia_titulo": "Guía del Viajero",
        "guia_subtitulo": "PREPARA TU AVENTURA",
        "recomendaciones_titulo": "RECOMENDACIONES",
        "equipaje_titulo": "EQUIPAJE",
        "mensaje_final_1": "¡Prepárate para vivir una experiencia inolvidable!",
        "mensaje_final_2": "Cada detalle cuenta para que tu viaje sea perfecto. ¡Nos vemos pronto en Cusco!",
        "notas_adicionales": "Notas Adicionales:"
    }
    try:
        json_labels = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Traduce este objeto de etiquetas de interfaz al {target_lang}, respetando las llaves y solo traduciendo los valores de texto: {json.dumps(labels_base)}"}
            ]
        )
        itinerary_data['labels'] = json.loads(json_labels.choices[0].message.content)
    except:
        itinerary_data['labels'] = labels_base

    return itinerary_data, None

