import cv2
import sys

def main():
    # Intentar abrir el dispositivo de captura 0
    cap = cv2.VideoCapture(0)
    
    # Intentar con el dispositivo 1 si el dispositivo 0 falla
    if not cap.isOpened():
        print("Advertencia: No se pudo abrir la cámara en el dispositivo 0. Intentando con el dispositivo 1...")
        cap = cv2.VideoCapture(1)
        
    # Validar si logramos abrir alguna cámara
    if not cap.isOpened():
        print("Error: No se pudo acceder a ninguna cámara (dispositivo 0 o 1). "
              "Por favor, asegúrate de que la cámara esté conectada.")
        sys.exit(1)

    print("Cámara iniciada correctamente. Presiona 'q' en la ventana de video para salir.")

    try:
        while True:
            # Capturar frame por frame
            ret, frame = cap.read()
            if not ret:
                print("Error: No se pudo recibir el frame de la cámara.")
                break

            # Obtener las dimensiones del frame
            h, w, _ = frame.shape

            # Calcular las coordenadas para un rectángulo central (ROI)
            # Definimos que la ROI ocupe el 50% del ancho y alto del frame
            roi_w = int(w * 0.5)
            roi_h = int(h * 0.5)
            
            start_x = int((w - roi_w) / 2)
            start_y = int((h - roi_h) / 2)
            end_x = start_x + roi_w
            end_y = start_y + roi_h

            # Dibujar el rectángulo (ROI) verde con grosor 2
            cv2.rectangle(frame, (start_x, start_y), (end_x, end_y), (0, 255, 0), 2)

            # Agregar texto guía en pantalla
            cv2.putText(
                frame, 
                "Presiona 'q' para salir", 
                (15, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, 
                (0, 255, 0), 
                2, 
                cv2.LINE_AA
            )

            # Mostrar el frame resultante
            cv2.imshow('Prueba de Camara', frame)

            # Romper el bucle si se presiona la tecla 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        # Liberar la cámara y destruir todas las ventanas abiertas por OpenCV
        cap.release()
        cv2.destroyAllWindows()
        print("Cámara liberada y ventanas cerradas.")

if __name__ == '__main__':
    main()
