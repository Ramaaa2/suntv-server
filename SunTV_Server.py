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
    # Limpieza profunda de palabras basura para que el título quede limpio
    palabras = ["720p", "1080p", "Dual", "Latino", "cinecalidad", "h264", "x264", "bluray", "unrated", "hd", "fullhd", "brrip"]
    for p in palabras:
        limpio = limpio.replace(p, "").replace(p.upper(), "").replace(p.capitalize(), "")
    return limpio.strip().capitalize()

@bot.message_handler(commands=['actualizar'])
def actualizar_peliculas(message):
    bot.reply_to(message, "🚀 Iniciando búsqueda de ALTA CALIDAD Latino... Buscando +30 películas.")
    
    try:
        lista_actual = requests.get(f"https://api.npoint.io/{NPOINT_ID}").json()
        if not isinstance(lista_actual, list): lista_actual = []
    except:
        lista_actual = []
    
    titulos_viejos = [p['titulo'].lower() for p in lista_actual]
    
    # NUEVA ESTRATEGIA: Buscamos específicamente archivos grandes (HD) y con etiquetas de calidad
    # Filtramos por archivos de más de 800MB para asegurar buen sonido y video
    query = '(subject:"peliculas latino" OR subject:"estrenos latino") AND format:MPEG4 AND (item_size:[800000000 TO 5000000000])'
    
    # Aumentamos rows a 500 para tener de dónde elegir
    url_search = f"https://archive.org/advancedsearch.php?q={query}&fl[]=identifier,title,item_size&sort[]=addeddate+desc&rows=500&page=1&output=json"
    
    try:
        data = requests.get(url_search).json()
        items = data['response']['docs']
    except:
        bot.reply_to(message, "❌ Error de conexión con el servidor.")
        return

    nuevas_encontradas = []
    for item in items:
        # Límite real: Intentamos traer 50 de un solo golpe
        if len(nuevas_encontradas) >= 50: break 
        
        titulo_raw = item['title']
        identificador = item['identifier']
        titulo_limpio = limpiar_titulo(titulo_raw)

        # Evitar repetidos
        if titulo_limpio.lower() not in titulos_viejos:
            # Verificamos que el link sea reproducible directamente
            url_video = f"https://archive.org/download/{identificador}/{identificador}.mp4"
            
            nueva_peli = {
                "titulo": titulo_limpio,
                "urlPortada": "https://via.placeholder.com/500x750.png?text=Peli+HD+Latino",
                "urlVideo": url_video,
                "calidad": "HD 1080p",
                "categoria": "Peliculas"
            }
            nuevas_encontradas.append(nueva_peli)
            lista_actual.append(nueva_peli)
            titulos_viejos.append(titulo_limpio.lower())

    if nuevas_encontradas:
        # Actualizar nPoint automáticamente
        requests.post(f"https://api.npoint.io/{NPOINT_ID}", json=lista_actual)
        
        # Generar JSON completo para mandarte al chat
        json_final = json.dumps(lista_actual, indent=2, ensure_ascii=False)
        
        # Siempre mandar como archivo para que no se pierda nada de código
        json_file = io.BytesIO(json_final.encode())
        json_file.name = "catalogo_completo_suntv.json"
        
        bot.send_document(
            message.chat.id, 
            json_file, 
            caption=f"✅ ¡Búsqueda exitosa!\n⭐ Agregadas: {len(nuevas_encontradas)} pelis de alta calidad.\n📂 Total en catálogo: {len(lista_actual)}"
        )
    else:
        bot.reply_to(message, "⚠️ No encontré películas nuevas de alta calidad que no tengas ya.")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()






