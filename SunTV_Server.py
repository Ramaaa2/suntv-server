import os
import threading
import json
import requests
import cloudscraper
import yt_dlp
from bs4 import BeautifulSoup
from flask import Flask, Response, stream_with_context, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# --- CONFIGURACIÓN ---
TOKEN = '8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870'
URL_RENDER = "https://suntv-servertv.onrender.com"

app = Flask(__name__)

# --- LÓGICA DEL SERVIDOR (PROXY) ---
@app.route('/')
def home():
    return "✅ Servidor SunTV Recolector Pro Activo"

@app.route('/video_proxy')
def video_proxy():
    video_url = request.args.get('url')
    if not video_url:
        return "Error: No URL", 400
    
    def generate():
        # Chunks de 1MB para estabilidad en 1080p
        with requests.get(video_url, stream=True, timeout=15) as r:
            for chunk in r.iter_content(chunk_size=1024*1024):
                yield chunk
    
    return Response(stream_with_context(generate()), content_type='video/mp4')

# --- LÓGICA DEL BOT (RECOLECTOR PRO) ---
async def recolectar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🕵️‍♂️ Iniciando barrido en Cuevana... Saltando protecciones y filtrando calidad.")
    
    url_base = "https://cuevana3cc.site/"
    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get(url_base)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Selectores ajustados para capturar películas de la portada
        items = soup.select('div.item') or soup.select('.ml-item') or soup.select('li.xxx')
        
        lista_final_json = []

        # Analizamos las primeras 10 para evitar que Render nos corte por tiempo
        for item in items[:10]:
            try:
                link_tag = item.find('a')
                if not link_tag: continue
                
                link_peli = link_tag['href']
                if not link_peli.startswith('http'):
                    link_peli = url_base + link_peli
                
                titulo = item.find('h2').text.strip() if item.find('h2') else "Película"
                img_tag = item.find('img')
                # Intentamos obtener la imagen de src o data-src (común en webs con lazy load)
                portada = img_tag.get('src') or img_tag.get('data-src') if img_tag else ""
                
                # yt-dlp extrae el link real del reproductor oculto
                ydl_opts = {'quiet': True, 'no_warnings': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link_peli, download=False)
                    alto = info.get('height', 0)
                    video_url = info.get('url')

                    # FILTRO DE CALIDAD: Aceptamos 720p o superior
                    if video_url and alto >= 720:
                        pelicula_obj = {
                            "titulo": titulo,
                            "urlPortada": portada,
                            "urlVideo": f"{URL_RENDER}/video_proxy?url={video_url}",
                            "calidad": f"{alto}p",
                            "categoria": "Novedades"
                        }
                        lista_final_json.append(pelicula_obj)
            except Exception:
                continue

        if not lista_final_json:
            await update.message.reply_text("⚠️ No se encontraron videos compatibles en 1080p/720p en este momento.")
            return

        # Guardar en archivo JSON
        nombre_archivo = "lista_suntv.json"
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            json.dump(lista_final_json, f, indent=2, ensure_ascii=False)
            
        await update.message.reply_document(
            document=open(nombre_archivo, "rb"), 
            caption=f"✅ ¡Barrido terminado!\nEncontré {len(lista_final_json)} películas en alta calidad."
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error crítico: {str(e)}")

# --- INICIO ---
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("recolectar", recolectar))
    
    print("Servidor SunTV en marcha...")
    application.run_polling()





