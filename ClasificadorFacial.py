import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
from deepface import DeepFace
import cv2
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class FacialImageClassifier:
    def __init__(self, known_faces_dir, unknown_files_dir, output_dir, use_output_as_reference=False, max_reference_images=5):
        self.known_faces_dir = known_faces_dir
        self.unknown_files_dir = unknown_files_dir
        self.output_dir = output_dir
        self.use_output_as_reference = use_output_as_reference
        self.max_reference_images = max_reference_images
        self.known_faces_data = {}
        self.image_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        self.video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        self.log_callback = None
        self.is_running = False
        self.model_name = "VGG-Face"
        self.distance_metric = "cosine"

    def set_log_callback(self, callback):
        self.log_callback = callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
    
    def is_safe_path(self, path):
        """Verifica si una ruta es segura para DeepFace (sin caracteres especiales)"""
        # Caracteres problemáticos para DeepFace
        problematic_chars = ['á', 'é', 'í', 'ó', 'ú', 'ñ', 'ü', 'Á', 'É', 'Í', 'Ó', 'Ú', 'Ñ', 'Ü']
        
        for char in problematic_chars:
            if char in path:
                return False
        
        # Verificar si hay espacios en la ruta (también puede causar problemas)
        # Esto es más permisivo ya que algunos sistemas los manejan bien
        return True

    def load_known_faces(self):
        """Carga rostros conocidos desde la carpeta de referencia o destino"""
        reference_dir = self.output_dir if self.use_output_as_reference else self.known_faces_dir
        
        self.log(f"📸 Cargando rostros conocidos desde: {os.path.basename(reference_dir)}")
        
        if not os.path.exists(reference_dir):
            self.log(f"❌ No existe la carpeta: {reference_dir}")
            return
        
        for person_name in os.listdir(reference_dir):
            person_dir = os.path.join(reference_dir, person_name)
            
            if not os.path.isdir(person_dir):
                continue
            
            self.log(f"  Procesando: {person_name}")
            face_images = []
            image_count = 0
            
            for image_name in os.listdir(person_dir):
                # Limitar número de imágenes de referencia
                if image_count >= self.max_reference_images:
                    break
                
                # Ignorar archivos ocultos de sistema (macOS, Windows)
                if image_name.startswith('.') or image_name.startswith('._'):
                    continue
                
                # Ignorar archivos Thumbs.db de Windows
                if image_name.lower() in ['thumbs.db', 'desktop.ini']:
                    continue
                
                if not any(image_name.lower().endswith(fmt) for fmt in self.image_formats):
                    continue
                
                image_path = os.path.join(person_dir, image_name)
                
                # Verificar si la ruta tiene caracteres problemáticos
                if not self.is_safe_path(image_path):
                    self.log(f"    ⚠️  Ruta con caracteres especiales (se omitirá): {image_name}")
                    self.log(f"        Sugerencia: Renombra la carpeta sin espacios/acentos")
                    continue
                
                try:
                    # Verificar que hay un rostro en la imagen
                    faces = DeepFace.extract_faces(
                        img_path=image_path,
                        detector_backend='opencv',
                        enforce_detection=False
                    )
                    
                    if faces and len(faces) > 0:
                        face_images.append(image_path)
                        image_count += 1
                    else:
                        self.log(f"    ⚠️  No se detectó rostro en: {image_name}")
                except Exception as e:
                    self.log(f"    ❌ Error al procesar {image_name}: {str(e)[:80]}")
            
            if face_images:
                self.known_faces_data[person_name] = face_images
                self.log(f"    ✓ {len(face_images)} imagen(es) de referencia")

    def extract_faces_from_video(self, video_path, sample_rate=30):
        """Extrae fotogramas del video y los guarda temporalmente"""
        temp_frames = []
        try:
            cap = cv2.VideoCapture(video_path)
            frame_count = 0
            temp_dir = os.path.join(os.path.dirname(video_path), "temp_frames")
            os.makedirs(temp_dir, exist_ok=True)
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % sample_rate == 0:
                    temp_frame_path = os.path.join(temp_dir, f"frame_{frame_count}.jpg")
                    cv2.imwrite(temp_frame_path, frame)
                    temp_frames.append(temp_frame_path)
                
                frame_count += 1
            
            cap.release()
            return temp_frames
        except Exception as e:
            self.log(f"    ❌ Error al procesar video: {e}")
            return []

    def identify_person(self, image_path, is_temp_frame=False):
        """Identifica a qué persona pertenece el rostro usando DeepFace"""
        try:
            best_match = None
            best_distance = float('inf')
            threshold = 0.6
            
            for person_name, reference_images in self.known_faces_data.items():
                for ref_image in reference_images:
                    try:
                        result = DeepFace.verify(
                            img1_path=image_path,
                            img2_path=ref_image,
                            model_name=self.model_name,
                            distance_metric=self.distance_metric,
                            detector_backend='opencv',
                            enforce_detection=False
                        )
                        
                        distance = result['distance']
                        
                        if distance < threshold and distance < best_distance:
                            best_distance = distance
                            best_match = person_name
                            
                    except Exception:
                        continue
            
            return best_match
            
        except Exception as e:
            if not is_temp_frame:
                self.log(f"    ⚠️ Error en identificación: {e}")
            return None

    def classify_files(self):
        if not self.known_faces_data:
            self.log("❌ No hay rostros conocidos cargados.")
            return
        
        self.log("\n🔍 Clasificando archivos...")
        classified_count = 0
        unclassified_count = 0
        
        for file_name in os.listdir(self.unknown_files_dir):
            if not self.is_running:
                self.log("⏸️  Proceso cancelado por el usuario")
                break
            
            file_path = os.path.join(self.unknown_files_dir, file_name)
            
            if not os.path.isfile(file_path):
                continue
            
            file_lower = file_name.lower()
            is_image = any(file_lower.endswith(fmt) for fmt in self.image_formats)
            is_video = any(file_lower.endswith(fmt) for fmt in self.video_formats)
            
            if not (is_image or is_video):
                continue
            
            try:
                if is_image:
                    self.log(f"  📷 Procesando imagen: {file_name}")
                    best_match = self.identify_person(file_path)
                    
                else:
                    self.log(f"  🎬 Procesando video: {file_name}")
                    temp_frames = self.extract_faces_from_video(file_path)
                    
                    if not temp_frames:
                        self.log(f"     ⚠️  No se pudieron extraer fotogramas")
                        unclassified_count += 1
                        continue
                    
                    # Analizar múltiples frames y usar votación
                    person_votes = {}
                    for frame_path in temp_frames[:10]:
                        match = self.identify_person(frame_path, is_temp_frame=True)
                        if match:
                            person_votes[match] = person_votes.get(match, 0) + 1
                    
                    # Limpiar frames temporales
                    for frame_path in temp_frames:
                        try:
                            os.remove(frame_path)
                        except:
                            pass
                    
                    # Eliminar directorio temporal
                    temp_dir = os.path.dirname(temp_frames[0]) if temp_frames else None
                    if temp_dir and os.path.exists(temp_dir):
                        try:
                            os.rmdir(temp_dir)
                        except:
                            pass
                    
                    best_match = max(person_votes, key=person_votes.get) if person_votes else None
                
                if best_match:
                    output_person_dir = os.path.join(self.output_dir, best_match)
                    os.makedirs(output_person_dir, exist_ok=True)
                    
                    output_path = os.path.join(output_person_dir, file_name)
                    
                    # Verificar si el archivo ya existe en destino (evitar sobrescribir)
                    if os.path.exists(output_path):
                        base, ext = os.path.splitext(file_name)
                        counter = 1
                        while os.path.exists(output_path):
                            output_path = os.path.join(output_person_dir, f"{base}_{counter}{ext}")
                            counter += 1
                    
                    shutil.move(file_path, output_path)
                    
                    self.log(f"     ✓ Movido a: {best_match}")
                    classified_count += 1
                else:
                    self.log(f"     ❌ No coincide con ninguna persona")
                    unclassified_count += 1
                    
            except Exception as e:
                self.log(f"     ❌ Error al procesar: {e}")
                unclassified_count += 1
        
        self.log(f"\n📊 Resumen:")
        self.log(f"  ✓ Clasificados: {classified_count}")
        self.log(f"  ❌ No clasificados: {unclassified_count}")
        self.log("✅ Proceso completado")

    def run(self):
        mode = "Carpeta Destino" if self.use_output_as_reference else "Carpeta Separada"
        self.log("=" * 60)
        self.log("🎭 Clasificador de Imágenes y Videos por Rostro (DeepFace)")
        self.log(f"Modo: {mode}")
        self.log(f"Límite de imágenes de referencia: {self.max_reference_images}")
        self.log(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Modelo: {self.model_name}")
        self.log("=" * 60)
        
        if self.use_output_as_reference:
            if not os.path.exists(self.output_dir):
                self.log(f"❌ No existe: {self.output_dir}")
                return
        else:
            if not os.path.exists(self.known_faces_dir):
                self.log(f"❌ No existe: {self.known_faces_dir}")
                return
        
        if not os.path.exists(self.unknown_files_dir):
            self.log(f"❌ No existe: {self.unknown_files_dir}")
            return
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.load_known_faces()
        self.classify_files()


class ClassifierGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎭 Clasificador Facial - DeepFace")
        self.root.geometry("900x750")
        self.root.resizable(True, True)
        self.classifier = None
        self.is_processing = False
        
        self.known_dir = tk.StringVar(value="./artistas_referencia")
        self.unknown_dir = tk.StringVar(value="./archivos_a_clasificar")
        self.output_dir = tk.StringVar(value="./archivos_clasificados")
        self.mode_var = tk.StringVar(value="separate")
        self.max_ref_images = tk.IntVar(value=5)
        
        self.setup_ui()
        self.toggle_mode()

    def setup_ui(self):
        # Frame para modo de operación
        mode_frame = tk.LabelFrame(self.root, text="Modo de Operación", padx=10, pady=10, font=("Arial", 10, "bold"))
        mode_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Radiobutton(mode_frame, text="📁 Modo 1: Usar carpeta destino como referencia (1 sola ruta)", 
                       variable=self.mode_var, value="unified", command=self.toggle_mode,
                       font=("Arial", 9)).pack(anchor='w', pady=2)
        tk.Label(mode_frame, text="   → Las imágenes de referencia están en las subcarpetas de destino", 
                 font=("Arial", 8), fg="gray").pack(anchor='w', padx=20)
        
        tk.Radiobutton(mode_frame, text="📂 Modo 2: Carpeta de referencia separada (2 rutas distintas)", 
                       variable=self.mode_var, value="separate", command=self.toggle_mode,
                       font=("Arial", 9)).pack(anchor='w', pady=2)
        tk.Label(mode_frame, text="   → Tienes una carpeta aparte solo con imágenes de referencia", 
                 font=("Arial", 8), fg="gray").pack(anchor='w', padx=20)
        
        # Frame superior para directorios
        top_frame = tk.LabelFrame(self.root, text="Configuración de Directorios", padx=10, pady=10, font=("Arial", 10, "bold"))
        top_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=False)
        
        # Directorio de rostros conocidos (solo en modo separado)
        self.known_label = tk.Label(top_frame, text="Rostros Conocidos:", font=("Arial", 9))
        self.known_label.grid(row=0, column=0, sticky="w")
        self.known_entry = tk.Entry(top_frame, width=50, textvariable=self.known_dir)
        self.known_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.known_btn = tk.Button(top_frame, text="Examinar", command=self.browse_known_dir, width=10)
        self.known_btn.grid(row=0, column=2, padx=5)
        
        # Directorio de archivos a clasificar
        tk.Label(top_frame, text="Archivos a Clasificar:", font=("Arial", 9)).grid(row=1, column=0, sticky="w", pady=5)
        self.unknown_entry = tk.Entry(top_frame, width=50, textvariable=self.unknown_dir)
        self.unknown_entry.grid(row=1, column=1, padx=5, sticky="ew")
        tk.Button(top_frame, text="Examinar", command=self.browse_unknown_dir, width=10).grid(row=1, column=2, padx=5)
        
        # Directorio de salida
        tk.Label(top_frame, text="Directorio de Salida:", font=("Arial", 9)).grid(row=2, column=0, sticky="w", pady=5)
        self.output_entry = tk.Entry(top_frame, width=50, textvariable=self.output_dir)
        self.output_entry.grid(row=2, column=1, padx=5, sticky="ew")
        tk.Button(top_frame, text="Examinar", command=self.browse_output_dir, width=10).grid(row=2, column=2, padx=5)
        
        # Configuración de límite de imágenes
        tk.Label(top_frame, text="Máx. imágenes de referencia:", font=("Arial", 9)).grid(row=3, column=0, sticky="w", pady=5)
        spinbox = tk.Spinbox(top_frame, from_=1, to=20, textvariable=self.max_ref_images, width=10, font=("Arial", 9))
        spinbox.grid(row=3, column=1, sticky="w", padx=5)
        tk.Label(top_frame, text="(por persona)", font=("Arial", 8), fg="gray").grid(row=3, column=1, sticky="w", padx=80)
        
        top_frame.columnconfigure(1, weight=1)
        
        # Frame de botones
        btn_frame = tk.Frame(self.root, padx=10, pady=10)
        btn_frame.pack(fill=tk.X)
        
        self.start_btn = tk.Button(btn_frame, text="▶️ Iniciar Clasificación", command=self.start_classification, 
                                    bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), padx=20, pady=10)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = tk.Button(btn_frame, text="⏹️ Cancelar", command=self.cancel_classification, 
                                     bg="#f44336", fg="white", font=("Arial", 11, "bold"), padx=20, pady=10, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = tk.Button(btn_frame, text="🗑️ Limpiar Log", command=self.clear_log, 
                                    bg="#FF9800", fg="white", font=("Arial", 11, "bold"), padx=20, pady=10)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Frame para el log
        log_frame = tk.LabelFrame(self.root, text="📋 Registro de Actividad", padx=10, pady=10, font=("Arial", 10, "bold"))
        log_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=100, font=("Courier", 9), 
                                                   bg="#f5f5f5", fg="#333333")
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Barra de estado
        self.status_var = tk.StringVar(value="Listo - Usando DeepFace")
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, 
                              font=("Arial", 9), bg="#e0e0e0")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def toggle_mode(self):
        """Habilita/deshabilita la carpeta de rostros conocidos según el modo"""
        if self.mode_var.get() == "unified":
            # Modo 1: Usar carpeta destino como referencia
            self.known_label.config(state='disabled', fg='gray')
            self.known_entry.config(state='disabled')
            self.known_btn.config(state='disabled')
        else:
            # Modo 2: Carpetas separadas
            self.known_label.config(state='normal', fg='black')
            self.known_entry.config(state='normal')
            self.known_btn.config(state='normal')

    def browse_known_dir(self):
        path = filedialog.askdirectory(title="Selecciona la carpeta de Rostros Conocidos")
        if path:
            self.known_dir.set(path)

    def browse_unknown_dir(self):
        path = filedialog.askdirectory(title="Selecciona la carpeta de Archivos a Clasificar")
        if path:
            self.unknown_dir.set(path)

    def browse_output_dir(self):
        path = filedialog.askdirectory(title="Selecciona la carpeta de Salida")
        if path:
            self.output_dir.set(path)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def start_classification(self):
        if self.is_processing:
            messagebox.showwarning("Advertencia", "Ya hay un proceso en marcha")
            return
        
        use_output_as_ref = (self.mode_var.get() == "unified")
        known = self.known_dir.get()
        unknown = self.unknown_dir.get()
        output = self.output_dir.get()
        
        # Validaciones según el modo
        if not use_output_as_ref:
            if not os.path.exists(known):
                messagebox.showerror("Error", f"No existe: {known}")
                return
        else:
            if not os.path.exists(output):
                messagebox.showerror("Error", f"No existe la carpeta destino: {output}")
                return
        
        if not os.path.exists(unknown):
            messagebox.showerror("Error", f"No existe: {unknown}")
            return
        
        self.classifier = FacialImageClassifier(
            known, 
            unknown, 
            output, 
            use_output_as_reference=use_output_as_ref,
            max_reference_images=self.max_ref_images.get()
        )
        self.classifier.set_log_callback(self.log)
        self.classifier.is_running = True
        self.is_processing = True
        
        self.start_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        mode_text = "Modo Unificado" if use_output_as_ref else "Modo Separado"
        self.status_var.set(f"▶️ Procesando ({mode_text})...")
        
        thread = threading.Thread(target=self._run_classification)
        thread.daemon = True
        thread.start()

    def _run_classification(self):
        try:
            self.classifier.run()
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
        finally:
            self.finish_classification()

    def cancel_classification(self):
        if self.classifier:
            self.classifier.is_running = False
            self.log("\n⏸️ Cancelando proceso...")

    def finish_classification(self):
        self.is_processing = False
        self.start_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.status_var.set("✅ Listo - Usando DeepFace")
        messagebox.showinfo("Completado", "El proceso ha finalizado. Revisa el log para más detalles.")

if __name__ == "__main__":
    root = tk.Tk()
    gui = ClassifierGUI(root)
    root.mainloop()