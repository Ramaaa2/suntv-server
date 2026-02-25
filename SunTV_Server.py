import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from flask import Flask, send_file
import threading

# 1. CONFIGURACIÓN
TOKEN = '8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870'
# Este bot crea un "túnel" para que el video se vea en la app
app = Flask(__name__)

@app.route('/')
def home():
    return "Servidor SunTV Activo"

# 2. LÓGICA DEL BOT
async def generar_enlace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        # El bot te responde con el link que pondrás en nPoint
        # Nota: 'tu_ip' sería la dirección de tu PC o servidor
        link_directo = f"http://TU_IP_PÚBLICA:5000/video/{file_id}"
        await update.message.reply_text(f"🎥 Link para SunTV:\n\n{link_directo}")

# Ejecutar Flask y el Bot al mismo tiempo
def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.VIDEO, generar_enlace))
    application.run_polling()