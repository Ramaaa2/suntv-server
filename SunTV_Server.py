import telebot
import os
from flask import Flask, redirect
from threading import Thread
import firebase_admin
from firebase_admin import credentials, db, auth

# --- CONFIGURACIÓN DE RENDER ---
TOKEN = os.environ.get('TOKEN') # Esto lo sacamos de la web de Render
FIREBASE_URL = os.environ.get('FIREBASE_URL')
ADMIN_IDS = [8090944258] 

# --- CONEXIÓN FIREBASE (Vía Variable de Entorno) ---
import json
firebase_config = os.environ.get('FIREBASE_CONFIG')
if firebase_config and not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(firebase_config))
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.view_functions.get('/', None)
@app.route('/')
def home(): 
    return "<h1>SunTV Server Online</h1><p>El sistema de descarga y usuarios está activo.</p>"

# Ruta para que la App descargue contenido o valide archivos
@app.route('/watch/<file_id>')
def stream_video(file_id):
    try:
        file_info = bot.get_file(file_id)
        return redirect(f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}")
    except: return "Error", 404

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ **SunTV Server Activo**\nEste bot mantiene la App online.")

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling(skip_pending=True)
