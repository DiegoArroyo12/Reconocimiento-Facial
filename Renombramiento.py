import os
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import stat
import threading

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
        actualizarMensaje(f"Error leyendo {filepath}: {e}")
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

def procesamientoArchivos(folder_path):
    """Función principal para eliminar duplicados y renombrar."""
    
    # Contar archivos totales para la barra de carga
    mensajeProceso("Escaneando cantidad de archivos...")
    todos_los_archivos = []
    try:
        # Obtenemos lista inicial para saber el total (excluyendo ocultos)
        todos_los_archivos = [
            f for f in os.scandir(folder_path) 
            if f.is_file() and not esOculto(f.path)
        ]
    except Exception as e:
        actualizarMensaje(f"Error de acceso: {e}")
        finalizarProceso()
        return

    total_archivos = len(todos_los_archivos)
    if total_archivos == 0:
        actualizarMensaje("Carpeta vacía o sin archivos visibles.")
        finalizarProceso()
        return

    # Configuramos la barra de progreso
    actualizarProgreso(0, total_archivos)
    actualizarMensaje("--- INICIANDO PROCESO ---")
    
    # Eliminar Duplicados
    mensajeProceso("Buscando y eliminando duplicados...")
    hashes = {}
    files_deleted = 0
    files_processed = 0

    # Recorremos la lista que ya obtuvimos
    for entry in todos_los_archivos:
        files_processed += 1
        
        # Actualizar UI (Barra y Texto)
        actualizarProgreso(files_processed, total_archivos)
        # Mostrar nombre corto para que no sature la vista
        nombre_corto = (entry.name[:40] + '..') if len(entry.name) > 40 else entry.name
        mensajeProceso(f"Procesando ({files_processed}/{total_archivos}): {nombre_corto}")

        file_hash = hashArchivo(entry.path)
        
        if not file_hash: continue

        if file_hash in hashes:
            try:
                os.remove(entry.path)
                actualizarMensaje(f"Eliminado (duplicado): {entry.name}")
                files_deleted += 1
            except Exception as e:
                actualizarMensaje(f"Error al eliminar {entry.name}: {e}")
        else:
            hashes[file_hash] = entry.path

    actualizarMensaje(f"{files_deleted} duplicados eliminados.")
    actualizarMensaje("-----------------------------------")

    # Renombrar
    mensajeProceso("Renombrando archivos restantes...")
    actualizarProgreso(0, 0) # Modo indeterminado (barra rebotando) para esta fase rápida
    iniciarBarraProgreso() 
    
    base_name = os.path.basename(folder_path)
    files_renamed = 0
    
    try:
        # Volvemos a leer el directorio ya limpio
        remaining_files = sorted(
            [f for f in os.scandir(folder_path) if f.is_file() and not esOculto(f.path)],
            key=lambda f: f.name)
    except Exception as e:
        actualizarMensaje(f"Error listando: {e}")
        finalizarProceso()
        return

    # Renombrado Temporal
    temp_files = []
    for i, entry in enumerate(remaining_files):
        _, ext = os.path.splitext(entry.name)
        temp_name = f"__temp_{i}{ext}"
        temp_path = os.path.join(folder_path, temp_name)
        try:
            os.rename(entry.path, temp_path)
            temp_files.append((temp_path, ext))
        except Exception as e:
            actualizarMensaje(f"Error temp: {entry.name}: {e}")

    # Renombrado Final
    for i, (temp_path, ext) in enumerate(temp_files):
        counter_str = "" if i == 0 else str(i)
        final_name = f"{base_name}{counter_str}{ext}"
        final_path = os.path.join(folder_path, final_name)
        try:
            os.rename(temp_path, final_path)
            files_renamed += 1
        except Exception as e:
            actualizarMensaje(f"Error final {final_name}: {e}")

    actualizarMensaje(f"{files_renamed} archivos renombrados.")
    actualizarMensaje("--- PROCESO FINALIZADO ---")
    
    # Llamar a la función de finalización
    finalizarProceso(exito=True)

def actualizarMensaje(mensaje):
    app_log.config(state="normal")
    app_log.insert(tk.END, mensaje + "\n")
    app_log.config(state="disabled")
    app_log.see(tk.END)

def mensajeProceso(texto):
    status_var.set(texto)

