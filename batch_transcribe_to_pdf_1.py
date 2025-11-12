#!/usr/bin/env python3
"""
Batch transcribe all videos (and audio files) in a folder using Deepgram,
then save each transcript as .txt, .json, and .pdf.

Usage:
  1) Install deps (ideally in a virtualenv):
       pip install -r requirements.txt
  2) Create a .env file with your API key:
       DEEPGRAM_API_KEY=your_key_here
  3) Run:
       python batch_transcribe_to_pdf.py -i /path/to/folder -o /path/to/out --language es

Notes:
  - Requires ffmpeg in your PATH to extract audio from video files.
  - By default uses model "nova-3" with smart_format enabled.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Callable

from dotenv import load_dotenv
from fpdf import FPDF

# Deepgram SDK

def _sanitize_for_core_fonts(s: str) -> str:
    # Replace common Unicode punctuation with ASCII approximations for core fonts
    replacements = {
        '—': '-', '–': '-', '…': '...', '“': '"', '”': '"', '‘': "'", '’': "'",
        '\u00a0': ' ', '\u200b': ''
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    try:
        return s.encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        return s



def _find_unicode_font_paths() -> Tuple[Optional[Path], Optional[Path]]:
    """
    Try to find a Unicode-capable TTF font on the system (Windows) or in a local ./fonts folder.
    Returns (regular_ttf, bold_ttf). If bold isn't found, returns (regular, None).
    """
    # 1) Local ./fonts next to this script
    here = Path(__file__).resolve()
    fonts_dir = here.with_name("fonts")
    local_candidates = [
        ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
        ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf"),
        ("Inter-Regular.ttf", "Inter-Bold.ttf"),
    ]
    for reg, bold in local_candidates:
        reg_p = fonts_dir / reg
        bold_p = fonts_dir / bold
        if reg_p.exists():
            return reg_p, bold_p if bold_p.exists() else None

    # 2) Common Windows fonts
    win_fonts = Path("C:/Windows/Fonts")
    if win_fonts.exists():
        pairs = [
            ("segoeui.ttf", "segoeuib.ttf"),
            ("arial.ttf", "arialbd.ttf"),
            ("calibri.ttf", "calibrib.ttf"),
            ("times.ttf", "timesbd.ttf"),  # Times New Roman
        ]
        for reg, bold in pairs:
            reg_p = win_fonts / reg
            bold_p = win_fonts / bold
            if reg_p.exists():
                return reg_p, bold_p if bold_p.exists() else None

    # 3) Nothing found
    return None, None


from deepgram import DeepgramClient, PrerecordedOptions, DeepgramClientOptions

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".mpg", ".mpeg", ".m4v", ".webm"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}

def has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False

def extract_audio_with_ffmpeg(input_path: Path, tmp_dir: Path) -> Path:
    """
    Extract mono 16kHz WAV audio from a video (or audio) file using ffmpeg.
    Returns the path to the generated WAV file.
    """
    output_wav = tmp_dir / f"{input_path.stem}.wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        str(output_wav),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_wav

def clean_filename(name: str) -> str:
    safe = "".join(ch for ch in name if ch.isalnum() or ch in (" ", "-", "_", "."))
    return safe.strip().replace(" ", "_")


def to_pdf(text: str, pdf_path: Path, title: str, meta: Optional[dict] = None, 
           font_regular: Optional[str] = None, font_bold: Optional[str] = None, 
           minimal: bool = False) -> None:
    """
    Save a plain text transcript to a readable PDF. Tries to use a Unicode font;
    if it falls back to core fonts, sanitizes unsupported characters.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Prefer user-provided font paths
    chosen_reg = Path(font_regular) if font_regular else None
    chosen_bold = Path(font_bold) if font_bold else None

    reg_ttf, auto_bold = _find_unicode_font_paths()
    if chosen_reg is not None:
        reg_ttf = chosen_reg
    bold_ttf = chosen_bold if chosen_bold is not None else auto_bold

    using_core = False
    if reg_ttf is not None:
        try:
            pdf.add_font("U", "", str(reg_ttf), uni=True)
            if bold_ttf is not None and Path(bold_ttf).exists():
                pdf.add_font("U", "B", str(bold_ttf), uni=True)
                header_font = ("U", "B", 16)
            else:
                header_font = ("U", "", 16)
            body_font = ("U", "", 12)
            meta_font = ("U", "", 10)
        except Exception:
            using_core = True
    else:
        using_core = True

    if using_core:
        header_font = ("Helvetica", "B", 16)
        body_font = ("Helvetica", "", 12)
        meta_font = ("Helvetica", "", 10)

    # Header (optional)
    if not minimal:
        pdf.set_font(*header_font)
        title_safe = title.replace("—", "-").replace("–", "-")
        if 'Helvetica' in header_font[0]:
            title_safe = _sanitize_for_core_fonts(title_safe)
        pdf.cell(0, 10, title_safe, ln=True)

        pdf.set_font(*meta_font)
        gen_line = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if 'Helvetica' in meta_font[0]:
            gen_line = _sanitize_for_core_fonts(gen_line)
        pdf.cell(0, 8, gen_line, ln=True)

        if meta and "info" in meta:
            info_line = str(meta["info"])
            if 'Helvetica' in meta_font[0]:
                info_line = _sanitize_for_core_fonts(info_line)
            pdf.multi_cell(0, 6, f"Info: {info_line}")
        pdf.ln(3)

    # Body
    pdf.set_font(*body_font)
    for line in text.splitlines():
        out = line
        if 'Helvetica' in body_font[0]:
            out = _sanitize_for_core_fonts(out)
        if not out.strip():
            pdf.ln(4)
        else:
            pdf.multi_cell(0, 6, out)

    pdf.output(str(pdf_path))
