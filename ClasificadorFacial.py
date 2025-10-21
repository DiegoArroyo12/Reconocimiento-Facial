import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import face_recognition
import numpy as np
import cv2
from datetime import datetime

class FacialImageClassifier:
    def __init__(self, known_faces_dir, unknown_files_dir, output_dir):
        self.known_faces_dir = known_faces_dir
        self.unknown_files_dir = unknown_files_dir
        self.output_dir = output_dir
        self.known_encodings = {}
        self.image_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        self.video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        self.log_callback = None
        self.is_running = False

    def set_log_callback(self, callback):
        self.log_callback = callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def load_known_faces(self):
        self.log("📸 Cargando rostros conocidos...")
        
        for person_name in os.listdir(self.known_faces_dir):
            person_dir = os.path.join(self.known_faces_dir, person_name)
            
            if not os.path.isdir(person_dir):
                continue
            
            self.log(f"  Procesando: {person_name}")
            encodings = []
            
            for image_name in os.listdir(person_dir):
                if not any(image_name.lower().endswith(fmt) for fmt in self.image_formats):
                    continue
                
                image_path = os.path.join(person_dir, image_name)
                try:
                    image = face_recognition.load_image_file(image_path)
                    face_encodings = face_recognition.face_encodings(image)
                    
                    if face_encodings:
                        encodings.append(face_encodings[0])
                    else:
                        self.log(f"    ⚠️  No se detectó rostro en: {image_name}")
                except Exception as e:
                    self.log(f"    ❌ Error al procesar {image_name}: {e}")
            
            if encodings:
                self.known_encodings[person_name] = encodings
                self.log(f"    ✓ {len(encodings)} rostro(s) codificado(s)")

    def extract_faces_from_video(self, video_path, sample_rate=30):
        faces = []
        try:
            cap = cv2.VideoCapture(video_path)
            frame_count = 0
            processed = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % sample_rate == 0:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    face_encodings = face_recognition.face_encodings(rgb_frame)
                    if face_encodings:
                        faces.extend(face_encodings)
                        processed += 1
                
                frame_count += 1
            
            cap.release()
            return faces
        except Exception as e:
            self.log(f"    ❌ Error al procesar video: {e}")
            return []

    def identify_file(self, file_encodings):
        if not file_encodings:
            return None
        
        best_match = None
        best_distance = 0.6
        person_votes = {}
        
        for encoding in file_encodings:
            for person_name, known_encodings in self.known_encodings.items():
                distances = face_recognition.face_distance(known_encodings, encoding)
                min_distance = np.min(distances)
                
                if min_distance < best_distance:
                    person_votes[person_name] = person_votes.get(person_name, 0) + 1
        
        if person_votes:
            best_match = max(person_votes, key=person_votes.get)
        
        return best_match

    def classify_files(self):
        if not self.known_encodings:
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
                    image = face_recognition.load_image_file(file_path)
                    file_encodings = face_recognition.face_encodings(image)
                else:
                    self.log(f"  🎬 Procesando video: {file_name}")
                    file_encodings = self.extract_faces_from_video(file_path)
                
                if not file_encodings:
                    self.log(f"     ⚠️  No se detectaron rostros")
                    unclassified_count += 1
                    continue
                
                best_match = self.identify_file(file_encodings)
                
                if best_match:
                    output_person_dir = os.path.join(self.output_dir, best_match)
                    os.makedirs(output_person_dir, exist_ok=True)
                    
                    output_path = os.path.join(output_person_dir, file_name)
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
        self.log("=" * 60)
        self.log("🎭 Clasificador de Imágenes y Videos por Rostro")
        self.log(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("=" * 60)
        
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
        self.root.title("🎭 Clasificador Facial")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        self.classifier = None
        self.is_processing = False
        
        self.setup_ui()
        self.known_dir = tk.StringVar(value="./artistas_referencia")
        self.unknown_dir = tk.StringVar(value="./archivos_a_clasificar")
        self.output_dir = tk.StringVar(value="./archivos_clasificados")

    def setup_ui(self):
        # Frame superior para directorios
        top_frame = tk.LabelFrame(self.root, text="Configuración de Directorios", padx=10, pady=10, font=("Arial", 10, "bold"))
        top_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=False)
        
        # Directorio de rostros conocidos
        tk.Label(top_frame, text="Rostros Conocidos:", font=("Arial", 9)).grid(row=0, column=0, sticky="w")
        self.known_entry = tk.Entry(top_frame, width=50, textvariable=self.known_dir)
        self.known_entry.grid(row=0, column=1, padx=5, sticky="ew")
        tk.Button(top_frame, text="Examinar", command=self.browse_known_dir, width=10).grid(row=0, column=2, padx=5)
        
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
        self.status_var = tk.StringVar(value="Listo")
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, 
                              font=("Arial", 9), bg="#e0e0e0")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

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
        
        known = self.known_dir.get()
        unknown = self.unknown_dir.get()
        output = self.output_dir.get()
        
        if not os.path.exists(known):
            messagebox.showerror("Error", f"No existe: {known}")
            return
        
        if not os.path.exists(unknown):
            messagebox.showerror("Error", f"No existe: {unknown}")
            return
        
        self.classifier = FacialImageClassifier(known, unknown, output)
        self.classifier.set_log_callback(self.log)
        self.classifier.is_running = True
        self.is_processing = True
        
        self.start_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.status_var.set("▶️ Procesando...")
        
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
        self.status_var.set("✅ Listo")
        messagebox.showinfo("Completado", "El proceso ha finalizado. Revisa el log para más detalles.")

if __name__ == "__main__":
    root = tk.Tk()
    gui = ClassifierGUI(root)
    root.mainloop()