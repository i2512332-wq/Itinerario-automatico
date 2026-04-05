# Análisis: Implementación de Traducción con Inteligencia Artificial (OpenAI)

Este documento detalla el análisis arquitectónico necesario para implementar la traducción de los itinerarios mediante IA sin que esto "rompa" o altere la lógica y base de datos actual. 

Actualmente, **ya existe un archivo sólido creado para esta tarea**: `utils/translator.py`. Sin embargo, tal como me pides, **no lo he tocado ni modificado en tu código fuente** para garantizar que tu programa siga en óptimas condiciones. A continuación, presento la metodología para habilitarlo cuando estés listo.

## Estado Actual 

1. **Dependencias:** Tu proyecto ya cuenta con las dependencias necesarias. En el archivo `requirements.txt` aparece `openai`.
2. **Back-end de la Traducción:** Cuentas con un método ya programado llamado `translate_itinerary(itinerary_data, target_lang)` dentro de `utils/translator.py`.
   - Este método ya utiliza el modelo `gpt-4o-mini`. 
   - Genera respuestas estructuradas en formato JSON respetando las variables, asegurando que los IDs, precios numéricos y moneda queden intactos.
   - Tiene integrado un *System Prompt* excelente que prohíbe explícitamente traducir los nombres patrimoniales como "Machu Picchu", o "Qorikancha".
3. **Importación:**  El archivo principal `modules/ventas/ui.py` ya hace la importación en las primeras líneas (`from utils.translator import translate_itinerary`), pero **no se está ejecutando** en ninguna parte del flujo de `ui.py`.

## Estrategia de Implementación en la UI (`modules/ventas/ui.py`)

Para integrar esto suavemente sin romper la generación actual, se deben insertar dos pequeños bloques en `ui.py`.

### Paso 1: Selector Visual de Idioma
En la barra lateral izquierda (Sidebar) o justo al lado de las opciones de "Estrategia de Venta" / "Moneda", se añadiría un *Select Box* para seleccionar el idioma.

```python
# Ejemplo conceptual de cómo iría en la UI
st.markdown("#### 🌍 Idioma del Itinerario")
target_lang = st.selectbox(
    "Selecciona el idioma del PDF final",
    ["Español (Original)", "English", "Português", "Français", "Italiano"]
)
```

### Paso 2: Ejecución Pre-Generación
Actualmente, el botón que genera el PDF o crea el diccionario de datos recopila toda la información en una variable tipo diccionario (generalmente llamada `itinerary_data` u objeto similar) y la pasa de frente a `generate_pdf(itinerary_data)`.

La IA debe inyectarse justo *en medio* como un middleware.

```python
# Ejemplo conceptual del flujo
itinerary_data = construir_diccionario_datos_completos() # Ya lo genera tu sistema

if target_lang != "Español (Original)":
    # Muestra un spinner mientras OpenAI trabaja (Tarda de 5 a 15 segundos)
    with st.spinner(f"🤖 Traducción mágica al {target_lang} en progreso..."):
        # Se envía la data, tu función la traduce y devuelve la nueva data
        itinerary_data, err = translate_itinerary(itinerary_data, target_lang)
        
        if err:
            st.error("Hubo un problema de traducción: " + err)
            # Podrías decidir detener la carga o generar el PDF en español como fallback

# Continúa con la generación regular
ruta_pdf = generate_pdf(itinerary_data)
st.success("PDF Generado!")
```

## Consideraciones Clave para que NADA se Rompa

> [!WARNING]
> La latencia (tiempo de espera) por presionar el botón subirá. Un itinerario de 5 días puede tardarle unos \~10 a 20 segundos extra a la IA para parsear y devolver JSONs consistentes. Es 100% indispensable usar un `st.spinner()` con un mensaje amigable para que el usuario no crea que la app "se ha colgado".

> [!IMPORTANT]
> **API KEY:** Revisa que el archivo `.env` o la configuración de secretos (`st.secrets`) del servidor tenga una declaración explícita como `OPENAI_API_KEY="sk-..."`. Si no está, `translator.py` devolverá un error predeterminado y generará en español.

> [!TIP]
> **Costos:** Como la función `translate_itinerary` utiliza inteligentemente `gpt-4o-mini`, el costo de traducción por itinerario será irrelevante (fracciones pequeñas de centavos de dólar por itinerario). Es un excelente modelo relación precio/rendimiento.

**Conclusión:**
Tu proyecto está listo técnicamente. El motor (traductor) y los componentes (librerías) ya están integrados en los *files* correctos. Solo hace falta inyectar la llamada a la UI con un pequeño condicional de idioma (justo antes de presionar "Generar PDF") para que comience a funcionar en base a parámetros estáticos. ¡Como pediste, no he modificado nada!
