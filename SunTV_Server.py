import telebot
import requests
import json
import io
import os
from flask import Flask, redirect
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
    bot.reply_to(message, "🎬 **Bienvenido a SunTV Admin**\n\n"
                          "1. **Video corto (<20MB):** Envíalo o reenvíalo directamente.\n"
                          "2. **Película pesada (>20MB):** Reenvíala a un bot como `@DirectLink_Bot`, y el link que te dé, pégalo aquí.")

@bot.message_handler(commands=['ver'])
def ver_json(message):
    catalogo = obtener_catalogo()
    json_str = json.dumps(catalogo, indent=2, ensure_ascii=False)
    bot.send_document(message.chat.id, io.BytesIO(json_str.encode()), visible_file_name="suntv_firebase.json", caption=f"📂 Películas en Firebase: {len(catalogo)}")

# --- NUEVO: MANEJADOR DE LINKS (Para evitar error de tamaño) ---
@bot.message_handler(func=lambda message: message.text and message.text.startswith("http") and not "/watch/" in message.text)
def manejar_link(message):
    msg_espera = bot.reply_to(message, "🔗 Link detectado. Agregando a Firebase...")
    try:
        url_directa = message.text.strip()
        catalogo = obtener_catalogo()
        
        nueva_peli = {
            "titulo": "Nueva Película (Editar en Firebase)",
            "descripcion": "Subido mediante Link Directo.",
            "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
            "urlVideo": url_directa,
            "calidad": "HD",
            "categoria": "Estrenos"
        }
        
        catalogo.append(nueva_peli)
        if guardar_catalogo(catalogo):
            bot.edit_message_text(f"✅ ¡Link guardado!\nTotal: {len(catalogo)}\n\n*Nota:* Ve a Firebase para cambiar el nombre.", message.chat.id, msg_espera.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ Error al guardar link en Firebase.", message.chat.id, msg_espera.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg_espera.message_id)

# --- MANEJADOR DE ARCHIVOS (Solo para archivos pequeños) ---
@bot.message_handler(content_types=['video', 'document'])
def manejar_archivo(message):
    msg_espera = bot.reply_to(message, "🚀 Procesando video corto...")
    try:
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_name = message.video.file_name or "video.mp4"
        else:
            file_id = message.document.file_id
            file_name = message.document.file_name or "archivo.mp4"

        direct_url = f"{URL_BASE}/watch/{file_id}"
        titulo_limpio = file_name.split('.')[0].replace("_", " ").capitalize()

        catalogo = obtener_catalogo()
        catalogo.append({
            "titulo": titulo_limpio,
            "descripcion": "Video corto vía Bot.",
            "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
            "urlVideo": direct_url,
            "calidad": "HD",
            "categoria": "Estrenos"
        })

        if guardar_catalogo(catalogo):
            bot.edit_message_text(f"✅ ¡Video corto guardado!\n🎬 {titulo_limpio}\n📂 Total: {len(catalogo)}", message.chat.id, msg_espera.message_id)
        else:
            bot.edit_message_text("❌ Error al escribir en Firebase.", message.chat.id, msg_espera.message_id)

    except Exception as e:
        if "file is too big" in str(e).lower():
            bot.edit_message_text("❌ **Archivo demasiado grande (>20MB).**\n\nPara películas pesadas, usa un bot de links (como @DirectLink_Bot) y pégame el enlace aquí.", message.chat.id, msg_espera.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg_espera.message_id)

# --- PUENTE DE STREAMING ---
@app.route('/watch/<file_id>')
def stream_video(file_id):
    try:
        file_info = bot.get_file(file_id)
        telegram_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        return redirect(telegram_url)
    except Exception as e:
        return f"Error de streaming: {str(e)}", 404

def run_flask(): 
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("Bot SunTV Firebase ONLINE")
    bot.infinity_polling()
