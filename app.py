# taller_web/app.py
import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

# Importamos las funciones con nombres profesionales
from db import (
    migrar, migrar_mensajes,
    crear_taller, listar_talleres, obtener_taller_por_email_pin, regenerar_pin_taller,
    listar_equipos, crear_equipo, actualizar_equipo, eliminar_equipo, obtener_equipo,
    listar_clientes, crear_cliente, obtener_cliente,
    registrar_orden, obtener_orden, cerrar_orden, listar_ordenes_activas,
    listar_plantillas, guardar_plantilla, eliminar_plantilla,
)
from tickets import (
    generar_ticket_taller, generar_enlace_whatsapp, generar_enlace_sms,
    generar_mensaje_celular,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esta-clave")

with app.app_context():
    try:
        migrar()
        migrar_mensajes()
    except Exception as e:
        print("⚠️ No se pudo migrar la base de datos:", e)

# ==================== LOGIN ====================

def taller_requerido(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("taller_id"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pin = request.form.get("pin", "").strip()
        taller = obtener_taller_por_email_pin(email, pin)
        if taller:
            session["taller_id"] = taller["id"]
            session["taller_nombre"] = taller["nombre"]
            return redirect(url_for("ordenes"))
        flash("Correo o PIN incorrecto", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==================== REGISTRO ====================

@app.route("/registro", methods=["POST"])
def registro_taller():
    nombre = request.form.get("nombre", "").strip()
    email = request.form.get("email", "").strip().lower()
    telefono = request.form.get("telefono", "").strip()
    direccion = request.form.get("direccion", "").strip()

    if not nombre or not email:
        flash("Nombre y correo son obligatorios.", "error")
        return redirect(url_for("login"))

    try:
        tid, pin = crear_taller(nombre, email, telefono, direccion)
    except Exception as e:
        flash(f"Error al registrar: {e}", "error")
        return redirect(url_for("login"))

    flash("✅ Solicitud recibida. Contacta al administrador para activar tu taller y recibir tu PIN.", "ok")
    return redirect(url_for("login"))


# ==================== PANEL DE CONTROL ====================

@app.route("/admin/control-pin", methods=["GET"])
def admin_control_pin():
    clave_secreta = request.args.get("clave")
    if clave_secreta != "tallermaster2026":
        return "Acceso denegado. Falta la clave secreta.", 403
    return render_template("admin_control_pin.html", talleres=listar_talleres())


@app.route("/admin/control-pin/<int:tid>/regenerar", methods=["POST"])
def admin_regenerar_pin(tid):
    try:
        nuevo_pin = regenerar_pin_taller(tid)
        flash(f"✅ PIN regenerado exitosamente: {nuevo_pin}", "ok")
    except Exception as e:
        flash(f"Error al regenerar PIN: {e}", "error")
    return redirect(url_for("admin_control_pin", clave="tallermaster2026"))


# ==================== INICIO ====================

@app.route("/")
@taller_requerido
def index():
    return redirect(url_for("ordenes"))


# ==================== EQUIPOS ====================

@app.route("/equipos", methods=["GET", "POST"])
@taller_requerido
def equipos():
    tid = session["taller_id"]
    if request.method == "POST":
        try:
            crear_equipo(
                tid,
                request.form["numero"].strip(), # Placa o Modelo
                request.form["tipo"].strip(),   # Marca o Tipo
                int(request.form["capacidad"]), # Año o Capacidad
                float(request.form["precio_dia"]), # Tarifa base
                request.form.get("notas", "").strip(),
            )
            flash("Equipo registrado exitosamente.", "ok")
        except Exception as e:
            flash(f"Error: {e}", "error")
        return redirect(url_for("equipos"))
    return render_template("equipos.html",
                           equipos=listar_equipos(tid),
                           taller_nombre=session.get("taller_nombre", ""))


@app.route("/equipos/<int:eid>/editar", methods=["GET", "POST"])
@taller_requerido
def editar_equipo(eid):
    tid = session["taller_id"]
    eq = obtener_equipo(tid, eid)
    if not eq:
        flash("Equipo no encontrado.", "error")
        return redirect(url_for("equipos"))
    if request.method == "POST":
        try:
            actualizar_equipo(
                tid, eid,
                request.form["numero"].strip(),
                request.form["tipo"].strip(),
                int(request.form["capacidad"]),
                float(request.form["precio_dia"]),
                request.form["estado"].strip(),
                request.form.get("notas", "").strip(),
            )
            flash("Datos del equipo actualizados.", "ok")
            return redirect(url_for("equipos"))
        except Exception as e:
            flash(f"Error: {e}", "error")
    return render_template("editar_equipo.html", eq=eq)


@app.route("/equipos/<int:eid>/eliminar", methods=["POST"])
@taller_requerido
def borrar_equipo(eid):
    try:
        eliminar_equipo(session["taller_id"], eid)
        flash("Equipo eliminado del sistema.", "ok")
    except Exception as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("equipos"))


# ==================== CLIENTES ====================

@app.route("/clientes", methods=["GET", "POST"])
@taller_requerido
def clientes():
    tid = session["taller_id"]
    if request.method == "POST":
        try:
            crear_cliente(
                tid,
                request.form["nombre"].strip(),
                request.form.get("documento", "").strip(), # Cédula / RUC
                request.form.get("telefono", "").strip(),
                request.form.get("correo", "").strip(),
            )
            flash("Cliente registrado exitosamente.", "ok")
        except Exception as e:
            flash(f"Error: {e}", "error")
        return redirect(url_for("clientes"))
    return render_template("clientes.html",
                           clientes=listar_clientes(tid),
                           taller_nombre=session.get("taller_nombre", ""))


# ==================== ÓRDENES DE SERVICIO ====================

@app.route("/ordenes", methods=["GET", "POST"])
@taller_requerido
def ordenes():
    tid = session["taller_id"]
    if request.method == "POST":
        try:
            oid, total = registrar_orden(
                tid,
                int(request.form["equipo_id"]),
                int(request.form["cliente_id"]),
                int(request.form["cantidad_periodos"]),
                float(request.form["tarifa"]),
                request.form.get("moneda", "USD"),
                request.form.get("periodo", "dia"),
                request.form.get("observaciones", ""),
            )
            flash(f"Orden de Servicio #{oid} creada. Total a cobrar: {total:.2f}", "ok")
            return redirect(url_for("ver_ticket", aid=oid))
        except Exception as e:
            flash(f"Error: {e}", "error")
        return redirect(url_for("ordenes"))
    return render_template("ordenes.html",
                           ordenes=listar_ordenes_activas(tid),
                           equipos=listar_equipos(tid, solo_libres=True),
                           clientes=listar_clientes(tid),
                           taller_nombre=session.get("taller_nombre", ""))


@app.route("/ordenes/<int:oid>/cerrar", methods=["POST"])
@taller_requerido
def cerrar_orden_ruta(oid):
    try:
        cerrar_orden(oid, session["taller_id"])
        flash("Orden de servicio entregada y cerrada.", "ok")
    except Exception as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("ordenes"))


# ==================== TICKET / RECIBO ====================

@app.route("/ticket/<int:oid>")
@taller_requerido
def ver_ticket(oid):
    tid = session["taller_id"]
    datos = obtener_orden(oid, tid)
    if not datos:
        flash("Ticket no encontrado.", "error")
        return redirect(url_for("ordenes"))
    texto = generar_ticket_taller(datos)
    tel = datos.get("telefono") or ""
    wa_link = generar_enlace_whatsapp(tel, texto)
    sms_link = generar_enlace_sms(tel, texto)
    return render_template("ticket.html",
                           texto=texto, aid=oid,
                           wa_link=wa_link, sms_link=sms_link)


# ==================== MENSAJES ====================

@app.route("/mensajes", methods=["GET", "POST"])
@taller_requerido
def mensajes():
    tid = session["taller_id"]
    if request.method == "POST":
        try:
            guardar_plantilla(
                request.form["nombre"].strip(),
                request.form["contenido"].strip(),
            )
            flash("Plantilla guardada.", "ok")
        except Exception as e:
            flash(f"Error: {e}", "error")
        return redirect(url_for("mensajes"))
    return render_template("mensajes.html",
                           plantillas=listar_plantillas(),
                           ordenes=listar_ordenes_activas(tid),
                           taller_nombre=session.get("taller_nombre", ""))


@app.route("/mensajes/<int:pid>/eliminar", methods=["POST"])
@taller_requerido
def borrar_plantilla(pid):
    try:
        eliminar_plantilla(pid)
        flash("Plantilla eliminada.", "ok")
    except Exception as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("mensajes"))


@app.route("/api/mensaje/<int:oid>")
@taller_requerido
def api_mensaje(oid):
    tid = session["taller_id"]
    datos = obtener_orden(oid, tid)
    if not datos:
        return {"ok": False, "error": "Orden no encontrada"}, 404
    plantilla_id = request.args.get("plantilla")
    plantilla = None
    if plantilla_id:
        for p in listar_plantillas():
            if str(p["id"]) == str(plantilla_id):
                plantilla = p["contenido"]
                break
    texto = generar_mensaje_celular(datos, plantilla, session.get("taller_nombre", ""))
    tel = "".join(c for c in (datos.get("telefono") or "") if c.isdigit())
    return {
        "ok": True,
        "texto": texto,
        "telefono": tel,
        "cliente": datos["cliente"],
        "wa_link": f"https://wa.me/{tel}?text={urllib.parse.quote(texto)}" if tel else None,
        "sms_link": generar_enlace_sms(tel, texto) if tel else None,
    }


# ==================== INICIO ====================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)