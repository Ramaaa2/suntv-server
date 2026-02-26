import telebot
import requests
import json
import io
import random
from flask import Flask
from threading import Thread

# --- CONFIGURACIÓN ---
TOKEN = "8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870"
NPOINT_ID = "f3098e77b66eb5a7d32c"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home(): return "Bot SunTV Activo"

def run_flask(): app.run(host='0.0.0.0', port=10000)

def limpiar_titulo(texto):
    limpio = texto.replace(".mp4", "").replace(".mkv", "").replace(".", " ").replace("_", " ")
    palabras = ["720p", "1080p", "Dual", "Latino", "cinecalidad", "h264", "x264", "bluray", "unrated", "hd", "fullhd", "brrip", "web-dl"]
    for p in palabras:
        limpio = limpio.replace(p, "").replace(p.upper(), "").replace(p.capitalize(), "")
    return limpio.strip().capitalize()

@bot.message_handler(commands=['actualizar'])
def actualizar_peliculas(message):
    bot.reply_to(message, "🧨 Iniciando Búsqueda Profunda... Analizando cientos de archivos HD.")
    
    try:
        lista_actual = requests.get(f"https://api.npoint.io/{NPOINT_ID}").json()
        if not isinstance(lista_actual, list): lista_actual = []
    except:
        lista_actual = []
    
    titulos_viejos = [p['titulo'].lower()[:10] for p in lista_actual] # Comparamos solo los primeros 10 caracteres
    
    # ESTRATEGIA: Varias búsquedas simultáneas para encontrar variedad
    queries = [
        'subject:"peliculas latino" AND format:MPEG4',
        'subject:"cine latino" AND format:MPEG4',
        'title:"latino" AND format:MPEG4 AND item_size:[500000000 TO 5000000000]'
    ]
    
    nuevas_encontradas = []
    
    for q in queries:
        if len(nuevas_encontradas) >= 40: break # Frenamos cuando tengamos suficientes
        
        # Pedimos una página aleatoria para no traer siempre lo mismo
        pagina = random.randint(1, 5)
        url_search = f"https://archive.org/advancedsearch.php?q={q}&fl[]=identifier,title&sort[]=addeddate+desc&rows=150&page={pagina}&output=json"
        
        try:
            data = requests.get(url_search).json()
            items = data['response']['docs']
            
            for item in items:
                if len(nuevas_encontradas) >= 40: break
                
                titulo_raw = item['title']
                identificador = item['identifier']
                titulo_limpio = limpiar_titulo(titulo_raw)

                # Si el inicio del título no está en la lista vieja, lo agregamos
                if titulo_limpio.lower()[:10] not in titulos_viejos:
                    url_video = f"https://archive.org/download/{identificador}/{identificador}.mp4"
                    
                    nueva_peli = {
                        "titulo": titulo_limpio,
                        "urlPortada": "https://via.placeholder.com/500x750.png?text=SunTV+Pelicula",
                        "urlVideo": url_video,
                        "calidad": "HD",
                        "categoria": "Peliculas"
                    }
                    nuevas_encontradas.append(nueva_peli)
                    lista_actual.append(nueva_peli)
                    titulos_viejos.append(titulo_limpio.lower()[:10])
        except:
            continue

    if nuevas_encontradas:
        # Subir a nPoint
        requests.post(f"https://api.npoint.io/{NPOINT_ID}", json=lista_actual)
        
        # Mandar el JSON completo al chat
        json_str = json.dumps(lista_actual, indent=2, ensure_ascii=False)
        json_file = io.BytesIO(json_str.encode())
        json_file.name = "catalogo_suntv.json"
        
        bot.send_document(message.chat.id, json_file, caption=f"✅ ¡Encontré {len(nuevas_encontradas)} pelis nuevas!\n📂 Total ahora: {len(lista_actual)}")
    else:
        bot.reply_to(message, "⚠️ Intenté buscar en varias páginas pero no hay nada nuevo en este momento. Probá de nuevo en un rato.")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()







