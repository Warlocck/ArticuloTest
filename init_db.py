import psycopg2
from psycopg2 import sql
import os

# Configuración de la base de datos
DB_CONFIG = {
    'host': os.environ["DB_HOST"],
    'port': os.environ["DB_PORT"],
    'database': os.environ["DB_NAME"],
    'user': os.environ["DB_USER"],
    'password': os.environ["DB_PASSWORD"]
}

def create_tables():
    commands = (
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            direccion TEXT,
            telefono VARCHAR(20),
            email VARCHAR(100)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            descripcion TEXT,
            precio DECIMAL(10, 2) NOT NULL,
            stock INTEGER DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS facturas (
            id SERIAL PRIMARY KEY,
            numero VARCHAR(20) NOT NULL UNIQUE,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cliente_id INTEGER NOT NULL,
            total DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS factura_items (
            id SERIAL PRIMARY KEY,
            factura_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            precio DECIMAL(10, 2) NOT NULL,
            subtotal DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (factura_id) REFERENCES facturas (id),
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
        """,
        """
        CREATE SEQUENCE IF NOT EXISTS factura_numero_seq START WITH 1000
        """
    )
    
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Eliminar tablas si existen (solo para desarrollo)
        cur.execute("DROP TABLE IF EXISTS factura_items CASCADE")
        cur.execute("DROP TABLE IF EXISTS facturas CASCADE")
        cur.execute("DROP TABLE IF EXISTS productos CASCADE")
        cur.execute("DROP TABLE IF EXISTS clientes CASCADE")
        cur.execute("DROP SEQUENCE IF EXISTS factura_numero_seq")
        conn.commit()
        
        for command in commands:
            cur.execute(command)
        
        # Insertar datos de prueba
        insert_test_data(cur)
        
        conn.commit()
        cur.close()
        print("Tablas creadas y datos de prueba insertados correctamente.")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error al crear tablas: {error}")
    finally:
        if conn is not None:
            conn.close()

def insert_test_data(cur):
    # Verificar si ya hay datos
    cur.execute("SELECT COUNT(*) FROM clientes;")
    if cur.fetchone()[0] > 0:
        return
    
    # Insertar clientes
    clientes = [
        ("Juan Pérez", "Av. Siempre Viva 742", "987654321", "juan.perez@example.com"),
        ("María García", "Calle Falsa 123", "987654322", "maria.garcia@example.com"),
        ("Carlos Sánchez", "Av. Los Álamos 456", "987654323", "carlos.sanchez@example.com"),
        ("Ana López", "Calle de la Rosa 789", "987654324", "ana.lopez@example.com"),
        ("Luis Martínez", "Av. del Sol 101", "987654325", "luis.martinez@example.com"),
        ("Laura Fernández", "Calle Luna 202", "987654326", "laura.fernandez@example.com"),
        ("Pedro Gómez", "Av. Estrella 303", "987654327", "pedro.gomez@example.com"),
        ("Sofía Torres", "Calle Mar 404", "987654328", "sofia.torres@example.com"),
        ("Miguel Díaz", "Av. Río 505", "987654329", "miguel.diaz@example.com"),
        ("Lucía Romero", "Calle Montaña 606", "987654330", "lucia.romero@example.com")
    ]
    
    for cliente in clientes:
        cur.execute(
            "INSERT INTO clientes (nombre, direccion, telefono, email) VALUES (%s, %s, %s, %s);",
            cliente
        )
    
    # Insertar productos
    productos = [
        ("Laptop HP", "Laptop HP con procesador Intel i5 y 8GB de RAM", 750.00),
        ("Smartphone Samsung", "Smartphone Samsung Galaxy S21", 999.99),
        ("Monitor LG", "Monitor LG de 24 pulgadas Full HD", 150.00),
        ("Teclado Mecánico", "Teclado mecánico con switches Cherry MX Blue", 85.50),
        ("Mouse Inalámbrico", "Mouse inalámbrico Logitech MX Master 3", 99.99),
        ("Impresora Canon", "Impresora multifuncional Canon Pixma", 120.00),
        ("Tablet Apple", "Tablet Apple iPad Pro 11 pulgadas", 799.00),
        ("Auriculares Sony", "Auriculares inalámbricos Sony WH-1000XM4", 350.00),
        ("Cámara Nikon", "Cámara réflex Nikon D3500", 450.00),
        ("Disco Duro Externo", "Disco duro externo Seagate 2TB", 70.00)
    ]
    
    for producto in productos:
        cur.execute(
            "INSERT INTO productos (nombre, descripcion, precio) VALUES (%s, %s, %s);",
            producto
        )

if __name__ == '__main__':
    create_tables()
