import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        # Definir la ruta estática para la base de datos SQLite
        self.db_path = 'database/inventario.db'
        # Asegurar que el directorio del archivo de base de datos exista
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def get_productos(self):
        """Retorna una lista de diccionarios con los productos activos."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id_producto, nombre, descripcion, activo, fecha_creacion 
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
        """Retorna un resumen con el conteo de detecciones por producto y lote."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.nombre AS producto, 
                    l.id_lote AS lote, 
                    COUNT(d.id_deteccion) AS conteo
                FROM Producto p
                JOIN Lote l ON p.id_producto = l.id_producto
                LEFT JOIN DeteccionInventario d ON p.id_producto = d.id_producto AND l.id_lote = d.id_lote
                WHERE p.activo = 1 AND l.activo = 1
                GROUP BY p.id_producto, l.id_lote
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
