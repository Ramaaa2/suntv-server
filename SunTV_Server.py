import os
import threading
import yt_dlp
from flask import Flask, Response, stream_with_context
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# CONFIGURACIÓN
TOKEN = '8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870'
URL_RENDER = "https://suntv-servertv.onrender.com"
app = Flask(__name__)

# FUNCIÓN PRO: Extrae el link directo saltando anuncios
def extraer_link_pro(url_web):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url_web, download=False)
            # Retorna el link directo del servidor de video (fembed, gounlimited, etc)
            return info.get('url', None)
        except Exception:
            return None

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url_usuario = update.message.text
    
    if "http" in url_usuario:
        await update.message.reply_text("🕵️‍♂️ Analizando link y saltando protecciones...")
        
        link_directo = extraer_link_pro(url_usuario)
        
        if link_directo:
            # Creamos el link disfrazado para la app
            link_final = f"{URL_RENDER}/video_proxy?url={link_directo}"
            await update.message.reply_text(f"✅ ¡Éxito! Video extraído.\n\nLink para nPoint:\n`{link_final}`")
        else:
            await update.message.reply_text("❌ No pude extraer el video. El sitio tiene una protección muy fuerte.")

# PROXY DE VIDEO: Hace que el video fluya a la TV sin bloqueos
@app.route('/video_proxy')
def video_proxy():
    video_url = request.args.get('url')
    def generate():
        with requests.get(video_url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024*1024): # Chunks de 1MB
                yield chunk
    return Response(stream_with_context(generate()), content_type='video/mp4')

# ... (El resto del código de Flask y Run que ya tienes)




