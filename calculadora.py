import streamlit as st
import streamlit.components.v1 as components
import os

# --- Configuración de la Página de Streamlit ---
st.set_page_config(
    page_title="Calculadora Eléctrica Profesional",
    page_icon="⚡",
    layout="wide" # Ocupa todo el ancho de la pantalla
)

# --- Función para cargar y mostrar el archivo HTML ---
def serve_html(file_path):
    """
    Esta función lee un archivo HTML y lo muestra en Streamlit.
    Ajusta la altura del componente para que ocupe la mayor parte de la pantalla.
    """
    try:
        # Abre el archivo HTML y lo lee
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            # Usa st.components.v1.html para renderizar el contenido HTML.
            # 'scrolling=True' permite el scroll dentro del iframe si el contenido es muy largo.
            # 'height=1500' le da un tamaño inicial generoso para minimizar el doble scroll.
            components.html(html_content, height=1500, scrolling=True)
    except FileNotFoundError:
        # Muestra un error amigable si el archivo index.html no se encuentra.
        st.error(f"Error: No se encontró el archivo '{file_path}'. Asegúrate de que 'index.html' esté en el mismo directorio que 'app.py'.")

# --- Punto de Entrada Principal ---
if __name__ == "__main__":
    # Define el nombre del archivo HTML que queremos mostrar.
    html_file = "index.html"
    
    # Obtiene la ruta del directorio actual donde se está ejecutando el script de Python.
    # Esto asegura que encuentre el 'index.html' sin importar desde dónde se ejecute.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, html_file)
    
    # Llama a la función para servir el archivo.
    serve_html(file_path)

