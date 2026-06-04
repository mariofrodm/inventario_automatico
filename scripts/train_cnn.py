import os
import json
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks
import matplotlib.pyplot as plt

def main():
    # 1. Definir rutas de origen y destino
    dataset_dir = "dataset/processed/"
    modelo_path = "models/keras/modelo_inventario.keras"
    etiquetas_path = "models/labels.json"
    graficas_dir = "reports/training/"

    # 2. Crear los directorios de destino si no existen
    os.makedirs(os.path.dirname(modelo_path), exist_ok=True)
    os.makedirs(graficas_dir, exist_ok=True)

    print("Cargando el dataset desde:", dataset_dir)

    # 3. Cargar imágenes usando tf.keras.utils.image_dataset_from_directory
    try:
        train_ds, val_ds = tf.keras.utils.image_dataset_from_directory(
            dataset_dir,
            validation_split=0.2,
            subset="both",
            seed=123,
            color_mode="grayscale",
            image_size=(128, 128),
            batch_size=32
        )
    except Exception as e:
        print(f"Error al cargar el dataset: {e}")
        print("Asegúrate de tener al menos 2 clases en la carpeta del dataset con imágenes en formato correcto.")
        return

    # 4. Obtener los nombres de las clases del dataset y guardarlas
    class_names = train_ds.class_names
    print(f"Clases detectadas: {class_names}")
    print(f"Número de clases detectadas: {len(class_names)}")

    # Guardar en models/labels.json
    with open(etiquetas_path, "w", encoding="utf-8") as f:
        json.dump(class_names, f, ensure_ascii=False, indent=4)
    print(f"Clases guardadas correctamente en: {etiquetas_path}")

    # 5. Extraer número dinámico de clases
    num_classes = len(class_names)
    if num_classes < 2:
        print("Error: Se requieren al menos 2 clases para el entrenamiento multiclase.")
        return

    # 6. Construir la arquitectura de la CNN
    print("Construyendo la arquitectura de la CNN...")
    model = models.Sequential([
        # Capa de re-escalado (0-255 a 0-1)
        layers.Rescaling(1./255, input_shape=(128, 128, 1)),
        
        # Bloque 1
        layers.Conv2D(32, (3, 3), activation='relu'),
        layers.MaxPooling2D((2, 2)),
        
        # Bloque 2
        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.MaxPooling2D((2, 2)),
        
        # Bloque 3
        layers.Conv2D(128, (3, 3), activation='relu'),
        layers.MaxPooling2D((2, 2)),
        
        # Aplanado
        layers.Flatten(),
        
        # Capa densa oculta
        layers.Dense(128, activation='relu'),
        
        # Prevención de sobreajuste
        layers.Dropout(0.5),
        
        # Capa de salida multiclase Softmax
        layers.Dense(num_classes, activation='softmax')
    ])

    model.summary()

    # 7. Compilar el modelo
    print("Compilando el modelo...")
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    # 8. Configurar EarlyStopping
    early_stopping = callbacks.EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True
    )

    # 9. Entrenar el modelo
    print("Iniciando el entrenamiento...")
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=100,
        callbacks=[early_stopping]
    )

    # 10. Guardar el modelo entrenado
    print(f"Guardando el modelo entrenado en: {modelo_path}")
    model.save(modelo_path)

    # 11. Generar gráficas de rendimiento con matplotlib.pyplot y guardarlas en reports/training/
    print("Generando gráficas de rendimiento...")
    
    # Gráfica de Pérdida (Loss / Val Loss)
    plt.figure(figsize=(10, 5))
    plt.plot(history.history['loss'], label='Pérdida Entrenamiento')
    plt.plot(history.history['val_loss'], label='Pérdida Validación')
    plt.title('Historial de Pérdida (Loss)')
    plt.xlabel('Época')
    plt.ylabel('Pérdida')
    plt.legend()
    plt.grid(True)
    loss_plot_path = os.path.join(graficas_dir, "loss_history.png")
    plt.savefig(loss_plot_path)
    plt.close()
    print(f"Gráfica de pérdida guardada en: {loss_plot_path}")

    # Gráfica de Precisión (Accuracy / Val Accuracy)
    plt.figure(figsize=(10, 5))
    plt.plot(history.history['accuracy'], label='Precisión Entrenamiento')
    plt.plot(history.history['val_accuracy'], label='Precisión Validación')
    plt.title('Historial de Precisión (Accuracy)')
    plt.xlabel('Época')
    plt.ylabel('Precisión')
    plt.legend()
    plt.grid(True)
    acc_plot_path = os.path.join(graficas_dir, "accuracy_history.png")
    plt.savefig(acc_plot_path)
    plt.close()
    print(f"Gráfica de precisión guardada en: {acc_plot_path}")

    print("Entrenamiento finalizado con éxito.")

if __name__ == '__main__':
    main()
