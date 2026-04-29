"""
Manejo de Google Sheets para almacenar gastos
"""
import os
import json
import tempfile
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = ["Fecha", "Hora", "Monto", "Categoria", "Descripcion", "Metodo de Pago"]


class SheetsManager:
    def __init__(self):
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if not spreadsheet_id:
            raise ValueError("SPREADSHEET_ID no encontrado en .env")

        # Soporta credenciales como JSON string (Railway) o archivo local
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
            creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)

        client = gspread.authorize(creds)
        self.sheet = client.open_by_key(spreadsheet_id).sheet1
        self._ensure_headers()

    def _ensure_headers(self):
        """Crea los encabezados si no existen."""
        first_row = self.sheet.row_values(1)
        if first_row != HEADERS:
            self.sheet.insert_row(HEADERS, 1)
            # Formato en negrita para los encabezados
            self.sheet.format("A1:F1", {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.13, "green": 0.59, "blue": 0.95},
            })

    def add_expense(self, date, time, amount, category, description, payment):
        """Agrega una fila nueva con el gasto."""
        self.sheet.append_row([date, time, amount, category, description, payment])

    def get_monthly_summary(self):
        """Devuelve un dict {categoria: total} del mes actual."""
        month = datetime.now().strftime("%m/%Y")
        records = self.sheet.get_all_records()
        summary = {}
        for row in records:
            fecha = str(row.get("Fecha", ""))
            if fecha.endswith(month):
                cat = row.get("Categoria", "Otros")
                try:
                    summary[cat] = summary.get(cat, 0) + float(row.get("Monto", 0))
                except (ValueError, TypeError):
                    pass
        return dict(sorted(summary.items(), key=lambda x: x[1], reverse=True))

    def get_today_expenses(self):
        """Devuelve lista de gastos del dia de hoy."""
        today = datetime.now().strftime("%d/%m/%Y")
        records = self.sheet.get_all_records()
        return [r for r in records if str(r.get("Fecha", "")) == today]

    def delete_last_expense(self):
        """Elimina el ultimo gasto registrado. Devuelve los datos borrados o None."""
        all_values = self.sheet.get_all_values()
        if len(all_values) <= 1:
            return None
        last_row = all_values[-1]
        self.sheet.delete_rows(len(all_values))
        return last_row  # [Fecha, Hora, Monto, Categoria, Descripcion, Metodo de Pago]
