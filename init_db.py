import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv
load_dotenv() 

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
            ruc VARCHAR(11) NOT NULL UNIQUE,
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
        """,
        """
        CREATE TABLE usuario (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """
    )

    procedures = (
        """
        CREATE OR REPLACE FUNCTION obtener_facturas()
        RETURNS TABLE(
            id INT,
            numero TEXT,
            fecha DATE,
            cliente TEXT,
            total NUMERIC
        )
        LANGUAGE sql
        AS $$
            SELECT f.id, f.numero, f.fecha, c.nombre, f.total
            FROM facturas f
            JOIN clientes c ON f.cliente_id = c.id
            ORDER BY f.fecha DESC;
        $$;
        """,
        """
        CREATE OR REPLACE FUNCTION obtener_precio_producto(p_id INT)
        RETURNS NUMERIC
        LANGUAGE sql
        AS $$
            SELECT precio FROM productos WHERE id = p_id;
        $$;
        """,
        """
        CREATE OR REPLACE FUNCTION obtener_siguiente_numero_factura()
        RETURNS BIGINT
        LANGUAGE sql
        AS $$
            SELECT nextval('factura_numero_seq');
        $$;
        """,
        """
        CREATE OR REPLACE FUNCTION insertar_factura(
            p_numero TEXT,
            p_cliente_id INT,
            p_total NUMERIC
        )
        RETURNS INT
        LANGUAGE plpgsql
        AS $$
        DECLARE
            nuevo_id INT;
        BEGIN
            INSERT INTO facturas (numero, cliente_id, total)
            VALUES (p_numero, p_cliente_id, p_total)
            RETURNING id INTO nuevo_id;

            RETURN nuevo_id;
        END;
        $$;
        """,
        """
        CREATE OR REPLACE PROCEDURE insertar_factura_item(
            p_factura_id INTEGER,
            p_producto_id INTEGER,
            p_cantidad NUMERIC,
            p_precio NUMERIC,
            p_subtotal NUMERIC
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO factura_items (factura_id, producto_id, cantidad, precio, subtotal)
            VALUES (p_factura_id, p_producto_id, p_cantidad, p_precio, p_subtotal);
        END;
        $$;
        """,
        """
        CREATE OR REPLACE FUNCTION obtener_clientes()
        RETURNS TABLE(id INT, nombre TEXT)
        LANGUAGE sql
        AS $$
            SELECT id, nombre FROM clientes ORDER BY nombre;
        $$;
        """,
        """
        CREATE OR REPLACE FUNCTION obtener_productos()
        RETURNS TABLE(id INT, nombre TEXT, precio NUMERIC)
        LANGUAGE sql
        AS $$
            SELECT id, nombre, precio FROM productos ORDER BY nombre;
        $$;
        """,
        """
        
        CREATE OR REPLACE FUNCTION obtener_factura_por_id(p_id INT)
        RETURNS TABLE(
            id INT,
            numero TEXT,
            fecha DATE,
            total NUMERIC,
            cliente_id INT,
            cliente_nombre TEXT,
            cliente_direccion TEXT,
            cliente_telefono TEXT,
            cliente_ruc TEXT,
            cliente_email TEXT
        )
        LANGUAGE sql
        AS $$
            SELECT f.id, f.numero, f.fecha, f.total,
                c.id, c.nombre, c.direccion, c.telefono, c.ruc, c.email
            FROM facturas f
            JOIN clientes c ON f.cliente_id = c.id
            WHERE f.id = p_id;
        $$;

        """,
        """
        CREATE OR REPLACE FUNCTION obtener_items_factura(p_factura_id INT)
        RETURNS TABLE(
            id INT,
            producto TEXT,
            cantidad NUMERIC,
            precio NUMERIC,
            subtotal NUMERIC
        )
        LANGUAGE sql
        AS $$
            SELECT fi.id, p.nombre, fi.cantidad, fi.precio, fi.subtotal
            FROM factura_items fi
            JOIN productos p ON fi.producto_id = p.id
            WHERE fi.factura_id = p_factura_id;
        $$;
        """,
        """
        CREATE OR REPLACE PROCEDURE insertar_usuario(
            p_username TEXT,
            p_email TEXT,
            p_password TEXT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM usuario WHERE username = p_username) THEN
                RAISE EXCEPTION 'Usuario con ese nombre ya existe';
            END IF;

            INSERT INTO usuario (username, email, password)
            VALUES (p_username, p_email, p_password);
        END;
        $$;
        """,
        """
        CREATE OR REPLACE FUNCTION obtener_usuario_por_username(p_username TEXT)
        RETURNS TABLE (
            id INT,
            username TEXT,
            password TEXT
        )
        LANGUAGE sql
        AS $$
            SELECT id, username, password
            FROM usuario
            WHERE username = p_username;
        $$;
        """,
        """
        CREATE OR REPLACE PROCEDURE borrar_factura(p_id INT)
        LANGUAGE plpgsql
        AS $$
        BEGIN
            DELETE FROM facturas WHERE id=p_id;
        END;
        $$;
        """,
        """
        CREATE OR REPLACE PROCEDURE borrar_items_factura(
            p_factura_id INT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            -- Verificar si la factura existe antes de borrar
            IF NOT EXISTS (SELECT 1 FROM facturas WHERE id = p_factura_id) THEN
                RAISE EXCEPTION 'La factura con ID % no existe', p_factura_id;
            END IF;
            
            -- Eliminar los items asociados a la factura
            DELETE FROM factura_items 
            WHERE factura_id = p_factura_id;
        END;
        $$;
        """,
        """
        CREATE OR REPLACE PROCEDURE insertar_cliente(
            p_ruc VARCHAR(11),
            p_nombre VARCHAR(100),
            p_direccion TEXT DEFAULT NULL,
            p_telefono VARCHAR(20) DEFAULT NULL,
            p_email VARCHAR(100) DEFAULT NULL
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            -- Validar que el RUC tenga 11 dígitos
            IF p_ruc !~ '^[0-9]{11}$' THEN
                RAISE EXCEPTION 'El RUC debe tener exactamente 11 dígitos';
            END IF;
            
            -- Insertar el nuevo cliente
            INSERT INTO clientes (ruc, nombre, direccion, telefono, email)
            VALUES (p_ruc, p_nombre, p_direccion, p_telefono, p_email);
            
            RAISE NOTICE 'Cliente insertado correctamente con RUC: %', p_ruc;
        END;
        $$;
        """,
        """
        CREATE OR REPLACE PROCEDURE registrar_producto(
            p_nombre VARCHAR(100),
            p_descripcion TEXT DEFAULT NULL,
            p_precio NUMERIC(10,2) DEFAULT 0.00,
            p_stock INTEGER DEFAULT 0
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            -- Validar que el nombre no esté vacío
            IF p_nombre IS NULL OR TRIM(p_nombre) = '' THEN
                RAISE EXCEPTION 'El nombre del producto no puede estar vacío';
            END IF;
            
            -- Validar que el precio sea positivo
            IF p_precio <= 0 THEN
                RAISE EXCEPTION 'El precio debe ser mayor que cero';
            END IF;
            
            -- Validar que el stock no sea negativo
            IF p_stock < 0 THEN
                RAISE EXCEPTION 'El stock no puede ser negativo';
            END IF;
            
            -- Validar que el nombre no exista (comparación case-insensitive)
            IF EXISTS (SELECT 1 FROM productos WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(p_nombre))) THEN
                RAISE EXCEPTION 'El producto "%" ya está registrado', p_nombre;
            END IF;
            
            -- Insertar el nuevo producto
            INSERT INTO productos (nombre, descripcion, precio, stock)
            VALUES (TRIM(p_nombre), NULLIF(TRIM(p_descripcion), ''), p_precio, p_stock);
            
            RAISE NOTICE 'Producto registrado exitosamente: %', p_nombre;
        END;
        $$;
        """,
        """
            CREATE OR REPLACE PROCEDURE actualizar_factura_con_productos(
                p_factura_id INTEGER,
                p_cliente_id INTEGER,
                p_productos JSONB
            )
            LANGUAGE plpgsql
            AS $$
            DECLARE
                v_total NUMERIC(10,2) := 0;
                v_producto JSONB;
                v_subtotal NUMERIC(10,2);
                v_error_message TEXT;
            BEGIN
                -- Validar que la factura existe
                IF NOT EXISTS (SELECT 1 FROM facturas WHERE id = p_factura_id) THEN
                    RAISE EXCEPTION 'La factura con ID % no existe', p_factura_id;
                END IF;
                
                -- Validar que el cliente existe
                IF NOT EXISTS (SELECT 1 FROM clientes WHERE id = p_cliente_id) THEN
                    RAISE EXCEPTION 'El cliente con ID % no existe', p_cliente_id;
                END IF;
                
                -- Iniciar bloque con manejo de errores
                BEGIN
                    -- Actualizar datos principales de la factura
                    UPDATE facturas
                    SET cliente_id = p_cliente_id
                    WHERE id = p_factura_id;
                    
                    -- Eliminar los items actuales de la factura
                    DELETE FROM factura_items WHERE factura_id = p_factura_id;
                    
                    -- Insertar los nuevos items de la factura
                    FOR v_producto IN SELECT * FROM jsonb_array_elements(p_productos)
                    LOOP
                        -- Validar que el producto existe
                        IF NOT EXISTS (SELECT 1 FROM productos WHERE id = (v_producto->>'producto_id')::INTEGER) THEN
                            RAISE EXCEPTION 'El producto con ID % no existe', (v_producto->>'producto_id')::INTEGER;
                        END IF;
                        
                        -- Calcular subtotal
                        v_subtotal := (v_producto->>'cantidad')::INTEGER * (v_producto->>'precio')::NUMERIC(10,2);
                        v_total := v_total + v_subtotal;
                        
                        -- Insertar item
                        INSERT INTO factura_items (
                            factura_id,
                            producto_id,
                            cantidad,
                            precio,
                            subtotal
                        ) VALUES (
                            p_factura_id,
                            (v_producto->>'producto_id')::INTEGER,
                            (v_producto->>'cantidad')::INTEGER,
                            (v_producto->>'precio')::NUMERIC(10,2),
                            v_subtotal
                        );
                    END LOOP;
                    
                    -- Actualizar el total de la factura
                    UPDATE facturas
                    SET total = v_total
                    WHERE id = p_factura_id;
                    
                EXCEPTION
                    WHEN OTHERS THEN
                        -- Obtener el mensaje de error
                        GET STACKED DIAGNOSTICS v_error_message = MESSAGE_TEXT;
                        -- Revertir cualquier cambio realizado en este bloque
                        RAISE EXCEPTION '%', v_error_message;
                END;
            END;
            $$;
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
        cur.execute("DROP TABLE IF EXISTS usuario CASCADE")
        cur.execute("DROP SEQUENCE IF EXISTS factura_numero_seq")
        conn.commit()

        # Eliminar funciones y procedimientos si existen (solo para desarrollo)
        cur.execute("DROP FUNCTION IF EXISTS obtener_facturas() CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS obtener_precio_producto(INTEGER) CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS obtener_siguiente_numero_factura() CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS insertar_factura(TEXT, INTEGER, NUMERIC) CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS insertar_factura_item() CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS obtener_clientes() CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS obtener_productos() CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS obtener_factura_por_id(INTEGER) CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS obtener_items_factura(INTEGER) CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS insertar_usuario() CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS obtener_usuario_por_username(TEXT) CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS borrar_factura() CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS borrar_items_factura() CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS insertar_cliente() CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS registrar_producto() CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS actualizar_factura_con_productos() CASCADE")

        for command in commands:
            cur.execute(command)
        
        for procedure in procedures:
            cur.execute(procedure)
        
        conn.commit()
        cur.close()
        print("Tablas creadas y datos de prueba insertados correctamente.")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error al crear tablas: {error}")
    finally:
        if conn is not None:
            conn.close()


if __name__ == '__main__':
    create_tables()