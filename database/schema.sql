-- Activar soporte para claves foráneas en SQLite
PRAGMA foreign_keys = ON;

-- Tabla Producto
CREATE TABLE IF NOT EXISTS Producto (
    id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    descripcion TEXT,
    activo INTEGER DEFAULT 1,
    fecha_creacion TEXT NOT NULL
);

-- Tabla Lote
CREATE TABLE IF NOT EXISTS Lote (
    id_lote INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL,
    fecha_creacion TEXT NOT NULL,
    precio_unitario REAL NOT NULL,
    cantidad_configurada INTEGER NOT NULL,
    activo INTEGER DEFAULT 1,
    FOREIGN KEY (id_producto) REFERENCES Producto(id_producto) ON DELETE CASCADE
);

-- Tabla DeteccionInventario
CREATE TABLE IF NOT EXISTS DeteccionInventario (
    id_deteccion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL,
    id_lote INTEGER NOT NULL,
    fecha_hora TEXT NOT NULL,
    confianza REAL NOT NULL,
    fuente TEXT NOT NULL,
    FOREIGN KEY (id_producto) REFERENCES Producto(id_producto) ON DELETE CASCADE,
    FOREIGN KEY (id_lote) REFERENCES Lote(id_lote) ON DELETE CASCADE
);