def actualizarProgreso(valor, maximo):
    # Configurar máximo si cambió
    if pb['maximum'] != maximo and maximo > 0:
        pb['maximum'] = maximo
    pb['mode'] = 'determinate'
    pb['value'] = valor

def iniciarBarraProgreso():
    pb['mode'] = 'indeterminate'
    pb.start(10)

def finalizarProceso(exito=False):
    # Detener barra y resetear UI
    pb.stop()
    pb['mode'] = 'determinate'
    pb['value'] = 100
    mensajeProceso("Listo.")
    btn_start.config(state="normal")
    
    if exito:
        messagebox.showinfo("Completado", "El proceso ha finalizado con éxito.")

def iniciarProceso():
    """Prepara la GUI e inicia el hilo."""
    folder = selected_folder_path.get()
    if not os.path.isdir(folder):
        messagebox.showerror("Error", "Carpeta no válida.")
        return
        
    confirm = messagebox.askyesno("Confirmar", f"¿Procesar carpeta:\n{folder}?")
    if not confirm: return

    # Bloquear interfaz
    btn_start.config(state="disabled")
    app_log.config(state="normal")
    app_log.delete(1.0, tk.END)
    app_log.config(state="disabled")
    
    # Iniciar Proceso
    t = threading.Thread(target=procesamientoArchivos, args=(folder,))
    t.start()

def interfaz():
    global window
    window = tk.Tk()
    window.title("Renombrar Archivos")
    window.geometry("600x500")
    window.minsize(500, 450)
    
    style = ttk.Style(window)
    try: style.theme_use('clam')
    except tk.TclError: style.theme_use('default')

    style.configure('Success.TButton', font=('Arial', 10, 'bold'),
                    background='#4CAF50', foreground='white')
    style.map('Success.TButton',
              background=[('active', '#5CDA60'), ('hover', '#55C259')],
              foreground=[('disabled', '#cccccc')])

    main_frame = ttk.Frame(window, padding=(20, 10, 20, 20))
    main_frame.pack(fill="both", expand=True)
    main_frame.rowconfigure(3, weight=1)
    main_frame.columnconfigure(0, weight=1)

    # Selección
    select_frame = ttk.Frame(main_frame)
    select_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    select_frame.columnconfigure(1, weight=1)
    
    global selected_folder_path
    selected_folder_path = tk.StringVar(value="Aún no has seleccionado una carpeta")

    ttk.Label(select_frame, text="Carpeta:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky="w", padx=(0, 10))
    ttk.Label(select_frame, textvariable=selected_folder_path, relief="sunken", anchor="w", padding=5).grid(row=0, column=1, sticky="ew")
    ttk.Button(select_frame, text="Seleccionar...", command=seleccionarCarpeta).grid(row=0, column=2, sticky="e", padx=(10, 0))

    # Botón Iniciar
    global btn_start
    btn_start = ttk.Button(main_frame, 
                           text="Iniciar Proceso", 
                           command=iniciarProceso,
                           style='Success.TButton')
    btn_start.grid(row=1, column=0, sticky="ew", pady=(0, 15), ipady=5)

    # Área de Progreso
    progress_frame = ttk.LabelFrame(main_frame, text="Estado del Proceso", padding=(10, 5))
    progress_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
    progress_frame.columnconfigure(0, weight=1)

    # Etiqueta de estado dinámico
    global status_var
    status_var = tk.StringVar(value="Esperando inicio...")
    lbl_status = ttk.Label(progress_frame, textvariable=status_var, font=("Arial", 9), foreground="#555")
    lbl_status.grid(row=0, column=0, sticky="w", pady=(0, 5))

    # Barra de progreso
    global pb
    pb = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate", length=100)
    pb.grid(row=1, column=0, sticky="ew")

    # Log
    log_frame = ttk.Frame(main_frame)
    log_frame.grid(row=3, column=0, sticky="nsew")
    log_frame.rowconfigure(0, weight=1)
    log_frame.columnconfigure(0, weight=1)

    global app_log
    app_log = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=8, 
                                        font=("Courier New", 9), state="disabled")
    app_log.grid(row=0, column=0, sticky="nsew")

    window.mainloop()

def seleccionarCarpeta():
    folder = filedialog.askdirectory()
    if folder: selected_folder_path.set(folder)

# Ejecutar
if __name__ == "__main__":
    interfaz()