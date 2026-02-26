import telebot
import requests
import json
import io
from flask import Flask
from threading import Thread

# --- CONFIGURACIÓN ---
TOKEN = "8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870"
NPOINT_ID = "35fca43f0d7e65606300"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home(): return "Bot SunTV Activo"

def run_flask(): app.run(host='0.0.0.0', port=10000)

def limpiar_titulo(texto):
    limpio = texto.replace(".mp4", "").replace(".mkv", "").replace(".", " ").replace("_", " ")
    for p in ["720p", "1080p", "Dual", "Latino", "cinecalidad", "h264", "x264", "bluray", "unrated"]:
        limpio = limpio.replace(p, "").replace(p.upper(), "").replace(p.capitalize(), "")
    return limpio.strip().capitalize()

@bot.message_handler(commands=['actualizar'])
def actualizar_peliculas(message):
    bot.reply_to(message, "🚀 Iniciando búsqueda masiva en Latino... Dame un momento.")
    
    # Intentamos bajar lo que ya hay para no repetir
    try:
        lista_actual = requests.get(f"https://api.npoint.io/{NPOINT_ID}").json()
        if not isinstance(lista_actual, list): lista_actual = []
    except:
        lista_actual = []
    
    titulos_viejos = [p['titulo'].lower() for p in lista_actual]
    
    # Aumentamos el rango de búsqueda (pedimos 300 resultados para filtrar los mejores 50)
    query = 'subject:"peliculas latino" AND format:MPEG4'
    url_search = f"https://archive.org/advancedsearch.php?q={query}&fl[]=identifier,title&rows=300&page=1&output=json"
    
    try:
        data = requests.get(url_search).json()
        items = data['response']['docs']
    except:
        bot.reply_to(message, "❌ Error de conexión con el servidor de películas.")
        return

    nuevas_encontradas = []
    for item in items:
        if len(nuevas_encontradas) >= 50: break # BUSCAMOS 50 ESTA VEZ
        
        titulo_raw = item['title']
        identificador = item['identifier']
        titulo_limpio = limpiar_titulo(titulo_raw)

        if titulo_limpio.lower() not in titulos_viejos:
            nueva_peli = {
                "titulo": titulo_limpio,
                "urlPortada": "https://via.placeholder.com/500x750.png?text=SunTV+Movie",
                "urlVideo": f"https://archive.org/download/{identificador}/{identificador}.mp4",
                "calidad": "HD",
                "categoria": "Peliculas"
            }
            nuevas_encontradas.append(nueva_peli)
            lista_actual.append(nueva_peli)
            titulos_viejos.append(titulo_limpio.lower())

    if nuevas_encontradas:
        # 1. Actualizamos nPoint
        requests.post(f"https://api.npoint.io/{NPOINT_ID}", json=lista_actual)
        
        # 2. Creamos un archivo JSON para enviarte al chat
        json_string = json.dumps(lista_actual, indent=4, ensure_ascii=False)
        json_file = io.BytesIO(json_string.encode())
        json_file.name = "suntv_catalogo.json"
        
        bot.send_document(message.chat.id, json_file, caption=f"✅ ¡Éxito! Encontré {len(nuevas_encontradas)} pelis nuevas.\nTotal: {len(lista_actual)} ítems.")
    else:
        bot.reply_to(message, "⚠️ No encontré películas nuevas en Latino que no estuvieran ya en tu lista.")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()











