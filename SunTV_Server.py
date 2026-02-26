import os
import threading
import requests
from flask import Flask, Response, stream_with_context
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# CONFIGURACIÓN
TOKEN = '8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870'
app = Flask(__name__)

# Página de inicio para evitar el 404
@app.route('/')
def home():
    return "✅ Servidor de SunTV funcionando correctamente"

# EL BOT: Genera el link para tu app
async def generar_enlace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        url_render = "https://suntv-servertv.onrender.com" 
        link_directo = f"{url_render}/video/{file_id}"
        await update.message.reply_text(f"✅ Link para nPoint:\n\n{link_directo}")

# EL PUENTE: Envía el video de Telegram a la TV
@app.route('/video/<file_id>')
def stream_video(file_id):
    try:
        url_telegram = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
        datos = requests.get(url_telegram).json()
        ruta_archivo = datos['result']['file_path']
        video_url = f"https://api.telegram.org/file/bot{TOKEN}/{ruta_archivo}"
        
        def generate():
            with requests.get(video_url, stream=True) as r:
                for chunk in r.iter_content(chunk_size=1024*512):
                    yield chunk
        return Response(stream_with_context(generate()), content_type='video/mp4')
    except Exception as e:
        return f"Error: {str(e)}", 500

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.VIDEO, generar_enlace))
    application.run_polling()



