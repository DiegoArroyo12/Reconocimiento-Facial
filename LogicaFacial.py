import os
import numpy as np
import threading
from deepface import DeepFace

class FaceBrain:
    def __init__(self, output_dir, log_callback=None, progress_callback=None):
        self.output_dir = output_dir
        self.known_embeddings = {} 
        self.log_callback = log_callback
        self.progress_callback = progress_callback 
        self.is_loading = False
        self.model_name = "ArcFace"
        self.detector_backend = "retinaface" 
        self.threshold = 0.65 

    def log(self, msg):
        if self.log_callback: 
            try: self.log_callback(msg)
            except: print(msg)
        else: print(msg)

    def cargar_referencias_async(self):
        thread = threading.Thread(target=self._load_references)
        thread.daemon = True
        thread.start()

    def _load_references(self):
        self.is_loading = True
        
        # Enviamos -1 para decir "Cargando Motor"
        if self.progress_callback: self.progress_callback(-1, 100, "Iniciando Motor...")
        
        self.log(f"IA: Iniciando motor {self.detector_backend} (esto toma tiempo)...")
        
        if not os.path.exists(self.output_dir):
            self.log("IA: Carpeta destino no existe.")
            self.is_loading = False
            return

        # Contar Personas (Carpetas)
        personas = [p for p in os.listdir(self.output_dir) if os.path.isdir(os.path.join(self.output_dir, p))]
        total_personas = len(personas)
        
        # Empezamos el proceso lineal
        for i, person_name in enumerate(personas):
            if self.progress_callback: 
                self.progress_callback(i, total_personas, f"Aprendiendo: {person_name}")

            person_dir = os.path.join(self.output_dir, person_name)
            self.known_embeddings[person_name] = []
            
            images_loaded = 0
            # Cargar imágenes de esta persona
            for img_name in os.listdir(person_dir):
                if img_name.lower().endswith(('.jpg', '.png', '.jpeg')):
                    img_path = os.path.join(person_dir, img_name)
                    try:
                        embedding_objs = DeepFace.represent(
                            img_path=img_path,
                            model_name=self.model_name,
                            enforce_detection=True,
                            detector_backend=self.detector_backend
                        )
                        embedding = embedding_objs[0]["embedding"]
                        self.known_embeddings[person_name].append(embedding)
                        images_loaded += 1
                    except Exception:
                        pass
                    if images_loaded >= 5: break
            
            if images_loaded > 0:
                self.log(f"IA: Aprendido -> {person_name}")
            
        self.is_loading = False
        self.log(f"IA: Carga Finalizada. {total_personas} personas listas.")
        
        # Forzar 100% al final
        if self.progress_callback: self.progress_callback(total_personas, total_personas, "IA Activa")

    def find_cosine_distance(self, source_representation, test_representation):
        a = np.matmul(np.transpose(source_representation), test_representation)
        b = np.sum(np.multiply(source_representation, source_representation))
        c = np.sum(np.multiply(test_representation, test_representation))
        return 1 - (a / (np.sqrt(b) * np.sqrt(c)))

    def sugerir_persona(self, image_path):
        if self.is_loading: return "Cargando Motor..."
        if not self.known_embeddings: return "Sin Referencias"

        try:
            target_objs = DeepFace.represent(
                img_path=image_path,
                model_name=self.model_name,
                enforce_detection=True,
                detector_backend=self.detector_backend
            )
            target_embedding = target_objs[0]["embedding"]
        except:
            return "Rostro no visible"

        best_match = None
        min_distance = float('inf')

        for name, embeddings_list in self.known_embeddings.items():
            for ref_embedding in embeddings_list:
                distance = self.find_cosine_distance(target_embedding, ref_embedding)
                if distance < min_distance:
                    min_distance = distance
                    best_match = name

        if min_distance < self.threshold:
            confianza = round((1 - min_distance) * 100, 1)
            return f"{best_match} ({confianza}%)"
        else:
            return f"Desconocido"