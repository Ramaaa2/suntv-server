import telebot
import os
import json
import random
import string
from flask import Flask, redirect
from threading import Thread
import firebase_admin
from firebase_admin import credentials, db, auth
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE RENDER ---
# Lee todo desde las variables de entorno de la página de Render
TOKEN = os.environ.get('TOKEN') 
FIREBASE_URL = os.environ.get('FIREBASE_URL')
ADMIN_IDS = [8090944258]

# --- CONEXIÓN FIREBASE EN LA NUBE ---
try:
    firebase_config = os.environ.get('FIREBASE_CONFIG')
    if firebase_config and not firebase_admin._apps:
        cred_dict = json.loads(firebase_config)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
    print("✅ Firebase en Render Conectado")
except Exception as e:
    print(f"❌ Error Firebase en Render: {e}")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- RUTAS WEB (Mantiene la App viva y hace el streaming) ---
@app.route('/')
def home():
    return "<h1>SunTV Server Online</h1><p>El servidor principal está funcionando al 100%.</p>"

@app.route('/watch/<file_id>')
def stream_video(file_id):
    try:
        file_info = bot.get_file(file_id)
        return redirect(f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}")
    except:
        return "Error al reproducir", 404

# --- GESTIÓN DE USUARIOS (Para vender desde el celular) ---
@bot.message_handler(commands=['buscar'])
def buscar_usuario(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        query = message.text.split()[1].lower()
        usuarios = db.reference('Usuarios').get()
        if not usuarios: return bot.reply_to(message, "No hay usuarios.")
        
        encontrados = ""
        for uid, info in usuarios.items():
            email = info.get('email', '').lower()
            cel = info.get('celular', '')
            if query in email or query in cel:
                estado = "✅" if info.get('estado') == "ACTIVO" else "🚫"
                encontrados += f"{estado} `{email}`\nID: `{uid}`\nCel: {cel}\n\n"
        
        bot.reply_to(message, encontrados if encontrados else "❌ Sin coincidencias.", parse_mode="Markdown")
    except: bot.reply_to(message, "❌ Uso: /buscar [email o celular]")

@bot.message_handler(commands=['vender'])
def vender(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        args = message.text.split()
        if len(args) < 3: return bot.reply_to(message, "❌ Uso: /vender [email] [celular]")
        email, celular = args[1], args[2]
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        user = auth.create_user(email=email, password=password)
        vencimiento = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        db.reference(f'Usuarios/{user.uid}').set({
            'email': email, 'celular': celular, 'estado': 'ACTIVO',
            'vencimiento': vencimiento, 'pantallas_max': 1
        })
        bot.reply_to(message, f"✅ **VENTA EXITOSA**\n\n📧 User: `{email}`\n🔑 Pass: `{password}`\n📅 Vence: {vencimiento}", parse_mode="Markdown")
    except Exception as e: bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['apagar', 'encender'])
def cambiar_estado(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        cmd = message.text.split()[0]
        uid = message.text.split()[1]
        nuevo_estado = "IMPAGO" if "apagar" in cmd else "ACTIVO"
        db.reference(f'Usuarios/{uid}').update({'estado': nuevo_estado})
        bot.reply_to(message, f"✅ Usuario {uid} cambiado a {nuevo_estado}")
    except: bot.reply_to(message, "❌ Uso: /apagar o /encender [UID]")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ **SunTV Render Online**\nEl servidor de la App está funcionando correctamente.")

# --- INICIO DEL SERVIDOR ---
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling(skip_pending=True)
