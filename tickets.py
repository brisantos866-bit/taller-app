# taller_web/tickets.py
import urllib.parse

def generar_ticket_taller(datos):
    simbolo = {"USD": "$", "HNL": "L", "EUR": "€"}.get(datos.get("moneda", "USD"), datos.get("moneda", "$"))
    lineas = [
        "=" * 45,
        f"  ORDEN DE SERVICIO #{datos.get('id', '')}",
        "=" * 45,
        f"Taller: {datos.get('taller_nombre', '')}",
        f"Cliente: {datos.get('cliente', '')}",
        f"Equipo/Vehículo: {datos.get('equipo_numero', '')} ({datos.get('equipo_tipo', '')})",
        "-" * 45,
        f"Diagnóstico/Servicio: {datos.get('observaciones', 'Mantenimiento general')}",
        f"Mano de Obra: {simbolo}{datos.get('tarifa', 0):.2f}",
        f"Cantidad/Horas: {datos.get('cantidad_periodos', '1')}",
        "-" * 45,
        f"TOTAL A PAGAR: {simbolo}{datos.get('total', 0):.2f} {datos.get('moneda', '')}",
        "=" * 45,
        "¡Gracias por su preferencia!",
        "Garantía válida presentando este ticket.",
    ]
    return "\n".join(lineas)


def generar_enlace_whatsapp(telefono, texto):
    tel = "".join(c for c in (telefono or "") if c.isdigit())
    if not tel:
        return None
    return f"https://wa.me/{tel}?text={urllib.parse.quote(texto)}"


def generar_enlace_sms(telefono, texto):
    tel = "".join(c for c in (telefono or "") if c.isdigit())
    if not tel:
        return None
    return f"sms:{tel}?body={urllib.parse.quote(texto)}"


def generar_mensaje_celular(datos, plantilla=None, taller_nombre=""):
    simbolo = {"USD": "$", "HNL": "L", "EUR": "€"}.get(datos.get("moneda", "USD"), datos.get("moneda", "$"))
    if not plantilla:
        plantilla = (
            "Hola {cliente}, te saludamos de {taller_nombre}. "
            "Tu equipo {equipo_numero} ya está listo. "
            "El total del servicio es {simbolo}{total} {moneda}. ¡Te esperamos!"
        )
    return (
        plantilla
        .replace("{cliente}", datos.get("cliente", ""))
        .replace("{taller_nombre}", taller_nombre)
        .replace("{equipo_numero}", str(datos.get("equipo_numero", "")))
        .replace("{equipo_tipo}", str(datos.get("equipo_tipo", "")))
        .replace("{cantidad}", str(datos.get("cantidad_periodos", "")))
        .replace("{periodo_texto}", "servicio")
        .replace("{simbolo}", simbolo)
        .replace("{total}", f"{datos.get('total', 0):.2f}")
        .replace("{moneda}", datos.get("moneda", ""))
    )