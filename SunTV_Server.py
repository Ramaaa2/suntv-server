import telebot
import json
import io
import os
from flask import Flask, redirect, Response
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
    # Le decimos al bot que use la llave maestra que descargaste
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_URL
    })
    print("✅ Conectado a Firebase como Administrador.")
except Exception as e:
    print(f"❌ Error crítico: No se encontró 'firebase-key.json' o es inválido. Error: {e}")

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

# --- FUNCIÓN: DESCARGAR APK ---
@app.route('/descargar')
def descargar_app():
    LINK_DIRECTO_APK = "https://dl.springsfern.in/dl/AAAAAeJCAwJFEVJMAAAHMA/DMjkHL8mwTJ0d92SwW28VgkxZn7dzsHMTgDIRSsXp2k"
    return redirect(LINK_DIRECTO_APK)

# --- FUNCIONES FIREBASE CON LLAVE MAESTRA ---
def obtener_catalogo():
    try:
        ref = db.reference('peliculas')
        data = ref.get()
        if data is None: return []
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

# --- MANEJADORES DEL BOT DE TELEGRAM ---

@bot.message_handler(commands=['start'])
def enviar_bienvenida(message):
    bot.reply_to(message, "🎬 **SunTV Admin Bot**\n\n"
                          "• Para videos cortos (<20MB): Reenvíalos directamente.\n"
                          "• Para películas o APK: Pega el link directo que te dé el bot de streaming.")

@bot.message_handler(commands=['ver'])
def ver_json(message):
    catalogo = obtener_catalogo()
    json_str = json.dumps(catalogo, indent=2, ensure_ascii=False)
    bot.send_document(message.chat.id, io.BytesIO(json_str.encode()), visible_file_name="suntv_firebase.json", caption=f"📂 Películas en Firebase: {len(catalogo)}")

# Manejador de Links
@bot.message_handler(func=lambda message: message.text and message.text.startswith("http") and not "/watch/" in message.text)
def manejar_link(message):
    msg_espera = bot.reply_to(message, "🔗 Link detectado. Agregando a Firebase...")
    try:
        url_directa = message.text.strip()
        catalogo = obtener_catalogo()
        
        nueva_peli = {
            "titulo": "Nueva Película (Editar en Firebase)",
            "descripcion": "Agregado vía Link Directo.",
            "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
            "urlVideo": url_directa,
            "calidad": "HD",
            "categoria": "Estrenos"
        }
        
        catalogo.append(nueva_peli)
        if guardar_catalogo(catalogo):
            bot.edit_message_text(f"✅ ¡Link guardado!\nTotal: {len(catalogo)}\n\n*Nota:* Edita el título y portada en la web de Firebase.", message.chat.id, msg_espera.message_id)
        else:
            bot.edit_message_text("❌ Error al guardar en Firebase.", message.chat.id, msg_espera.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg_espera.message_id)

# Manejador de Archivos Directos (Videos)
@bot.message_handler(content_types=['video', 'document'])
def manejar_archivo(message):
    msg_espera = bot.reply_to(message, "🚀 Procesando archivo...")
    try:
        file_id = message.video.file_id if message.content_type == 'video' else message.document.file_id
        file_name = (message.video.file_name if message.content_type == 'video' else message.document.file_name) or "video.mp4"
        
        direct_url = f"{URL_BASE}/watch/{file_id}"
        titulo_limpio = file_name.split('.')[0].replace("_", " ").capitalize()

        catalogo = obtener_catalogo()
        catalogo.append({
            "titulo": titulo_limpio,
            "descripcion": "Video corto enviado directamente.",
            "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
            "urlVideo": direct_url,
            "calidad": "HD",
            "categoria": "Estrenos"
        })

        if guardar_catalogo(catalogo):
            bot.edit_message_text(f"✅ ¡Video guardado!\n🎬 {titulo_limpio}", message.chat.id, msg_espera.message_id)
        else:
            bot.edit_message_text("❌ Error al escribir en Firebase.", message.chat.id, msg_espera.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error crítico: {str(e)}", message.chat.id, msg_espera.message_id)

def run_flask(): 
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("Servidor SunTV ONLINE")
    bot.infinity_polling()





