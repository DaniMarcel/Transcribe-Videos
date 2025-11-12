# Transcriptor de Videos

Esta aplicación permite transcribir videos y archivos de audio en lote usando la API de Deepgram, generando transcripciones en formato TXT, JSON y PDF. Incluye una interfaz gráfica (GUI) para facilitar el uso.

## Requisitos

- **Sistema operativo**: Windows (compatible con versiones recientes).
- **Python** (opcional, solo si ejecutas desde código fuente): Versión 3.8 o superior.
- **ffmpeg**: Herramienta necesaria para extraer audio de videos. Descárgala de [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html), instálala y agrégala al PATH de tu sistema. Verifica con `ffmpeg -version` en la terminal.
- **API Key de Deepgram**: Obtén una en [https://console.deepgram.com/](https://console.deepgram.com/).

## Instalación

### Opción 1: Ejecutable (.exe) - Recomendado para usuarios finales

1. Descarga el archivo `gui.exe` (proporcionado por el desarrollador).
2. Ejecuta `gui.exe` directamente. No requiere instalación adicional de Python.

### Opción 2: Desde código fuente

1. Clona o descarga el repositorio.
2. Instala dependencias: `pip install -r requirements.txt` (incluye `deepgram`, `fpdf`, `python-dotenv`, `customtkinter`).
3. Asegúrate de que `ffmpeg` esté instalado y en PATH.

## Uso

### Interfaz Gráfica (GUI)

1. Ejecuta `gui.exe` (o `python gui.py` desde código fuente).
2. Ingresa tu API Key de Deepgram.
3. Selecciona la carpeta con videos/audio de entrada.
4. Selecciona la carpeta de salida (se crearán subcarpetas para TXT, JSON y PDF).
5. Opcional: Configura idioma (ej: "es"), modelo (ej: "nova-3"), y opciones como smart_format o sobrescribir archivos.
6. Presiona "Iniciar Transcripción". Los logs aparecerán en la interfaz.

### Script de Lote (Línea de Comandos)

Ejecuta desde terminal: python batch_transcribe_to_pdf_1.py -i /ruta/carpeta/videos -o /ruta/carpeta/salida --language es

Opciones disponibles: `-h` para ayuda. Requiere API key en archivo `.env` (DEEPGRAM_API_KEY=tu_clave).

## Notas

- Formatos soportados: MP4, MOV, MKV, AVI, MPG, MPEG, M4V, WEBM, WAV, MP3, M4A, AAC, FLAC, OGG, OPUS, WMA.
- La transcripción usa el modelo "nova-3" por defecto con smart_format activado.
- Para PDFs, intenta usar fuentes Unicode; si no, sanitiza caracteres.
- Si vendes este script, incluye términos de uso: los usuarios deben proporcionar su propia API key de Deepgram.

## Licencia

Este proyecto es de código abierto bajo la licencia MIT. Consulta el archivo LICENSE para detalles. Para uso comercial, contacta al desarrollador.

## Soporte

Si encuentras problemas, verifica que `ffmpeg` esté instalado y la API key sea válida. Para errores específicos, revisa los logs de la GUI.
