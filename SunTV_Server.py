import os
import threading
import json
import requests
from bs4 import BeautifulSoup
import yt_dlp
from flask import Flask, Response, stream_with_context, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- CONFIGURACIÓN ---
TOKEN = '8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870'
URL_RENDER = "https://suntv-servertv.onrender.com"

app = Flask(__name__)

# --- LÓGICA DEL SERVIDOR (PROXY) ---
@app.route('/')
def home():
    return "✅ Servidor SunTV Recolector Activo"

@app.route('/video_proxy')
def video_proxy():
    video_url = request.args.get('url')
    if not video_url:
        return "Error: No se proporcionó URL", 400
    
    def generate():
        # Los videos 1080p son pesados, usamos chunks de 1MB
        with requests.get(video_url, stream=True, timeout=10) as r:
            for chunk in r.iter_content(chunk_size=1024*1024):
                yield chunk
    
    return Response(stream_with_context(generate()), content_type='video/mp4')

# --- LÓGICA DEL BOT (RECOLECTOR) ---
async def recolectar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🕵️‍♂️ Iniciando barrido en Cuevana... Buscando solo 1080p de alta calidad.")
    
    url_base = "https://cuevana3cc.site/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url_base, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscamos las películas en el listado principal (ajustado a la estructura común de Cuevana)
        items = soup.select('ul.movies li') or soup.find_all('li', class_='xxx')
        
        lista_final_json = []

        # Analizamos las últimas 15 para no saturar el servidor gratuito
        for item in items[:15]:
            try:
                link_tag = item.find('a')
                if not link_tag: continue
                
                link_peli = link_tag['href']
                titulo = item.find('h2').text.strip() if item.find('h2') else "Sin Título"
                portada = item.find('img')['src'] if item.find('img') else ""
                
                # El bot inspecciona la calidad sin descargar
                ydl_opts = {'quiet': True, 'no_warnings': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link_peli, download=False)
                    
                    # FILTRO: Solo si es 1080p o más
                    if info.get('height', 0) >= 1080:
                        video_url = info.get('url')
                        
                        pelicula_obj = {
                            "titulo": titulo,
                            "urlPortada": portada,
                            "urlVideo": f"{URL_RENDER}/video_proxy?url={video_url}",
                            "calidad": "1080p",
                            "categoria": "Novedades"
                        }
                        lista_final_json.append(pelicula_obj)
            except Exception:
                continue

        if not lista_final_json:
            await update.message.reply_text("⚠️ No se encontraron películas 1080p en esta página en este momento.")
            return

        # Generamos el archivo JSON
        nombre_archivo = "lista_suntv.json"
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            json.dump(lista_final_json, f, indent=2, ensure_ascii=False)
            
        await update.message.reply_document(
            document=open(nombre_archivo, "rb"), 
            caption=f"✅ ¡Barrido completo! Se encontraron {len(lista_final_json)} pelis en 1080p."
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error en el barrido: {str(e)}")

# --- EJECUCIÓN ---
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Hilo para Flask
    threading.Thread(target=run_flask).start()
    
    # Configuración del Bot
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Comando /recolectar
    application.add_handler(CommandHandler("recolectar", recolectar))
    
    print("Bot SunTV iniciado...")
    application.run_polling()





