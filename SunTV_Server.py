import os
import threading
import json
import requests
from flask import Flask, Response, stream_with_context, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# --- CONFIGURACIÓN ---
TOKEN = '8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870'
URL_RENDER = "https://suntv-servertv.onrender.com"
# Esta es una clave de prueba para buscar películas, no necesitas crear cuenta
API_KEY_TMDB = "f09d3949989a5e5812e964098939c381" 

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ SunTV API Engine Activo"

@app.route('/video_proxy')
def video_proxy():
    # Este proxy intentará "enganchar" el video de servidores públicos
    video_url = request.args.get('url')
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://vidsrc.to/'}
    try:
        def generate():
            with requests.get(video_url, stream=True, headers=headers, timeout=20) as r:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    yield chunk
        return Response(stream_with_context(generate()), content_type='video/mp4')
    except:
        return "Error", 500

# --- RECOLECTOR PROFESIONAL (VÍA API) ---
async def recolectar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Generando catálogo SunTV vía API (Sin bloqueos)...")
    
    try:
        # Buscamos las películas más populares en Español Latino
        url_tmdb = f"https://api.themoviedb.org/3/movie/popular?api_key={API_KEY_TMDB}&language=es-MX&page=1"
        data = requests.get(url_tmdb).json()
        
        lista_final_json = []

        for peli in data['results'][:20]: # Traemos las 20 mejores
            titulo = peli['title']
            id_tmdb = peli['id']
            portada = f"https://image.tmdb.org/t/p/w500{peli['poster_path']}"
            
            # Generamos un link "Universal" que busca el video automáticamente
            # Usamos un servidor de video que no bloquea a Render (Vidsrc/Embed)
            video_api_url = f"https://vidsrc.to/embed/movie/{id_tmdb}"
            
            pelicula_obj = {
                "titulo": titulo,
                "urlPortada": portada,
                "urlVideo": f"{URL_RENDER}/video_proxy?url={video_api_url}",
                "calidad": "1080p",
                "categoria": "Tendencias"
            }
            lista_final_json.append(pelicula_obj)

        # Guardar JSON
        with open("lista_suntv.json", "w", encoding="utf-8") as f:
            json.dump(lista_final_json, f, indent=2, ensure_ascii=False)
            
        await update.message.reply_document(
            document=open("lista_suntv.json", "rb"), 
            caption=f"✅ ¡Catálogo generado!\nEncontré {len(lista_final_json)} películas en HD listas para nPoint."
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error en API: {str(e)}")

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("recolectar", recolectar))
    application.run_polling()




