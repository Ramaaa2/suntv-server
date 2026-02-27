import telebot
import requests
import json
import io
import os
from flask import Flask
from threading import Thread

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("BOT_TOKEN")
# URL de Firebase (ej: https://tu-app-default-rtdb.firebaseio.com/)
FIREBASE_URL = os.environ.get("FIREBASE_URL", "").strip("/")
URL_BASE = os.environ.get("URL", "").strip("/")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home(): return "SunTV Firebase Server - ONLINE"

# --- FUNCIONES FIREBASE ---

def obtener_catalogo():
    try:
        # Firebase devuelve .json al final de la URL
        res = requests.get(f"{FIREBASE_URL}/peliculas.json")
        if res.status_code == 200:
            data = res.json()
            return data if isinstance(data, list) else []
        return []
    except:
        return []

def guardar_catalogo(lista):
    try:
        # Usamos PUT para sobrescribir la lista completa
        res = requests.put(f"{FIREBASE_URL}/peliculas.json", json=lista)
        return res.status_code == 200
    except:
        return False

# --- MANEJADORES ---

@bot.message_handler(commands=['start'])
def bienvenida(message):
    bot.reply_to(message, "🔥 **SunTV + Firebase** 🔥\nEnviame un video y se actualizará al instante.")

@bot.message_handler(content_types=['video', 'document'])
def manejar_archivo(message):
    msg = bot.reply_to(message, "🚀 Subiendo a Firebase...")
    try:
        file_id = message.video.file_id if message.content_type == 'video' else message.document.file_id
        file_name = (message.video.file_name if message.content_type == 'video' else message.document.file_name) or "peli.mp4"
        
        direct_url = f"{URL_BASE}/watch/{file_id}"
        titulo = file_name.split('.')[0].replace("_", " ").capitalize()

        catalogo = obtener_catalogo()
        catalogo.append({
            "titulo": titulo,
            "descripcion": "Estreno SunTV",
            "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
            "urlVideo": direct_url,
            "calidad": "1080p",
            "categoria": "Peliculas"
        })

        if guardar_catalogo(catalogo):
            bot.edit_message_text(f"✅ ¡Firebase Actualizado!\n🎬 {titulo}\n📂 Total: {len(catalogo)}", message.chat.id, msg.message_id)
        else:
            bot.edit_message_text("❌ Error al conectar con Firebase.", message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg.message_id)

@app.route('/watch/<file_id>')
def stream_video(file_id):
    try:
        file_info = bot.get_file(file_id)
        return requests.utils.redirect(f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}")
    except: return "Error", 404

def run_flask(): 
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
