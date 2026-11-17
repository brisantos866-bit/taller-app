# taller_web/db.py
import os
import random
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/taller_db")

def obtener_conexion():
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url, cursor_factory=RealDictCursor)

def migrar():
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS talleres (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    telefono VARCHAR(50),
                    direccion TEXT,
                    pin VARCHAR(6) NOT NULL,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS equipos (
                    id SERIAL PRIMARY KEY,
                    taller_id INTEGER REFERENCES talleres(id) ON DELETE CASCADE,
                    numero VARCHAR(50) NOT NULL,
                    tipo VARCHAR(100) NOT NULL,
                    capacidad INTEGER NOT NULL,
                    precio_dia NUMERIC(10,2) NOT NULL,
                    estado VARCHAR(50) DEFAULT 'libre',
                    notas TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    taller_id INTEGER REFERENCES talleres(id) ON DELETE CASCADE,
                    nombre VARCHAR(255) NOT NULL,
                    documento VARCHAR(50),
                    telefono VARCHAR(50),
                    correo VARCHAR(255)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ordenes (
                    id SERIAL PRIMARY KEY,
                    taller_id INTEGER REFERENCES talleres(id) ON DELETE CASCADE,
                    equipo_id INTEGER REFERENCES equipos(id) ON DELETE CASCADE,
                    cliente_id INTEGER REFERENCES clientes(id) ON DELETE CASCADE,
                    cantidad_periodos INTEGER NOT NULL,
                    tarifa NUMERIC(10,2) NOT NULL,
                    moneda VARCHAR(10) DEFAULT 'USD',
                    periodo VARCHAR(50) DEFAULT 'dia',
                    observaciones TEXT,
                    total NUMERIC(10,2) NOT NULL,
                    estado VARCHAR(50) DEFAULT 'activo',
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()

def migrar_mensajes():
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS plantillas (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    contenido TEXT NOT NULL
                );
            """)
        conn.commit()

# ==================== TALLERES ====================

def crear_taller(nombre, email, telefono="", direccion=""):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            pin = str(random.randint(100000, 999999))
            cur.execute(
                "INSERT INTO talleres (nombre, email, telefono, direccion, pin) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (nombre, email, telefono, direccion, pin)
            )
            tid = cur.fetchone()["id"]
        conn.commit()
        return tid, pin

def listar_talleres():
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM talleres ORDER BY id DESC")
            return cur.fetchall()

def obtener_taller(tid):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM talleres WHERE id = %s", (tid,))
            return cur.fetchone()

def obtener_taller_por_email_pin(email, pin):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM talleres WHERE email = %s AND pin = %s", (email, pin))
            return cur.fetchone()

def regenerar_pin_taller(tid):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            nuevo_pin = str(random.randint(100000, 999999))
            cur.execute("UPDATE talleres SET pin = %s WHERE id = %s", (nuevo_pin, tid))
        conn.commit()
        return nuevo_pin

# ==================== EQUIPOS ====================

def listar_equipos(tid, solo_libres=False):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            query = "SELECT * FROM equipos WHERE taller_id = %s"
            if solo_libres:
                query += " AND estado = 'libre'"
            query += " ORDER BY numero"
            cur.execute(query, (tid,))
            return cur.fetchall()

def crear_equipo(tid, numero, tipo, capacidad, precio_dia, notas=""):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO equipos (taller_id, numero, tipo, capacidad, precio_dia, notas) VALUES (%s, %s, %s, %s, %s, %s)",
                (tid, numero, tipo, capacidad, precio_dia, notas)
            )
        conn.commit()

def actualizar_equipo(tid, eq_id, numero, tipo, capacidad, precio_dia, estado, notas=""):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE equipos 
                SET numero=%s, tipo=%s, capacidad=%s, precio_dia=%s, estado=%s, notas=%s 
                WHERE id=%s AND taller_id=%s
            """, (numero, tipo, capacidad, precio_dia, estado, notas, eq_id, tid))
        conn.commit()

def eliminar_equipo(tid, eq_id):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM equipos WHERE id=%s AND taller_id=%s", (eq_id, tid))
        conn.commit()

def obtener_equipo(tid, eq_id):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM equipos WHERE id=%s AND taller_id=%s", (eq_id, tid))
            return cur.fetchone()

# ==================== CLIENTES ====================

def listar_clientes(tid):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM clientes WHERE taller_id = %s ORDER BY nombre", (tid,))
            return cur.fetchall()

def crear_cliente(tid, nombre, documento="", telefono="", correo=""):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO clientes (taller_id, nombre, documento, telefono, correo) VALUES (%s, %s, %s, %s, %s)",
                (tid, nombre, documento, telefono, correo)
            )
        conn.commit()

def obtener_cliente(tid, cliente_id):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM clientes WHERE id=%s AND taller_id=%s", (cliente_id, tid))
            return cur.fetchone()

# ==================== ÓRDENES DE SERVICIO ====================

def registrar_orden(tid, equipo_id, cliente_id, cantidad_periodos, tarifa, moneda="USD", periodo="dia", observaciones=""):
    total = cantidad_periodos * tarifa
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ordenes (taller_id, equipo_id, cliente_id, cantidad_periodos, tarifa, moneda, periodo, observaciones, total)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (tid, equipo_id, cliente_id, cantidad_periodos, tarifa, moneda, periodo, observaciones, total))
            oid = cur.fetchone()["id"]
            cur.execute("UPDATE equipos SET estado = 'ocupada' WHERE id = %s", (equipo_id,))
        conn.commit()
        return oid, total

def obtener_orden(oid, tid):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.*, 
                       c.nombre as cliente, c.telefono, c.documento,
                       e.numero as equipo_numero, e.tipo as equipo_tipo,
                       t.nombre as taller_nombre
                FROM ordenes o
                JOIN clientes c ON o.cliente_id = c.id
                JOIN equipos e ON o.equipo_id = e.id
                JOIN talleres t ON o.taller_id = t.id
                WHERE o.id = %s AND o.taller_id = %s
            """, (oid, tid))
            return cur.fetchone()

def cerrar_orden(oid, tid):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT equipo_id FROM ordenes WHERE id=%s AND taller_id=%s", (oid, tid))
            res = cur.fetchone()
            if res:
                eq_id = res["equipo_id"]
                cur.execute("UPDATE ordenes SET estado = 'cerrado' WHERE id=%s", (oid,))
                cur.execute("UPDATE equipos SET estado = 'libre' WHERE id=%s", (eq_id,))
        conn.commit()

def listar_ordenes_activas(tid):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.*, 
                       c.nombre as cliente,
                       e.numero as equipo_numero, e.tipo as equipo_tipo
                FROM ordenes o
                JOIN clientes c ON o.cliente_id = c.id
                JOIN equipos e ON o.equipo_id = e.id
                WHERE o.taller_id = %s AND o.estado = 'activo'
                ORDER BY o.id DESC
            """, (tid,))
            return cur.fetchall()

# ==================== PLANTILLAS ====================

def listar_plantillas():
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM plantillas ORDER BY id")
            return cur.fetchall()

def guardar_plantilla(nombre, contenido):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO plantillas (nombre, contenido) VALUES (%s, %s)", (nombre, contenido))
        conn.commit()

def eliminar_plantilla(pid):
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM plantillas WHERE id=%s", (pid,))
        conn.commit()