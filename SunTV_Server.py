import telebot
import requests
import json
import io
from flask import Flask
from threading import Thread

# --- CONFIGURACIÓN ---
TOKEN = "TU_TOKEN_DE_TELEGRAM_AQUI"
NPOINT_ID = "f3098e77b66eb5a7d32c"
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
    bot.reply_to(message, "🚀 Buscando películas en Latino y generando JSON...")
    
    try:
        lista_actual = requests.get(f"https://api.npoint.io/{NPOINT_ID}").json()
        if not isinstance(lista_actual, list): lista_actual = []
    except:
        lista_actual = []
    
    titulos_viejos = [p['titulo'].lower() for p in lista_actual]
    
    # Búsqueda ampliada en Archive.org
    query = 'subject:"peliculas latino" AND format:MPEG4'
    url_search = f"https://archive.org/advancedsearch.php?q={query}&fl[]=identifier,title&rows=200&page=1&output=json"
    
    try:
        data = requests.get(url_search).json()
        items = data['response']['docs']
    except:
        bot.reply_to(message, "❌ Error de conexión.")
        return

    nuevas_encontradas = []
    for item in items:
        if len(nuevas_encontradas) >= 40: break # Intentamos traer 40
        
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
        # Actualizar nPoint automáticamente
        requests.post(f"https://api.npoint.io/{NPOINT_ID}", json=lista_actual)
        
        # Convertir a texto JSON
        json_bonito = json.dumps(lista_actual, indent=2, ensure_ascii=False)
        
        # SI ES CORTO: Mandar como texto de código
        if len(json_bonito) < 4000:
            bot.send_message(message.chat.id, f"✅ ¡Nuevas pelis sumadas!\n\n```json\n{json_bonito}\n```", parse_mode="Markdown")
        else:
            # SI ES LARGO: Mandar como archivo para que no se corte
            json_file = io.BytesIO(json_bonito.encode())
            json_file.name = "catalogo_suntv.json"
            bot.send_document(message.chat.id, json_file, caption=f"✅ Catálogo actualizado con {len(nuevas_encontradas)} pelis nuevas.")
    else:
        bot.reply_to(message, "⚠️ No hay películas nuevas para agregar por ahora.")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()










