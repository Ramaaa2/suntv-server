import telebot
import os
import json
import random
import string
import requests
import time
from flask import Flask, redirect
from threading import Thread
import firebase_admin
from firebase_admin import credentials, db, auth
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE RENDER Y VARIABLES GLOBALES ---
# Usamos os.environ para que tus llaves no queden expuestas en el historial de GitHub
TOKEN = os.environ.get('TOKEN', '8685460740:AAEFnbdbd7T0VTARP8f5Y3X1zF4_jtAqpDQ') 
FIREBASE_URL = os.environ.get('FIREBASE_URL', 'https://suntv-app-33e92-default-rtdb.firebaseio.com/')
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', 'f89f1b10ba76c14e544f07a1473f7d08')
ADMIN_IDS = [8090944258]

user_links = {}
pending_saves = {}

GENEROS_TMDB = {
    28: "Acción", 12: "Aventura", 16: "Animación", 35: "Comedia", 80: "Crimen",
    99: "Documental", 18: "Drama", 10751: "Familia", 14: "Fantasía", 36: "Historia",
    27: "Terror", 10402: "Música", 9648: "Misterio", 10749: "Romance",
    878: "Ciencia Ficción", 10770: "Película de TV", 53: "Suspenso", 10752: "Bélica", 37: "Western",
    10759: "Acción y Aventura", 10762: "Infantil", 10765: "Sci-Fi & Fantasía", 10768: "Guerra y Política"
}

# --- CONEXIÓN FIREBASE ---
try:
    firebase_config = os.environ.get('FIREBASE_CONFIG')
    if not firebase_admin._apps:
        if firebase_config:
            # Si estás en Render, cargamos el JSON desde la variable de entorno
            cred_dict = json.loads(firebase_config)
            cred = credentials.Certificate(cred_dict)
        else:
            # Si estás local, busca el archivo físico
            cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
    print("✅ Firebase Conectado con éxito")
except Exception as e:
    print(f"❌ Error al conectar Firebase: {e}")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- RUTAS WEB ---
@app.route('/')
def home():
    return "<h1>SunTV Server Online</h1><p>Vigilante de Peticiones y API de carga activos.</p>"

@app.route('/watch/<file_id>')
def stream_video(file_id):
    try:
        file_info = bot.get_file(file_id)
        return redirect(f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}")
    except:
        return "Error al reproducir", 404

# --- VIGILANTE DE PEDIDOS DE PELÍCULAS ---
def escuchar_peticiones(event):
    try:
        if event.data and isinstance(event.data, dict):
            # Caso 1: Un solo pedido nuevo
            if event.path != '/':
                key = event.path.replace('/', '')
                procesar_peticion(key, event.data)
            # Caso 2: Carga inicial con múltiples pedidos
            else:
                for key, datos in event.data.items():
                    procesar_peticion(key, datos)
    except Exception as e:
        print(f"Error en el vigilante: {e}")

def procesar_peticion(key, datos):
    if not isinstance(datos, dict): return
    pedido = datos.get('pedido', 'Desconocido')
    usuario = datos.get('usuario', 'Desconocido')
    
    mensaje = f"🍿 **¡NUEVO PEDIDO DE PELÍCULA!** 🍿\n━━━━━━━━━━━━━━━━━━━━\n👤 **Usuario:** `{usuario}`\n🎬 **Quiere ver:** {pedido}"
    
    try:
        bot.send_message(ADMIN_IDS[0], mensaje, parse_mode="Markdown")
        # Borramos el pedido de Firebase para no repetir notificaciones
        db.reference(f'Peticiones/{key}').delete()
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")

# --- COMANDOS DE GESTIÓN ---
@bot.message_handler(commands=['vender'])
def vender(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        args = message.text.split()
        if len(args) < 3: return bot.reply_to(message, "❌ Uso: `/vender [email] [celular] [pantallas]`")
        email, celular = args[1], args[2]
        pantallas = int(args[3]) if len(args) > 3 else 1
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        user = auth.create_user(email=email, password=password)
        vencimiento_dt = datetime.now() + timedelta(days=30)
        
        db.reference(f'Usuarios/{user.uid}').set({
            'email': email, 'celular': celular, 'estado': 'ACTIVO',
            'vencimiento': vencimiento_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'limite_pantallas': pantallas,
            'perfiles': {"perfil_1": {"nombre": "Principal", "avatar": "https://api.dicebear.com/7.x/bottts/png?seed=Principal&backgroundColor=E50914"}},
            'sessions': {}
        })
        
        bot.reply_to(message, f"✨ **CUENTA ACTIVADA**\n📧 `{email}`\n🔑 `{password}`\n📅 Vence: {vencimiento_dt.strftime('%d/%m/%Y')}", parse_mode="Markdown")
    except Exception as e: bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['buscar'])
