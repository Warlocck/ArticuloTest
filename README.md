# Módulo de Facturación 

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/flask-2.3.x-lightgrey)
![PostgreSQL](https://img.shields.io/badge/postgresql-12%2B-blueviolet)

Sistema de facturación desarrollado con Flask y PostgreSQL para la gestión comercial de múltiples sucursales.

### Requisitos Previos
- Python 3.10 o superior
- PostgreSQL 12+
- pip (gestor de paquetes de Python)

##  Instalación
### Configuración Inicial

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/FJBarahona/Testing
   cd Testing
2. **Configurar variables de entorno:**
    - Crear archivo .env en la raíz del proyecto con:
    ```bash
    # Database
    DB_HOST=localhost
    DB_USER=tu_usuario_postgres
    DB_PASSWORD=tu_contraseña
    DB_NAME=facturacion_db
    DB_PORT=5432

    # App Security
    FLASK_SECRET_KEY=generar_clave_segura_única
3. **Entorno virtual:**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
4. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt

##  Configuración de Base de Datos
1. **Crear base de datos en PostgreSQL:**
   ```bash
   CREATE DATABASE facturacion_db;
2. **Inicializar estructura:**
   ```bash
   python init_db.py

##  Ejecución
- **Iniciar servidor de desarrollo:**
  ```bash
  flask run
- **O alternativamente:**
  ```bash
  python app.py

##  INTENGRANTES
- ALVAREZ LLANOS YANALIT KAPRIATTY
- BARAHONA CAHUANA FRANZ JONATHAN
- HUANCA HUARICALLO STEFFANY AIDA
- HUAROC CONDORI ANDRE NICOLAS


