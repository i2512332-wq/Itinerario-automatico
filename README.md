# Sistema de Gestión de Itinerarios - Motor Híbrido 🚀

Este proyecto utiliza una arquitectura de alto rendimiento combinando **Streamlit** para la interfaz de usuario y **FastAPI** como el motor de lógica (Brain) para cálculos pesados, traducciones y generación de PDFs.

## 🏗️ Arquitectura
- **Frontend**: Streamlit (Maneja la UI y el estado de sesión).
- **Backend / API**: FastAPI + Uvicorn (Procesa precios, traducción con IA y renderizado de PDF vía Playwright).
- **Base de Datos**: Supabase (PostgreSQL).

## 🛠️ Instalación Local

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

2. Configurar variables de entorno (en un archivo `.env` o similar):
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `OPENAI_API_KEY` (Para traducciones con IA)

3. Ejecutar la aplicación:
   **Opción A (Recomendada):** Solo ejecuta el frontend. El sistema arrancará la API automáticamente en segundo plano.
   ```bash
   streamlit run App_Ventas.py
   ```

   **Opción B (Manual):** Abre dos terminales.
   - Terminal 1: `uvicorn app_api:app --reload --port 8000`
   - Terminal 2: `streamlit run App_Ventas.py`

## ☁️ Despliegue en Streamlit Cloud

1. Sube este repositorio a GitHub.
2. En Streamlit Cloud, conecta el repositorio.
3. **IMPORTANTE (Secrets):** Copia tus variables de entorno en la sección "Secrets" del panel de Streamlit Cloud.
4. El archivo `packages.txt` instalará automáticamente las dependencias de sistema para que los PDFs funcionen correctamente.

## 📄 Notas Técnicas
- El backend escucha en `127.0.0.1:8000` para comunicación interna ultra-rápida.
- La sesión de usuario es persistente por **7 días** gracias al buffer de cookies mejorado.
