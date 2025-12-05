import os
import hashlib
import stat

class RenamerTool:
    def __init__(self, log_callback=None, progress_callback=None):
        self.log_callback = log_callback
        self.progress_callback = progress_callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def hash_archivo(self, filepath):
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return None

    def es_oculto(self, filepath):
        try:
            if os.path.basename(filepath).startswith('.'): return True
            attrs = os.stat(filepath).st_file_attributes
            if attrs & stat.FILE_ATTRIBUTE_HIDDEN: return True
        except: pass
        return False

    def procesar_carpeta(self, folder_path):
        if not os.path.exists(folder_path):
            self.log(f"Error: Carpeta no existe {folder_path}")
            return

        # Obtener lista total de archivos para la barra
        all_files = [
            os.path.join(folder_path, f) for f in os.listdir(folder_path) 
            if os.path.isfile(os.path.join(folder_path, f)) and not self.es_oculto(os.path.join(folder_path, f))
        ]
        total_files = len(all_files)
        
        if total_files == 0:
            if self.progress_callback: self.progress_callback(100, 100)
            return

        self.log(f"--- Procesando: {os.path.basename(folder_path)} ---")
        
        # ELIMINAR DUPLICADOS (Hashing)
        files_sorted = sorted(all_files)
        hashes = {}
        eliminados = 0
        
        for i, filepath in enumerate(files_sorted):
            # Actualizar barra (Primera mitad del proceso: 0-50%)
            if self.progress_callback:
                self.progress_callback(i, total_files * 2, f"Analizando: {os.path.basename(filepath)}")

            f_hash = self.hash_archivo(filepath)
            if not f_hash: continue
            
            if f_hash in hashes:
                try:
                    os.remove(filepath)
                    eliminados += 1
                    self.log(f"Eliminado duplicado: {os.path.basename(filepath)}")
                except Exception as e:
                    self.log(f"Error borrando: {e}")
            else:
                hashes[f_hash] = filepath

        # RENOMBRAR (Secuencial)
        remaining = sorted([f for f in os.listdir(folder_path) 
                            if os.path.isfile(os.path.join(folder_path, f)) and not self.es_oculto(os.path.join(folder_path, f))])
        
        base_name = os.path.basename(folder_path)
        temp_map = []
        
        # Renombrado temporal
        for i, filename in enumerate(remaining):
            # Barra (50-75%)
            if self.progress_callback:
                current_step = total_files + (i / 2) # calculo aproximado
                self.progress_callback(current_step, total_files * 2, "Renombrando (Temp)...")

            _, ext = os.path.splitext(filename)
            old_path = os.path.join(folder_path, filename)
            temp_path = os.path.join(folder_path, f"__temp_{i}{ext}")
            try:
                os.rename(old_path, temp_path)
                temp_map.append(temp_path)
            except: pass

        # Renombrado final
        renombrados = 0
        for i, temp_path in enumerate(temp_map):
            # Barra (75-100%)
            if self.progress_callback:
                current_step = total_files + (len(remaining)/2) + (i / 2)
                self.progress_callback(current_step, total_files * 2, f"Finalizando: {i+1}/{len(temp_map)}")

            _, ext = os.path.splitext(temp_path)
            counter = "" if i == 0 else str(i)
            new_name = f"{base_name}{counter}{ext}"
            new_path = os.path.join(folder_path, new_name)
            try:
                os.rename(temp_path, new_path)
                renombrados += 1
            except: pass
            
        self.log(f"Proceso finalizado. Duplicados: {eliminados}, Renombrados: {renombrados}")
        
        # Forzar 100%
        if self.progress_callback: self.progress_callback(100, 100, "Completado")