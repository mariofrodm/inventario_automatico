import argparse
import sys
import os
import tkinter as tk

# Registrar la raíz del proyecto para habilitar importaciones absolutas
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.models.database import DatabaseManager
from app.views.inventario_gui import InventarioGUI

def main():
    # Configurar argparse para recibir el argumento --camara e --auto-start
    parser = argparse.ArgumentParser(description="Lanzador de la aplicación de Inventario Automático.")
    parser.add_argument('--camara', type=int, default=0, help='Índice del dispositivo de cámara (0 por defecto)')
    parser.add_argument('--auto-start', action='store_true', help='Iniciar la cámara automáticamente después del arranque')
    args = parser.parse_args()

    # Inicializar el gestor de base de datos
    db = DatabaseManager()
    
    # Crear la ventana principal de Tkinter
    root = tk.Tk()
    
    # Instanciar e iniciar la interfaz gráfica del Inventario pasándole la cámara
    app = InventarioGUI(root, db, camera_index=args.camara)
    
    # Si --auto-start está activo, programar el inicio automático de la cámara 500ms después
    if args.auto_start:
        root.after(500, app.iniciar_camara)
    
    # Arrancar el ciclo de eventos principal
    root.mainloop()

if __name__ == '__main__':
    main()
