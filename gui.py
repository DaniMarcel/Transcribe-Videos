import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
from batch_transcribe_to_pdf_1 import process_videos

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Transcriptor de Videos")
        self.geometry("800x700")  # Aumenté el tamaño para acomodar más campos

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(1, weight=1)

        # --- Widgets ---

        # API Key
        self.api_key_label = ctk.CTkLabel(self, text="Deepgram API Key:")
        self.api_key_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.api_key_entry = ctk.CTkEntry(self, placeholder_text="Introduce tu API Key de Deepgram", width=400)
        self.api_key_entry.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")

        # Input folder
        self.input_dir_label = ctk.CTkLabel(self, text="Carpeta de Videos:")
        self.input_dir_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.input_dir_entry = ctk.CTkEntry(self, placeholder_text="Selecciona una carpeta...", width=400)
        self.input_dir_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        self.input_dir_button = ctk.CTkButton(self, text="Seleccionar", command=self.select_input_dir)
        self.input_dir_button.grid(row=1, column=2, padx=20, pady=10)

        # Output folder
        self.output_dir_label = ctk.CTkLabel(self, text="Carpeta de Salida:")
        self.output_dir_label.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.output_dir_entry = ctk.CTkEntry(self, placeholder_text="Selecciona una carpeta...", width=400)
        self.output_dir_entry.grid(row=2, column=1, padx=20, pady=10, sticky="ew")
        self.output_dir_button = ctk.CTkButton(self, text="Seleccionar", command=self.select_output_dir)
        self.output_dir_button.grid(row=2, column=2, padx=20, pady=10)

        # Language
        self.language_label = ctk.CTkLabel(self, text="Idioma (opcional):")
        self.language_label.grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.language_entry = ctk.CTkEntry(self, placeholder_text="ej: es, en, pt-BR (default: es)", width=400)
        self.language_entry.grid(row=3, column=1, padx=20, pady=10, sticky="ew")

        # Model
        self.model_label = ctk.CTkLabel(self, text="Modelo (opcional):")
        self.model_label.grid(row=4, column=0, padx=20, pady=10, sticky="w")
        self.model_entry = ctk.CTkEntry(self, placeholder_text="ej: nova-3 (default: nova-3)", width=400)
        self.model_entry.grid(row=4, column=1, padx=20, pady=10, sticky="ew")

        # Smart Format
        self.smart_format_var = ctk.BooleanVar(value=True)
        self.smart_format_check = ctk.CTkCheckBox(self, text="Usar smart_format (default: sí)", variable=self.smart_format_var)
        self.smart_format_check.grid(row=5, column=1, padx=20, pady=10, sticky="w")

        # Overwrite
        self.overwrite_var = ctk.BooleanVar(value=False)
        self.overwrite_check = ctk.CTkCheckBox(self, text="Sobrescribir archivos existentes", variable=self.overwrite_var)
        self.overwrite_check.grid(row=6, column=1, padx=20, pady=10, sticky="w")

        # PDF Minimal
        self.pdf_minimal_var = ctk.BooleanVar(value=False)
        self.pdf_minimal_check = ctk.CTkCheckBox(self, text="PDF minimal (solo texto, sin encabezado)", variable=self.pdf_minimal_var)
        self.pdf_minimal_check.grid(row=7, column=1, padx=20, pady=10, sticky="w")

        # Start button
        self.start_button = ctk.CTkButton(self, text="Iniciar Transcripción", command=self.start_transcription_thread)
        self.start_button.grid(row=8, column=1, padx=20, pady=20)

        # Log textbox
        self.log_textbox = ctk.CTkTextbox(self, width=700, height=250)
        self.log_textbox.grid(row=9, column=0, columnspan=3, padx=20, pady=10, sticky="nsew")
        self.log_textbox.configure(state="disabled")

    def select_input_dir(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.input_dir_entry.delete(0, "end")
            self.input_dir_entry.insert(0, folder_selected)

    def select_output_dir(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_dir_entry.delete(0, "end")
            self.output_dir_entry.insert(0, folder_selected)

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")
        self.update_idletasks()

    def start_transcription_thread(self):
        api_key = self.api_key_entry.get()
        input_dir = self.input_dir_entry.get()
        output_dir = self.output_dir_entry.get()
        language = self.language_entry.get() or None
        model = self.model_entry.get() or "nova-3"
        smart_format = self.smart_format_var.get()
        overwrite = self.overwrite_var.get()
        pdf_minimal = self.pdf_minimal_var.get()

        if not api_key or not input_dir or not output_dir:
            messagebox.showerror("Error", "Por favor, completa los campos obligatorios (API Key, carpetas).")
            return

        if not os.path.isdir(input_dir):
            messagebox.showerror("Error", "La carpeta de videos no es válida.")
            return
        
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir)
                self.log(f"Carpeta de salida creada en: {output_dir}")
            except OSError as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta de salida: {e}")
                return

        self.start_button.configure(state="disabled", text="Procesando...")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

        thread = threading.Thread(target=self.run_transcription, args=(api_key, input_dir, output_dir, language, model, smart_format, overwrite, pdf_minimal))
        thread.start()

    def run_transcription(self, api_key, input_dir, output_dir, language, model, smart_format, overwrite, pdf_minimal):
        try:
            process_videos(
                api_key=api_key,
                input_dir_str=input_dir,
                output_dir_str=output_dir,
                log_callback=self.log,
                language=language,
                model=model,
                smart_format=smart_format,
                overwrite=overwrite,
                pdf_minimal=pdf_minimal,
                # Opcionales: txt_dir_str, json_dir_str, pdf_dir_str, font_regular, font_bold se dejan como None (usarán defaults)
            )
            self.log("\n¡Proceso completado!")
            messagebox.showinfo("Éxito", "Todos los videos han sido transcritos.")
        except Exception as e:
            self.log(f"\nERROR: {e}")
            messagebox.showerror("Error", f"Ocurrió un error durante la transcripción: {e}")
        finally:
            self.start_button.configure(state="normal", text="Iniciar Transcripción")

if __name__ == "__main__":
    app = App()
    app.mainloop()
