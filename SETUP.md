# Guia de Configuracion - Bot de Gastos WhatsApp

## Que necesitas antes de empezar
- Python 3.10 o superior instalado
- Una cuenta de Google (para Google Sheets)
- Una cuenta de Twilio (gratuita)
- ngrok instalado (para exponer el bot a internet)

---

## PASO 1 — Instalar dependencias

Abre una terminal en la carpeta `gastos_bot` y ejecuta:

```bash
pip install -r requirements.txt
```

---

## PASO 2 — Configurar Google Sheets

### 2a. Crear el Spreadsheet
1. Ve a https://sheets.new y crea una hoja nueva
2. Ponle nombre: **Mis Gastos**
3. Copia el ID de la URL: `docs.google.com/spreadsheets/d/**ESTE_ES_EL_ID**/edit`

### 2b. Crear credenciales de Google
1. Ve a https://console.cloud.google.com
2. Crea un proyecto nuevo (ej: "bot-gastos")
3. Busca y habilita la **Google Sheets API** y la **Google Drive API**
4. Ve a **Credenciales > Crear credenciales > Cuenta de servicio**
5. Ponle nombre (ej: "bot-sheets") y crea
6. Haz clic en la cuenta creada > pestaña **Claves** > Agregar clave > JSON
7. Se descarga un archivo JSON — renambralo `credentials.json` y ponlo en la carpeta `gastos_bot`
8. Copia el email de la cuenta de servicio (termina en `@...gserviceaccount.com`)
9. En tu Spreadsheet, haz clic en **Compartir** y pega ese email con permisos de **Editor**

---

## PASO 3 — Configurar Twilio

1. Crea cuenta gratuita en https://www.twilio.com
2. Ve a **Messaging > Try it out > Send a WhatsApp message**
3. Sigue las instrucciones para conectar tu celular al sandbox de WhatsApp
   (basicamente envias un mensaje con un codigo al numero de Twilio)
4. Anota el **Account SID** y el **Auth Token** del dashboard

---

## PASO 4 — Crear el archivo .env

```bash
cp .env.example .env
```

Edita `.env` con tus datos reales.

---

## PASO 5 — Exponer el bot con ngrok

Twilio necesita una URL publica para enviarte los mensajes.

### Instalar ngrok
Descargalo de https://ngrok.com/download o con:
```bash
winget install ngrok
```

### Iniciar ngrok
En una terminal separada:
```bash
ngrok http 5000
```

Vas a ver algo como:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:5000
```

Copia esa URL (la que empieza con `https://`).

---

## PASO 6 — Configurar webhook en Twilio

1. Ve al dashboard de Twilio > **WhatsApp Sandbox Settings**
2. En el campo **"When a message comes in"** pega:
   ```
   https://abc123.ngrok-free.app/webhook
   ```
3. Metodo: **HTTP POST**
4. Guarda los cambios

---

## PASO 7 — Iniciar el bot

```bash
python bot.py
```

Listo! Manda un mensaje de WhatsApp al numero de Twilio.

---

## Como usar el bot

| Accion | Que escribir |
|--------|-------------|
| Registrar gasto | Escribe el monto (ej: `150`) |
| Ver gastos del mes | `resumen` |
| Ver gastos de hoy | `hoy` |
| Cancelar registro | `cancelar` |
| Ver ayuda | `ayuda` |

### Ejemplo de conversacion:
```
Tu:  150
Bot: Monto: $150.00
     Categorias: 1.Comida 2.Transporte ...
Tu:  1
Bot: Categoria: Comida
     Escribi una descripcion o "no" para omitir
Tu:  almuerzo en el centro
Bot: Metodo de pago: 1.Efectivo ...
Tu:  1
Bot: Gasto registrado! ✓
```

---

## Notas importantes

- **ngrok gratis** genera una URL diferente cada vez que lo reinicias — tenes que actualizar el webhook en Twilio.
- Si quieres una URL fija, puedes usar una cuenta paga de ngrok o deployar el bot en Railway/Render (gratis).
- El sandbox de Twilio solo funciona con numeros que escaneen el QR. Para produccion necesitas un numero de Twilio real.
