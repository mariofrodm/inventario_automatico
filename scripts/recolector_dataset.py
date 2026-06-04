import argparse
import cv2
import os
import time

def main():
    # 1. Configurar argparse para requerir el argumento --clase
    parser = argparse.ArgumentParser(description="Herramienta de recolección de imágenes para el dataset.")
    parser.add_argument('--clase', required=True, help="Nombre de la clase de producto a recolectar.")
    parser.add_argument('--camara', type=int, default=0, help='Índice de la cámara')
    args = parser.parse_args()
    clase = args.clase

    # 2. Crear dinámicamente las carpetas dataset/raw/{clase} y dataset/processed/{clase}
    raw_dir = os.path.join("dataset", "raw", clase)
    processed_dir = os.path.join("dataset", "processed", clase)
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    # 3. Iniciar la captura de video
    print(f"Iniciando cámara en el índice: {args.camara}")
    cap = cv2.VideoCapture(args.camara)

    if not cap.isOpened():
        print(f"Error: No se pudo abrir la cámara en el índice {args.camara}.")
        return

    # Forzar la resolución a 640x480 si el hardware lo permite
    cap.set(3, 640)
    cap.set(4, 480)

    print(f"Iniciando recolección para la clase: {clase}")
    print("Controles del operador:")
    print(" - Presiona 's' para capturar y guardar la ROI.")
    print(" - Presiona 'q' para salir.")

    try:
        while True:
            # Leer el frame
            ret, frame = cap.read()
            if not ret:
                print("Error: No se pudo recibir el frame de la cámara.")
                break

            # Obtener las dimensiones del frame
            h, w, _ = frame.shape

            # Definir la misma ROI central que en probar_camara.py (50% del ancho y alto)
            roi_w = int(w * 0.5)
            roi_h = int(h * 0.5)
            
            start_x = int((w - roi_w) / 2)
            start_y = int((h - roi_h) / 2)
            end_x = start_x + roi_w
            end_y = start_y + roi_h

            # Extraer la porción de la imagen correspondiente a la ROI antes de modificar el frame
            roi_raw = frame[start_y:end_y, start_x:end_x].copy()

            # Dibujar el rectángulo verde de la ROI en el frame principal
            cv2.rectangle(frame, (start_x, start_y), (end_x, end_y), (0, 255, 0), 2)

            # Añadir texto en el frame principal
            info_text = f"Clase: {clase} | 's': Guardar | 'q': Salir"
            cv2.putText(
                frame, 
                info_text, 
                (15, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.6, 
                (0, 255, 0), 
                2, 
                cv2.LINE_AA
            )

            # Mostrar el frame en una ventana
            cv2.imshow("Recolector de Dataset", frame)

            # Capturar la tecla presionada con waitKey(1)
            key = cv2.waitKey(1) & 0xFF

            # Si se presiona la tecla 's'
            if key == ord('s'):
                # Generar nombre de archivo único basado en el tiempo
                nombre_archivo = f"img_{int(time.time() * 1000)}.jpg"

                # Guardar la ROI original (a color)
                path_raw = os.path.join(raw_dir, nombre_archivo)
                cv2.imwrite(path_raw, roi_raw)

                # Procesar la ROI extraída:
                # a) Aplicar filtro Gaussiano con kernel (5, 5) directamente sobre la ROI a color
                blurred = cv2.GaussianBlur(roi_raw, (5, 5), 0)
                # b) Redimensionar exactamente a 128x128 píxeles
                processed = cv2.resize(blurred, (128, 128))

                # Guardar la ROI procesada (en color)
                path_processed = os.path.join(processed_dir, nombre_archivo)
                cv2.imwrite(path_processed, processed)

                print(f"Imagen guardada: {nombre_archivo}")

            # Si se presiona 'q', salir
            elif key == ord('q'):
                break
    finally:
        # Liberar la cámara y cerrar ventanas al finalizar
        cap.release()
        cv2.destroyAllWindows()
        print("Recolector finalizado. Cámara liberada y ventanas cerradas.")

if __name__ == '__main__':
    main()
