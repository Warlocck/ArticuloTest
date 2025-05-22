from flask import Flask, make_response, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2 import sql, errors as pg_errors
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import abort
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from io import BytesIO
import json

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
        username = request.form.get('username', '').strip().upper()
        password = request.form.get('password', '')

        # Validaciones
        if not username or not password:
            flash("Por favor, ingrese su nombre de usuario y contraseña", "error")
            return redirect(url_for('login'))

        if len(username) < 5:
            flash("El nombre de usuario debe tener al menos 5 caracteres", "error")
            return redirect(url_for('login'))

        if len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres", "error")
            return redirect(url_for('login'))

        # Conexión a la base de datos
        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("SELECT * FROM obtener_usuario_por_username(%s);", (username,))
            user = cur.fetchone()
        except Exception as e:
            print(f"Error al buscar el usuario: {e}")
            flash("Ocurrió un error al buscar el usuario", "error")
            return redirect(url_for('login'))
        finally:
            cur.close()
            conn.close()

        if user and check_password_hash(user[2], password):
            session['usuario_id'] = user[0]
            session['usuario'] = str(user[1]).upper()
            return redirect(url_for('listar_facturas'))
        else:
            flash('Nombre de usuario o contraseña incorrectos', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('nombre', '').strip().upper()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        key_secret = request.form.get('key_secret', '').strip()

        # Validaciones
        if not username:
            flash("Por favor, ingrese su nombre de usuario", "error")
            return redirect(url_for('register'))

        if not email:
            flash("Por favor, ingrese su correo electrónico", "error")
            return redirect(url_for('register'))
        elif '@' not in email or '.' not in email:
            flash("Formato de correo inválido", "error")
            return redirect(url_for('register'))

        if not password:
            flash("Por favor, ingrese su contraseña", "error")
            return redirect(url_for('register'))
        elif len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres", "error")
            return redirect(url_for('register'))

        if not key_secret:
            flash("Por favor, ingrese la clave secreta", "error")
            return redirect(url_for('register'))

        # Comparar clave secreta
        expected_key = os.environ.get("KEY_SECRET_ADMIN")
        if key_secret != expected_key:
            flash("Clave secreta incorrecta", "error")
            return redirect(url_for('register'))

        # Intentar registrar usuario
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                'CALL insertar_usuario(%s, %s, %s);',
                (username, email, generate_password_hash(password))
            )
            conn.commit()
            flash('Usuario registrado exitosamente', 'success')
            return redirect(url_for('login'))
        except pg_errors.UniqueViolation:
            conn.rollback()
            flash('El nombre de usuario o correo ya están registrados', 'error')
        except Exception as e:
            conn.rollback()
            print(f"Error al registrar el usuario: {e}")
            flash('Ocurrió un error al registrar el usuario', 'error')
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('login'))
@app.route('/facturas', methods=['GET', 'POST'])
def listar_facturas():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    facturas = []
    error = None

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if request.method == 'POST':
                    numero = request.form.get('numero', '').strip()
                    cliente = request.form.get('cliente', '').strip()
                    fecha = request.form.get('fecha', '').strip()

                    condiciones = []
                    valores = []

                    # Validación: número de factura debe ser exactamente 4 dígitos
                    if numero:
                        if not numero.isdigit() or len(numero) != 4:
                            flash("El número de factura debe contener exactamente 4 dígitos numéricos.", "danger")
                            return redirect(url_for('listar_facturas'))
                        condiciones.append("RIGHT(f.numero, 4) = %s")
                        valores.append(numero)

                    # Validación: cliente solo letras (incluyendo ñ y tildes)
                    if cliente:
                        import re
                        if not re.match(r"^[A-Za-zÑñÁÉÍÓÚáéíóú\s]+$", cliente):
                            flash("El nombre del cliente solo puede contener letras y espacios.", "danger")
                            return redirect(url_for('listar_facturas'))
                        condiciones.append("c.nombre ILIKE %s")
                        valores.append(f"%{cliente}%")

                    # Validación básica de fecha
                    if fecha:
                        condiciones.append("CAST(f.fecha AS TEXT) ILIKE %s")
                        valores.append(f"%{fecha}%")

                    query = """
                        SELECT f.id, f.numero, f.fecha, c.nombre, f.total
                        FROM facturas f
                        JOIN clientes c ON f.cliente_id = c.id
                    """

                    if condiciones:
                        query += " WHERE " + " AND ".join(condiciones)

                    query += " ORDER BY f.fecha DESC"

                    cur.execute(query, tuple(valores))
                    facturas = cur.fetchall()
                else:
                    cur.execute('SELECT * FROM obtener_facturas();')
                    facturas = cur.fetchall()
    except Exception as e:
        error = "Ocurrió un error al obtener las facturas. Intente más tarde."
        print(f"Error en listar_facturas: {e}")

    if error:
        flash(error, 'danger')

    return render_template('factura.html', facturas=facturas)

