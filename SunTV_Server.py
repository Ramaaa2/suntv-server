import telebot
import json
import io
import os
from flask import Flask, redirect, Response, make_response
from threading import Thread

# Librerías de administrador de Firebase
import firebase_admin
from firebase_admin import credentials, db

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("BOT_TOKEN", "8756442233:AAFG959KZpb-JXmtbp3Hhx1PLkLft5jsy2k")
FIREBASE_URL = os.environ.get("FIREBASE_URL", "https://suntv-app-33e92-default-rtdb.firebaseio.com/").strip("/")
URL_BASE = os.environ.get("URL", "").strip("/")

# --- CONEXIÓN VIP A FIREBASE ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_URL
        })
    print("✅ Conectado a Firebase como Administrador.")
except Exception as e:
    print(f"❌ Error crítico de Firebase: {e}")

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

# --- FUNCIÓN: DESCARGAR APK (CON ANTI-CACHÉ FORZADO) ---
@app.route('/descargar')
def descargar_app():
    """
    Redirecciona al link de GitHub v2.0 forzando la descarga fresca.
    """
    # Agregamos '?v=2' al final para que GitHub y los navegadores crean que es un archivo nuevo
    LINK_DIRECTO_APK = "https://github.com/Ramaaa2/suntv-server/releases/download/v2.0/app-debug.apk?v=2"
    
    # Creamos una respuesta que prohíbe guardar el link en caché
    response = make_response(redirect(LINK_DIRECTO_APK))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# --- FUNCIONES FIREBASE ---
def obtener_catalogo():
    try:
        ref = db.reference('peliculas')
        data = ref.get()
        if data is None: return []
        if isinstance(data, dict):
            return list(data.values())
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error obteniendo Firebase: {e}")
        return []

def guardar_catalogo(lista):
    try:
        ref = db.reference('peliculas')
        ref.set(lista)
        return True
    except Exception as e:
        print(f"Error guardando en Firebase: {e}")
        return False

# --- MANEJADORES DEL BOT ---

@bot.message_handler(commands=['start'])
def enviar_bienvenida(message):
    bot.reply_to(message, "🎬 **SunTV Admin Bot v2.0**\n\n"
                          "• Envía un link para agregar peli.\n"
                          "• /ver - Descarga el JSON.\n"
                          "• /descargar - Link de la APK nueva.")

@bot.message_handler(commands=['ver'])
def ver_json(message):
    catalogo = obtener_catalogo()
    json_str = json.dumps(catalogo, indent=2, ensure_ascii=False)
    bot.send_document(message.chat.id, io.BytesIO(json_str.encode()), 
                     visible_file_name="suntv_firebase.json", 
                     caption=f"📂 Películas en Firebase: {len(catalogo)}")

@bot.message_handler(commands=['descargar'])
def link_descarga(message):
    bot.reply_to(message, "🚀 **Descarga SunTV v2.0 (Forzada):**\nhttps://github.com/Ramaaa2/suntv-server/releases/download/v2.0/app-debug.apk")

@bot.message_handler(func=lambda message: message.text and message.text.startswith("http") and not "/watch/" in message.text)
def manejar_link(message):
    msg_espera = bot.reply_to(message, "🔗 Agregando a Firebase...")
    try:
        url_directa = message.text.strip()
        catalogo = obtener_catalogo()
        catalogo.append({
            "titulo": "Nueva Película",
            "descripcion": "Agregado vía Bot.",
            "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
            "urlVideo": url_directa,
            "calidad": "HD",
            "categoria": "Estrenos"
        })
        if guardar_catalogo(catalogo):
            bot.edit_message_text(f"✅ ¡Guardado!\nTotal: {len(catalogo)}", message.chat.id, msg_espera.message_id)
        else:
            bot.edit_message_text("❌ Error en Firebase.", message.chat.id, msg_espera.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg_espera.message_id)

@bot.message_handler(content_types=['video', 'document'])
def manejar_archivo(message):
    msg_espera = bot.reply_to(message, "🚀 Procesando video...")
    try:
        file_id = message.video.file_id if message.content_type == 'video' else message.document.file_id
        file_name = (message.video.file_name if message.content_type == 'video' else message.document.file_name) or "video.mp4"
        direct_url = f"{URL_BASE}/watch/{file_id}"
        titulo_limpio = file_name.split('.')[0].replace("_", " ").capitalize()
        catalogo = obtener_catalogo()
        catalogo.append({
            "titulo": titulo_limpio,
            "urlVideo": direct_url,
            "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
            "calidad": "HD",
            "categoria": "Telegram"
        })
        if guardar_catalogo(catalogo):
            bot.edit_message_text(f"✅ ¡Video guardado!\n🎬 {titulo_limpio}", message.chat.id, msg_espera.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg_espera.message_id)

def run_flask(): 
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()






