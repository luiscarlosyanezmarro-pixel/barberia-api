from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
import mysql.connector
import hashlib
import re
import os
from dotenv import load_dotenv
import sys

# Cargar variables de entorno desde archivo .env (ruta explícita)
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

# Verificar que las variables se cargaron
print(f"📁 Archivo .env buscado en: {env_path}")
print(f"📁 Archivo .env existe: {os.path.exists(env_path)}")
print(f"🔑 DB_HOST: {os.getenv('DB_HOST', 'NO CARGADO')}")
print(f"🔑 DB_USER: {os.getenv('DB_USER', 'NO CARGADO')}")

# ============================================================
# CONFIGURACIÓN DE LA BASE DE DATOS (desde variables de entorno)
# ============================================================

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'barberia_db'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'autocommit': True,
    'use_pure': True,
    'connection_timeout': 30
}

print(f"🔌 Conectando a: {DB_CONFIG['host']}:{DB_CONFIG['port']} como {DB_CONFIG['user']}")

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    return mysql.connector.connect(**DB_CONFIG)

# ============================================================
# MODELOS PYDANTIC
# ============================================================

class UserLogin(BaseModel):
    username: str
    password: str

class Material(BaseModel):
    name: str
    description: Optional[str] = None
    stock: int = 0
    min_stock: int = 5
    unit: str = "unidad"
    price: float = 0.0
    supplier: Optional[str] = None

