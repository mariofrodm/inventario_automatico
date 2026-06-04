import os
import json
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt

def main():
    modelo_path = "models/keras/modelo_inventario.keras"
    etiquetas_path = "models/labels.json"
    dataset_dir = "dataset/processed/"
    grafica_path = "reports/training/matriz_confusion.png"

    # Verificar que existen el modelo y las etiquetas
    if not os.path.exists(modelo_path):
        print(f"Error: El modelo no se encuentra en {modelo_path}")
        return
    if not os.path.exists(etiquetas_path):
        print(f"Error: Las etiquetas no se encuentran en {etiquetas_path}")
        return

    # 1. Cargar el modelo
    print(f"Cargando modelo desde {modelo_path}...")
    model = tf.keras.models.load_model(modelo_path)

    # 2. Cargar las etiquetas
    with open(etiquetas_path, "r", encoding="utf-8") as f:
        class_names = json.load(f)
    print(f"Clases cargadas: {class_names}")

    # 3. Cargar el dataset de validación con los mismos parámetros
    print(f"Cargando dataset de validación desde {dataset_dir}...")
    try:
        val_ds = tf.keras.utils.image_dataset_from_directory(
            dataset_dir,
            validation_split=0.2,
            subset="validation",
            seed=123,
            color_mode="grayscale",
            image_size=(128, 128),
            batch_size=32
        )
    except Exception as e:
        print(f"Error al cargar el dataset de validación: {e}")
        return

    # 4. Evaluar el modelo
    print("Evaluando el modelo...")
    loss, accuracy = model.evaluate(val_ds, verbose=1)
    print(f"\nResultados de la evaluación:")
    print(f"Pérdida (Loss) final: {loss:.4f}")
    print(f"Precisión (Accuracy) final: {accuracy:.4f}")

    # 5. Realizar predicciones y extraer etiquetas reales
    print("Calculando predicciones de validación...")
    y_true = []
    y_pred = []
    for images, labels in val_ds:
        preds = model.predict(images, verbose=0)
        y_pred.extend(np.argmax(preds, axis=1))
        y_true.extend(labels.numpy())

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    # 6. Generar la matriz de confusión con tf.math.confusion_matrix
    cm = tf.math.confusion_matrix(y_true, y_pred).numpy()

    # 7. Dibujar la matriz usando matplotlib
    print("Generando gráfica de la matriz de confusión...")
    num_classes = len(class_names)
    fig, ax = plt.subplots(figsize=(8, 8))
    cax = ax.matshow(cm, cmap=plt.cm.Blues)
    fig.colorbar(cax)

    # Configuración de los ejes
    ax.set_xticks(np.arange(num_classes))
    ax.set_yticks(np.arange(num_classes))
    ax.set_xticklabels(class_names, rotation=45, ha='left')
    ax.set_yticklabels(class_names)

    ax.set_xlabel('Predicho')
    ax.set_ylabel('Real')
    ax.xaxis.set_label_position('top')

    # Anotar los valores numéricos dentro de cada celda
    for i in range(num_classes):
        for j in range(num_classes):
            text_color = "white" if cm[i, j] > cm.max() / 2.0 else "black"
            ax.text(j, i, str(cm[i, j]), va='center', ha='center', color=text_color, fontweight='bold')

    plt.title('Matriz de Confusión - Inventario', y=1.1, fontsize=14, fontweight='bold')
    plt.tight_layout()

    # Asegurar que el directorio de salida existe
    os.makedirs(os.path.dirname(grafica_path), exist_ok=True)

    # 8. Guardar la imagen sin usar plt.show()
    plt.savefig(grafica_path, dpi=300)
    plt.close()
    print(f"Matriz de confusión guardada con éxito en: {grafica_path}")

if __name__ == '__main__':
    main()