def extract_transcript_from_response(response_obj) -> Tuple[str, dict, Optional[float]]:
    """
    Try to pull a clean transcript string and confidence from the Deepgram response.
    Returns (transcript_text, full_json_dict, confidence or None)
    """
    data = {}
    try:
        # Deepgram Python SDK v3 returns a model object; convert it to a dict.
        # Using to_dict() is more direct than to_json() -> json.loads().
        data = response_obj.to_dict()
    except Exception:
        # Fallback if it's already a dict-like object for some reason.
        if hasattr(response_obj, 'keys'):
            data = response_obj
        else:
            # If it's not a dict and not a response object, we can't do much.
            return "[Error: Could not process response object]", {}, None

    transcript = ""
    confidence = None

    try:
        alt = data["results"]["channels"][0]["alternatives"][0]
        transcript = alt.get("paragraphs", {}).get("transcript") or alt.get("transcript", "") or ""
        confidence = alt.get("confidence")
    except Exception:
        # Leave transcript empty if unexpected shape
        pass

    return transcript, data, confidence

def transcribe_audio_file(dg: DeepgramClient, audio_path: Path, model: str, language: Optional[str], smart_format: bool):
    """
    Send a local audio file buffer to Deepgram for transcription.
    """
    with open(audio_path, "rb") as f:
        buffer_data = f.read()

    payload = {"buffer": buffer_data}

    # Build options, explicitly requesting paragraphs for clean transcripts.
    # Language can be None; the SDK handles it (API will default to auto-detection).
    options = PrerecordedOptions(
        model=model,
        smart_format=smart_format,
        paragraphs=True,
        language=language,
    )

    # Call API using the `prerecorded` endpoint, which is the correct method
    # for pre-recorded files in recent SDK versions.
    response = dg.listen.prerecorded.v("1").transcribe_file(
        payload,
        options
    )
    return response

