import os
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import stat

def hashArchivo(filepath):
    """Calcula el hash MD5 de un archivo. Lee en bloques para archivos grandes."""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            # Lee el archivo en trozos de 4096 bytes
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        mensajeProceso(f"Error leyendo {filepath}: {e}")
        return None
    
def esOculto(filepath):
    """
    Comprueba si un archivo es oculto.
    - En Windows, comprueba el atributo de archivo.
    - En macOS/Linux, comprueba si empieza con un punto (.).
    """
    try:
        # Primero, comprobar la convención de "dot-file" (macOS/Linux)
        if os.path.basename(filepath).startswith('.'): return True
        
        # Segundo, comprobar el atributo de archivo "oculto" de Windows
        attrs = os.stat(filepath).st_file_attributes
        if attrs & stat.FILE_ATTRIBUTE_HIDDEN: return True
            
    # Si hay cualquier error (ej. permisos), trátalo como "no oculto"
    except Exception: pass
        
    return False

def procesamientoArchivos(folder_path, log_widget):
    """Función principal para eliminar duplicados y renombrar."""
    
    if not folder_path:
        messagebox.showwarning("Advertencia", "Por favor, selecciona una carpeta primero.")
        return

    mensajeProceso("--- INICIANDO PROCESO ---")
    
    # Eliminar Duplicados por Hash
    mensajeProceso("Buscando duplicados...")
    hashes = {}
    files_deleted = 0
    files_scanned = 0

    for entry in os.scandir(folder_path):
        if entry.is_file():
            
            # Omitir si es oculto
            if esOculto(entry.path): continue

            files_scanned += 1
            file_hash = hashArchivo(entry.path)
            
            if not file_hash:
                continue

            if file_hash in hashes:
                try:
                    os.remove(entry.path)
                    mensajeProceso(f"Eliminado (duplicado): {entry.name}")
                    files_deleted += 1
                except Exception as e:
                    mensajeProceso(f"Error al eliminar {entry.name}: {e}")
            else:
                hashes[file_hash] = entry.path

    mensajeProceso(f"{files_deleted} duplicados eliminados de {files_scanned} archivos escaneados.")
    mensajeProceso("-------------------------------------------------------------------------------")

    # Renombrar Archivos Restantes
    mensajeProceso(f"Renombrando archivos restantes...")
    base_name = os.path.basename(folder_path)
    files_renamed = 0
    
    try:
        # Filtrar ocultos de la lista de renombrado
        remaining_files = sorted(
            [f for f in os.scandir(folder_path) if f.is_file() and not esOculto(f.path)],
            key=lambda f: f.name)
    except Exception as e:
        mensajeProceso(f"Error listando archivos para renombrar: {e}")
        return

    temp_files = []
    for i, entry in enumerate(remaining_files):
        _, ext = os.path.splitext(entry.name)
        temp_name = f"__temp_{i}{ext}"
        temp_path = os.path.join(folder_path, temp_name)
        
        try:
            os.rename(entry.path, temp_path)
            temp_files.append((temp_path, ext))
        except Exception as e:
            mensajeProceso(f"Error en renombrado temporal de {entry.name}: {e}")

    for i, (temp_path, ext) in enumerate(temp_files):
        counter_str = "" if i == 0 else str(i)
        
        final_name = f"{base_name}{counter_str}{ext}"
        final_path = os.path.join(folder_path, final_name)
        
        try:
            os.rename(temp_path, final_path)
            files_renamed += 1
        except Exception as e:
            mensajeProceso(f"Error en renombrado final a {final_name}: {e}")

    mensajeProceso(f"{files_renamed} archivos renombrados.")
    mensajeProceso("--- PROCESO FINALIZADO ---")
    messagebox.showinfo("Completado", "El proceso ha finalizado con éxito.")