def buscar_usuario(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        query = message.text.split()[1].lower()
        usuarios = db.reference('Usuarios').get()
        if not usuarios: return bot.reply_to(message, "No hay usuarios registrados.")
        encontrados = ""
        for uid, info in usuarios.items():
            if query in info.get('email', '').lower() or query in info.get('celular', ''):
                estado = "✅" if info.get('estado') == "ACTIVO" else "🎁" if info.get('estado') == "DEMO" else "🚫"
                encontrados += f"{estado} `{info.get('email')}`\nID: `{uid}`\n\n"
        bot.reply_to(message, encontrados if encontrados else "❌ Sin coincidencias.", parse_mode="Markdown")
    except: bot.reply_to(message, "❌ Uso: /buscar [email]")

# --- SISTEMA DE CARGA TMDB ---
@bot.message_handler(func=lambda m: m.text and m.text.startswith("http") and "dicebear" not in m.text)
def detectar_link(message):
    if message.from_user.id not in ADMIN_IDS: return
    user_links[message.from_user.id] = message.text.strip()
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🎬 PELÍCULA", callback_data="tipo_Peli"),
               telebot.types.InlineKeyboardButton("📺 SERIE", callback_data="tipo_Serie"))
    bot.reply_to(message, "¡Link detectado! ¿Qué quieres subir?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("tipo_"))
def procesar_tipo(call):
    tipo = call.data.replace("tipo_", "")
    msg = bot.send_message(call.message.chat.id, "📝 Escribí el nombre (Ej: Batman 2026):")
    bot.register_next_step_handler(msg, lambda m: preparar_guardado(m, user_links.get(call.from_user.id), tipo))

def obtener_tmdb(nombre):
    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={nombre}&language=es-ES"
    try:
        r = requests.get(url).json()
        if r['results']:
            m = r['results'][0]
            saga_nombre = ""
            if m.get('media_type') == 'movie' or 'title' in m:
                url_detalle = f"https://api.themoviedb.org/3/movie/{m.get('id')}?api_key={TMDB_API_KEY}&language=es-ES"
                det_r = requests.get(url_detalle).json()
                coleccion = det_r.get('belongs_to_collection')
                if coleccion: saga_nombre = coleccion.get('name', '')

            ids = m.get('genre_ids', [])
            genero = ", ".join([GENEROS_TMDB.get(i, "") for i in ids if i in GENEROS_TMDB]) or "General"
            return {"descripcion": m.get('overview', 'Sin desc.'), "urlPortada": f"https://image.tmdb.org/t/p/w500{m.get('poster_path')}",
                    "genero": genero, "saga": saga_nombre}
    except: pass
    return None

def preparar_guardado(message, url, tipo):
    chat_id = message.chat.id
    nombre_full = message.text
    nombre_limpio = nombre_full.split("-")[0].replace("2026", "").strip()
    info = obtener_tmdb(nombre_limpio)
    
    cat_base = f"Serie, {info['genero']}" if info and tipo == "Serie" else (info['genero'] if info else "General")
    
    datos = {
        "tipo": tipo, "titulo": nombre_full, "descripcion": info['descripcion'] if info else "Sin desc.",
        "urlPortada": info['urlPortada'] if info else "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
        "urlVideo": url, "calidad": "1080p HD", "categoria": f"2026, {cat_base}" if "2026" in nombre_full else cat_base,
        "saga": info['saga'] if info else "", "nombre_carpeta": nombre_limpio.replace(" ", "_")
    }
    pending_saves[chat_id] = datos
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("✅ Guardar", callback_data="accion_guardar"),
               telebot.types.InlineKeyboardButton("❌ Cancelar", callback_data="accion_cancelar"))
    bot.send_photo(chat_id, datos['urlPortada'], caption=f"🎬 **Confirmar:** {datos['titulo']}\n📚 **Saga:** {datos['saga']}", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("accion_"))
def accion_preview(call):
    if call.data == "accion_guardar":
        datos = pending_saves.pop(call.message.chat.id, None)
        if not datos: return
        payload = {k:v for k,v in datos.items() if k not in ['tipo', 'nombre_carpeta']}
        if datos['tipo'] == "Serie":
            db.reference(f"series/{datos['nombre_carpeta']}/capitulos").push(payload)
            db.reference(f"series/{datos['nombre_carpeta']}/info").set({"titulo": datos['titulo'].split("-")[0].strip(), "urlPortada": datos['urlPortada'], "categoria": datos['categoria']})
        else:
            ref = db.reference('peliculas')
            actuales = ref.get() or []
            if isinstance(actuales, dict): actuales = list(actuales.values())
            actuales.append(payload)
            ref.set(actuales)
        bot.edit_message_caption("✅ ¡Publicado con éxito!", chat_id=call.message.chat.id, message_id=call.message.message_id)
    else:
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "🚀 **SunTV Cloud Bot Online**\nUsa /vender o manda un link para empezar.")

# --- INICIO ---
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    def iniciar_vigilante():
        time.sleep(10) # Espera a que Render estabilice la red
        print("👀 Vigilante encendido...")
        db.reference('Peticiones').listen(escuchar_peticiones)

    Thread(target=iniciar_vigilante).start()
    Thread(target=run_flask).start()
    bot.infinity_polling(skip_pending=True)
