import telebot
import requests
import json

# --- CONFIGURACIÓN ---
TOKEN = "8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870"
NPOINT_ID = "https://api.npoint.io/f3098e77b66eb5a7d32c"
bot = telebot.TeleBot(TOKEN)

# Función para limpiar los nombres de los archivos
def limpiar_titulo(texto):
    limpio = texto.replace(".mp4", "").replace(".mkv", "").replace(".", " ").replace("_", " ")
    for palabra in ["720p", "1080p", "Dual", "Latino", "cinecalidad", "h264", "x264", "unrated"]:
        limpio = limpio.replace(palabra, "")
        limpio = limpio.replace(palabra.upper(), "")
    return limpio.strip().capitalize()

# Función para obtener lo que ya hay en nPoint
def obtener_catalogo():
    try:
        res = requests.get(f"https://api.npoint.io/{NPOINT_ID}")
        data = res.json()
        return data if isinstance(data, list) else []
    except:
        return []

# --- COMANDO PRINCIPAL ---
@bot.message_handler(commands=['actualizar'])
def actualizar_peliculas(message):
    bot.reply_to(message, "🔍 Buscando 30 películas nuevas en Latino... Espere un momento.")
    
    # 1. Bajamos la lista actual
    lista_actual = obtener_catalogo()
    titulos_viejos = [p['titulo'] for p in lista_actual]

    # 2. Buscamos en Archive.org (Contenido en Latino)
    query = 'subject:"peliculas latino" AND format:MPEG4'
    url_search = f"https://archive.org/advancedsearch.php?q={query}&fl[]=identifier,title&rows=100&page=1&output=json"
    
    try:
        data = requests.get(url_search).json()
        items = data['response']['docs']
    except:
        bot.reply_to(message, "❌ Error al conectar con Archive.org")
        return

    agregadas = 0
    for item in items:
        if agregadas >= 30: break
        
        titulo_raw = item['title']
        id_item = item['identifier']
        titulo_limpio = limpiar_titulo(titulo_raw)

        # Solo agregamos si el título no existe ya
        if titulo_limpio not in titulos_viejos:
            url_video = f"https://archive.org/download/{id_item}/{id_item}.mp4"
            # Portada temporal (luego le ponemos la de TMDB)
            portada = "https://via.placeholder.com/500x750.png?text=Pelicula+Latina"
            
            lista_actual.append({
                "titulo": titulo_limpio,
                "urlPortada": portada,
                "urlVideo": url_video,
                "calidad": "HD",
                "categoria": "Peliculas"
            })
            titulos_viejos.append(titulo_limpio)
            agregadas += 1

    # 3. Guardamos en nPoint
    if agregadas > 0:
        requests.post(f"https://api.npoint.io/{NPOINT_ID}", json=lista_actual)
        bot.reply_to(message, f"✅ ¡Listo! Se agregaron {agregadas} películas nuevas.\nTotal en SunTV: {len(lista_actual)}")
    else:
        bot.reply_to(message, "⚠️ No encontré películas nuevas que no estuvieran ya en la lista.")

# Iniciar el Bot
print("Bot en marcha...")
bot.infinity_polling()









