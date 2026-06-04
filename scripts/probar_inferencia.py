import argparse
import json
import os
import numpy as np
import cv2
import tensorflow as tf

def main():
    # Configurar argparse para seleccionar el dispositivo de cámara
    parser = argparse.ArgumentParser()
    parser.add_argument('--camara', type=int, default=0, help='Índice del dispositivo de cámara (0 por defecto)')
    args = parser.parse_args()

    modelo_tflite_path = "models/tflite/modelo_inventario.tflite"
    labels_path = "models/labels.json"

    # Verificar existencia de archivos obligatorios
    if not os.path.exists(labels_path):
        print(f"Error: No se encontró el archivo de etiquetas en {labels_path}")
        return
    if not os.path.exists(modelo_tflite_path):
        print(f"Error: No se encontró el modelo TFLite en {modelo_tflite_path}")
        return

    # 1. Cargar las etiquetas desde models/labels.json
    print("Cargando etiquetas...")
    with open(labels_path, "r", encoding="utf-8") as f:
        class_names = json.load(f)
    print(f"Clases cargadas: {class_names}")

    # 2. Inicializar el intérprete TFLite
    print(f"Cargando modelo TFLite desde {modelo_tflite_path}...")
    interpreter = tf.lite.Interpreter(model_path=modelo_tflite_path)
    interpreter.allocate_tensors()

    # Obtener detalles de entrada y salida del modelo
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # 3. Iniciar la captura de video
    print(f"Iniciando cámara en el índice: {args.camara}")
    cap = cv2.VideoCapture(args.camara)
    if not cap.isOpened():
        print(f"Error: No se pudo abrir la cámara en el índice {args.camara}.")
        return

    # Forzar la resolución a 640x480 si el hardware lo permite
    cap.set(3, 640)
    cap.set(4, 480)

    # 4. Definir las variables de estado
    estado_cruce = 0
    conteo_clases = {clase: 0 for clase in class_names}
    cooldown = 0

    print("\nIniciando inferencia en tiempo real...")
    print("Presiona 'q' en la ventana de video para salir.")

    try:
        while True:
            # Leer el frame de la cámara
            ret, frame = cap.read()
            if not ret:
                print("Error: No se pudo recibir el frame de la cámara.")
                break

            alto, ancho = frame.shape[:2]

            # Definir la misma ROI central que en recolector_dataset.py (50% centrado)
            x1 = int(ancho * 0.25)
            y1 = int(alto * 0.25)
            x2 = int(ancho * 0.75)
            y2 = int(alto * 0.75)

            # Mapear a variables existentes para compatibilidad descendente
            start_x, start_y = x1, y1
            end_x, end_y = x2, y2

            # Extraer la imagen cruda de la ROI antes de dibujar superposiciones
            roi_raw = frame[y1:y2, x1:x2].copy()

            # Dibujar el rectángulo verde de la ROI
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Definir una línea horizontal en el centro exacto de la ROI (eje Y) y dibujarla de azul
            centro_y = y1 + (y2 - y1) // 2
            y_line = centro_y
            cv2.line(frame, (x1, centro_y), (x2, centro_y), (255, 0, 0), 2)

            # Preprocesamiento estricto de la ROI para el modelo
            # a) Aplicar filtro Gaussiano con kernel (5, 5) directamente sobre la ROI a color
            blurred = cv2.GaussianBlur(roi_raw, (5, 5), 0)
            # b) Redimensionar exactamente a 128x128 píxeles
            resized = cv2.resize(blurred, (128, 128))
            
            # Convertir a float32 sin normalizar (ya que el modelo tiene una capa interna Rescaling) y hacer reshape a (1, 128, 128, 3)
            input_tensor = resized.astype(np.float32).reshape(1, 128, 128, 3)

            # Inyectar el tensor al intérprete
            interpreter.set_tensor(input_details[0]['index'], input_tensor)
            # Ejecutar la inferencia
            interpreter.invoke()
            # Extraer resultado de salida
            output_data = interpreter.get_tensor(output_details[0]['index'])

            # Encontrar la clase con mayor probabilidad y confianza
            class_idx = np.argmax(output_data[0])
            confianza = output_data[0][class_idx]
            clase_detectada = class_names[class_idx]

            # Lógica de toma de decisiones basada en el umbral de confianza (> 0.85)
            if confianza > 0.85:
                # Mostrar el nombre de la clase y porcentaje en pantalla
                texto_pred = f"Clase: {clase_detectada} ({confianza*100:.1f}%)"
                cv2.putText(
                    frame, 
                    texto_pred, 
                    (start_x, start_y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, 
                    (0, 255, 0), 
                    2, 
                    cv2.LINE_AA
                )
                
                # Lógica de conteo utilizando una máquina de estados simple con cooldown para evitar flickering
                if cooldown > 0:
                    cooldown -= 1
                    
                if estado_cruce == 0:
                    estado_cruce = 1
                elif estado_cruce == 1 and cooldown == 0:
                    conteo_clases[clase_detectada] += 1
                    print(f"[CRUCE] {clase_detectada} detectada. Total: {conteo_clases[clase_detectada]}")
                    estado_cruce = 2
                    cooldown = 15
            else:
                # Mostrar "Buscando..." si no supera el umbral de confianza
                cv2.putText(
                    frame, 
                    "Buscando...", 
                    (start_x, start_y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, 
                    (0, 0, 255), 
                    2, 
                    cv2.LINE_AA
                )
                # Reiniciar estado de cruce
                estado_cruce = 0
                # Disminuir cooldown para estar listos ante el próximo objeto
                if cooldown > 0:
                    cooldown -= 1

            # Imprimir los contadores actuales en la parte superior izquierda de la pantalla usando cv2.putText
            y_offset = 30
            cv2.putText(
                frame, 
                "CANTIDADES DETECTADAS:", 
                (15, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, 
                (255, 255, 255), 
                2, 
                cv2.LINE_AA
            )
            y_offset += 20
            for clase, count in conteo_clases.items():
                count_text = f" - {clase}: {count}"
                cv2.putText(
                    frame, 
                    count_text, 
                    (15, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, 
                    (255, 255, 0), 
                    2, 
                    cv2.LINE_AA
                )
                y_offset += 20

            # Mostrar el frame procesado en la ventana
            cv2.imshow("Inferencia en Tiempo Real (TFLite)", frame)

            # Salir si se presiona 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        # Liberar los recursos de video y destruir ventanas
        cap.release()
        cv2.destroyAllWindows()
        print("Recursos liberados. Inferencia finalizada.")

if __name__ == '__main__':
    main()
