"""
Bot de WhatsApp para registro de gastos personales
Usa Twilio Sandbox + Google Sheets
"""
import os
import logging
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from sheets import SheetsManager
from datetime import datetime

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
sheets = SheetsManager()

# Estado de conversacion por usuario (en memoria)
# formato: { "whatsapp:+549...": { "state": "AMOUNT", "data": {...} } }
sessions = {}

CATEGORIES = [
    "Comida", "Transporte", "Entretenimiento",
    "Ropa", "Salud", "Educacion", "Tecnologia",
    "Suscripciones", "Otros"
]

PAYMENTS = ["Efectivo", "Debito", "Credito", "Transferencia"]

STATES = {
    "IDLE": "idle",
    "AMOUNT": "amount",
    "CATEGORY": "category",
    "DESCRIPTION": "description",
    "PAYMENT": "payment",
}

HELP_MSG = (
    "*Bot de Gastos*\n\n"
    "Escribe el monto para empezar (ej: *150* o *1500.50*)\n\n"
    "Comandos:\n"
    "• *resumen* - Ver gastos del mes\n"
    "• *hoy* - Ver gastos de hoy\n"
    "• *cancelar* - Cancelar registro\n"
    "• *borrar* - Eliminar el ultimo gasto guardado\n"
    "• *ayuda* - Ver este mensaje"
)


def get_session(phone):
    if phone not in sessions:
        sessions[phone] = {"state": STATES["IDLE"], "data": {}}
    return sessions[phone]


def reset_session(phone):
    sessions[phone] = {"state": STATES["IDLE"], "data": {}}


def build_category_menu():
    lines = ["*Categorias disponibles:*\n"]
    for i, cat in enumerate(CATEGORIES, 1):
        lines.append(f"{i}. {cat}")
    lines.append("\nResponde con el *numero* de la categoria.")
    return "\n".join(lines)


def build_payment_menu():
    lines = ["*Metodo de pago:*\n"]
    for i, pay in enumerate(PAYMENTS, 1):
        lines.append(f"{i}. {pay}")
    lines.append("\nResponde con el *numero*.")
    return "\n".join(lines)


def process_message(phone, body):
    """Procesa el mensaje entrante y devuelve la respuesta."""
    session = get_session(phone)
    state = session["state"]
    text = body.strip()

    # Comandos globales (funcionan en cualquier estado)
    if text.lower() == "cancelar":
        reset_session(phone)
        return "Registro cancelado."

    if text.lower() == "ayuda":
        return HELP_MSG

    if text.lower() == "resumen":
        return handle_resumen()

    if text.lower() == "hoy":
        return handle_hoy()

    if text.lower() == "borrar":
        return handle_borrar()

    # --- Estado: IDLE ---
    if state == STATES["IDLE"]:
        # Si escribe un numero, lo tomamos como monto
        return handle_amount(phone, text, session)

    # --- Estado: AMOUNT ---
    if state == STATES["AMOUNT"]:
        return handle_amount(phone, text, session)

    # --- Estado: CATEGORY ---
    if state == STATES["CATEGORY"]:
        try:
            idx = int(text) - 1
            if idx < 0 or idx >= len(CATEGORIES):
                raise ValueError
            session["data"]["category"] = CATEGORIES[idx]
            session["state"] = STATES["DESCRIPTION"]
            return (
                f"Categoria: *{CATEGORIES[idx]}*\n\n"
                "Escribe una descripcion (ej: 'almuerzo en el centro')\n"
                "O escribe *no* para omitir."
            )
        except (ValueError, IndexError):
            return f"Opcion invalida. Elige un numero del 1 al {len(CATEGORIES)}:\n\n{build_category_menu()}"

    # --- Estado: DESCRIPTION ---
    if state == STATES["DESCRIPTION"]:
        session["data"]["description"] = "" if text.lower() == "no" else text
        session["state"] = STATES["PAYMENT"]
        return build_payment_menu()

    # --- Estado: PAYMENT ---
    if state == STATES["PAYMENT"]:
        try:
            idx = int(text) - 1
            if idx < 0 or idx >= len(PAYMENTS):
                raise ValueError
            session["data"]["payment"] = PAYMENTS[idx]
            return save_expense(phone, session)
        except (ValueError, IndexError):
            return f"Opcion invalida. Elige un numero del 1 al {len(PAYMENTS)}:\n\n{build_payment_menu()}"

    return HELP_MSG


