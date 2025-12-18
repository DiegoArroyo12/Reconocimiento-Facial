import tkinter as tk
from tkinter import Toplevel, Canvas, Button, messagebox
from PIL import Image, ImageTk

class EditorImagen:
    def __init__(self, master, image_path, callback_guardado):
        self.master = master
        self.image_path = image_path
        self.callback_guardado = callback_guardado
        
        self.window = Toplevel(master)
        self.window.title("Editor de Recorte")
        self.window.configure(bg="#202124")
        
        # Maximizar ventana para tener espacio
        w, h = master.winfo_screenwidth() - 100, master.winfo_screenheight() - 100
        self.window.geometry(f"{w}x{h}+50+50")

        # Cargar imagen original
        self.original_image = Image.open(image_path)
        self.original_w, self.original_h = self.original_image.size
        
        # Calcular tamaño para mostrar en pantalla (sin deformar)
        self.display_w = w - 50
        self.display_h = h - 100
        
        ratio = min(self.display_w/self.original_w, self.display_h/self.original_h)
        self.new_w = int(self.original_w * ratio)
        self.new_h = int(self.original_h * ratio)
        
        # Imagen redimensionada para vista previa
        self.resized_image = self.original_image.resize((self.new_w, self.new_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.resized_image)

        # UI
        self.canvas = Canvas(self.window, width=self.new_w, height=self.new_h, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(pady=20)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        # Variables de dibujo
        self.rect_id = None
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None

        # Eventos del Mouse
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # Botones
        frame_btns = tk.Frame(self.window, bg="#202124")
        frame_btns.pack(fill="x", pady=10)
        
        tk.Button(frame_btns, text="💾 Guardar Recorte (Sobrescribir)", command=self.guardar, 
                  bg="#5865F2", fg="white", font=("Segoe UI", 10, "bold"), padx=20).pack(side="top")
        
        tk.Label(frame_btns, text="Dibuja un rectángulo sobre el área que quieres conservar", 
                 bg="#202124", fg="#b9bbbe").pack(side="top", pady=5)

    def on_press(self, event):
        # Guardar coordenadas iniciales
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        # Borrar rectangulo anterior si existe
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        
        # Crear nuevo rectángulo (borde rojo)
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="#faa61a", width=3)

    def on_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        
        # Actualizar tamaño del rectángulo
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        self.end_x = self.canvas.canvasx(event.x)
        self.end_y = self.canvas.canvasy(event.y)

    def guardar(self):
        if not self.rect_id:
            messagebox.showwarning("Error", "Primero dibuja un rectángulo.")
            return

        # 1. Ordenar coordenadas (por si dibujó de derecha a izquierda)
        x1 = min(self.start_x, self.end_x)
        y1 = min(self.start_y, self.end_y)
        x2 = max(self.start_x, self.end_x)
        y2 = max(self.start_y, self.end_y)

        # 2. Calcular factor de escala (Real vs Pantalla)
        scale_x = self.original_w / self.new_w
        scale_y = self.original_h / self.new_h

        # 3. Traducir coordenadas a la imagen original
        real_x1 = int(x1 * scale_x)
        real_y1 = int(y1 * scale_y)
        real_x2 = int(x2 * scale_x)
        real_y2 = int(y2 * scale_y)

        # 4. Recortar
        try:
            cropped = self.original_image.crop((real_x1, real_y1, real_x2, real_y2))
            cropped.save(self.image_path) # Sobrescribir
            
            messagebox.showinfo("Éxito", "Imagen recortada correctamente.")
            self.window.destroy()
            if self.callback_guardado:
                self.callback_guardado() # Recargar en la app principal
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")