def process_videos(
    api_key: str,
    input_dir_str: str,
    output_dir_str: str,
    log_callback: Callable[[str], None],
    language: Optional[str] = "es",
    model: str = "nova-3",
    smart_format: bool = True,
    overwrite: bool = False,
    pdf_minimal: bool = False,
    txt_dir_str: Optional[str] = None,
    json_dir_str: Optional[str] = None,
    pdf_dir_str: Optional[str] = None,
    font_regular: Optional[str] = None,
    font_bold: Optional[str] = None,
):
    """
    Main logic for processing files. Can be called from a GUI or CLI.
    """
    in_dir = Path(input_dir_str).expanduser().resolve()
    out_dir = Path(output_dir_str).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Subcarpetas por tipo
    txt_dir = Path(txt_dir_str).expanduser().resolve() if txt_dir_str else (out_dir / 'txt')
    json_dir = Path(json_dir_str).expanduser().resolve() if json_dir_str else (out_dir / 'json')
    pdf_dir = Path(pdf_dir_str).expanduser().resolve() if pdf_dir_str else (out_dir / 'pdf')
    txt_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    if not in_dir.exists() or not in_dir.is_dir():
        raise FileNotFoundError(f"Input path '{in_dir}' is not a valid directory.")

    # Initialize client
    config = DeepgramClientOptions(verbose=0) # Suppress SDK logs
    dg = DeepgramClient(api_key, config)

    # Check for ffmpeg
    ffmpeg_ok = has_ffmpeg()
    if not ffmpeg_ok:
        log_callback("ADVERTENCIA: ffmpeg no se encontró. Los archivos de video se procesarán directamente (puede ser más lento).")

    files = sorted([p for p in in_dir.iterdir() if p.is_file() and p.suffix.lower() in (VIDEO_EXTS | AUDIO_EXTS)])
    if not files:
        log_callback("No se encontraron archivos de video o audio compatibles.")
        return

    log_callback(f"Se encontraron {len(files)} archivos. Iniciando transcripción...\n")

    for idx, src in enumerate(files, start=1):
        stem = clean_filename(src.stem)
        txt_path = txt_dir / f"{stem}.txt"
        json_path = json_dir / f"{stem}.deepgram.json"
        pdf_path = pdf_dir / f"{stem}.pdf"

        if not overwrite and txt_path.exists() and pdf_path.exists() and json_path.exists():
            log_callback(f"[{idx}/{len(files)}] Omitiendo '{src.name}' (ya procesado).")
            continue

        log_callback(f"[{idx}/{len(files)}] Procesando: {src.name}")

        use_path = src
        is_video = src.suffix.lower() in VIDEO_EXTS
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            if is_video and ffmpeg_ok:
                try:
                    use_path = extract_audio_with_ffmpeg(src, td_path)
                    log_callback(f"  - Audio extraído: {use_path.name}")
                except subprocess.CalledProcessError:
                    log_callback(f"  ! Falló la extracción de audio con ffmpeg para '{src.name}'. Se enviará el archivo original.")
                    use_path = src
            
            try:
                response = transcribe_audio_file(dg, use_path, model, language, smart_format)
            except Exception as e:
                log_callback(f"  ! Error de transcripción: {e}")
                continue

        transcript_text, full_json, confidence = extract_transcript_from_response(response)

        if not transcript_text.strip():
            transcript_text = "[Transcripción vacía]\n(Revisa el archivo .deepgram.json para ver la respuesta completa.)"

        try:
            with open(json_path, "w", encoding="utf-8") as fjson:
                json.dump(full_json, fjson, ensure_ascii=False, indent=2)
        except Exception:
            with open(json_path, "w", encoding="utf-8") as fjson:
                fjson.write(str(response))

        with open(txt_path, "w", encoding="utf-8") as ftxt:
            ftxt.write(transcript_text)

        meta = {"info": f"Model={model} | Language={language or 'auto'} | Confidence={confidence if confidence is not None else 'n/a'}"}
        try:
            to_pdf(transcript_text, pdf_path, title=f"Transcripción - {src.stem}", meta=meta, font_regular=font_regular, font_bold=font_bold, minimal=pdf_minimal)
        except Exception as e:
            log_callback(f"  ! No se pudo escribir el PDF: {e}")

        log_callback(f"  ✓ Guardado:\n     - {txt_path.name}\n     - {json_path.name}\n     - {pdf_path.name}\n")

    log_callback("Proceso finalizado.")


def main():
    parser = argparse.ArgumentParser(description="Batch transcribe videos/audio in a folder with Deepgram and export PDFs.")
    parser.add_argument("-i", "--input", required=True, help="Input folder with video/audio files.")
    parser.add_argument("-o", "--output", default="out_transcripts", help="Output folder (default: out_transcripts)")
    parser.add_argument("--language", default="es", help="Optional language code (e.g., es, en, pt-BR). Default: es.")
    parser.add_argument("--model", default="nova-3", help='Deepgram model (default: "nova-3")')
    parser.add_argument("--no-smart-format", action="store_false", dest="smart_format", help="Disable Deepgram smart_format.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs.")
    parser.add_argument("--pdf-minimal", action="store_true", help="PDF solo con el texto (sin encabezado/metadatos).")
    parser.add_argument("--txt-dir", default=None, help="Directorio para .txt (por defecto: <output>/txt)")
    parser.add_argument("--json-dir", default=None, help="Directorio para .json (por defecto: <output>/json)")
    parser.add_argument("--pdf-dir", default=None, help="Directorio para .pdf (por defecto: <output>/pdf)")
    parser.add_argument("--font-regular", default=None, help="Path to a Unicode TTF/OTF font file for body/title")
    parser.add_argument("--font-bold", default=None, help="Optional path to matching bold TTF/OTF font file")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("ERROR: Missing DEEPGRAM_API_KEY. Put it in a .env file or export it in your environment.", file=sys.stderr)
        sys.exit(1)

    try:
        process_videos(
            api_key=api_key,
            input_dir_str=args.input,
            output_dir_str=args.output,
            log_callback=print,
            language=args.language,
            model=args.model,
            smart_format=args.smart_format,
            overwrite=args.overwrite,
            pdf_minimal=args.pdf_minimal,
            txt_dir_str=args.txt_dir,
            json_dir_str=args.json_dir,
            pdf_dir_str=args.pdf_dir,
            font_regular=args.font_regular,
            font_bold=args.font_bold,
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    

if __name__ == "__main__":
    main()