# Configuración de la Interfaz Gráfica (GUI)
def interfaz():
    window = tk.Tk()
    window.title("Renombrar Archivos")
    window.geometry("600x450")
    window.minsize(500, 400)
    
    style = ttk.Style(window)
    
    try: style.theme_use('clam')
    except tk.TclError: style.theme_use('default')

    # Estilo para el botón principal (verde)
    style.configure('Success.TButton', 
                    font=('Arial', 10, 'bold'),
                    background='#4CAF50',
                    foreground='white')
    
    # Mapeo para cuando el ratón está encima (hover) o presionado (active)
    style.map('Success.TButton',
              background=[('active', '#5CDA60'),
                          ('hover', '#55C259')],
              foreground=[('disabled', '#F0F0F0')])
    
    # Frame principal con padding exterior
    main_frame = ttk.Frame(window, padding=(20, 10, 20, 20))
    main_frame.pack(fill="both", expand=True)

    # Configurar la cuadrícula
    main_frame.rowconfigure(2, weight=1)
    main_frame.columnconfigure(0, weight=1)

    # Frame de Selección de Carpeta
    select_frame = ttk.Frame(main_frame)
    select_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
    select_frame.columnconfigure(1, weight=1)
    
    global selected_folder_path
    selected_folder_path = tk.StringVar()
    selected_folder_path.set("Aún no has seleccionado una carpeta")

    # Etiqueta "Carpeta:"
    lbl_folder_text = ttk.Label(select_frame, text="Carpeta:", font=('Arial', 10, 'bold'))
    lbl_folder_text.grid(row=0, column=0, sticky="w", padx=(0, 10))

    # Etiqueta que muestra la ruta
    lbl_folder_path = ttk.Label(select_frame, textvariable=selected_folder_path, 
                                relief="sunken", anchor="w", padding=(5, 5),
                                font=('Arial', 9))
    lbl_folder_path.grid(row=0, column=1, sticky="ew")

    # Botón "Seleccionar..."
    btn_select = ttk.Button(select_frame, text="Seleccionar...", command=seleccionarCarpeta)
    btn_select.grid(row=0, column=2, sticky="e", padx=(10, 0))

    # Botón de Iniciar
    btn_start = ttk.Button(main_frame, 
                           text="Iniciar Proceso (Eliminar Duplicados y Renombrar)", 
                           command=renombramiento,
                           style='Success.TButton') # Aplicar el estilo verde
    btn_start.grid(row=1, column=0, sticky="ew", pady=(0, 15), ipady=8) # ipady lo hace más alto

    # Área de Registro (Log)
    log_frame = ttk.Frame(main_frame, padding=(0, 0, 0, 0))
    log_frame.grid(row=2, column=0, sticky="nsew")
    log_frame.rowconfigure(0, weight=1)
    log_frame.columnconfigure(0, weight=1)

    log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, 
                                         font=("Courier New", 9),
                                         state="disabled",
                                         relief="solid", borderwidth=1)
    log_area.grid(row=0, column=0, sticky="nsew")

    # Hacemos el log_area accesible globalmente
    global app_log
    app_log = log_area

    window.mainloop()

def seleccionarCarpeta():
    """Abre el diálogo para seleccionar carpeta."""
    folder = filedialog.askdirectory()
    if folder:
        selected_folder_path.set(folder)
        mensajeProceso(f"Carpeta seleccionada: {folder}")

def renombramiento():
    """Inicia el proceso en la carpeta seleccionada."""
    folder = selected_folder_path.get()
    if not os.path.isdir(folder):
        messagebox.showerror("Error", "La ruta seleccionada no es una carpeta válida.")
        return
        
    # Pedir confirmación
    confirm = messagebox.askyesno("Confirmación", 
        f"¿Estás seguro de que quieres procesar la carpeta:\n{folder}\n\n"
        "Esto eliminará permanentemente archivos duplicados y renombrará el resto. "
        "Esta acción no se puede deshacer.")
        
    if confirm:
        # Ejecutamos el procesamiento
        try: procesamientoArchivos(folder, app_log)
        except Exception as e:
            mensajeProceso(f"--- ERROR INESPERADO ---: {e}")
            messagebox.showerror("Error Crítico", f"Ha ocurrido un error: {e}")

def mensajeProceso(message):
    """Añade un mensaje al área de registro."""
    app_log.config(state="normal")
    app_log.insert(tk.END, message + "\n")
    app_log.config(state="disabled")
    app_log.see(tk.END) # Auto-scroll al final


# Ejecutar la aplicación
if __name__ == "__main__":
    interfaz()