from flask import Flask, make_response, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2 import sql
import os
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

# Configuración de la base de datos
DB_CONFIG = {
    'host': os.environ["DB_HOST"],
    'port': os.environ["DB_PORT"],
    'database': os.environ["DB_NAME"],
    'user': os.environ["DB_USER"],
    'password': os.environ["DB_PASSWORD"]
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Buscar el usuario
        cur.execute("SELECT * FROM obtener_usuario_por_username(%s);", (username,))
        user = cur.fetchone()
        
        cur.close()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['usuario_id'] = user[0]
            session['usuario'] = str(user[1]).upper()
            return redirect(url_for('listar_facturas'))
        else:
            flash('Credenciales inválidas', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        key_secret = request.form['key_secret']

        key = os.environ["KEY_SECRET_ADMIN"]

        if key_secret != key:
            return "Clave secreta incorrecta", 401

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('CALL insertar_usuario(%s, %s, %s);',
                    (nombre, email, generate_password_hash(password)))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()  # Borra todos los datos de sesión
    return redirect(url_for('login'))

@app.route('/facturas', methods=['GET', 'POST'])
def listar_facturas():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        criterio = request.form['criterio']
        valor = request.form['valor']
        if criterio == 'numero':
            cur.execute("SELECT * FROM obtener_facturas() WHERE numero ILIKE %s", ('%' + valor + '%',))
        elif criterio == 'fecha':
            cur.execute("SELECT * FROM obtener_facturas() WHERE fecha::text ILIKE %s", ('%' + valor + '%',))
        elif criterio == 'cliente':
            cur.execute("SELECT * FROM obtener_facturas() WHERE cliente ILIKE %s", ('%' + valor + '%',))
    else:
        cur.execute('SELECT * FROM obtener_facturas();')
    
    facturas = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('factura.html', facturas=facturas)

@app.route('/factura/nueva', methods=['GET', 'POST'])
def nueva_factura():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        # Obtener datos del formulario
        cliente_id = request.form['cliente_id']
        items = []
        total = 0
        
        # Procesar items
        for i in range(1, 6):  # Máximo 5 items por factura
            producto_id = request.form.get(f'producto_id_{i}')
            cantidad = request.form.get(f'cantidad_{i}')
            if producto_id and cantidad:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute('SELECT * FROM obtener_precio_producto(%s);', (producto_id,))
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
        
        # Insertar factura con número generado
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Obtener el próximo número de factura de la secuencia
        cur.execute("SELECT * FROM obtener_siguiente_numero_factura()")
        numero_factura = f"FACT-{cur.fetchone()[0]}"
        
        cur.execute(
            'SELECT insertar_factura(%s, %s, %s);',
            (numero_factura, cliente_id, total)
        )
        factura_id = cur.fetchone()[0]
        
        # Insertar items de factura
        for item in items:
            cur.execute(
                'CALL insertar_factura_item(%s, %s, %s, %s, %s);',
                (factura_id, item['producto_id'], item['cantidad'], item['precio'], item['subtotal'])
            )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return redirect(url_for('ver_factura', id=factura_id))
    
    else:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Obtener clientes
        cur.execute('SELECT * FROM obtener_clientes();')
        clientes = cur.fetchall()
        
        # Obtener productos
        cur.execute('SELECT * FROM obtener_productos();')
        productos = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('nueva_factura.html', clientes=clientes, productos=productos)

@app.route('/factura/<int:id>')
def ver_factura(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Obtener factura
    cur.execute('''
        SELECT * FROM obtener_factura_por_id(%s);
    ''', (id,))
    factura = cur.fetchone()
    
    # Obtener items
    cur.execute('''
        SELECT * FROM obtener_items_factura(%s);
    ''', (id,))
    items = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('ver_factura.html', factura=factura, items=items)

@app.route('/factura/editar/<int:id>', methods=['GET', 'POST'])
def editar_factura(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        items = []
        total = 0

        for i in range(1, 6):
            producto_id = request.form.get(f'producto_id_{i}')
            cantidad = request.form.get(f'cantidad_{i}')
            if producto_id and cantidad:
                cur.execute('SELECT * FROM obtener_precio_producto(%s);', (producto_id,))
                precio = cur.fetchone()[0]
                subtotal = float(precio) * float(cantidad)
                items.append({
                    'producto_id': producto_id,
                    'cantidad': cantidad,
                    'precio': precio,
                    'subtotal': subtotal
                })
                total += subtotal

        cur.execute('UPDATE facturas SET cliente_id = %s, total = %s WHERE id = %s;', (cliente_id, total, id))
        cur.execute('DELETE FROM factura_items WHERE factura_id = %s;', (id,))

        for item in items:
            cur.execute(
                'CALL insertar_factura_item(%s, %s, %s, %s, %s);',
                (id, item['producto_id'], item['cantidad'], item['precio'], item['subtotal'])
            )

        conn.commit()
        cur.close()
        conn.close()

        flash('Factura actualizada exitosamente', 'success')
        return redirect(url_for('ver_factura', id=id))

    # Método GET: mostrar formulario con datos actuales
    cur.execute('SELECT * FROM obtener_factura_por_id(%s);', (id,))
    factura = cur.fetchone()

    cur.execute('SELECT * FROM obtener_items_factura(%s);', (id,))
    items = cur.fetchall()

    cur.execute('SELECT * FROM obtener_clientes();')
    clientes = cur.fetchall()

    cur.execute('SELECT * FROM obtener_productos();')
    productos = cur.fetchall()

    # Preparar los productos y cantidades seleccionadas para el formulario
    productos_seleccionados = {}
    cantidades_seleccionadas = {}

    for idx in range(5):
        if idx < len(items):
            productos_seleccionados[f'producto_id_{idx+1}'] = items[idx][2]  # producto_id
            cantidades_seleccionadas[f'cantidad_{idx+1}'] = items[idx][3]    # cantidad
        else:
            productos_seleccionados[f'producto_id_{idx+1}'] = ''
            cantidades_seleccionadas[f'cantidad_{idx+1}'] = ''

    cur.close()
    conn.close()

    return render_template(
        'editar_factura.html',
        factura=factura,
        items=items,
        clientes=clientes,
        productos=productos,
        productos_seleccionados=productos_seleccionados,
        cantidades_seleccionadas=cantidades_seleccionadas
    )

@app.route('/factura/pdf/<int:id>')
def exportar_factura_pdf(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT * FROM obtener_factura_por_id(%s);', (id,))
        factura = cur.fetchone()
        
        if not factura:
            flash('Factura no encontrada', 'danger')
            return redirect(url_for('listar_facturas'))
        
        cur.execute('SELECT * FROM obtener_items_factura(%s);', (id,))
        items = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Crear el PDF en memoria
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        elements = []
        
        styles = getSampleStyleSheet()
        title = Paragraph(f"Factura #{factura[1]}", styles['Title'])
        elements.append(title)
        
        # Información de la factura
        factura_info = [
            ["Fecha:", factura[2]],
            ["Cliente:", factura[5]],
            ["Dirección:", factura[6]],
            ["Teléfono:", factura[7]],
        ]
        table_factura_info = Table(factura_info, hAlign='LEFT')
        table_factura_info.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table_factura_info)
        elements.append(Paragraph("<br/><br/>", styles['Normal']))
        
        # Items de la factura
        items_data = [["Producto", "Cantidad", "Precio Unitario", "Subtotal"]]
        for item in items:
            items_data.append([item[1], item[2], f"S/.{item[3]:.2f}", f"S/.{item[4]:.2f}"])
        
        table_items = Table(items_data, colWidths=[doc.width/4.0]*4, hAlign='LEFT')
        table_items.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table_items)
        elements.append(Paragraph("<br/><br/>", styles['Normal']))
        
        # Total de la factura
        total_data = [["Total:", f"S/.{factura[3]:.2f}"]]
        table_total = Table(total_data, colWidths=[doc.width/4.0]*4, hAlign='LEFT')
        table_total.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table_total)
        
        doc.build(elements)
        
        # Preparar la respuesta
        pdf_buffer.seek(0)
        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=factura_{factura[1]}.pdf'
        
        return response
    except Exception as e:
        flash(f'Error al generar el PDF: {str(e)}', 'danger')
        return redirect(url_for('listar_facturas'))

if __name__ == '__main__':
    app.run(debug=True)