import os
import threading
import requests
from flask import Flask, Response, request, stream_with_context
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# CONFIGURACIÓN
TOKEN = '8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870'
app = Flask(__name__)

# 1. EL BOT: Genera el link para tu app
async def generar_enlace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        # Reemplaza esto con la URL exacta que te dé Render (ej: https://suntv-bot.onrender.com)
        url_render = "https://suntv-server.onrender.com" 
        link_directo = f"{url_render}/video/{file_id}"
        await update.message.reply_text(f"✅ Link Directo para SunTV:\n\n{link_directo}")

# 2. EL PUENTE (STREAMING BRIDGE)
@app.route('/video/<file_id>')
def stream_video(file_id):
    # Buscamos la ruta del archivo en Telegram
    url_telegram = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    datos = requests.get(url_telegram).json()
    
    if 'result' not in datos:
        return "Error: No se pudo obtener el archivo de Telegram", 404
        
    ruta_archivo = datos['result']['file_path']
    video_url = f"https://api.telegram.org/file/bot{TOKEN}/{ruta_archivo}"
    
    # Soporte para "Streaming" fluido (permite adelantar y retroceder)
    def generate():
        with requests.get(video_url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024*512): # Chunks de 512KB para mejor velocidad
                yield chunk

    return Response(stream_with_context(generate()), content_type='video/mp4')

# 3. EJECUCIÓN
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Iniciamos el servidor Web en un hilo separado
    threading.Thread(target=run_flask).start()
    
    # Iniciamos el Bot de Telegram
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.VIDEO, generar_enlace))
    application.run_polling()
