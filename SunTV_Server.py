import telebot
import requests
import json
import io
import os
from flask import Flask
from threading import Thread

# --- CONFIGURACIÓN ---
# Las variables se leen de Render para mayor seguridad
TOKEN = os.environ.get("BOT_TOKEN", "8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870")
NPOINT_ID = os.environ.get("NPOINT_ID", "78c73ead7cd12e9ce032")
URL_BASE = os.environ.get("URL", "").strip("/")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home(): 
    return "Servidor SunTV Películas - Estado: ONLINE"

def run_flask(): 
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- FUNCIONES DE AYUDA ---

def obtener_catalogo():
    """Lee la lista actual de nPoint con headers para evitar bloqueos"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(f"https://api.npoint.io/{NPOINT_ID}", headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data if isinstance(data, list) else []
        return []
    except Exception as e:
        print(f"Error al obtener nPoint: {e}")
        return []

def guardar_catalogo(lista):
    """Sube la lista actualizada a nPoint"""
    try:
        res = requests.post(f"https://api.npoint.io/{NPOINT_ID}", json=lista, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"Error al guardar en nPoint: {e}")
        return False

# --- MANEJADORES DEL BOT ---

@bot.message_handler(commands=['start'])
def enviar_bienvenida(message):
    bot.reply_to(message, "🎬 **Servidor SunTV v2.0**\n\nEnviame un archivo de video o reenvialo desde tu canal privado y lo agregaré a la App automáticamente.")

@bot.message_handler(commands=['ver'])
def ver_json(message):
    catalogo = obtener_catalogo()
    json_str = json.dumps(catalogo, indent=2, ensure_ascii=False)
    bot.send_document(message.chat.id, io.BytesIO(json_str.encode()), visible_file_name="suntv_check.json", caption=f"📂 Total de películas: {len(catalogo)}")

@bot.message_handler(content_types=['video', 'document'])
def manejar_archivo(message):
    msg_espera = bot.reply_to(message, "⏳ Procesando archivo y actualizando nPoint...")
    
    try:
        # 1. Identificar el archivo
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_name = message.video.file_name or f"Video_{message.video.file_unique_id}.mp4"
        else:
            file_id = message.document.file_id
            file_name = message.document.file_name or "archivo_desconocido.mp4"

        # 2. Verificar URL de Render
        if not URL_BASE:
            bot.edit_message_text("❌ Error: Falta configurar la variable 'URL' en Render.", message.chat.id, msg_espera.message_id)
            return

        # 3. Generar el link de streaming
        # Este link apunta a tu bot en Render que hace de puente
        direct_url = f"{URL_BASE}/watch/{file_id}"

        # 4. Limpiar el título para la App
        titulo_limpio = file_name.replace(".mp4", "").replace(".mkv", "").replace("_", " ").strip().capitalize()

        # 5. Proceso de actualización
        catalogo = obtener_catalogo()
        
        nueva_peli = {
            "titulo": titulo_limpio,
            "descripcion": "Agregado automáticamente por SunTV Server.",
            "urlPortada": "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
            "urlVideo": direct_url,
            "calidad": "HD",
            "categoria": "Estrenos"
        }
        
        catalogo.append(nueva_peli)
        
        if guardar_catalogo(catalogo):
            bot.edit_message_text(
                f"✅ **¡Película agregada con éxito!**\n\n"
                f"🎥 **Título:** {titulo_limpio}\n"
                f"📂 **Total en catálogo:** {len(catalogo)}\n\n"
                f"Refresca tu App SunTV para verla.", 
                message.chat.id, msg_espera.message_id, parse_mode="Markdown"
            )
        else:
            bot.edit_message_text("❌ Error: No se pudo guardar en nPoint. Revisa la conexión.", message.chat.id, msg_espera.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Error crítico: {str(e)}", message.chat.id, msg_espera.message_id)

# --- SERVIDOR DE STREAMING (EL PUENTE) ---
@app.route('/watch/<file_id>')
def stream_video(file_id):
    # Genera el link directo temporal de Telegram para que el reproductor lo lea
    try:
        file_info = bot.get_file(file_id)
        telegram_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        return requests.utils.redirect(telegram_url)
    except:
        return "Error al obtener el stream de Telegram", 404

if __name__ == "__main__":
    # Iniciar Flask en un hilo separado
    Thread(target=run_flask).start()
    # Iniciar el bot
    print("Bot SunTV iniciado...")
    bot.infinity_polling()
