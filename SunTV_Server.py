import os
import yt_dlp
import requests
from flask import Flask, Response, stream_with_context, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# CONFIGURACIÓN
TOKEN = '8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870'
URL_RENDER = "https://suntv-servertv.onrender.com"
app = Flask(__name__)

def obtener_video_alta_calidad(url_cuevana):
    # Configuramos el extractor para buscar específicamente 1080p o superior
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'bestvideo[height>=1080][ext=mp4]+bestaudio[ext=m4a]/best[height>=1080]/best',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url_cuevana, download=False)
            ancho = info.get('width', 0)
            alto = info.get('height', 0)
            url_directa = info.get('url', None)

            # FILTRO: Si la altura es menor a 1080, lo rechazamos
            if alto >= 1080:
                return {
                    "url": url_directa,
                    "resolucion": f"{ancho}x{alto}",
                    "calidad": "Full HD 1080p"
                }
            else:
                return None # Calidad insuficiente
        except:
            return None

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url_usuario = update.message.text
    if "http" in url_usuario:
        await update.message.reply_text("🧐 Analizando calidad del video... buscando 1080p.")
        
        resultado = obtener_video_alta_calidad(url_usuario)
        
        if resultado:
            link_final = f"{URL_RENDER}/video_proxy?url={resultado['url']}"
            mensaje = (
                f"✅ **¡CALIDAD VERIFICADA!**\n"
                f"📺 Resolución: {resultado['resolucion']}\n"
                f"✨ Etiqueta: {resultado['calidad']}\n\n"
                f"Link para nPoint:\n`{link_final}`"
            )
            await update.message.reply_text(mensaje, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Calidad insuficiente. Este link no llega a 1080p y fue descartado para SunTV.")

# PROXY DE VIDEO (Para que fluya sin cortes en la TV)
@app.route('/video_proxy')
def video_proxy():
    video_url = request.args.get('url')
    def generate():
        # Aumentamos el tamaño del chunk para videos pesados de 1080p
        with requests.get(video_url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024*1024): # 1MB por chunk
                yield chunk
    return Response(stream_with_context(generate()), content_type='video/mp4')

# ... (El resto del código de ejecución igual que antes)





