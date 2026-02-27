import telebot
import requests
import json
import io
import os
from flask import Flask, redirect, Response
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

# --- FUNCIÓN: DESCARGAR APK ---
@app.route('/descargar')
def descargar_app():
    """
    Redirecciona directamente al link de descarga de tu APK.
    Cuando actualices la App, solo cambia este link de aquí abajo.
    """
    LINK_DIRECTO_APK = "https://dl.springsfern.in/dl/AAAAAeJCAwJFEVJMAAAG-Q/Eh1tnarfB6Wsr51Dn-sqxgkuNDb1juEYcbmD1oPIjb8"
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
    bot.reply_to(message, "🎬 **SunTV Admin Bot**\n\n"
                          "• Para videos cortos (<20MB): Reenvíalos directamente.\n"
                          "• Para películas o APK: Pega el link directo que te dé el bot de streaming.")

@bot.message_handler(commands=['ver'])
def ver_json(message):
    catalogo = obtener_catalogo()
    json_str = json.dumps(catalogo, indent=2, ensure_ascii=False)
    bot.send_document(message.chat.id, io.BytesIO(json_str.encode()), visible_file_name="suntv_firebase.json", caption=f"📂 Películas en Firebase: {len(catalogo)}")

# Manejador de Links (Películas grandes o Links externos)
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

# Manejador de Archivos Directos (Videos cortos)
@bot.message_handler(content_types=['video', 'document'])
def manejar_archivo(message):
    msg_espera = bot.reply_to(message, "🚀 Procesando archivo...")
    try:
        file_id = message.video.file_id if message.content_type == 'video' else message.document.file_id
        file_name = (message.video.file_name if message.content_type == 'video' else message.document.file_name) or "video.mp4"
        
        # Link que pasará por el puente /watch/
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
    # Hilo para Flask (Web y Descargas)
    Thread(target=run_flask).start()
    # Polling del Bot de Telegram
    print("Servidor SunTV ONLINE")
    bot.infinity_polling()


