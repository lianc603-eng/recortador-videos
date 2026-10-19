import os
import subprocess
import tempfile
import zipfile
import streamlit as st
import yt_dlp

st.set_page_config(
    page_title="Recortador de Videos y Canciones", page_icon="✂️", layout="centered"
)

st.title("✂️ Recortador de Videos y Canciones")
st.markdown(
    "Sube un video largo o ingresa un enlace de YouTube, define los"
    " fragmentos con marcas de tiempo y descárgalos por separado."
)

# Selección de fuente: Archivo local o YouTube
source_type = st.radio(
    "Selecciona la fuente del video:",
    ["📂 Subir archivo de video", "🔗 Enlace de YouTube"],
    horizontal=True,
)

video_path = None
source_name = ""

if source_type == "📂 Subir archivo de video":
  uploaded_file = st.file_uploader(
      "Sube tu archivo de video (MP4, MKV, MOV, AVI)",
      type=["mp4", "mkv", "mov", "avi"],
  )
  if uploaded_file is not None:
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tfile.write(uploaded_file.read())
    video_path = tfile.name
    source_name = uploaded_file.name
    st.success("¡Video cargado con éxito!")

else:
  youtube_url = st.text_input(
      "Pega el enlace del video de YouTube:",
      placeholder="https://www.youtube.com/watch?v=...",
  )
  if youtube_url:
    if st.button("📥 Descargar video de YouTube", type="primary"):
      output_dir_yt = tempfile.mkdtemp()
      video_path = os.path.join(output_dir_yt, "youtube_video.mp4")

      progress_bar = st.progress(0)
      status_text = st.empty()


      def my_hook(d):
        if d['status'] == 'downloading':
          try:
            total_bytes = d.get('total_bytes') or d.get(
                'total_bytes_estimate'
            , 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            if total_bytes > 0:
              percentage = float(downloaded_bytes) / float(total_bytes)
              progress_bar.progress(min(max(percentage, 0.0), 1.0))
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            status_text.text(
                f'⬇️ Descargando video ligero... | Velocidad: {speed} | Restante'
                f' aprox: {eta}'
            )
          except Exception:
            pass
        elif d['status'] == 'finished':
          progress_bar.progress(1.0)
          status_text.text('✅ Descarga completada con éxito.')


      # Usamos el formato 18 (MP4 360p con audio integrado) para evitar bloqueos y lentitud en la nube
      ydl_opts = {
          'format': '18/best[ext=mp4]/best',
          'outtmpl': video_path,
          'noplaylist': True,
          'progress_hooks': [my_hook],
      }

      try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
          info = ydl.extract_info(youtube_url, download=True)
          source_name = info.get('title', 'Video de YouTube')
        st.success(f'¡Video listo: {source_name}!')
      except Exception as e:
        st.error(
            f'Error al descargar el video de YouTube: {e}. Prueba con otro'
            ' enlace o video más corto.'
        )
        video_path = None

# Si ya tenemos un video cargado o descargado, mostramos la sección de cortes
if video_path and os.path.exists(video_path):
  with st.expander('Ver información del video seleccionado'):
    st.write(f'Fuente: {source_name}')

  st.divider()
  st.subheader('🎵 Define los fragmentos a recortar')
  st.markdown(
      'Agrega los intervalos de tiempo (Formato: `HH:MM:SS` o segundos'
      ' totales) para cada canción o parte que quieras extraer.'
  )

  if 'cortes' not in st.session_state:
    st.session_state.cortes = [{
        'nombre': 'Cancion_1',
        'inicio': '00:00:00',
        'fin': '00:03:30',
    }]


  def agregar_corte():
    st.session_state.cortes.append({
        'nombre': f"Cancion_{len(st.session_state.cortes) + 1}",
        'inicio': '00:00:00',
        'fin': '00:00:00',
    })


  def eliminar_corte(index):
    st.session_state.cortes.pop(index)


  for i, corte in enumerate(st.session_state.cortes):
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    with col1:
      st.session_state.cortes[i]['nombre'] = st.text_input(
          f'Nombre #{i+1}', corte['nombre'], key=f'nombre_{i}'
      )
    with col2:
      st.session_state.cortes[i]['inicio'] = st.text_input(
          f"Inicio #{i+1} (HH:MM:SS)", corte['inicio'], key=f'inicio_{i}'
      )
    with col3:
      st.session_state.cortes[i]['fin'] = st.text_input(
          f"Fin #{i+1} (HH:MM:SS)", corte['fin'], key=f'fin_{i}'
      )
    with col4:
      st.markdown('<br>', unsafe_allow_html=True)
      if len(st.session_state.cortes) > 1:
        st.button(
            '🗑️',
            key=f'del_{i}',
            on_click=eliminar_corte,
            args=(i,),
            help='Eliminar este corte',
        )

  st.button('➕ Agregar otro fragmento', on_click=agregar_corte)

  st.divider()

  if st.button(
      '🚀 Procesar y Recortar Fragmentos',
      type='primary',
      use_container_width=True,
  ):
    output_dir = tempfile.mkdtemp()
    archivos_generados = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    total_cortes = len(st.session_state.cortes)

    for i, corte in enumerate(st.session_state.cortes):
      nombre_limpio = ''.join(
          c for c in corte['nombre'] if c.isalnum() or c in (' ', '_', '-')
      ).strip()
      nombre_limpio = nombre_limpio.replace(' ', '_') or f'fragmento_{i+1}'
      output_filename = f'{nombre_limpio}.mp4'
      output_filepath = os.path.join(output_dir, output_filename)

      status_text.text(
          f"Procesando ({i+1}/{total_cortes}): {corte['nombre']}..."
      )

      cmd = [
          'ffmpeg',
          '-y',
          '-ss',
          str(corte['inicio']),
          '-to',
          str(corte['fin']),
          '-i',
          video_path,
          '-c',
          'copy',
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
        archivos_generados.append((corte['nombre'], output_filepath))
      except subprocess.CalledProcessError as e:
        st.error(
            f"Error al procesar el fragmento '{corte['nombre']}':"
            f" {e.stderr.strip()}"
        )

      progress_bar.progress((i + 1) / total_cortes)

    status_text.text('¡Proceso completado con éxito!')
    st.success('¡Todos los fragmentos han sido recortados!')

    if len(archivos_generados) > 1:
      zip_path = os.path.join(output_dir, 'fragmentos_recortados.zip')
      with zipfile.ZipFile(zip_path, 'w') as zipf:
        for nombre, filepath in archivos_generados:
          zipf.write(filepath, arcname=os.path.basename(filepath))

      with open(zip_path, 'rb') as fp:
        st.download_button(
            label='📦 Descargar todos los fragmentos en un ZIP',
            data=fp,
            file_name='fragmentos_recortados.zip',
            mime='application/zip',
            use_container_width=True,
        )

    st.divider()
    st.subheader('📥 Descargar fragmentos individuales')

    for nombre, filepath in archivos_generados:
      if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
          st.download_button(
              label=f'⬇️ Descargar: {nombre}.mp4',
              data=f,
              file_name=f'{os.path.basename(filepath)}',
              mime='video/mp4',
          )

    if os.path.exists(video_path):
      os.remove(video_path)
