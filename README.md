# Streamlit Dashboard con Google Sheets

Este proyecto es un dashboard construido con Streamlit que se conecta a Google Sheets usando la API de Google.

## Estructura del proyecto
- `src/` - Código principal de la app Streamlit
- `utils/` - Utilidades y módulos auxiliares
- `config/` - Archivos de configuración y credenciales
- `static/` - Recursos estáticos (imágenes, etc)

## Instalación
1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Coloca tus credenciales de Google en la carpeta `config/`.
3. Ejecuta la app:
   ```bash
   streamlit run src/app.py
   ```

## Notas
- Asegúrate de habilitar la API de Google Sheets y descargar el archivo de credenciales JSON.
