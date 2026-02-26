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
    return "✅ Servidor SunTV Recolector Activo"

@app.route('/video_proxy')
def video_proxy():
    video_url = request.args.get('url')
    if not video_url: return "Error", 400
    def generate():
        with requests.get(video_url, stream=True, timeout=15) as r:
            for chunk in r.iter_content(chunk_size=1024*512):
                yield chunk
    return Response(stream_with_context(generate()), content_type='video/mp4')

# --- LÓGICA DE RECOLECCIÓN ---
async def recolectar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Iniciando recolección profunda... esto puede tardar un poco.")
    
    # URL de la sección de Estrenos/Tendencias
    url_base = "https://cuevana3cc.site/peliculas"
    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get(url_base)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Intentamos capturar los elementos de la lista
        items = soup.select('.ml-item') or soup.select('.item') or soup.find_all('li')
        
        lista_final_json = []

        for item in items[:12]: # Analizamos 12 pelis
            try:
                link_tag = item.find('a')
                if not link_tag: continue
                
                url_peli = link_tag['href']
                titulo = item.find('h2').text.strip() if item.find('h2') else "Película"
                img_tag = item.find('img')
                portada = img_tag.get('src') or img_tag.get('data-src') or ""

                # IMPORTANTE: Para que no de error, el bot genera un link "espejo"
                # que se activará cuando le des play en la TV
                pelicula_obj = {
                    "titulo": titulo,
                    "urlPortada": portada,
                    "urlVideo": f"{URL_RENDER}/video_proxy?url={url_peli}", # Enlace dinámico
                    "calidad": "1080p",
                    "categoria": "Recién Agregadas"
                }
                lista_final_json.append(pelicula_obj)
            except:
                continue

        if not lista_final_json:
            await update.message.reply_text("❌ No se pudieron extraer los datos. La estructura de la web cambió.")
            return

        with open("lista_suntv.json", "w", encoding="utf-8") as f:
            json.dump(lista_final_json, f, indent=2, ensure_ascii=False)
            
        await update.message.reply_document(document=open("lista_suntv.json", "rb"), caption="✅ ¡Hecho! JSON generado con éxito.")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("recolectar", recolectar))
    application.run_polling()





