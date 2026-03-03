import telebot
import json
import os
import requests
import random
import string
from flask import Flask, redirect
from threading import Thread
import firebase_admin
from firebase_admin import credentials, db, auth
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
# En Render, estas variables se sacan de la pestaña 'Environment'
TOKEN = os.environ.get('TOKEN')
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', 'f89f1b10ba76c14e544f07a1473f7d08')
FIREBASE_URL = os.environ.get('FIREBASE_URL', 'https://suntv-app-33e92-default-rtdb.firebaseio.com/')
ADMIN_IDS = [8090944258] 

# --- CONEXIÓN FIREBASE SEGURA ---
try:
    if not firebase_admin._apps:
        firebase_config = os.environ.get('FIREBASE_CONFIG')
        if firebase_config:
            # Configuración para RENDER (usa la variable de entorno)
            cred = credentials.Certificate(json.loads(firebase_config))
        else:
            # Configuración para TU PC (usa el archivo local)
            cred = credentials.Certificate("firebase-key.json")
        
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
    print("✅ Firebase Conectado")
except Exception as e:
    print(f"❌ Error Firebase: {e}")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>SunTV Server Online</h1><p>Servidor de peliculas y series activo.</p>"

@app.route('/watch/<file_id>')
def stream_video(file_id):
    try:
        file_info = bot.get_file(file_id)
        return redirect(f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}")
    except:
        return "Error al obtener el video", 404

# --- GESTIÓN DE USUARIOS ---

@bot.message_handler(commands=['buscar'])
def buscar_usuario(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        query = message.text.split()[1].lower()
        usuarios = db.reference('Usuarios').get()
        if not usuarios: return bot.reply_to(message, "No hay usuarios registrados.")
        
        encontrados = ""
        for uid, info in usuarios.items():
            email = info.get('email', '').lower()
            cel = info.get('celular', '')
            if query in email or query in cel:
                estado = "✅" if info.get('estado') == "ACTIVO" else "🚫"
                encontrados += f"{estado} `{email}`\nID: `{uid}`\nCel: {cel}\n\n"
        
        bot.reply_to(message, encontrados if encontrados else "❌ No hay coincidencias.", parse_mode="Markdown")
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

# --- CARGA DE PELIS Y SERIES ---

@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def detectar_link(message):
    if message.from_user.id not in ADMIN_IDS: return
    url = message.text.strip()
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("🎬 PELÍCULA", callback_data=f"t_Peli|{url}"),
        telebot.types.InlineKeyboardButton("📺 SERIE", callback_data=f"t_Serie|{url}")
    )
    bot.reply_to(message, "¿Qué estás subiendo?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("t_"))
def procesar_tipo(call):
    tipo, url = call.data.replace("t_", "").split("|")
    msg = bot.send_message(call.message.chat.id, f"📝 Escribí el nombre (Ej: Los Simpson - 35x01):")
    bot.register_next_step_handler(msg, lambda m: guardar_en_firebase(m, url, tipo))

def guardar_en_firebase(message, url, tipo):
    nombre_full = message.text
    nombre_busqueda = nombre_full.split("-")[0].strip() if "-" in nombre_full else nombre_full
    
    info = obtener_tmdb(nombre_busqueda)
    cat = "Serie" if tipo == "Serie" else (info['genero'] if info else "General")

    datos = {
        "titulo": nombre_full,
        "descripcion": info['desc'] if info else "Sin descripción.",
        "urlPortada": info['portada'] if info else "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
        "urlVideo": url,
        "calidad": "HD",
        "categoria": cat
    }

    if tipo == "Serie":
        nombre_carpeta = nombre_busqueda.replace(" ", "_")
        db.reference(f'series/{nombre_carpeta}/capitulos').push(datos)
    else:
        ref = db.reference('peliculas')
        actuales = ref.get() or []
        if isinstance(actuales, dict): actuales = list(actuales.values())
        actuales.append(datos)
        ref.set(actuales)

    bot.send_message(message.chat.id, f"✅ {tipo} guardada: {nombre_full}")

def obtener_tmdb(nombre):
    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={nombre}&language=es-ES"
    try:
        r = requests.get(url).json()
        if r['results']:
            m = r['results'][0]
            return {
                "desc": m.get('overview', 'Sin descripción'),
                "portada": f"https://image.tmdb.org/t/p/w500{m.get('poster_path')}",
                "genero": "Acción"
            }
    except: return None

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🎥 **SunTV Admin Online**\n\nEnvía un link para empezar.")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    print("🤖 Bot iniciado...")
    bot.infinity_polling(skip_pending=True)
