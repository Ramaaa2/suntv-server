import telebot
import requests
import json
import io
import os
from flask import Flask, redirect, send_file
from threading import Thread

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("BOT_TOKEN", "8756442233:AAFG959KZpb-JXmtbp3Hhx1PLkLft5jsy2k")
FIREBASE_URL = os.environ.get("FIREBASE_URL", "https://suntv-app-33e92-default-rtdb.firebaseio.com/").strip("/")
URL_BASE = os.environ.get("URL", "").strip("/")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home(): 
    return "SunTV Firebase Server - ONLINE"

# --- PUENTE DE STREAMING ---
@app.route('/watch/<file_id>')
def stream_video(file_id):
    try:
        file_info = bot.get_file(file_id)
        telegram_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        return redirect(telegram_url)
    except Exception as e:
        return f"Error de streaming: {str(e)}", 404

# --- NUEVA FUNCIÓN: DESCARGAR APK ---
@app.route('/descargar')
def descargar_app():
    """
    Esta ruta sirve para que pongas el link de tu APK.
    Puedes subir el APK a MediaFire, GitHub o Drive y pegar el link directo aquí.
    """
    # REEMPLAZA ESTE LINK por el link de descarga de tu APK (puedes usar el que te da @DirectLink_Bot para tu APK)
    LINK_DIRECTO_APK = "https://dl.springsfern.in/dl/AAAAAeJCAwJFEVJMAAAG9A/DwHzpWgQq_qOxXqoVPHqjtoopDU6ozExBRyRZtNzQtU" 
    
    if LINK_DIRECTO_APK == "https://dl.springsfern.in/dl/AAAAAeJCAwJFEVJMAAAG9A/DwHzpWgQq_qOxXqoVPHqjtoopDU6ozExBRyRZtNzQtU":
        return "Error: No has configurado el link del APK en el código.", 400
        
    return redirect(LINK_DIRECTO_APK)

# --- FUNCIONES FIREBASE ---

def obtener_catalogo():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(f"{FIREBASE_URL}/peliculas.json", headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data is None: return []
            return data if isinstance(data, list) else []
        return []
    except Exception as e:
        print(f"Error obteniendo Firebase: {e}")
        return []

def guardar_catalogo(lista):
    try:
        res = requests.put(f"{FIREBASE_URL}/peliculas.json", json=lista, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"Error guardando en Firebase: {e}")
        return False

# --- MANEJADORES DEL BOT ---

@bot.message_handler(commands=['start'])
def enviar_bienvenida(message):
    bot.reply_to(message, "🎬 **Bienvenido a SunTV Admin**\n\nEnvía videos cortos o links directos de pelis.")

@bot.message_handler(func=lambda message: message.text and message.text.startswith("http") and not "/watch/" in message.text)
def manejar_link(message):
    msg_espera = bot.reply_to(message, "🔗 Link detectado. Agregando...")
    try:
        url_directa = message.text.strip()
        catalogo = obtener_catalogo()
        catalogo.append({
            "titulo": "Nueva Película (Editar en Firebase)",
            "descripcion": "Subido vía Link.",
            "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
            "urlVideo": url_directa,
            "calidad": "HD",
            "categoria": "Estrenos"
        })
        if guardar_catalogo(catalogo):
            bot.edit_message_text(f"✅ ¡Link guardado!\nTotal: {len(catalogo)}", message.chat.id, msg_espera.message_id)
        else:
            bot.edit_message_text("❌ Error Firebase.", message.chat.id, msg_espera.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg_espera.message_id)

@bot.message_handler(content_types=['video', 'document'])
def manejar_archivo(message):
    msg_espera = bot.reply_to(message, "🚀 Procesando...")
    try:
        file_id = message.video.file_id if message.content_type == 'video' else message.document.file_id
        file_name = (message.video.file_name if message.content_type == 'video' else message.document.file_name) or "video.mp4"
        direct_url = f"{URL_BASE}/watch/{file_id}"
        titulo_limpio = file_name.split('.')[0].replace("_", " ").capitalize()
        catalogo = obtener_catalogo()
        catalogo.append({
            "titulo": titulo_limpio, "descripcion": "Video corto.", "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
            "urlVideo": direct_url, "calidad": "HD", "categoria": "Estrenos"
        })
        guardar_catalogo(catalogo)
        bot.edit_message_text(f"✅ ¡Video guardado!", message.chat.id, msg_espera.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg_espera.message_id)

def run_flask(): 
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()

