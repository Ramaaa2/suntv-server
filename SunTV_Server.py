import telebot
import os
import json
import random
import string
import requests
from flask import Flask, redirect
from threading import Thread
import firebase_admin
from firebase_admin import credentials, db, auth
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE RENDER Y VARIABLES GLOBALES ---
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

# --- CONEXIÓN FIREBASE (Híbrida: Nube o Local) ---
try:
    firebase_config = os.environ.get('FIREBASE_CONFIG')
    if not firebase_admin._apps:
        if firebase_config:
            cred_dict = json.loads(firebase_config)
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
    print("✅ Firebase Conectado (Nube/Local)")
except Exception as e:
    print(f"❌ Error al conectar Firebase: {e}")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- RUTAS WEB (Mantiene la App viva y hace el streaming) ---
@app.route('/')
def home():
    return "<h1>SunTV Server Online</h1><p>El servidor principal y el motor de streaming están funcionando al 100%.</p>"

@app.route('/watch/<file_id>')
def stream_video(file_id):
    try:
        file_info = bot.get_file(file_id)
        return redirect(f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}")
    except:
        return "Error al reproducir", 404

# --- VIGILANTE DE PEDIDOS DE PELÍCULAS ---
def escuchar_peticiones(event):
    if event.data and isinstance(event.data, dict):
        if event.path != '/':
            datos = event.data
            pedido = datos.get('pedido', 'Desconocido')
            usuario = datos.get('usuario', 'Desconocido')
            
            mensaje = f"🍿 **¡NUEVO PEDIDO DE PELÍCULA!** 🍿\n👤 **Usuario:** `{usuario}`\n🎬 **Quiere ver:** {pedido}"
            bot.send_message(ADMIN_IDS[0], mensaje, parse_mode="Markdown")
            
            # Limpia la base de datos
            db.reference(f'Peticiones{event.path}').delete()

# --- GESTIÓN DE USUARIOS ---
@bot.message_handler(commands=['vender'])
def vender(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        args = message.text.split()
        if len(args) < 3: return bot.reply_to(message, "❌ Uso: `/vender [email] [celular] [pantallas]`", parse_mode="Markdown")

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
        
        ticket = (f"✨ **SUNTV - ACTIVACIÓN** ✨\n"
                  f"📧 User: `{email}`\n🔑 Pass: `{password}`\n"
                  f"📅 Vence: `{vencimiento_dt.strftime('%d/%m/%Y')}`")
        bot.reply_to(message, ticket, parse_mode="Markdown")
    except Exception as e: bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['demo'])
