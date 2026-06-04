import os
from datetime import datetime
import calendar
import sys
import json
import time
import threading
import numpy as np
import cv2
import tensorflow as tf
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# Permitir importaciones absolutas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.services.report_service import ReportService

class InventarioGUI:
    def __init__(self, root, db_manager, camera_index=0):
        self.root = root
        self.db = db_manager
        self.camera_index = camera_index
        self.root.title("Sistema de Inventario Automático (Banda Transportadora)")
        self.root.geometry("1280x720")
        self.root.configure(bg="#F5F7FA")
        
        # Inicializar variables de control de hilos
        self.running = False
        self.inference_thread = None
        self.current_frame = None
        self.need_update_tree = False
        self.lote_actualizado = False
        self.frame_lock = threading.Lock() # Lock para proteger el acceso concurrente a self.current_frame
        self.first_gui_frame_printed = False
        
        # Cargar etiquetas
        self.class_names = []
        labels_path = "models/labels.json"
        if os.path.exists(labels_path):
            try:
                with open(labels_path, "r", encoding="utf-8") as f:
                    self.class_names = json.load(f)
            except Exception as e:
                print(f"Error al leer etiquetas: {e}")
        
        if not self.class_names:
            self.class_names = ["clase_1", "clase_2", "clase_3"]
            
        # Mapear nombres de clases a productos en DB
        self.mapeo_productos_db = {}
        self.mapeo_nombre_interno_a_id = {}
        self.mapeo_id_a_nombre_visible = {}
        self.mapeo_nombre_visible_a_id = {}
        self.mapeo_nombre_interno_a_nombre_visible = {}
        self.recargar_mapeo_productos()

        # Estilo para la UI
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configurar colores del tema profesional (Slate / Teal)
        self.style.configure(".", background="#F5F7FA", foreground="#2C3E50", font=("Helvetica", 10))
        self.style.configure("TFrame", background="#F5F7FA")
        self.style.configure("Header.TFrame", background="#2C3E50")
        self.style.configure("Card.TFrame", background="#FFFFFF", relief="flat", borderwidth=1)
        self.style.configure("Action.TButton", background="#1ABC9C", foreground="white", font=("Helvetica", 10, "bold"), borderwidth=0)
        self.style.map("Action.TButton", background=[("active", "#16A085")])
        self.style.configure("Danger.TButton", background="#E74C3C", foreground="white", font=("Helvetica", 10, "bold"), borderwidth=0)
        self.style.map("Danger.TButton", background=[("active", "#C0392B")])
        
        self._build_ui()
        
        # Iniciar refresco del Frame
        self.update_gui_loop()

    def recargar_mapeo_productos(self):
        """Precarga los productos e ID desde la base de datos y mapea nombres visibles."""
        try:
            productos = self.db.get_productos()
            self.mapeo_nombre_interno_a_id = {p['nombre']: p['id_producto'] for p in productos}
            self.mapeo_id_a_nombre_visible = {p['id_producto']: p['nombre_visible'] for p in productos}
            self.mapeo_nombre_visible_a_id = {p['nombre_visible']: p['id_producto'] for p in productos}
            self.mapeo_nombre_interno_a_nombre_visible = {p['nombre']: p['nombre_visible'] for p in productos}
            
            # Para compatibilidad con código existente:
            self.mapeo_productos_db = self.mapeo_nombre_interno_a_id
        except Exception as e:
            print(f"Advertencia: No se pudo obtener productos de base de datos: {e}")


    def _build_ui(self):
        # 1. Banner Superior (Header)
        header = ttk.Frame(self.root, style="Header.TFrame", height=60)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        header_label = tk.Label(
            header, 
            text="SISTEMA DE INVENTARIO AUTOMÁTICO - CONTROL EN TIEMPO REAL", 
            fg="#FFFFFF", 
            bg="#2C3E50", 
            font=("Helvetica", 14, "bold")
        )
        header_label.pack(side="left", padx=20, pady=15)

        # Contenedor Principal (4 columnas con proporciones 5% / 60% / 30% / 5%)
        main_container = ttk.Frame(self.root, padding=15)
        main_container.pack(fill="both", expand=True)

        main_container.columnconfigure(0, weight=5)
        main_container.columnconfigure(1, weight=60)
        main_container.columnconfigure(2, weight=30)
        main_container.columnconfigure(3, weight=5)
        main_container.rowconfigure(0, weight=1)

        # Margen izquierdo (5%)
        left_margin = ttk.Frame(main_container)
        left_margin.grid(row=0, column=0, sticky="nsew")

        # ================= COLUMNA IZQUIERDA: CÁMARA & CONTROLES (60%) =================
        left_column = ttk.Frame(main_container)
        left_column.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        left_column.rowconfigure(0, weight=1)
        left_column.columnconfigure(0, weight=1)

        # Panel de Cámara (Card)
        video_card = ttk.Frame(left_column, style="Card.TFrame", padding=10)
        video_card.grid(row=0, column=0, sticky="nsew")
        video_card.rowconfigure(2, weight=1)
        video_card.columnconfigure(0, weight=1)
        
        video_title = tk.Label(video_card, text="Feed de Video de la Banda Transportadora", font=("Helvetica", 11, "bold"), bg="#FFFFFF", fg="#34495E")
        video_title.grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Panel de Controles de Cámara (colocado ARRIBA de la etiqueta de video para asegurar visibilidad)
        control_frame = ttk.Frame(video_card, padding=(0, 5, 0, 10))
        control_frame.grid(row=1, column=0, sticky="ew")

        ttk.Label(control_frame, text="Dispositivo de Cámara:").pack(side="left", padx=5)
        
        self.cam_combo = ttk.Combobox(control_frame, values=["0", "1", "2", "3"], width=5, state="readonly")
        self.cam_combo.set(str(self.camera_index))
        self.cam_combo.pack(side="left", padx=5)

        self.btn_iniciar = ttk.Button(control_frame, text="Iniciar Cámara", style="Action.TButton", command=self.iniciar_camara)
        self.btn_iniciar.pack(side="left", padx=10)

        self.btn_detener = ttk.Button(control_frame, text="Detener", style="Danger.TButton", command=self.detener_camara, state="disabled")
        self.btn_detener.pack(side="left", padx=5)

        # Label donde se renderiza la imagen del hilo de inferencia (debajo de los controles)
        self.video_label = tk.Label(video_card, bg="#000000", width=640, height=480)
        self.video_label.grid(row=2, column=0, sticky="nsew", pady=(5, 0))

        # ================= COLUMNA DERECHA: TABLA, LOTES & REPORTES (30%) =================
        right_column = ttk.Frame(main_container)
        right_column.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        right_column.rowconfigure(0, weight=3)  # tabla
        right_column.rowconfigure(1, weight=1)  # lotes
        right_column.rowconfigure(2, weight=0)  # configuración rápida
        right_column.rowconfigure(3, weight=0)  # reportes
        right_column.columnconfigure(0, weight=1)

        # 1. Tabla de Inventario Actual (Card)
        table_card = ttk.Frame(right_column, style="Card.TFrame", padding=10)
        table_card.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        tk.Label(table_card, text="Inventario registrado", font=("Helvetica", 11, "bold"), bg="#FFFFFF", fg="#34495E").pack(anchor="w", pady=(0, 5))

        # Configurar Treeview
        columns = ("producto", "lote", "precio", "unidades", "total")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", height=8)
        self.tree.heading("producto", text="Producto")
        self.tree.heading("lote", text="Lote")
        self.tree.heading("precio", text="Precio")
        self.tree.heading("unidades", text="Unid.")
        self.tree.heading("total", text="Total")
        
        self.tree.column("producto", width=90, anchor="center")
        self.tree.column("lote", width=70, anchor="center")
        self.tree.column("precio", width=75, anchor="center")
        self.tree.column("unidades", width=65, anchor="center")
        self.tree.column("total", width=75, anchor="center")
        self.tree.pack(fill="both", expand=True)

        btn_refresh = ttk.Button(table_card, text="Actualizar Tabla", command=self.refrescar_treeview)
        btn_refresh.pack(pady=5, anchor="e")

        # 2. Card de Gestión de Lotes
        lote_card = ttk.Frame(right_column, style="Card.TFrame", padding=10)
        lote_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        tk.Label(lote_card, text="Gestión de Lotes Activos", font=("Helvetica", 11, "bold"), bg="#FFFFFF", fg="#34495E").pack(anchor="w", pady=(0, 10))

        # Inputs de Lote
        inputs_frame = ttk.Frame(lote_card)
        inputs_frame.pack(fill="x")

        ttk.Label(inputs_frame, text="Producto:").grid(row=0, column=0, sticky="w", pady=4, padx=5)
        visible_names = list(self.mapeo_nombre_visible_a_id.keys())
        self.lote_prod_combo = ttk.Combobox(inputs_frame, values=visible_names, state="readonly", width=18)
        if visible_names:
            self.lote_prod_combo.set(visible_names[0])
        self.lote_prod_combo.grid(row=0, column=1, pady=4, padx=5)

        ttk.Label(inputs_frame, text="Precio Unit:").grid(row=1, column=0, sticky="w", pady=4, padx=5)
        self.lote_precio_entry = ttk.Entry(inputs_frame, width=10)
        self.lote_precio_entry.insert(0, "15.50")
        self.lote_precio_entry.grid(row=1, column=1, sticky="w", pady=4, padx=5)

        ttk.Label(inputs_frame, text="Cant Config:").grid(row=1, column=2, sticky="w", pady=4, padx=5)
        self.lote_cantidad_entry = ttk.Entry(inputs_frame, width=10)
        self.lote_cantidad_entry.insert(0, "1000")
        self.lote_cantidad_entry.grid(row=1, column=3, sticky="w", pady=4, padx=5)

        btn_save_lote = ttk.Button(lote_card, text="Establecer Lote Activo", style="Action.TButton", command=self.guardar_nuevo_lote)
        btn_save_lote.pack(pady=10, fill="x")

        # Card de Ajustes Rápidos
        config_card = ttk.Frame(right_column, style="Card.TFrame", padding=10)
        config_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        tk.Label(config_card, text="Configuración Rápida", font=("Helvetica", 11, "bold"), bg="#FFFFFF", fg="#34495E").pack(anchor="w", pady=(0, 10))
        
        btn_frame = ttk.Frame(config_card)
        btn_frame.pack(fill="x")
        
        btn_edit_name = ttk.Button(btn_frame, text="Editar Nombre Producto", style="Action.TButton", command=self.abrir_modal_editar_nombre)
        btn_edit_name.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        btn_edit_price = ttk.Button(btn_frame, text="Editar Precio Lote", style="Action.TButton", command=self.abrir_modal_editar_precio)
        btn_edit_price.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # 3. Card de Reportes
        report_card = ttk.Frame(right_column, style="Card.TFrame", padding=10)
        report_card.grid(row=3, column=0, sticky="ew")

        tk.Label(report_card, text="Reportes y Auditoría", font=("Helvetica", 11, "bold"), bg="#FFFFFF", fg="#34495E").pack(anchor="w", pady=(0, 10))
        
        btn_pdf = ttk.Button(report_card, text="Generar Reporte PDF", style="Action.TButton", command=self.exportar_pdf_reporte)
        btn_pdf.pack(fill="x", pady=5)

        # Margen derecho (5%)
        right_margin = ttk.Frame(main_container)
        right_margin.grid(row=0, column=3, sticky="nsew")

        # Barra de estado inferior
        self.status_bar = tk.Label(self.root, text="Estado: Conectado a base de datos | Cámara Detenida", bd=1, relief="sunken", anchor="w", bg="#E2E8F0", fg="#475569")
        self.status_bar.pack(side="bottom", fill="x")

    def refrescar_treeview(self):
        """Consulta la base de datos y refresca el Treeview de inventario."""
        try:
            # Limpiar datos antiguos
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Obtener inventario de SQLite
            datos = self.db.get_inventario_actual()
            for d in datos:
                # d contiene: id_producto, producto_interno, producto_visible, lote, precio_unitario, conteo, total_lote
                prod_vis = d.get('producto_visible') or d.get('producto_interno')
                precio_val = f"Q{d['precio_unitario']:.2f}"
                total_val = f"Q{d['total_lote']:.2f}"
                self.tree.insert("", "end", values=(prod_vis, f"Lote #{d['lote']}", precio_val, d['conteo'], total_val))
        except Exception as e:
            print(f"Error al refrescar Treeview: {e}")

    def guardar_nuevo_lote(self):
        """Crea y activa un nuevo lote para el producto seleccionado."""
        producto = self.lote_prod_combo.get()
        precio_str = self.lote_precio_entry.get()
        cantidad_str = self.lote_cantidad_entry.get()
        
        # Validar producto mapeado usando nombre visible
        id_prod = self.mapeo_nombre_visible_a_id.get(producto)
        if not id_prod:
            # Reintentar cargar
            self.recargar_mapeo_productos()
            id_prod = self.mapeo_nombre_visible_a_id.get(producto)
            if not id_prod:
                messagebox.showerror("Error", f"El producto {producto} no está inicializado en la base de datos.")
                return

        # Validaciones de campos
        try:
            precio = float(precio_str)
            cantidad = int(cantidad_str)
            if precio <= 0 or cantidad <= 0:
                raise ValueError("Valores deben ser mayores a cero")
        except ValueError:
            messagebox.showerror("Error de Formato", "El precio debe ser un número decimal y la cantidad un número entero válidos y mayores a cero.")
            return

        try:
            self.db.crear_lote_activo(id_prod, precio, cantidad)
            self.lote_actualizado = True
            messagebox.showinfo("Éxito", f"Se ha registrado y activado un nuevo lote para el producto {producto}.")
            self.refrescar_treeview()
        except Exception as e:
            messagebox.showerror("Error de Base de Datos", f"No se pudo guardar el lote: {e}")

    def abrir_modal_editar_nombre(self):
        """Abre un modal para editar el nombre visible de un producto."""
        modal = tk.Toplevel(self.root)
        modal.title("Editar Nombre de Producto")
        modal.geometry("400x250")
        modal.configure(bg="#F5F7FA")
        modal.transient(self.root)
        modal.grab_set()
        
        # Centrar modal
        modal.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - modal.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - modal.winfo_height()) // 2
        modal.geometry(f"+{x}+{y}")
        
        # Title Label
        tk.Label(modal, text="Editar Nombre Visible de Producto", font=("Helvetica", 12, "bold"), bg="#F5F7FA", fg="#2C3E50").pack(pady=15)
        
        frame = ttk.Frame(modal, padding=15)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Seleccionar Producto:").grid(row=0, column=0, sticky="w", pady=10)
        
        self.recargar_mapeo_productos()
        visible_names = list(self.mapeo_nombre_visible_a_id.keys())
        
        combo = ttk.Combobox(frame, values=visible_names, state="readonly", width=25)
        if visible_names:
            combo.set(visible_names[0])
        combo.grid(row=0, column=1, pady=10, padx=10)
        
        ttk.Label(frame, text="Nuevo Nombre Visible:").grid(row=1, column=0, sticky="w", pady=10)
        entry_nuevo = ttk.Entry(frame, width=27)
        entry_nuevo.grid(row=1, column=1, pady=10, padx=10)
        
        def guardar():
            nombre_vis = combo.get()
            nuevo_nombre = entry_nuevo.get().strip()
            
            if not nuevo_nombre:
                messagebox.showerror("Error", "El nuevo nombre no puede estar vacío.", parent=modal)
                return
                
            id_prod = self.mapeo_nombre_visible_a_id.get(nombre_vis)
            if not id_prod:
                messagebox.showerror("Error", "Producto no válido.", parent=modal)
                return
                
            try:
                self.db.actualizar_nombre_visible_producto(id_prod, nuevo_nombre)
                messagebox.showinfo("Éxito", "Nombre de producto actualizado correctamente.", parent=modal)
                self.recargar_mapeo_productos()
                self.actualizar_comboboxes_productos()
                self.refrescar_treeview()
                modal.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el nombre: {e}", parent=modal)
                
        btn_save = ttk.Button(frame, text="Guardar", style="Action.TButton", command=guardar)
        btn_save.grid(row=2, column=0, columnspan=2, pady=20)

    def abrir_modal_editar_precio(self):
        """Abre un modal para editar el precio unitario de un lote."""
        modal = tk.Toplevel(self.root)
        modal.title("Editar Precio de Lote")
        modal.geometry("450x300")
        modal.configure(bg="#F5F7FA")
        modal.transient(self.root)
        modal.grab_set()
        
        # Centrar modal
        modal.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - modal.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - modal.winfo_height()) // 2
        modal.geometry(f"+{x}+{y}")
        
        # Title Label
        tk.Label(modal, text="Editar Precio Unitario de Lote", font=("Helvetica", 12, "bold"), bg="#F5F7FA", fg="#2C3E50").pack(pady=15)
        
        frame = ttk.Frame(modal, padding=15)
        frame.pack(fill="both", expand=True)
        
        self.recargar_mapeo_productos()
        visible_names = list(self.mapeo_nombre_visible_a_id.keys())
        
        ttk.Label(frame, text="Producto:").grid(row=0, column=0, sticky="w", pady=8)
        combo_prod = ttk.Combobox(frame, values=visible_names, state="readonly", width=25)
        if visible_names:
            combo_prod.set(visible_names[0])
        combo_prod.grid(row=0, column=1, pady=8, padx=10)
        
        ttk.Label(frame, text="Seleccionar Lote:").grid(row=1, column=0, sticky="w", pady=8)
        combo_lote = ttk.Combobox(frame, state="readonly", width=25)
        combo_lote.grid(row=1, column=1, pady=8, padx=10)
        
        ttk.Label(frame, text="Precio Actual:").grid(row=2, column=0, sticky="w", pady=8)
        label_precio_actual = ttk.Label(frame, text="-")
        label_precio_actual.grid(row=2, column=1, sticky="w", pady=8, padx=10)
        
        ttk.Label(frame, text="Nuevo Precio:").grid(row=3, column=0, sticky="w", pady=8)
        entry_precio = ttk.Entry(frame, width=27)
        entry_precio.grid(row=3, column=1, pady=8, padx=10)
        
        lotes_actuales = []
        
        def actualizar_lotes(event=None):
            nonlocal lotes_actuales
            prod_vis = combo_prod.get()
            id_prod = self.mapeo_nombre_visible_a_id.get(prod_vis)
            if not id_prod:
                combo_lote.configure(values=[])
                label_precio_actual.configure(text="-")
                return
                
            try:
                lotes_actuales = self.db.get_lotes_producto(id_prod)
                lotes_vis = []
                for l in lotes_actuales:
                    estado = "Activo" if l['activo'] == 1 else "Inactivo"
                    lotes_vis.append(f"Lote #{l['id_lote']} ({estado}) - Q{l['precio_unitario']:.2f}")
                
                combo_lote.configure(values=lotes_vis)
                if lotes_vis:
                    combo_lote.set(lotes_vis[0])
                    actualizar_precio_info()
                else:
                    combo_lote.set("")
                    label_precio_actual.configure(text="-")
            except Exception as e:
                print(f"Error al cargar lotes: {e}")
                
        def actualizar_precio_info(event=None):
            idx = combo_lote.current()
            if idx >= 0 and idx < len(lotes_actuales):
                l = lotes_actuales[idx]
                label_precio_actual.configure(text=f"Q {l['precio_unitario']:.2f}")
                entry_precio.delete(0, tk.END)
                entry_precio.insert(0, f"{l['precio_unitario']:.2f}")
            else:
                label_precio_actual.configure(text="-")
                entry_precio.delete(0, tk.END)
                
        combo_prod.bind("<<ComboboxSelected>>", actualizar_lotes)
        combo_lote.bind("<<ComboboxSelected>>", actualizar_precio_info)
        
        if visible_names:
            actualizar_lotes()
            
        def guardar():
            idx = combo_lote.current()
            if idx < 0 or idx >= len(lotes_actuales):
                messagebox.showerror("Error", "Debe seleccionar un lote válido.", parent=modal)
                return
                
            id_lote = lotes_actuales[idx]['id_lote']
            nuevo_precio = entry_precio.get().strip()
            
            try:
                self.db.actualizar_precio_lote(id_lote, nuevo_precio)
                self.lote_actualizado = True
                messagebox.showinfo("Éxito", "Precio de lote actualizado correctamente.", parent=modal)
                self.refrescar_treeview()
                modal.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=modal)
                
        btn_save = ttk.Button(frame, text="Guardar", style="Action.TButton", command=guardar)
        btn_save.grid(row=4, column=0, columnspan=2, pady=15)

    def actualizar_comboboxes_productos(self):
        """Actualiza los comboboxes de productos cuando cambian sus nombres visibles."""
        visible_names = list(self.mapeo_nombre_visible_a_id.keys())
        self.lote_prod_combo.configure(values=visible_names)
        if visible_names:
            curr = self.lote_prod_combo.get()
            if curr not in visible_names:
                self.lote_prod_combo.set(visible_names[0])

    def abrir_selector_fecha(self, entry_destino):
        """Abre un modal de Toplevel con un calendario interactivo para seleccionar una fecha."""
        # Obtener fecha actual o fecha preexistente en el entry
        val_actual = entry_destino.get().strip()
        hoy = datetime.now()
        año_actual = hoy.year
        mes_actual = hoy.month
        
        if val_actual:
            try:
                dt = datetime.strptime(val_actual, "%Y-%m-%d")
                año_actual = dt.year
                mes_actual = dt.month
            except ValueError:
                pass
                
        # Crear modal Toplevel
        cal_modal = tk.Toplevel(self.root)
        cal_modal.title("Seleccionar Fecha")
        cal_modal.geometry("320x350")
        cal_modal.configure(bg="#F5F7FA")
        cal_modal.transient(entry_destino.winfo_toplevel())
        cal_modal.grab_set()
        
        # Centrar relativo al modal de reportes
        cal_modal.update_idletasks()
        parent_w = entry_destino.winfo_toplevel()
        x = parent_w.winfo_x() + (parent_w.winfo_width() - cal_modal.winfo_width()) // 2
        y = parent_w.winfo_y() + (parent_w.winfo_height() - cal_modal.winfo_height()) // 2
        cal_modal.geometry(f"+{x}+{y}")
        
        # Variables de control
        var_año = tk.IntVar(value=año_actual)
        var_mes = tk.IntVar(value=mes_actual)
        
        # Frame del header (Mes y Año con botones < y >)
        header_frame = ttk.Frame(cal_modal)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        def cambiar_mes(delta):
            m = var_mes.get() + delta
            y = var_año.get()
            if m < 1:
                m = 12
                y -= 1
            elif m > 12:
                m = 1
                y += 1
            var_mes.set(m)
            var_año.set(y)
            dibujar_dias()
            
        btn_prev = ttk.Button(header_frame, text="<", width=3, command=lambda: cambiar_mes(-1))
        btn_prev.pack(side="left")
        
        lbl_mes_año = tk.Label(header_frame, text="", font=("Helvetica", 10, "bold"), bg="#F5F7FA", fg="#2C3E50")
        lbl_mes_año.pack(side="left", fill="x", expand=True)
        
        btn_next = ttk.Button(header_frame, text=">", width=3, command=lambda: cambiar_mes(1))
        btn_next.pack(side="right")
        
        # Frame de los días de la semana y cuadrícula
        dias_frame = ttk.Frame(cal_modal)
        dias_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Encabezados de días de la semana
        semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for col_idx, dia_sem in enumerate(semana):
            lbl_sem = tk.Label(dias_frame, text=dia_sem, font=("Helvetica", 9, "bold"), fg="#7F8C8D")
            lbl_sem.grid(row=0, column=col_idx, pady=2, sticky="nsew")
            
        # Grid para los botones de los días
        grid_botones = []
        
        def seleccionar_dia(dia):
            y = var_año.get()
            m = var_mes.get()
            fecha_str = f"{y:04d}-{m:02d}-{dia:02d}"
            
            entry_destino.configure(state="normal")
            entry_destino.delete(0, tk.END)
            entry_destino.insert(0, fecha_str)
            entry_destino.configure(state="readonly")
            
            cal_modal.destroy()
            
        def dibujar_dias():
            # Limpiar botones anteriores
            for btn in grid_botones:
                btn.destroy()
            grid_botones.clear()
            
            y = var_año.get()
            m = var_mes.get()
            
            # Nombre del mes traducido
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            lbl_mes_año.configure(text=f"{meses_nombres[m-1]} {y}")
            
            # Obtener días del mes (primer día de la semana y total de días)
            primer_dia_sem, total_dias = calendar.monthrange(y, m)
            
            # Dibujar días en filas y columnas
            fila = 1
            columna = primer_dia_sem
            
            for dia in range(1, total_dias + 1):
                btn_dia = tk.Button(
                    dias_frame, 
                    text=str(dia), 
                    font=("Helvetica", 9),
                    bg="#FFFFFF", 
                    fg="#2C3E50",
                    relief="flat",
                    bd=1,
                    width=3, 
                    height=1,
                    command=lambda d=dia: seleccionar_dia(d)
                )
                btn_dia.grid(row=fila, column=columna, padx=2, pady=2, sticky="nsew")
                grid_botones.append(btn_dia)
                
                columna += 1
                if columna > 6:
                    columna = 0
                    fila += 1
                    
        # Inicializar días
        dibujar_dias()
        
        # Botones de control inferiores
        control_frame = ttk.Frame(cal_modal)
        control_frame.pack(fill="x", side="bottom", padx=10, pady=10)
        
        def limpiar():
            entry_destino.configure(state="normal")
            entry_destino.delete(0, tk.END)
            entry_destino.configure(state="readonly")
            cal_modal.destroy()
            
        btn_limpiar = ttk.Button(control_frame, text="Limpiar fecha", command=limpiar)
        btn_limpiar.pack(side="left", padx=5)
        
        btn_cancelar = ttk.Button(control_frame, text="Cancelar", command=cal_modal.destroy)
        btn_cancelar.pack(side="right", padx=5)

    def exportar_pdf_reporte(self):
        """Abre un modal para configurar filtros de reporte y exportar PDF."""
        try:
            from tkinter import filedialog
            
            modal = tk.Toplevel(self.root)
            modal.title("Configurar Reporte de Inventario")
            modal.geometry("600x520")
            modal.configure(bg="#F5F7FA")
            modal.transient(self.root)
            modal.grab_set()
            
            # Centrar modal
            modal.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - modal.winfo_width()) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - modal.winfo_height()) // 2
            modal.geometry(f"+{x}+{y}")
            
            main_frame = ttk.Frame(modal, padding=15)
            main_frame.pack(fill="both", expand=True)
            
            main_frame.columnconfigure(0, weight=1)
            main_frame.columnconfigure(1, weight=1)
            
            # Row 0: Title Label
            lbl_title = tk.Label(main_frame, text="Configurar Reporte de Inventario", font=("Helvetica", 12, "bold"), bg="#F5F7FA", fg="#2C3E50")
            lbl_title.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky="w")
            
            # Row 1: Label
            lbl_prod = ttk.Label(main_frame, text="Productos: (Ctrl+Click para seleccionar múltiples)", font=("Helvetica", 10, "bold"))
            lbl_prod.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 5))
            
            self.recargar_mapeo_productos()
            visible_names = list(self.mapeo_nombre_visible_a_id.keys())
            
            # Row 2: Listbox + Scrollbar Frame
            listbox_frame = ttk.Frame(main_frame)
            listbox_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=5)
            
            scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical")
            scrollbar.pack(side="right", fill="y")
            
            listbox = tk.Listbox(listbox_frame, selectmode="multiple", yscrollcommand=scrollbar.set, height=6)
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=listbox.yview)
            
            for name in visible_names:
                listbox.insert(tk.END, name)
            
            # Seleccionar todos por defecto
            listbox.select_set(0, tk.END)
            
            # Row 3: Buttons for selection
            btn_sel_all = ttk.Button(main_frame, text="Seleccionar todos", command=lambda: listbox.select_set(0, tk.END))
            btn_sel_all.grid(row=3, column=0, sticky="w", pady=5)
            
            btn_clear_sel = ttk.Button(main_frame, text="Limpiar selección", command=lambda: listbox.select_clear(0, tk.END))
            btn_clear_sel.grid(row=3, column=1, sticky="e", pady=5)
            
            # Row 4: Dates Section
            date_frame = ttk.LabelFrame(main_frame, text="Rango de Fechas (Opcional)", padding=10)
            date_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=15)
            date_frame.columnconfigure(1, weight=1)
            
            ttk.Label(date_frame, text="Fecha Inicio:").grid(row=0, column=0, sticky="w", pady=5)
            entry_inicio = ttk.Entry(date_frame, state="readonly")
            entry_inicio.grid(row=0, column=1, pady=5, padx=5, sticky="ew")
            btn_inicio = ttk.Button(date_frame, text="Seleccionar", command=lambda: self.abrir_selector_fecha(entry_inicio))
            btn_inicio.grid(row=0, column=2, pady=5, padx=5, sticky="e")
            
            ttk.Label(date_frame, text="Fecha Fin:").grid(row=1, column=0, sticky="w", pady=5)
            entry_fin = ttk.Entry(date_frame, state="readonly")
            entry_fin.grid(row=1, column=1, pady=5, padx=5, sticky="ew")
            btn_fin = ttk.Button(date_frame, text="Seleccionar", command=lambda: self.abrir_selector_fecha(entry_fin))
            btn_fin.grid(row=1, column=2, pady=5, padx=5, sticky="e")
            
            # Row 5: Location Section
            loc_frame = ttk.LabelFrame(main_frame, text="Ubicación del Reporte PDF", padding=10)
            loc_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 15))
            loc_frame.columnconfigure(0, weight=1)
            
            ruta_pdf_var = tk.StringVar(value="")
            entry_ruta = ttk.Entry(loc_frame, textvariable=ruta_pdf_var, state="readonly")
            entry_ruta.grid(row=0, column=0, pady=5, padx=(0, 5), sticky="ew")
            
            def elegir_ruta():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                default_filename = f"reporte_inventario_{timestamp}.pdf"
                path = filedialog.asksaveasfilename(
                    parent=modal,
                    title="Configurar Reporte de Inventario",
                    initialfile=default_filename,
                    defaultextension=".pdf",
                    filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")]
                )
                if path:
                    ruta_pdf_var.set(path)
                    
            btn_elegir_ruta = ttk.Button(loc_frame, text="Elegir ubicación", command=elegir_ruta)
            btn_elegir_ruta.grid(row=0, column=1, pady=5, padx=5, sticky="e")
            
            # Row 6: Bottom Buttons Frame
            btn_frame = ttk.Frame(main_frame)
            btn_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=10)
            btn_frame.columnconfigure(0, weight=1)
            btn_frame.columnconfigure(1, weight=1)
            
            def generar():
                pdf_path = ruta_pdf_var.get().strip()
                if not pdf_path:
                    elegir_ruta()
                    pdf_path = ruta_pdf_var.get().strip()
                    if not pdf_path:
                        return
                
                selected_indices = listbox.curselection()
                selected_visible_names = [listbox.get(i) for i in selected_indices]
                
                product_ids = []
                if not selected_visible_names:
                    product_ids = None
                else:
                    for name in selected_visible_names:
                        p_id = self.mapeo_nombre_visible_a_id.get(name)
                        if p_id:
                            product_ids.append(p_id)
                
                fecha_inicio = entry_inicio.get().strip()
                fecha_fin = entry_fin.get().strip()
                
                # Validar rango de fechas lógico
                if fecha_inicio and fecha_fin:
                    try:
                        d_ini = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                        d_fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
                        if d_ini > d_fin:
                            messagebox.showerror("Error de Rango", "La fecha de inicio no puede ser posterior a la fecha final.", parent=modal)
                            return
                    except Exception as ex_date:
                        print(f"Error al validar rango de fechas: {ex_date}")
                
                try:
                    datos = self.db.get_reporte_inventario(product_ids=product_ids, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
                    total_unidades = sum(d['unidades_registradas'] for d in datos)
                    if not datos or total_unidades == 0:
                        messagebox.showwarning("Sin Datos", "No hay artículos registrados para los filtros seleccionados.", parent=modal)
                        return
                except Exception as db_err:
                    messagebox.showerror("Error de Base de Datos", f"Error al consultar el inventario: {db_err}", parent=modal)
                    return
                
                filtros_aplicados = {
                    'productos': selected_visible_names if selected_visible_names else ["Todos los productos"],
                    'fecha_inicio': fecha_inicio if fecha_inicio else "Sin filtro",
                    'fecha_fin': fecha_fin if fecha_fin else "Sin filtro"
                }
                
                try:
                    pdf_generado = ReportService.generar_pdf(datos, pdf_path=pdf_path, filtros=filtros_aplicados)
                    messagebox.showinfo("Reporte Generado", f"El reporte de inventario se guardó con éxito en:\n\n{pdf_generado}", parent=modal)
                    modal.destroy()
                except Exception as pdf_err:
                    messagebox.showerror("Error al Generar PDF", f"Ocurrió un error al compilar el PDF: {pdf_err}", parent=modal)
            
            btn_cancelar = ttk.Button(btn_frame, text="Cancelar", command=modal.destroy)
            btn_cancelar.grid(row=0, column=0, padx=5, sticky="ew")
            
            btn_generar = ttk.Button(btn_frame, text="Generar PDF", style="Action.TButton", command=generar)
            btn_generar.grid(row=0, column=1, padx=5, sticky="ew")
            
        except Exception as modal_err:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al construir el modal de reporte: {modal_err}")

    def iniciar_camara(self):
        """Inicia el hilo de inferencia."""
        if self.running:
            return
            
        try:
            self.camera_index = int(self.cam_combo.get())
        except ValueError:
            self.camera_index = 0
            
        self.running = True
        self.btn_iniciar.configure(state="disabled")
        self.cam_combo.configure(state="disabled")
        self.btn_detener.configure(state="enabled")
        self.status_bar.configure(text=f"Estado: Ejecutando inferencia en cámara {self.camera_index}...")
        
        # Lanzar hilo en segundo plano
        self.inference_thread = threading.Thread(target=self.procesamiento_video_loop, daemon=True)
        self.inference_thread.start()

    def detener_camara(self):
        """Señala al hilo de inferencia que se detenga."""
        if not self.running:
            return
            
        self.running = False
        self.status_bar.configure(text="Estado: Deteniendo cámara...")

    def procesamiento_video_loop(self):
        """Hilo secundario de inferencia y cruce."""
        modelo_tflite_path = "models/tflite/modelo_inventario.tflite"
        labels_path = "models/labels.json"

        # Validaciones de archivos
        if not os.path.exists(labels_path) or not os.path.exists(modelo_tflite_path):
            print("Error: No se encontraron los modelos o etiquetas.")
            self.running = False
            self.root.after(0, lambda: messagebox.showerror("Error de Modelo", "No se encontró el modelo TFLite o labels.json. Entrena el modelo y expórtalo primero."))
            self.root.after(0, self.reset_buttons)
            return

        # Cargar intérprete
        try:
            interpreter = tf.lite.Interpreter(model_path=modelo_tflite_path)
            interpreter.allocate_tensors()
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()
        except Exception as e:
            self.running = False
            self.root.after(0, lambda: messagebox.showerror("Error", f"No se pudo inicializar el modelo TFLite: {e}"))
            self.root.after(0, self.reset_buttons)
            return

        # Recargar mapeo de productos en DB antes del bucle
        self.recargar_mapeo_productos()
        
        # Mapeo local de lotes activos
        mapeo_lotes = {}
        try:
            productos = self.db.get_productos()
            for p in productos:
                id_prod = p['id_producto']
                nombre = p['nombre']
                id_lote = self.db.get_lote_activo(id_prod)
                if id_lote:
                    mapeo_lotes[nombre] = {
                        'id_prod': id_prod,
                        'id_lote': id_lote
                    }
        except Exception as e:
            print(f"Error cargando mapeo de base de datos en hilo: {e}")

        # Inicializar cámara prefiriendo V4L2 en Linux
        print(f"[GUI] Iniciando cámara en índice {self.camera_index}")
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)
        if not cap.isOpened():
            print(f"[GUI] Advertencia: Falló el backend CAP_V4L2 en índice {self.camera_index}. Intentando fallback...")
            cap = cv2.VideoCapture(self.camera_index)
            
        if not cap.isOpened():
            self.running = False
            self.root.after(0, lambda: messagebox.showerror("Error de Cámara", f"No se pudo abrir el dispositivo de cámara {self.camera_index}."))
            self.root.after(0, self.reset_buttons)
            return

        print("[GUI] Cámara abierta correctamente")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Variables de conteo e histórico local
        estado_cruce = 0
        conteo_clases = {clase: 0 for clase in self.class_names}
        cooldown = 0
        fallos_frame = 0
        first_frame_printed = False

        while self.running:
            # Recargar mapeo de lotes si hubo cambios en la GUI
            if getattr(self, 'lote_actualizado', False):
                try:
                    productos_temp = self.db.get_productos()
                    for p in productos_temp:
                        id_prod_t = p['id_producto']
                        nombre_t = p['nombre']
                        id_lote_t = self.db.get_lote_activo(id_prod_t)
                        if id_lote_t:
                            mapeo_lotes[nombre_t] = {
                                'id_prod': id_prod_t,
                                'id_lote': id_lote_t
                            }
                    self.lote_actualizado = False
                    print("[GUI Thread] Mapeo de lotes actualizado en el hilo de inferencia.")
                except Exception as ex:
                    print(f"Error recargando mapeo de lotes en hilo: {ex}")

            ret, frame = cap.read()
            if not ret:
                fallos_frame += 1
                print(f"[GUI] Error de lectura de frame consecutivo {fallos_frame}/30")
                if fallos_frame >= 30:
                    print("[GUI] Se alcanzó el límite de 30 fallos consecutivos. Cerrando captura.")
                    break
                time.sleep(0.03) # Espera antes de reintentar
                continue

            # Resetear contador al leer con éxito
            fallos_frame = 0

            if not first_frame_printed:
                print(f"[GUI] Primer frame recibido: shape={frame.shape}")
                first_frame_printed = True

            alto, ancho = frame.shape[:2]

            # Definir ROI del 50% centrado
            x1 = int(ancho * 0.25)
            y1 = int(alto * 0.25)
            x2 = int(ancho * 0.75)
            y2 = int(alto * 0.75)

            # Extraer ROI limpia
            roi_raw = frame[y1:y2, x1:x2].copy()

            # Dibujar rect y línea de cruce (azul) en el frame de video
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            centro_y = y1 + (y2 - y1) // 2
            cv2.line(frame, (x1, centro_y), (x2, centro_y), (255, 0, 0), 2)

            # Preprocesamiento estricto sobre el frame de color
            blurred = cv2.GaussianBlur(roi_raw, (5, 5), 0)
            resized = cv2.resize(blurred, (128, 128))
            input_tensor = resized.astype(np.float32).reshape(1, 128, 128, 3)

            # Ejecutar inferencia
            interpreter.set_tensor(input_details[0]['index'], input_tensor)
            interpreter.invoke()
            output_data = interpreter.get_tensor(output_details[0]['index'])

            class_idx = np.argmax(output_data[0])
            confianza_max = output_data[0][class_idx]
            clase_detectada = self.class_names[class_idx]

            # Lógica de toma de decisiones
            if confianza_max > 0.85:
                nombre_vis = self.mapeo_nombre_interno_a_nombre_visible.get(clase_detectada, clase_detectada)
                texto_pred = f"{nombre_vis} ({confianza_max*100:.1f}%)"
                cv2.putText(frame, texto_pred, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                
                # Cooldown y detección de cruce
                if cooldown > 0:
                    cooldown -= 1
                
                if estado_cruce == 0:
                    estado_cruce = 1
                elif estado_cruce == 1 and cooldown == 0:
                    # Registrar conteo en memoria de UI
                    if clase_detectada in conteo_clases:
                        conteo_clases[clase_detectada] += 1
                        
                    # Persistencia en SQLite de forma asíncrona respecto a la interfaz
                    info_lote = mapeo_lotes.get(clase_detectada)
                    if info_lote:
                        id_p = info_lote['id_prod']
                        id_l = info_lote['id_lote']
                        try:
                            self.db.registrar_deteccion(id_p, id_l, float(confianza_max), f"GUI_Cam_{self.camera_index}")
                            self.need_update_tree = True
                        except Exception as db_err:
                            print(f"Error escribiendo en base de datos en hilo: {db_err}")
                    else:
                        print(f"Advertencia: No hay lote activo para {clase_detectada}. Detección omitida de SQLite.")
                        
                    estado_cruce = 2
                    cooldown = 15
            else:
                cv2.putText(frame, "Buscando...", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
                estado_cruce = 0
                if cooldown > 0:
                    cooldown -= 1

            # Dibujar contadores sobre el frame en tiempo real
            y_offset = 30
            cv2.putText(frame, "CONTEO ACTUAL:", (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
            y_offset += 20
            for clase, cnt in conteo_clases.items():
                nombre_vis = self.mapeo_nombre_interno_a_nombre_visible.get(clase, clase)
                cv2.putText(frame, f" - {nombre_vis}: {cnt}", (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2, cv2.LINE_AA)
                y_offset += 20

            # Guardar el frame actual en memoria compartida para renderizado
            with self.frame_lock:
                self.current_frame = frame.copy()
            time.sleep(0.01) # Reducir uso de CPU
            
        # Liberar recursos
        cap.release()
        self.current_frame = None
        self.running = False
        self.root.after(0, self.reset_buttons)

    def reset_buttons(self):
        """Restablece los botones del frame principal tras detener la inferencia."""
        self.btn_iniciar.configure(state="enabled")
        self.cam_combo.configure(state="readonly")
        self.btn_detener.configure(state="disabled")
        self.status_bar.configure(text="Estado: Conectado a base de datos | Cámara Detenida")
        # Limpiar label de cámara
        self.video_label.configure(image="")
        self.video_label.image = None

    def update_gui_loop(self):
        """Bucle periódico en el hilo principal de Tkinter para actualizar el frame y la tabla."""
        frame_to_show = None
        with self.frame_lock:
            if self.current_frame is not None:
                frame_to_show = self.current_frame.copy()

        if frame_to_show is not None:
            try:
                # Convertir de OpenCV (BGR) a formato visual (RGB)
                rgb_frame = cv2.cvtColor(frame_to_show, cv2.COLOR_BGR2RGB)
                image_pil = Image.fromarray(rgb_frame)
                img_tk = ImageTk.PhotoImage(image=image_pil)
                
                # Asignar al widget de video
                self.video_label.configure(image=img_tk)
                self.video_label.image = img_tk
                
                # Mensaje de diagnóstico frame enviado a Tkinter
                if not self.first_gui_frame_printed:
                    print("[GUI] Frame enviado a Tkinter")
                    self.first_gui_frame_printed = True
            except Exception as e:
                print(f"Error al renderizar frame en label: {e}")

        # Si el hilo detectó un cruce y escribió en DB, refrescamos el listado
        if self.need_update_tree:
            self.refrescar_treeview()
            self.need_update_tree = False

        # Volver a programar
        self.root.after(30, self.update_gui_loop)
