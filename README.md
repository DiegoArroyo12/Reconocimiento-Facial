# Reconocimiento-Facial
Organizador de fotos por reconocimiento facial con Python

**Dependencias:**

```
pip install deepface tf-keras opencv-python pillow
```

## Ajustes que puedes hacer:
- `threshold = 0.6` (Baja este valor si es muy estricto a 0.4 - 0.5), sube si es muy permisivo (0.7 - 0.8).
- Cambiar el modelo: se ocupa el modelo `VGG-Face` que es el más preciso, pero puedes optar por estas otras opciones:
- `Facenet` - Más rápido
- `OpenFace` - Balance entre velocidad y precisión
- `DeepFace` - Modelo original


## Cómo funcionan los videos
El parámetro `sample_rate=30` significa que analiza 1 de cada 30 fotogramas. Puedes ajustarlo: 

- Valor bajo (5 - 10): Más análisis pero más lento
- Valor alto (50+): Más rápido pero menos preciso

Si quieres cambiar la precisión, modifica esta línea:
```
file_encodings = self.extract_faces_from_video(file_path, sample_rate=15)  # Analiza más fotogramas
```