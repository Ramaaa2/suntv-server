import telebot
import requests
import json
from flask import Flask
from threading import Thread

# --- CONFIGURACIÓN ---
TOKEN = "8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870"
NPOINT_ID = "cac981efb6d82a87ccb4"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- PARTE PARA QUE RENDER NO SE APAGUE ---
@app.route('/')
def home():
    return "SunTV Bot está vivo y funcionando"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- LÓGICA DEL BOT ---
def limpiar_titulo(texto):
    limpio = texto.replace(".mp4", "").replace(".mkv", "").replace(".", " ").replace("_", " ")
    for palabra in ["720p", "1080p", "Dual", "Latino", "cinecalidad", "h264", "x264", "unrated", "bluray"]:
        limpio = limpio.replace(palabra, "").replace(palabra.upper(), "").replace(palabra.capitalize(), "")
    return limpio.strip().capitalize()

def obtener_catalogo():
    try:
        res = requests.get(f"https://api.npoint.io/{NPOINT_ID}")
        data = res.json()
        return data if isinstance(data, list) else []
    except:
        return []

@bot.message_handler(commands=['actualizar'])
def actualizar_peliculas(message):
    bot.reply_to(message, "🔍 Buscando 30 películas nuevas en Latino... Esto puede tardar unos segundos.")
    
    lista_actual = obtener_catalogo()
    titulos_viejos = [p['titulo'].lower() for p in lista_actual]

    # Query para Archive.org filtrando por "latino" y "mp4"
    query = 'subject:"peliculas latino" AND format:MPEG4'
    url_search = f"https://archive.org/advancedsearch.php?q={query}&fl[]=identifier,title&rows=100&page=1&output=json"
    
    try:
        data = requests.get(url_search).json()
        items = data['response']['docs']
    except Exception as e:
        bot.reply_to(message, f"❌ Error al buscar: {str(e)}")
        return

    agregadas = 0
    for item in items:
        if agregadas >= 30: break
        
        titulo_raw = item['title']
        identificador = item['identifier']
        titulo_limpio = limpiar_titulo(titulo_raw)

        # Filtro de repetición
        if titulo_limpio.lower() not in titulos_viejos:
            url_video = f"https://archive.org/download/{identificador}/{identificador}.mp4"
            # Portada placeholder (Luego agregamos TMDB)
            portada = f"https://via.placeholder.com/500x750.png?text={identificador[:10]}"
            
            lista_actual.append({
                "titulo": titulo_limpio,
                "urlPortada": portada,
                "urlVideo": url_video,
                "calidad": "HD",
                "categoria": "Peliculas"
            })
            titulos_viejos.append(titulo_limpio.lower())
            agregadas += 1

    if agregadas > 0:
        requests.post(f"https://api.npoint.io/{NPOINT_ID}", json=lista_actual)
        bot.reply_to(message, f"✅ ¡Éxito! Se sumaron {agregadas} películas.\nTotal en el catálogo: {len(lista_actual)}")
    else:
        bot.reply_to(message, "⚠️ No se encontraron novedades en Latino que no estuvieran ya en la lista.")

# --- INICIO DEL SERVIDOR Y EL BOT ---
if __name__ == "__main__":
    # Iniciamos Flask en un hilo separado
    Thread(target=run_flask).start()
    # Iniciamos el Bot de Telegram
    print("Bot SunTV iniciado...")
    bot.infinity_polling()









