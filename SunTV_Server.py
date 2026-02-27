import telebot
import requests
import json
import io
import os
from flask import Flask
from threading import Thread

# --- CONFIGURACIÓN ---
TOKEN = "8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870"
NPOINT_ID = "78c73ead7cd12e9ce032" # TU ID DE NPOINT DE PELICULAS
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home(): return "Servidor SunTV Películas Activo"

def run_flask(): 
    # Render usa el puerto que le asigne la variable de entorno PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Función para obtener la lista actual de nPoint
def obtener_catalogo():
    try:
        res = requests.get(f"https://api.npoint.io/{NPOINT_ID}")
        data = res.json()
        return data if isinstance(data, list) else []
    except:
        return []

# Función para subir al nPoint
def guardar_catalogo(lista):
    requests.post(f"https://api.npoint.io/{NPOINT_ID}", json=lista)

@bot.message_handler(commands=['start'])
def enviar_bienvenida(message):
    bot.reply_to(message, "🎬 **Bienvenido al Servidor de SunTV**\n\nEnviame un archivo de video (.mp4) y yo lo agregaré automáticamente al catálogo de la App.")

# MANEJADOR DE VIDEOS Y DOCUMENTOS
@bot.message_handler(content_types=['video', 'document'])
def manejar_archivo(message):
    msg_espera = bot.reply_to(message, "⏳ Procesando video... por favor espera.")
    
    try:
        # 1. Obtener datos del archivo
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_name = message.video.file_name or f"Pelicula_{message.video.file_unique_id}.mp4"
        else:
            file_id = message.document.file_id
            file_name = message.document.file_name

        # 2. Obtener el link de descarga directa de Telegram
        # NOTA: Los links de Telegram duran 1 hora. 
        # Para que sean permanentes, lo ideal es usar un servidor intermedio como File.io o similar.
        file_info = bot.get_file(file_id)
        # Este link es el que usaremos (requiere que el bot esté activo para servirlo)
        direct_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

        # 3. Limpiar título
        titulo_final = file_name.replace(".mp4", "").replace(".mkv", "").replace("_", " ").capitalize()

        # 4. Actualizar nPoint
        catalogo = obtener_catalogo()
        
        nueva_entrada = {
            "titulo": titulo_final,
            "descripcion": "Subido mediante SunTV Server Bot.",
            "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png", # Foto por defecto
            "urlVideo": direct_url,
            "calidad": "HD",
            "categoria": "Estrenos"
        }
        
        catalogo.append(nueva_entrada)
        guardar_catalogo(catalogo)
        
        bot.edit_message_text(f"✅ **¡Película agregada!**\n\n🎥 **Título:** {titulo_final}\n📂 Total en App: {len(catalogo)}", 
                             message.chat.id, msg_espera.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.edit_message_text(f"❌ Error al procesar: {str(e)}", message.chat.id, msg_espera.message_id)

@bot.message_handler(commands=['ver'])
def ver_json(message):
    catalogo = obtener_catalogo()
    json_str = json.dumps(catalogo, indent=2, ensure_ascii=False)
    bot.send_document(message.chat.id, io.BytesIO(json_str.encode()), visible_file_name="suntv_pelis.json")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