def crear_demo(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        id_demo = random.randint(100, 999)
        email, password = f"demo{id_demo}@suntv.com", ''.join(random.choices(string.digits, k=6))
        expiracion_dt = datetime.now() + timedelta(minutes=30)
        user = auth.create_user(email=email, password=password)
        
        db.reference(f'Usuarios/{user.uid}').set({
            'email': email, 'estado': 'DEMO', 'vencimiento': expiracion_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'limite_pantallas': 1, 'perfiles': {"perfil_1": {"nombre": "Invitado", "avatar": "https://api.dicebear.com/7.x/bottts/png?seed=Guest&backgroundColor=808080"}},
            'sessions': {}
        })
        ticket = f"🎁 **DEMO 30 MIN**\n📧 `{email}`\n🔑 `{password}`\n⏰ Vence: `{expiracion_dt.strftime('%H:%M')} hs`"
        bot.reply_to(message, ticket, parse_mode="Markdown")
    except Exception as e: bot.reply_to(message, f"❌ Error: {e}")

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
                estado = "✅" if info.get('estado') == "ACTIVO" else "🎁" if info.get('estado') == "DEMO" else "🚫"
                encontrados += f"{estado} `{email}`\nUID: `{uid}`\nCel: {cel}\n\n"
        bot.reply_to(message, encontrados if encontrados else "❌ Sin coincidencias.", parse_mode="Markdown")
    except: bot.reply_to(message, "❌ Uso: /buscar [email o celular]")

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

# --- SISTEMA DE CARGA DE CONTENIDO CON TMDB Y SAGAS ---
@bot.message_handler(func=lambda m: m.text and m.text.startswith("http") and "dicebear" not in m.text)
def detectar_link(message):
    if message.from_user.id not in ADMIN_IDS: return
    user_links[message.from_user.id] = message.text.strip()
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("🎬 PELÍCULA", callback_data="tipo_Peli"),
        telebot.types.InlineKeyboardButton("📺 SERIE", callback_data="tipo_Serie")
    )
    bot.reply_to(message, "¡Link detectado! ¿Qué quieres subir?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("tipo_"))
def procesar_tipo(call):
    tipo = call.data.replace("tipo_", "")
    msg = bot.send_message(call.message.chat.id, f"📝 Escribí el nombre (Ej: Batman 2026):")
    bot.register_next_step_handler(msg, lambda m: preparar_guardado(m, user_links.get(call.from_user.id), tipo))

def obtener_tmdb(nombre):
    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={nombre}&language=es-ES"
    try:
        r = requests.get(url).json()
        if r['results']:
            m = r['results'][0]
            saga_nombre = ""
            if m.get('media_type') == 'movie' or 'title' in m:
                movie_id = m.get('id')
                url_detalle = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=es-ES"
                det_r = requests.get(url_detalle).json()
                coleccion = det_r.get('belongs_to_collection')
                if coleccion and isinstance(coleccion, dict):
                    saga_nombre = coleccion.get('name', '')

            ids = m.get('genre_ids', [])
            genero_final = ", ".join([GENEROS_TMDB.get(i, "") for i in ids if i in GENEROS_TMDB]) or "General"
            desc = m.get('overview', '').strip()
            poster = m.get('poster_path')
            return {
                "descripcion": desc if desc else "Sin descripción.",
                "urlPortada": f"https://image.tmdb.org/t/p/w500{poster}" if poster else "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
                "genero": genero_final,
                "saga": saga_nombre
            }
    except: pass
    return None

def preparar_guardado(message, url, tipo):
    chat_id = message.chat.id
    nombre_full = message.text
    nombre_busqueda = nombre_full.split("-")[0].replace("2026", "").strip()
    
    info = obtener_tmdb(nombre_busqueda)
    
    desc_final = info['descripcion'] if info else "Sin descripción."
    portada_final = info['urlPortada'] if info else "https://i.postimg.cc/sgf0p9Lz/Canal-E.png"
    cat_base = f"Serie, {info['genero']}" if info and tipo == "Serie" else (info['genero'] if info else "General")
    final_cat = f"2026, {cat_base}" if "2026" in nombre_full else cat_base

    datos = {
        "tipo": tipo, "titulo": nombre_full, "descripcion": desc_final,
        "urlPortada": portada_final, "urlVideo": url, "calidad": "1080p HD",
        "categoria": final_cat, "saga": info['saga'] if info and 'saga' in info else "",
        "nombre_carpeta": nombre_busqueda.replace(" ", "_")
    }
    pending_saves[chat_id] = datos
    mostrar_preview(chat_id)

def mostrar_preview(chat_id):
    datos = pending_saves.get(chat_id)
    if not datos: return
    texto_saga = f"📚 **Saga:** `{datos['saga']}`\n" if datos.get('saga') else ""
    preview = (f"👀 **VISTA PREVIA** 👀\n\n🎬 **Título:** `{datos['titulo']}`\n{texto_saga}"
               f"🎞 **Cat:** `{datos['categoria']}`\n📝 **Desc:** {datos['descripcion'][:60]}...\n")
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("✅ Guardar", callback_data="accion_guardar"),
        telebot.types.InlineKeyboardButton("❌ Cancelar", callback_data="accion_cancelar")
    )
    bot.send_photo(chat_id, datos['urlPortada'], caption=preview, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("accion_"))
def accion_preview(call):
    chat_id = call.message.chat.id
    accion = call.data.replace("accion_", "")
    if accion == "cancelar":
        pending_saves.pop(chat_id, None)
        bot.delete_message(chat_id, call.message.message_id)
    elif accion == "guardar":
        datos = pending_saves.pop(chat_id, None)
        if not datos: return
        payload = {k:v for k,v in datos.items() if k not in ['tipo', 'nombre_carpeta']}
        if datos['tipo'] == "Serie":
            carpeta = datos['nombre_carpeta']
            db.reference(f"series/{carpeta}/capitulos").push(payload)
            db.reference(f"series/{carpeta}/info").set({"titulo": carpeta.replace("_", " "), "urlPortada": datos['urlPortada'], "categoria": datos['categoria']})
        else:
            ref = db.reference('peliculas')
            actuales = ref.get() or []
            if isinstance(actuales, dict): actuales = list(actuales.values())
            actuales.append(payload)
            ref.set(actuales)
        bot.edit_message_caption(f"✅ ¡Publicado en Firebase!", chat_id=chat_id, message_id=call.message.message_id)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ **SunTV Cloud Bot**\nServidor online y vigilante de Peticiones activo.")

# --- INICIO DEL SERVIDOR ---
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Inicia el vigilante de pedidos en la nube
    Thread(target=lambda: db.reference('Peticiones').listen(escuchar_peticiones)).start()
    # Inicia el servidor web de Render
    Thread(target=run_flask).start()
    # Inicia el bot de Telegram
    bot.infinity_polling(skip_pending=True)
