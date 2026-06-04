import os
import sqlite3
from datetime import datetime

def seed():
    db_dir = "database"
    db_path = os.path.join(db_dir, "inventario.db")
    schema_path = os.path.join(db_dir, "schema.sql")

    # Asegurar que el directorio de la base de datos existe
    os.makedirs(db_dir, exist_ok=True)

    print(f"Conectando a la base de datos en {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Habilitar soporte de claves foráneas
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Aplicar el esquema si existe para crear las tablas antes de poblar
        if os.path.exists(schema_path):
            print(f"Aplicando el esquema de base de datos desde {schema_path}...")
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            cursor.executescript(schema_sql)

        print("Limpiando tablas para evitar registros duplicados...")
        # Limpiar en orden inverso de dependencias (respetando FKs)
        cursor.execute("DELETE FROM DeteccionInventario;")
        cursor.execute("DELETE FROM Lote;")
        cursor.execute("DELETE FROM Producto;")
        
        # Reiniciar secuencias de autoincremento
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('Producto', 'Lote', 'DeteccionInventario');")

        productos = ['clase_1', 'clase_2', 'clase_3']
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("Insertando productos base y sus lotes activos...")
        for nombre in productos:
            # Insertar producto
            cursor.execute("""
                INSERT INTO Producto (nombre, descripcion, activo, fecha_creacion)
                VALUES (?, ?, 1, ?)
            """, (nombre, f"Descripción del producto {nombre}", fecha_actual))
            
            # Recuperar el ID asignado
            id_producto = cursor.lastrowid
            
            # Insertar lote activo para el producto
            cursor.execute("""
                INSERT INTO Lote (id_producto, fecha_creacion, precio_unitario, cantidad_configurada, activo)
                VALUES (?, ?, 15.50, 1000, 1)
            """, (id_producto, fecha_actual))

        conn.commit()
        print("¡Base de datos poblada con éxito!")

    except Exception as e:
        conn.rollback()
        print(f"Error crítico al poblar la base de datos: {e}")

    finally:
        conn.close()
        print("Conexión a base de datos cerrada.")

if __name__ == '__main__':
    seed()