@app.route('/factura/nueva', methods=['GET', 'POST'])
def nueva_factura():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        # Obtener datos del formulario
        cliente_id = request.form['cliente_id']
        items = []
        total = 0

        # CAMBIO 8 
        # 🛡️ Validación: verificar si el cliente existe
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM clientes WHERE id = %s;", (cliente_id,))
            cliente_existe = cur.fetchone()[0] > 0
            cur.close()
            conn.close()

            if not cliente_existe:
                flash("El cliente no existe.", "error")
                return redirect(url_for('nueva_factura'))
        except Exception as e:
            print(f"Error al verificar cliente: {e}")
            flash("Error al verificar el cliente.", "error")
            return redirect(url_for('nueva_factura'))

        # Procesar items
        for i in range(1, 6):  # Máximo 5 items por factura
            producto_id = request.form.get(f'producto_id_{i}')
            cantidad = request.form.get(f'cantidad_{i}')
            try:
                if producto_id and cantidad:
                    conn = get_db_connection()
                    cur = conn.cursor()

                    # Obtener precio y stock del producto
                    cur.execute('SELECT precio, stock FROM productos WHERE id = %s;', (producto_id,))
                    producto = cur.fetchone()

                    if not producto:
                        flash(f"El producto con ID {producto_id} no existe.", "error")
                        cur.close()
                        conn.close()
                        return redirect(url_for('nueva_factura'))

                    precio, stock_disponible = producto
                    cantidad = int(cantidad)

                    if cantidad > stock_disponible:
                        flash(f"La cantidad solicitada ({cantidad}) excede el stock disponible ({stock_disponible}) para el producto ID {producto_id}.", "error")
                        cur.close()
                        conn.close()
                        return redirect(url_for('nueva_factura'))

                    subtotal = float(precio) * cantidad
                    items.append({
                        'producto_id': producto_id,
                        'cantidad': cantidad,
                        'precio': precio,
                        'subtotal': subtotal
                    })
                    total += subtotal
            except Exception as e:
                print(f"Error al procesar el item: {e}")
                flash('Error al procesar el item.', 'error')
                return redirect(url_for('nueva_factura'))
            finally:
                cur.close()
                conn.close()
        
        # --- VALIDACIÓN CRÍTICA ---
        if not items:
            flash('Error: Una factura debe tener al menos un producto.', 'error')
            return redirect(url_for('nueva_factura'))  # Redirige de vuelta al formulario

        try:
            # Insertar factura con número generado
            conn = get_db_connection()
            cur = conn.cursor()

            # Obtener el próximo número de factura de la secuencia
            cur.execute("SELECT * FROM obtener_siguiente_numero_factura()")
            numero_factura = f"FACT-{cur.fetchone()[0]}"

            cur.execute(
                'SELECT insertar_factura(%s, %s, %s);', (numero_factura, cliente_id, total)
                )
            factura_id = cur.fetchone()[0]
            conn.commit()

            # Insertar items de factura y actualizar stock
            for item in items:
                cur.execute(
                    'CALL insertar_factura_item(%s, %s, %s, %s, %s);',
                    (factura_id, item['producto_id'], item['cantidad'], item['precio'], item['subtotal'])
                )

                # Actualizar el stock del producto
                cur.execute(
                    'UPDATE productos SET stock = stock - %s WHERE id = %s;',
                    (item['cantidad'], item['producto_id'])
                )


            conn.commit()
        except Exception as e:
            print(f"Error al insertar la factura: {e}")
            conn.rollback()
            flash('Error al insertar la factura.', 'error')
            return redirect(url_for('nueva_factura'))
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('ver_factura', id=factura_id))
    else:
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Obtener clientes
            cur.execute('SELECT * FROM obtener_clientes();')
            clientes = cur.fetchall()

            # Obtener productos
            cur.execute('SELECT * FROM obtener_productos();')
            productos = cur.fetchall()

        except Exception as e:
            print(f"Error al obtener clientes o productos: {e}")
            flash('Error al cargar los datos.', 'error')
            return redirect(url_for('listar_facturas'))
        finally:
            cur.close()
            conn.close()
        return render_template('nueva_factura.html', clientes=clientes, productos=productos)