def handle_amount(phone, text, session):
    """Intenta parsear el texto como monto."""
    cleaned = text.replace(",", ".").replace("$", "").strip()
    try:
        amount = float(cleaned)
        if amount <= 0:
            raise ValueError
    except ValueError:
        if session["state"] == STATES["IDLE"]:
            return HELP_MSG
        return "Monto invalido. Escribe un numero (ej: *150* o *1500.50*):"

    now = datetime.now()
    session["data"] = {
        "amount": amount,
        "date": now.strftime("%d/%m/%Y"),
        "time": now.strftime("%H:%M"),
    }
    session["state"] = STATES["CATEGORY"]
    return (
        f"Monto: *${amount:,.2f}*\n\n"
        + build_category_menu()
    )


def save_expense(phone, session):
    """Guarda el gasto en Google Sheets y resetea la sesion."""
    data = session["data"]
    try:
        sheets.add_expense(
            date=data["date"],
            time=data["time"],
            amount=data["amount"],
            category=data["category"],
            description=data.get("description", ""),
            payment=data["payment"],
        )
        response = (
            "*Gasto registrado!*\n\n"
            f"Fecha: {data['date']} {data['time']}\n"
            f"Monto: *${data['amount']:,.2f}*\n"
            f"Categoria: {data['category']}\n"
            f"Descripcion: {data.get('description') or '-'}\n"
            f"Pago: {data['payment']}\n\n"
            "Escribe otro monto para registrar otro gasto."
        )
    except Exception as e:
        logging.error(f"Error guardando gasto: {e}")
        response = "Error al guardar el gasto. Intenta de nuevo."

    reset_session(phone)
    return response


def handle_resumen():
    try:
        summary = sheets.get_monthly_summary()
        if not summary:
            return "No hay gastos registrados este mes."

        month_name = datetime.now().strftime("%B %Y")
        lines = [f"*Resumen de {month_name}*\n"]
        total = 0
        for cat, amount in summary.items():
            lines.append(f"• {cat}: *${amount:,.2f}*")
            total += amount
        lines.append(f"\n*Total: ${total:,.2f}*")
        return "\n".join(lines)
    except Exception as e:
        logging.error(f"Error en resumen: {e}")
        return "Error al obtener el resumen."


def handle_borrar():
    try:
        deleted = sheets.delete_last_expense()
        if not deleted:
            return "No hay gastos para borrar."
        return (
            "Ultimo gasto eliminado:\n"
            f"Fecha: {deleted[0]} {deleted[1]}\n"
            f"Monto: *${float(deleted[2]):,.2f}*\n"
            f"Categoria: {deleted[3]}\n"
            f"Descripcion: {deleted[4] or '-'}\n"
            f"Pago: {deleted[5]}"
        )
    except Exception as e:
        logging.error(f"Error borrando gasto: {e}")
        return "Error al borrar el gasto."


def handle_hoy():
    try:
        gastos = sheets.get_today_expenses()
        if not gastos:
            return "No hay gastos registrados hoy."

        today = datetime.now().strftime("%d/%m/%Y")
        lines = [f"*Gastos de hoy ({today})*\n"]
        total = 0
        for g in gastos:
            desc = f" ({g['Descripcion']})" if g.get("Descripcion") else ""
            lines.append(f"• {g['Categoria']}{desc}: *${float(g['Monto']):,.2f}*")
            total += float(g["Monto"])
        lines.append(f"\n*Total: ${total:,.2f}*")
        return "\n".join(lines)
    except Exception as e:
        logging.error(f"Error en hoy: {e}")
        return "Error al obtener los gastos de hoy."


@app.route("/webhook", methods=["POST"])
def webhook():
    phone = request.form.get("From", "")
    body = request.form.get("Body", "").strip()

    logging.info(f"Mensaje de {phone}: {body}")

    reply = process_message(phone, body)

    logging.info(f"Respuesta -> {reply[:80]}")

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)


@app.route("/", methods=["GET"])
def index():
    return "Bot de gastos activo.", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)
