import os
import tensorflow as tf

def main():
    modelo_keras_path = "models/keras/modelo_inventario.keras"
    modelo_tflite_path = "models/tflite/modelo_inventario.tflite"

    # Verificar que el modelo Keras existe
    if not os.path.exists(modelo_keras_path):
        print(f"Error: El modelo de Keras no se encuentra en {modelo_keras_path}")
        return

    # 1. Cargar el modelo Keras
    print(f"Cargando modelo de Keras desde {modelo_keras_path}...")
    model = tf.keras.models.load_model(modelo_keras_path)

    # 2. Instanciar el conversor
    print("Instanciando el conversor de TensorFlow Lite...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    # 3. Convertir el modelo
    print("Convirtiendo el modelo a formato TFLite (esto puede tomar unos momentos)...")
    tflite_model = converter.convert()

    # Asegurar que el directorio de destino existe
    os.makedirs(os.path.dirname(modelo_tflite_path), exist_ok=True)

    # 4. Guardar el archivo binario
    print(f"Guardando el archivo TFLite en {modelo_tflite_path}...")
    with open(modelo_tflite_path, "wb") as f:
        f.write(tflite_model)

    # 5. Obtener el tamaño en MB e imprimir mensaje de éxito
    size_bytes = os.path.getsize(modelo_tflite_path)
    size_mb = size_bytes / (1024 * 1024)
    print(f"\n¡Conversión completada con éxito!")
    print(f"Ruta del archivo TFLite: {modelo_tflite_path}")
    print(f"Tamaño del modelo: {size_mb:.2f} MB")

if __name__ == '__main__':
    main()