@app.route('/factura/<int:id>', methods=['GET'])
def ver_factura(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtener factura
    cur.execute('''SELECT * FROM obtener_factura_por_id(%s);''', (id,))
    factura = cur.fetchone()
    #Cambio 9
    # Validación: si no existe la factura, redirigir con mensaje
    if not factura:
        cur.close()
        conn.close()
        flash("La factura no existe o ha sido eliminada.", "error")
        return redirect(url_for('listar_facturas'))

    # Obtener items
    cur.execute('''SELECT * FROM obtener_items_factura(%s);''', (id,))
    items = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('ver_factura.html', factura=factura, items=items)


@app.route('/factura/editar/<int:id>', methods=['GET', 'POST'])
def editar_factura(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Obtener datos básicos de la factura
        cur.execute('SELECT id, cliente_id, total, numero FROM facturas WHERE id = %s;', (id,))
        factura = cur.fetchone()

        if not factura:
            flash('Factura no encontrada', 'danger')
            return redirect(url_for('listar_facturas'))

        # Manejo del POST (actualización)
        if request.method == 'POST':
            cliente_id = request.form['cliente_id']
            items = []

            # Procesar los 5 posibles productos del formulario
            for i in range(1, 6):
                producto_id = request.form.get(f'producto_id_{i}')
                cantidad = request.form.get(f'cantidad_{i}')
                
                if producto_id and cantidad and int(cantidad) > 0:
                    precio = request.form.get(f'precio_{i}')
                    items.append({
                        'producto_id': producto_id,
                        'cantidad': cantidad,
                        'precio': precio
                    })

            try:
                # Convertir a JSON para el procedimiento almacenado
                productos_json = json.dumps(items)
                
                # Ejecutar el procedimiento almacenado
                cur.execute("CALL actualizar_factura_con_productos(%s, %s, %s)", (id, cliente_id, productos_json))
                conn.commit()
                
                flash('Factura actualizada correctamente', 'success')
                return redirect(url_for('ver_factura', id=id))

            except Exception as e:
                conn.rollback()
                flash(f'Error al actualizar factura: {str(e)}', 'danger')

        # Obtener datos para el formulario (GET o POST con error)
        cur.execute('''
            SELECT fi.id, fi.producto_id, p.nombre, fi.cantidad, fi.precio, fi.subtotal
            FROM factura_items fi
            JOIN productos p ON fi.producto_id = p.id
            WHERE fi.factura_id = %s
            ORDER BY fi.id;
        ''', (id,))
        items = cur.fetchall()

        cur.execute('SELECT id, nombre FROM clientes ORDER BY nombre;')
        clientes = cur.fetchall()

        cur.execute('SELECT id, nombre, precio FROM productos ORDER BY nombre;')
        productos = cur.fetchall()

        # Preparar datos para los selects
        productos_seleccionados = {}
        cantidades_seleccionadas = {}
        
        for idx in range(5):  # Para las 5 filas del formulario
            if idx < len(items):
                productos_seleccionados[f'producto_id_{idx+1}'] = items[idx][1]  # producto_id
                cantidades_seleccionadas[f'cantidad_{idx+1}'] = items[idx][3]    # cantidad
            else:
                productos_seleccionados[f'producto_id_{idx+1}'] = ''
                cantidades_seleccionadas[f'cantidad_{idx+1}'] = ''

        return render_template(
            'editar_factura.html',
            factura=factura,
            items=items,
            clientes=clientes,
            productos=productos,
            productos_seleccionados=productos_seleccionados,
            cantidades_seleccionadas=cantidades_seleccionadas
        )

    except Exception as e:
        flash(f'Error al cargar la página: {str(e)}', 'danger')
        return redirect(url_for('listar_facturas'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/factura/borrar/<int:id>')
def borrar_factura(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Borrar items de la factura
        cur.execute('CALL borrar_items_factura(%s);', (id,))
        conn.commit()
        # Borrar la factura
        cur.execute('CALL borrar_factura(%s);', (id,))
        conn.commit()
        flash("Factura eliminada exitosamente.", "success")
    except Exception as e:
            print(f"Error al eliminar la factura: {e}")
            conn.rollback()
            flash("Error al eliminar la factura.", "error")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('listar_facturas'))


@app.route('/factura/registrar_cliente', methods=['POST', 'GET'])
def registrar_cliente():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        ruc = request.form.get('ruc')
        if not ruc:
            print("RUC no proporcionado")
            flash("El RUC es obligatorio.", "error")
            return redirect(url_for('nueva_factura'))
        nombre = request.form.get('nombre').upper()
        if not nombre:
            print("Nombre no proporcionado")
            flash("El nombre es obligatorio.", "error")
            return redirect(url_for('nueva_factura'))
        email = request.form.get('email').lower()
        if not email:
            print("Email no proporcionado")
            flash("El email es obligatorio.", "error")
            return redirect(url_for('nueva_factura'))
        telefono = request.form.get('telefono')
        if len(telefono) < 9:
            print("Teléfono inválido")
            flash("El teléfono debe tener al menos 9 dígitos.", "error")
            return redirect(url_for('nueva_factura'))
        direccion = request.form.get('direccion').upper()
        if not direccion:
            print("Dirección no proporcionada")
            flash("La dirección es obligatoria.", "error")
            return redirect(url_for('nueva_factura'))

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute('CALL insertar_cliente(%s, %s, %s, %s, %s);', (ruc, nombre, direccion, telefono, email))
            conn.commit()
            flash("Cliente registrado exitosamente.", "success")
        except pg_errors.UniqueViolation:
            conn.rollback()
            flash("El cliente ya existe con ese RUC.", "error")
        except Exception as e:
            print(f"Error al registrar el cliente: {e}")
            conn.rollback()
            flash("Error al registrar el cliente.", "error")
        finally:
            cur.close()
            conn.close()
    
    return render_template('registrar_cliente.html')

@app.route('/factura/registrar_producto', methods=['POST', 'GET'])
def registrar_producto():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form.get('nombre').upper()
        descripcion = request.form.get('descripcion').upper()
        precio = request.form.get('precio')
        stock = request.form.get('stock')

        if not nombre or not descripcion or not precio or not stock:
            flash("Todos los campos son obligatorios.", "error")
            return redirect(url_for('registrar_producto'))

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute('CALL registrar_producto(%s, %s, %s, %s);', (nombre, descripcion, precio, stock))
            conn.commit()
            flash("Producto registrado exitosamente.", "success")
        except pg_errors.RaiseException as e:
            print(f"Error al registrar el producto: {e}")
            conn.rollback()
            flash("El producto ya existe.", "error")
        except pg_errors.UniqueViolation:
            conn.rollback()
            flash("El producto ya existe.", "error")
        except Exception as e:
            print(f"Error al registrar el producto: {e}")
            conn.rollback()
            flash("Error al registrar el producto.", "error")
        finally:
            cur.close()
            conn.close()

    return render_template('registrar_producto.html')

@app.route('/factura/pdf/<int:id>')
def exportar_factura_pdf(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Obtener los datos de la factura
        cur.execute('SELECT * FROM obtener_factura_por_id(%s);', (id,))
        factura = cur.fetchone()

        if not factura:
            flash('Factura no encontrada', 'danger')
            return redirect(url_for('listar_facturas'))

        # Obtener los ítems de la factura
        cur.execute('SELECT * FROM obtener_items_factura(%s);', (id,))
        items = cur.fetchall()

    except Exception as e:
        flash(f'Error al obtener datos de la factura: {str(e)}', 'danger')
        return redirect(url_for('listar_facturas'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
    # Crear el PDF en memoria
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"Factura #{factura[1]}", styles['Title']))

    # Datos básicos de la factura
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

    # Lista de ítems de la factura
    items_data = [["Producto", "Cantidad", "Precio Unitario", "Subtotal"]]
    for item in items:
        items_data.append([
            item[1],
            item[2],
            f"S/.{item[3]:.2f}",
            f"S/.{item[4]:.2f}"
        ])

    table_items = Table(items_data, colWidths=[doc.width / 4.0] * 4, hAlign='LEFT')
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
    table_total = Table(total_data, colWidths=[doc.width / 4.0] * 4, hAlign='LEFT')
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

    # Generar PDF y enviarlo como respuesta
    doc.build(elements)
    pdf_buffer.seek(0)

    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=factura_{factura[1]}.pdf'

    return response

@app.route('/productos/actualizar_stock', methods=['GET', 'POST'])
def actualizar_stock():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    productos = []
    error = None

    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            for key in request.form:
                if key.startswith('stock_'):
                    try:
                        producto_id = int(key.split('_')[1])
                        nuevo_stock = int(request.form[key])

                        if nuevo_stock < 0:
                            flash(f"El stock para el producto ID {producto_id} no puede ser negativo.", "danger")
                            continue

                        cur.execute('UPDATE productos SET stock = %s WHERE id = %s;', (nuevo_stock, producto_id))
                    except ValueError:
                        flash(f"Entrada inválida para el producto con clave {key}.", "danger")
                        continue

            conn.commit()
            flash("Stock actualizado correctamente.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error al actualizar el stock: {e}", "error")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('actualizar_stock'))

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, nombre, stock FROM productos ORDER BY nombre;')
        productos = cur.fetchall()
    except Exception as e:
        error = f"Error al obtener productos: {e}"
        flash(error, "danger")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template('actualizar_stock.html', productos=productos)

if __name__ == '__main__':
    app.run(debug=True)