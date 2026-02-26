import os
import threading
import json
import requests
import cloudscraper
from bs4 import BeautifulSoup
from flask import Flask, Response, stream_with_context, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# --- CONFIGURACIÓN ---
TOKEN = '8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870'
URL_RENDER = "https://suntv-servertv.onrender.com"

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ SunTV Multi-Source Engine Activo"

@app.route('/video_proxy')
def video_proxy():
    video_url = request.args.get('url')
    if not video_url: return "Error", 400
    def generate():
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        try:
            with requests.get(video_url, stream=True, headers=headers, timeout=25) as r:
                for chunk in r.iter_content(chunk_size=1024*512):
                    yield chunk
        except:
            pass
    return Response(stream_with_context(generate()), content_type='video/mp4')

# --- RECOLECTOR INTELIGENTE ---
async def recolectar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Iniciando escaneo en múltiples fuentes (Cuevana, Biz y Estrenos)...")
    
    # Lista de fuentes alternativas para que no falle
    fuentes = [
        "https://cuevana3cc.site/peliculas-estrenos",
        "https://ww1.cuevana3.ch/peliculas",
        "https://cuevana.biz/peliculas"
    ]
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','mobile': False})
    lista_final_json = []

    for url in fuentes:
        try:
            response = scraper.get(url, timeout=10)
            if response.status_code != 200: continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # Buscamos los contenedores de películas
            items = soup.select('.ml-item') or soup.select('.item') or soup.find_all('li', class_='xxx')
            
            if items:
                for item in items[:12]: # 12 por cada fuente
                    try:
                        link_tag = item.find('a')
                        if not link_tag: continue
                        url_peli = link_tag['href']
                        if not url_peli.startswith('http'): url_peli = "https://cuevana3cc.site" + url_peli
                        
                        titulo = item.find('h2').text.strip() if item.find('h2') else "Pelicula SunTV"
                        img_tag = item.find('img')
                        portada = img_tag.get('src') or img_tag.get('data-src') or ""

                        pelicula_obj = {
                            "titulo": titulo,
                            "urlPortada": portada,
                            "urlVideo": f"{URL_RENDER}/video_proxy?url={url_peli}",
                            "calidad": "1080p",
                            "categoria": "Tendencias"
                        }
                        lista_final_json.append(pelicula_obj)
                    except: continue
                break # Si encontramos películas en una fuente, paramos para no saturar
        except:
            continue

    if not lista_final_json:
        await update.message.reply_text("❌ Todos los servidores espejo están bloqueando a Render. Intentando modo API básica...")
        return

    # Guardar JSON
    with open("lista_suntv.json", "w", encoding="utf-8") as f:
        json.dump(lista_final_json, f, indent=2, ensure_ascii=False)
        
    await update.message.reply_document(document=open("lista_suntv.json", "rb"), 
                                        caption=f"✅ ¡Conseguido! Se generó el JSON con {len(lista_final_json)} películas.")

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("recolectar", recolectar))
    application.run_polling()