class Service(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    duration: int = 30
    active: bool = True

class Sale(BaseModel):
    service_id: int
    client_name: str
    client_phone: Optional[str] = None
    price: float
    payment_method: str = "efectivo"
    barber_name: Optional[str] = None

class Purchase(BaseModel):
    material_id: int
    quantity: int
    total_price: float
    supplier: Optional[str] = None

class Appointment(BaseModel):
    client_name: str
    client_phone: Optional[str] = None
    service_id: int
    appointment_date: str
    appointment_time: str
    barber_name: Optional[str] = None
    status: str = "pendiente"

class AppointmentStatus(BaseModel):
    status: str

# ============================================================
# APLICACIÓN FASTAPI
# ============================================================

app = FastAPI(title="Barbería API", version="1.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ENDPOINTS DE AUTENTICACIÓN
# ============================================================

@app.get("/")
def read_root():
    return {"mensaje": "API de Barbería funcionando correctamente"}

@app.post("/api/login")
def login(user: UserLogin):
    hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, username, name, role FROM users 
        WHERE username = %s AND password = %s
    """, (user.username, hashed_password))
    db_user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if db_user:
        return {"success": True, "user": db_user}
    else:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

# ============================================================
# ENDPOINTS DE MATERIALES
# ============================================================

@app.get("/api/materials")
def get_materials():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM materials ORDER BY name")
    materials = cursor.fetchall()
    cursor.close()
    conn.close()
    return materials

@app.get("/api/materials/{material_id}")
def get_material(material_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM materials WHERE id = %s", (material_id,))
    material = cursor.fetchone()
    cursor.close()
    conn.close()
    if material:
        return material
    raise HTTPException(status_code=404, detail="Material no encontrado")

@app.post("/api/materials")
def create_material(material: Material):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO materials (name, description, stock, min_stock, unit, price, supplier)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (material.name, material.description, material.stock, material.min_stock,
          material.unit, material.price, material.supplier))
    material_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return {"id": material_id, "message": "Material creado exitosamente"}

@app.put("/api/materials/{material_id}")
def update_material(material_id: int, material: Material):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE materials 
        SET name = %s, description = %s, stock = %s, min_stock = %s,
            unit = %s, price = %s, supplier = %s
        WHERE id = %s
    """, (material.name, material.description, material.stock, material.min_stock,
          material.unit, material.price, material.supplier, material_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Material actualizado exitosamente"}

@app.delete("/api/materials/{material_id}")
def delete_material(material_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM materials WHERE id = %s", (material_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Material eliminado exitosamente"}

# ============================================================
# ENDPOINTS DE SERVICIOS
# ============================================================

@app.get("/api/services")
def get_services():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM services WHERE active = 1 ORDER BY name")
    services = cursor.fetchall()
    cursor.close()
    conn.close()
    return services

@app.get("/api/services/{service_id}")
def get_service(service_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM services WHERE id = %s", (service_id,))
    service = cursor.fetchone()
    cursor.close()
    conn.close()
    if service:
        return service
    raise HTTPException(status_code=404, detail="Servicio no encontrado")

@app.post("/api/services")
def create_service(service: Service):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO services (name, description, price, duration, active)
        VALUES (%s, %s, %s, %s, 1)
    """, (service.name, service.description, service.price, service.duration))
    service_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return {"id": service_id, "message": "Servicio creado exitosamente"}

@app.put("/api/services/{service_id}")
def update_service(service_id: int, service: Service):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE services 
        SET name = %s, description = %s, price = %s, duration = %s
        WHERE id = %s
    """, (service.name, service.description, service.price, service.duration, service_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Servicio actualizado exitosamente"}

@app.delete("/api/services/{service_id}")
def delete_service(service_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE services SET active = 0 WHERE id = %s", (service_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Servicio eliminado exitosamente"}

# ============================================================
# ENDPOINTS DE VENTAS
# ============================================================

@app.get("/api/sales/by-date")
def get_sales_by_date(date: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT COALESCE(SUM(price), 0) as total 
        FROM sales 
        WHERE DATE(sale_date) = %s
    """, (date,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return {"total": float(result['total']) if result else 0.0}

@app.get("/api/sales")
def get_sales():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.id, s.service_id, s.client_name, s.client_phone, s.price, 
               s.sale_date, s.payment_method, s.barber_name, s.user_id
        FROM sales s
        ORDER BY s.sale_date DESC
        LIMIT 50
    """)
    sales = cursor.fetchall()
    
    for sale in sales:
        if sale.get('sale_date'):
            sale['sale_date'] = str(sale['sale_date'])
    
    cursor.close()
    conn.close()
    return sales

@app.get("/api/sales/{sale_id}")
def get_sale(sale_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.id, s.service_id, s.client_name, s.client_phone, s.price, 
               s.sale_date, s.payment_method, s.barber_name, s.user_id
        FROM sales s
        WHERE s.id = %s
    """, (sale_id,))
    sale = cursor.fetchone()
    cursor.close()
    conn.close()
    if sale:
        if sale.get('sale_date'):
            sale['sale_date'] = str(sale['sale_date'])
        return sale
    raise HTTPException(status_code=404, detail="Venta no encontrada")

@app.post("/api/sales")
def create_sale(sale: Sale):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sales (service_id, client_name, client_phone, price, payment_method, barber_name)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (sale.service_id, sale.client_name, sale.client_phone, sale.price,
          sale.payment_method, sale.barber_name))
    sale_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return {"id": sale_id, "message": "Venta registrada exitosamente"}

@app.put("/api/sales/{sale_id}")
def update_sale(sale_id: int, sale: Sale):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE sales 
        SET service_id = %s, client_name = %s, client_phone = %s, 
            price = %s, payment_method = %s, barber_name = %s
        WHERE id = %s
    """, (sale.service_id, sale.client_name, sale.client_phone,
          sale.price, sale.payment_method, sale.barber_name, sale_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Venta actualizada exitosamente"}

@app.delete("/api/sales/{sale_id}")
def delete_sale(sale_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sales WHERE id = %s", (sale_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Venta eliminada exitosamente"}

# ============================================================
# ENDPOINTS DE COMPRAS
# ============================================================

@app.get("/api/purchases")
def get_purchases():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.id, p.material_id, p.quantity, p.total_price, p.supplier, p.purchase_date,
               m.name as material_name, m.price as material_price
        FROM purchases p
        JOIN materials m ON p.material_id = m.id
        ORDER BY p.purchase_date DESC
        LIMIT 50
    """)
    purchases = cursor.fetchall()
    
    for purchase in purchases:
        if purchase.get('purchase_date'):
            purchase['purchase_date'] = str(purchase['purchase_date'])
    
    cursor.close()
    conn.close()
    return purchases

@app.get("/api/purchases/{purchase_id}")
def get_purchase(purchase_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.id, p.material_id, p.quantity, p.total_price, p.supplier, p.purchase_date,
               m.name as material_name, m.price as material_price
        FROM purchases p
        JOIN materials m ON p.material_id = m.id
        WHERE p.id = %s
    """, (purchase_id,))
    purchase = cursor.fetchone()
    cursor.close()
    conn.close()
    if purchase:
        if purchase.get('purchase_date'):
            purchase['purchase_date'] = str(purchase['purchase_date'])
        return purchase
    raise HTTPException(status_code=404, detail="Compra no encontrada")

@app.post("/api/purchases")
def create_purchase(purchase: Purchase):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO purchases (material_id, quantity, total_price, supplier)
        VALUES (%s, %s, %s, %s)
    """, (purchase.material_id, purchase.quantity, purchase.total_price, purchase.supplier))
    purchase_id = cursor.lastrowid
    
    cursor.execute("UPDATE materials SET stock = stock + %s WHERE id = %s", 
                   (purchase.quantity, purchase.material_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"id": purchase_id, "message": "Compra registrada exitosamente"}

@app.put("/api/purchases/{purchase_id}")
def update_purchase(purchase_id: int, purchase: Purchase):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT material_id, quantity FROM purchases WHERE id = %s", (purchase_id,))
    old = cursor.fetchone()
    
    if old:
        old_material_id, old_quantity = old
        
        cursor.execute("UPDATE materials SET stock = stock - %s WHERE id = %s", 
                       (old_quantity, old_material_id))
        
        cursor.execute("""
            UPDATE purchases 
            SET material_id = %s, quantity = %s, total_price = %s, supplier = %s
            WHERE id = %s
        """, (purchase.material_id, purchase.quantity, purchase.total_price, purchase.supplier, purchase_id))
        
        cursor.execute("UPDATE materials SET stock = stock + %s WHERE id = %s", 
                       (purchase.quantity, purchase.material_id))
        
        conn.commit()
    
    cursor.close()
    conn.close()
    return {"message": "Compra actualizada exitosamente"}

@app.delete("/api/purchases/{purchase_id}")
def delete_purchase(purchase_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT material_id, quantity FROM purchases WHERE id = %s", (purchase_id,))
    purchase = cursor.fetchone()
    
    if purchase:
        material_id, quantity = purchase
        cursor.execute("UPDATE materials SET stock = stock - %s WHERE id = %s", (quantity, material_id))
        cursor.execute("DELETE FROM purchases WHERE id = %s", (purchase_id,))
        conn.commit()
    
    cursor.close()
    conn.close()
    return {"message": "Compra eliminada exitosamente"}

# ============================================================
# ENDPOINTS DE CITAS
# ============================================================

@app.get("/api/appointments")
def get_appointments(filter_date: Optional[str] = Query(None)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if filter_date:
        cursor.execute("""
            SELECT a.id, a.client_name, a.client_phone, a.service_id, a.appointment_date,
                   a.appointment_time, a.barber_name, a.status, a.created_at,
                   s.name as service_name
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            WHERE a.appointment_date = %s
            ORDER BY a.appointment_date DESC, a.appointment_time ASC
        """, (filter_date,))
    else:
        cursor.execute("""
            SELECT a.id, a.client_name, a.client_phone, a.service_id, a.appointment_date,
                   a.appointment_time, a.barber_name, a.status, a.created_at,
                   s.name as service_name
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            ORDER BY a.appointment_date DESC, a.appointment_time ASC
            LIMIT 50
        """)
    
    appointments = cursor.fetchall()
    for a in appointments:
        if a.get('appointment_date'):
            a['appointment_date'] = str(a['appointment_date'])
        if a.get('appointment_time'):
            a['appointment_time'] = str(a['appointment_time'])
    
    cursor.close()
    conn.close()
    return appointments

@app.get("/api/appointments/{appointment_id}")
def get_appointment(appointment_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.id, a.client_name, a.client_phone, a.service_id, a.appointment_date,
               a.appointment_time, a.barber_name, a.status, a.created_at,
               s.name as service_name
        FROM appointments a
        JOIN services s ON a.service_id = s.id
        WHERE a.id = %s
    """, (appointment_id,))
    appointment = cursor.fetchone()
    cursor.close()
    conn.close()
    if appointment:
        if appointment.get('appointment_date'):
            appointment['appointment_date'] = str(appointment['appointment_date'])
        if appointment.get('appointment_time'):
            appointment['appointment_time'] = str(appointment['appointment_time'])
        return appointment
    raise HTTPException(status_code=404, detail="Cita no encontrada")

@app.post("/api/appointments")
def create_appointment(appointment: Appointment):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO appointments (client_name, client_phone, service_id, 
                                appointment_date, appointment_time, barber_name, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (appointment.client_name, appointment.client_phone, appointment.service_id,
          appointment.appointment_date, appointment.appointment_time, 
          appointment.barber_name, appointment.status))
    appointment_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return {"id": appointment_id, "message": "Cita agendada exitosamente"}

@app.put("/api/appointments/{appointment_id}")
def update_appointment(appointment_id: int, appointment: Appointment):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE appointments 
        SET client_name = %s, client_phone = %s, service_id = %s,
            appointment_date = %s, appointment_time = %s, barber_name = %s, status = %s
        WHERE id = %s
    """, (appointment.client_name, appointment.client_phone, appointment.service_id,
          appointment.appointment_date, appointment.appointment_time, 
          appointment.barber_name, appointment.status, appointment_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Cita actualizada exitosamente"}

@app.put("/api/appointments/{appointment_id}/status")
def update_appointment_status(appointment_id: int, status_data: AppointmentStatus):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = %s WHERE id = %s", 
                   (status_data.status, appointment_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Estado de cita actualizado a {status_data.status}"}

@app.delete("/api/appointments/{appointment_id}")
def delete_appointment(appointment_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Cita eliminada exitosamente"}

# ============================================================
# ENDPOINTS DE DASHBOARD
# ============================================================

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT COUNT(*) as total FROM services WHERE active = 1")
    result = cursor.fetchone()
    total_services = result['total'] if result else 0
    
    cursor.execute("SELECT COALESCE(SUM(price), 0) as total FROM sales WHERE DATE(sale_date) = CURDATE()")
    result = cursor.fetchone()
    sales_today = float(result['total']) if result and result['total'] is not None else 0.0
    
    cursor.execute("SELECT COUNT(*) as total FROM appointments WHERE DATE(appointment_date) = CURDATE()")
    result = cursor.fetchone()
    appointments_today = result['total'] if result else 0
    
    cursor.execute("SELECT COUNT(*) as total FROM materials WHERE stock <= min_stock")
    result = cursor.fetchone()
    low_stock = result['total'] if result else 0
    
    cursor.close()
    conn.close()
    
    return {
        "total_services": total_services,
        "sales_today": sales_today,
        "appointments_today": appointments_today,
        "low_stock": low_stock
    }

@app.get("/api/dashboard/recent-sales")
def get_recent_sales(limit: int = 5):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.client_name, ser.name as service_name, s.price, s.sale_date
        FROM sales s
        JOIN services ser ON s.service_id = ser.id
        ORDER BY s.sale_date DESC
        LIMIT %s
    """, (limit,))
    sales = cursor.fetchall()
    
    for sale in sales:
        if sale.get('sale_date'):
            sale['sale_date'] = str(sale['sale_date'])
    
    cursor.close()
    conn.close()
    return sales

# ============================================================
# ENDPOINT DE DEPURACIÓN
# ============================================================

@app.get("/api/sales/debug")
def debug_sales():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id, price, sale_date, DATE(sale_date) as sale_date_only FROM sales ORDER BY sale_date DESC")
    sales = cursor.fetchall()
    
    for sale in sales:
        if sale.get('sale_date'):
            sale['sale_date'] = str(sale['sale_date'])
        if sale.get('sale_date_only'):
            sale['sale_date_only'] = str(sale['sale_date_only'])
    
    cursor.execute("SELECT CURDATE() as today")
    today = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return {
        "server_today": str(today['today']) if today else "unknown",
        "sales": sales,
        "count": len(sales)
    }

# ============================================================
# INICIALIZACIÓN DE TABLAS
# ============================================================

@app.on_event("startup")
def startup_event():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Crear tablas si no existen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(100) NOT NULL,
                role VARCHAR(50) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL,
                duration INT DEFAULT 30,
                active BOOLEAN DEFAULT TRUE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                stock INT DEFAULT 0,
                min_stock INT DEFAULT 5,
                unit VARCHAR(20) DEFAULT 'unidad',
                price DECIMAL(10, 2) DEFAULT 0,
                supplier VARCHAR(100)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INT AUTO_INCREMENT PRIMARY KEY,
                material_id INT,
                quantity INT NOT NULL,
                total_price DECIMAL(10, 2) NOT NULL,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                supplier VARCHAR(100),
                user_id INT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                service_id INT,
                client_name VARCHAR(100),
                client_phone VARCHAR(20),
                price DECIMAL(10, 2) NOT NULL,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payment_method VARCHAR(50),
                barber_name VARCHAR(100),
                user_id INT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                client_name VARCHAR(100) NOT NULL,
                client_phone VARCHAR(20),
                service_id INT,
                appointment_date DATE,
                appointment_time TIME,
                barber_name VARCHAR(100),
                status VARCHAR(50) DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crear usuario admin
        hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (username, password, name, role) 
                VALUES (%s, %s, %s, %s)
            """, ('admin', hashed_password, 'Administrador', 'admin'))
            print("Usuario admin creado")
        
        # Insertar servicios de ejemplo si no hay
        cursor.execute("SELECT COUNT(*) FROM services")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO services (name, price, duration, active) VALUES 
                ('Corte de Cabello', 15.00, 30, 1),
                ('Barba', 10.00, 20, 1),
                ('Corte + Barba', 22.00, 50, 1)
            """)
            print("Servicios de ejemplo creados")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Base de datos inicializada correctamente")
        
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {e}")

# ============================================================
# EJECUCIÓN LOCAL
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)