import telebot
import requests
import json
import io
import os
from flask import Flask, redirect  # Se corrigió el import del redirect
from threading import Thread

# --- CONFIGURACIÓN ---
# Estos valores se pueden configurar en Render (Environment) o dejarlos aquí
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
    """Lee la lista actual de Firebase"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Importante: Firebase requiere el .json al final
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
    """Sube la lista actualizada a Firebase"""
    try:
        res = requests.put(f"{FIREBASE_URL}/peliculas.json", json=lista, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"Error guardando en Firebase: {e}")
        return False

# --- MANEJADORES DEL BOT ---

@bot.message_handler(commands=['start'])
def enviar_bienvenida(message):
    bot.reply_to(message, "🎬 **Servidor SunTV + Firebase**\n\nEnviame un video o reenvialo desde tu canal privado para agregarlo a la App.")

@bot.message_handler(commands=['ver'])
def ver_json(message):
    catalogo = obtener_catalogo()
    json_str = json.dumps(catalogo, indent=2, ensure_ascii=False)
    bot.send_document(message.chat.id, io.BytesIO(json_str.encode()), visible_file_name="suntv_firebase.json", caption=f"📂 Películas en Firebase: {len(catalogo)}")

@bot.message_handler(content_types=['video', 'document'])
def manejar_archivo(message):
    msg_espera = bot.reply_to(message, "🚀 Procesando y subiendo a Firebase...")
    
    try:
        # 1. Identificar archivo
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_name = message.video.file_name or f"Video_{message.video.file_unique_id}.mp4"
        else:
            file_id = message.document.file_id
            file_name = message.document.file_name or "archivo.mp4"

        # 2. Verificar URL de Render
        if not URL_BASE:
            bot.edit_message_text("❌ Error: Falta la variable 'URL' en Render.", message.chat.id, msg_espera.message_id)
            return

        # 3. Generar link de streaming puente
        direct_url = f"{URL_BASE}/watch/{file_id}"

        # 4. Limpiar título
        titulo_limpio = file_name.replace(".mp4", "").replace(".mkv", "").replace("_", " ").strip().capitalize()

        # 5. Guardar en Firebase
        catalogo = obtener_catalogo()
        
        nueva_peli = {
            "titulo": titulo_limpio,
            "descripcion": "Agregado vía SunTV Bot.",
            "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
            "urlVideo": direct_url,
            "calidad": "HD",
            "categoria": "Estrenos"
        }
        
        catalogo.append(nueva_peli)
        
        if guardar_catalogo(catalogo):
            bot.edit_message_text(
                f"✅ **¡Firebase Actualizado!**\n\n"
                f"🎥 **Título:** {titulo_limpio}\n"
                f"📂 **Total:** {len(catalogo)}", 
                message.chat.id, msg_espera.message_id, parse_mode="Markdown"
            )
        else:
            bot.edit_message_text("❌ Error al escribir en Firebase.", message.chat.id, msg_espera.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Error crítico: {str(e)}", message.chat.id, msg_espera.message_id)

# --- PUENTE DE STREAMING (CORREGIDO) ---
@app.route('/watch/<file_id>')
def stream_video(file_id):
    try:
        # Obtenemos la ruta real del archivo en Telegram
        file_info = bot.get_file(file_id)
        # URL oficial de descarga/stream de Telegram
        telegram_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        # Redireccionamos el reproductor (ExoPlayer) directamente al archivo
        return redirect(telegram_url)
    except Exception as e:
        return f"Error de streaming: {str(e)}", 404

def run_flask(): 
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Iniciar Flask en un hilo separado
    Thread(target=run_flask).start()
    # Iniciar el bot (Infinity polling para evitar caídas)
    print("Bot SunTV Firebase iniciado...")
    bot.infinity_polling()

