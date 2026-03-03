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
TOKEN = os.environ.get('TOKEN')
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', 'TU_TMDB_KEY_AQUI')
FIREBASE_URL = os.environ.get('FIREBASE_URL', 'TU_URL_FIREBASE_AQUI')
ADMIN_IDS = [8090944258] 

# --- CONEXIÓN FIREBASE SEGURA ---
try:
    if not firebase_admin._apps:
        # Intenta leer desde variable de entorno (Render) o archivo local (PC)
        firebase_config = os.environ.get('FIREBASE_CONFIG')
        if firebase_config:
            cred = credentials.Certificate(json.loads(firebase_config))
        else:
            cred = credentials.Certificate("firebase-key.json")
        
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
    print("✅ Firebase Conectado")
except Exception as e:
    print(f"❌ Error Firebase: {e}")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home(): return "SunTV Server Online"

@app.route('/watch/<file_id>')
def stream_video(file_id):
    try:
        file_info = bot.get_file(file_id)
        return redirect(f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}")
    except: return "Error", 404

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

# --- CARGA DE PELIS Y SERIES ---

@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text.startswith("http"))
def detectar_link(message):
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
    # Limpiamos el nombre para buscar en TMDB (sacamos el "1x01" etc)
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
        # Guardar en series/Nombre_Serie/capitulos
        nombre_carpeta = nombre_busqueda.replace(" ", "_")
        db.reference(f'series/{nombre_carpeta}/capitulos').push(datos)
    else:
        # Guardar en peliculas
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
                "genero": "Acción" # Simplificado
            }
    except: return None

# --- COMANDOS EXTRAS ---
@bot.message_handler(commands=['usuarios'])
def lista_usuarios(message):
    if message.from_user.id not in ADMIN_IDS: return
    users = db.reference('Usuarios').get()
    if not users: return bot.reply_to(message, "Sin usuarios.")
    txt = "👥 **LISTA DE CLIENTES:**\n\n"
    for uid, info in users.items():
        txt += f"• `{info.get('email')}` | ID: `{uid}`\n"
    bot.reply_to(message, txt, parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🎥 **SunTV Admin**\n\nEnvía un link para empezar.\nUsa `/buscar` para gestionar clientes.")

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("🤖 Bot iniciado...")
    bot.infinity_polling(skip_pending=True)






