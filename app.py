import os
import subprocess
import tempfile
import zipfile
import streamlit as st

st.set_page_config(
    page_title="Recortador de Videos y Canciones", page_icon="✂️", layout="centered"
)

st.title("✂️ Recortador de Videos y Canciones")
st.markdown(
    "Sube un video largo (como un set de música o concierto de 1:30 hr), define los fragmentos con marcas de tiempo y descárgalos por separado."
)

# 1. Subir video
uploaded_file = st.file_uploader(
    "Sube tu archivo de video (MP4, MKV, MOV, AVI)",
    type=["mp4", "mkv", "mov", "avi"],
)

if uploaded_file is not None:
  # Guardar el video subido en un archivo temporal
  tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
  tfile.write(uploaded_file.read())
  video_path = tfile.name

  st.success("¡Video cargado con éxito!")

  # Mostrar reproductor de video opcional o información básica
  with st.expander("Ver información del archivo"):
    st.write(f"Nombre: {uploaded_file.name}")
    st.write(f"Tamaño: {uploaded_file.size / (1024*1024):.2f} MB")

  st.divider()
  st.subheader("🎵 Define los fragmentos a recortar")
  st.markdown(
    "Agrega los intervalos de tiempo (Formato: `HH:MM:SS` o segundos totales) para"
    " cada canción o parte que quieras extraer."
  )

  # Usar Session State para almacenar la lista de cortes
  if "cortes" not in st.session_state:
    st.session_state.cortes = [{
        "nombre": "Cancion_1",
        "inicio": "00:00:00",
        "fin": "00:03:30",
    }]


  def agregar_corte():
    st.session_state.cortes.append({
        "nombre": f"Cancion_{len(st.session_state.cortes) + 1}",
        "inicio": "00:00:00",
        "fin": "00:00:00",
    })


  def eliminar_corte(index):
    st.session_state.cortes.pop(index)


  # Formulario dinámico para los cortes
  for i, corte in enumerate(st.session_state.cortes):
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    with col1:
      st.session_state.cortes[i]["nombre"] = st.text_input(
          f"Nombre #{i+1}", corte["nombre"], key=f"nombre_{i}"
      )
    with col2:
      st.session_state.cortes[i]["inicio"] = st.text_input(
          f"Inicio #{i+1} (HH:MM:SS)", corte["inicio"], key=f"inicio_{i}"
      )
    with col3:
      st.session_state.cortes[i]["fin"] = st.text_input(
          f"Fin #{i+1} (HH:MM:SS)", corte["fin"], key=f"fin_{i}"
      )
    with col4:
      st.markdown("<br>", unsafe_allow_html=True)
      if len(st.session_state.cortes) > 1:
        st.button(
            "🗑️",
            key=f"del_{i}",
            on_click=eliminar_corte,
            args=(i,),
            help="Eliminar este corte",
        )

  st.button("➕ Agregar otro fragmento", on_click=agregar_corte)

  st.divider()

  # Botón para procesar los recortes
  if st.button(
      "🚀 Procesar y Recortar Fragmentos",
      type="primary",
      use_container_width=True,
  ):
    output_dir = tempfile.mkdtemp()
    archivos_generados = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    total_cortes = len(st.session_state.cortes)

    for i, corte in enumerate(st.session_state.cortes):
      nombre_limpio = "".join(
          c for c in corte["nombre"] if c.isalnum() or c in (" ", "_", "-")
      ).strip()
      nombre_limpio = nombre_limpio.replace(" ", "_") or f"fragmento_{i+1}"
      output_filename = f"{nombre_limpio}.mp4"
      output_filepath = os.path.join(output_dir, output_filename)

      status_text.text(
          f"Procesando ({i+1}/{total_cortes}): {corte['nombre']}..."
      )

      # Comando de FFmpeg optimizado para corte rápido sin re-codificar (-c copy)
      # Nota: Usamos -ss antes y después de -i para máxima precisión y velocidad
      cmd = [
          "ffmpeg",
          "-y",
          "-ss",
          str(corte["inicio"]),
          "-to",
          str(corte["fin"]),
          "-i",
          video_path,
          "-c",
          "copy",
          output_filepath,
      ]

      try:
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        archivos_generados.append((corte["nombre"], output_filepath))
      except subprocess.CalledProcessError as e:
        st.error(
            f"Error al procesar el fragmento '{corte['nombre']}':"
            f" {e.stderr.strip()}"
        )

      progress_bar.progress((i + 1) / total_cortes)

    status_text.text("¡Proceso completado con éxito!")
    st.success("¡Todos los fragmentos han sido recortados!")

    # Opción 1: Descargar como ZIP si hay varios archivos
    if len(archivos_generados) > 1:
      zip_path = os.path.join(output_dir, "fragmentos_recortados.zip")
      with zipfile.ZipFile(zip_path, "w") as zipf:
        for nombre, filepath in archivos_generados:
          zipf.write(filepath, arcname=os.path.basename(filepath))

      with open(zip_path, "rb") as fp:
        st.download_button(
            label="📦 Descargar todos los fragmentos en un ZIP",
            data=fp,
            file_name="fragmentos_recortados.zip",
            mime="application/zip",
            use_container_width=True,
        )

    st.divider()
    st.subheader("📥 Descargar fragmentos individuales")

    for nombre, filepath in archivos_generados:
      if os.path.exists(filepath):
        with open(filepath, "rb") as f:
          st.download_button(
              label=f"⬇️ Descargar: {nombre}.mp4",
              data=f,
              file_name=f"{os.path.basename(filepath)}",
              mime="video/mp4",
          )

    # Limpiar archivo de video original temporal
    if os.path.exists(video_path):
      os.remove(video_path)
