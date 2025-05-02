from flask import Flask, render_template, request, redirect, url_for
import psycopg2
from psycopg2 import sql

app = Flask(__name__)

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'database': 'facturacion_db',
    'user': 'postgres',
    'password': 'alumno'
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

@app.route('/')
def index():
    return redirect(url_for('listar_facturas'))

@app.route('/facturas')
def listar_facturas():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT f.id, f.numero, f.fecha, c.nombre as cliente, f.total FROM facturas f JOIN clientes c ON f.cliente_id = c.id ORDER BY f.fecha DESC;')
    facturas = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('facturas.html', facturas=facturas)

@app.route('/factura/nueva', methods=['GET', 'POST'])
def nueva_factura():
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        items = []
        total = 0
        
        for i in range(1, 6):  
            producto_id = request.form.get(f'producto_id_{i}')
            cantidad = request.form.get(f'cantidad_{i}')
            if producto_id and cantidad:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute('SELECT precio FROM productos WHERE id = %s;', (producto_id,))
                precio = cur.fetchone()[0]
                subtotal = float(precio) * float(cantidad)
                items.append({
                    'producto_id': producto_id,
                    'cantidad': cantidad,
                    'precio': precio,
                    'subtotal': subtotal
                })
                total += subtotal
                cur.close()
                conn.close()
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT nextval('factura_numero_seq')")
        numero_factura = f"FACT-{cur.fetchone()[0]}"
        
        cur.execute(
            'INSERT INTO facturas (numero, cliente_id, total) VALUES (%s, %s, %s) RETURNING id;',
            (numero_factura, cliente_id, total)
        )
        factura_id = cur.fetchone()[0]
        
        for item in items:
            cur.execute(
                'INSERT INTO factura_items (factura_id, producto_id, cantidad, precio, subtotal) VALUES (%s, %s, %s, %s, %s);',
                (factura_id, item['producto_id'], item['cantidad'], item['precio'], item['subtotal'])
            )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return redirect(url_for('ver_factura', id=factura_id))
    
    else:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT id, nombre FROM clientes ORDER BY nombre;')
        clientes = cur.fetchall()
        
        cur.execute('SELECT id, nombre, precio FROM productos ORDER BY nombre;')
        productos = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('nueva_factura.html', clientes=clientes, productos=productos)

@app.route('/factura/<int:id>')
def ver_factura(id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT f.id, f.numero, f.fecha, f.total, c.id as cliente_id, c.nombre as cliente_nombre, 
               c.direccion as cliente_direccion, c.telefono as cliente_telefono
        FROM facturas f JOIN clientes c ON f.cliente_id = c.id WHERE f.id = %s;
    ''', (id,))
    factura = cur.fetchone()
    
    cur.execute('''
        SELECT fi.id, p.nombre as producto, fi.cantidad, fi.precio, fi.subtotal
        FROM factura_items fi JOIN productos p ON fi.producto_id = p.id
        WHERE fi.factura_id = %s;
    ''', (id,))
    items = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('ver_factura.html', factura=factura, items=items)

if __name__ == '__main__':
    app.run(debug=True)