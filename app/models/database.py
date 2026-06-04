import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        # Definir la ruta estática para la base de datos SQLite
        self.db_path = 'database/inventario.db'
        # Asegurar que el directorio del archivo de base de datos exista
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Asegurar que la estructura del esquema esté actualizada
        self.asegurar_columnas_producto()

    def asegurar_columnas_producto(self):
        """Revisa la tabla Producto, agrega la columna nombre_visible si no existe y puebla valores por defecto."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(Producto)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'nombre_visible' not in columns:
                print("[DB] Agregando columna 'nombre_visible' a la tabla Producto...")
                cursor.execute("ALTER TABLE Producto ADD COLUMN nombre_visible TEXT")
                conn.commit()
                
            # Poblar valores por defecto si están vacíos
            cursor.execute("SELECT id_producto, nombre, nombre_visible FROM Producto")
            productos = cursor.fetchall()
            for id_prod, nombre, nombre_vis in productos:
                if nombre_vis is None or str(nombre_vis).strip() == "":
                    # Valores amigables por defecto
                    if nombre == 'clase_1':
                        def_name = "Producto 1"
                    elif nombre == 'clase_2':
                        def_name = "Producto 2"
                    elif nombre == 'clase_3':
                        def_name = "Producto 3"
                    else:
                        def_name = nombre.replace("_", " ").title()
                    
                    cursor.execute("""
                        UPDATE Producto 
                        SET nombre_visible = ? 
                        WHERE id_producto = ?
                    """, (def_name, id_prod))
            conn.commit()

    def get_productos(self):
        """Retorna una lista de diccionarios con los productos activos."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id_producto, nombre, nombre_visible, descripcion, activo, fecha_creacion 
                FROM Producto 
                WHERE activo = 1
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_lote_activo(self, id_producto):
        """Retorna el id_lote del lote activo para un producto dado."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id_lote 
                FROM Lote 
                WHERE id_producto = ? AND activo = 1 
                LIMIT 1
            """, (id_producto,))
            row = cursor.fetchone()
            return row[0] if row else None

    def registrar_deteccion(self, id_producto, id_lote, confianza, fuente):
        """Inserta un nuevo registro en DeteccionInventario usando la fecha y hora actual."""
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO DeteccionInventario (id_producto, id_lote, fecha_hora, confianza, fuente)
                VALUES (?, ?, ?, ?, ?)
            """, (id_producto, id_lote, fecha_hora, confianza, fuente))
            conn.commit()

    def get_inventario_actual(self):
        """Retorna un resumen con el conteo de detecciones por producto y lote activo."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.id_producto AS id_producto,
                    p.nombre AS producto_interno, 
                    p.nombre_visible AS producto_visible,
                    l.id_lote AS lote, 
                    l.precio_unitario AS precio_unitario,
                    COUNT(d.id_deteccion) AS conteo
                FROM Producto p
                JOIN Lote l ON p.id_producto = l.id_producto
                LEFT JOIN DeteccionInventario d ON p.id_producto = d.id_producto AND l.id_lote = d.id_lote
                WHERE p.activo = 1 AND l.activo = 1
                GROUP BY p.id_producto, l.id_lote
            """)
            rows = cursor.fetchall()
            res = []
            for row in rows:
                item = dict(row)
                item['total_lote'] = item['conteo'] * item['precio_unitario']
                res.append(item)
            return res

    def crear_lote_activo(self, id_producto, precio_unitario, cantidad_configurada):
        """Desactiva los lotes anteriores del producto especificado y crea uno nuevo activo."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 1. Desactivar lotes anteriores para este producto
            cursor.execute("""
                UPDATE Lote 
                SET activo = 0 
                WHERE id_producto = ?
            """, (id_producto,))
            
            # 2. Insertar nuevo lote activo
            fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO Lote (id_producto, fecha_creacion, precio_unitario, cantidad_configurada, activo)
                VALUES (?, ?, ?, ?, 1)
            """, (id_producto, fecha_creacion, precio_unitario, cantidad_configurada))
            conn.commit()

    def actualizar_nombre_visible_producto(self, id_producto, nombre_visible):
        """Actualiza el nombre visible de un producto. Valida que no esté vacío."""
        if not nombre_visible or nombre_visible.strip() == "":
            raise ValueError("El nombre visible del producto no puede estar vacío.")
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Producto 
                SET nombre_visible = ? 
                WHERE id_producto = ?
            """, (nombre_visible.strip(), id_producto))
            conn.commit()

    def get_lotes_producto(self, id_producto):
        """Retorna todos los lotes del producto especificado."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id_lote, fecha_creacion, precio_unitario, cantidad_configurada, activo 
                FROM Lote 
                WHERE id_producto = ?
                ORDER BY id_lote DESC
            """, (id_producto,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def actualizar_precio_lote(self, id_lote, precio_unitario):
        """Actualiza el precio unitario de un lote. Valida que sea mayor a cero."""
        try:
            precio = float(precio_unitario)
            if precio <= 0:
                raise ValueError()
        except ValueError:
            raise ValueError("El precio unitario debe ser un número mayor a cero.")
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Lote 
                SET precio_unitario = ? 
                WHERE id_lote = ?
            """, (precio, id_lote))
            conn.commit()

    def get_reporte_inventario(self, product_ids=None, fecha_inicio=None, fecha_fin=None):
        """Retorna el reporte de inventario filtrado por productos y fechas."""
        f_inicio_str = None
        if fecha_inicio and fecha_inicio.strip():
            val = fecha_inicio.strip()
            if len(val) == 10:  # YYYY-MM-DD
                f_inicio_str = f"{val} 00:00:00"
            else:
                f_inicio_str = val
                
        f_fin_str = None
        if fecha_fin and fecha_fin.strip():
            val = fecha_fin.strip()
            if len(val) == 10:  # YYYY-MM-DD
                f_fin_str = f"{val} 23:59:59"
            else:
                f_fin_str = val

        # Consulta base con LEFT JOIN
        query = """
            SELECT 
                p.id_producto,
                p.nombre AS producto_interno,
                COALESCE(p.nombre_visible, p.nombre) AS producto_visible,
                l.id_lote AS lote,
                l.fecha_creacion AS fecha_creacion_lote,
                l.precio_unitario,
                COUNT(d.id_deteccion) AS unidades_registradas,
                ROUND(l.precio_unitario * COUNT(d.id_deteccion), 2) AS total_lote,
                MIN(d.fecha_hora) AS primera_fecha_registro,
                MAX(d.fecha_hora) AS ultima_fecha_registro
            FROM Producto p
            JOIN Lote l ON p.id_producto = l.id_producto
            LEFT JOIN DeteccionInventario d 
                ON d.id_producto = p.id_producto 
                AND d.id_lote = l.id_lote
        """
        
        # Filtros de fecha en la cláusula ON del LEFT JOIN para considerar solo el rango en el conteo
        join_params = []
        on_clause_extras = []
        if f_inicio_str:
            on_clause_extras.append("d.fecha_hora >= ?")
            join_params.append(f_inicio_str)
        if f_fin_str:
            on_clause_extras.append("d.fecha_hora <= ?")
            join_params.append(f_fin_str)
            
        if on_clause_extras:
            query += " AND " + " AND ".join(on_clause_extras)
            
        # Filtros en la cláusula WHERE (incluyendo solo productos activos)
        conditions = ["p.activo = 1"]
        where_params = []
        if product_ids:
            placeholders = ",".join(["?"] * len(product_ids))
            conditions.append(f"p.id_producto IN ({placeholders})")
            where_params.extend(product_ids)
            
        query += " WHERE " + " AND ".join(conditions)
        query += " GROUP BY p.id_producto, l.id_lote"
        query += " ORDER BY p.nombre_visible, l.id_lote"
        
        # Combinar parámetros en orden correcto
        all_params = join_params + where_params
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, all_params)
            rows = cursor.fetchall()
            
            res = []
            for row in rows:
                item = dict(row)
                item['fecha_inicio_aplicada'] = f_inicio_str
                item['fecha_fin_aplicada'] = f_fin_str
                res.append(item)
            return res

