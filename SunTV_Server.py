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

# 🌟 ========================================== 🌟
# 🛡️ CONFIGURACIÓN SEGURA PARA NUBE / GITHUB 🛡️
# 🌟 ========================================== 🌟

# Usamos os.environ para que los hackers no vean tus contraseñas si leen tu GitHub
TOKEN = os.environ.get('TOKEN', '8685460740:AAEFnbdbd7T0VTARP8f5Y3X1zF4_jtAqpDQ') 
FIREBASE_URL = os.environ.get('FIREBASE_URL', 'https://suntv-app-33e92-default-rtdb.firebaseio.com/')
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', 'f89f1b10ba76c14e544f07a1473f7d08')

# 🛡️ SEGURIDAD ESTRICTA: Solo tu cuenta de Telegram puede usar el bot
ADMIN_IDS = [8090944258]

# Diccionarios temporales de trabajo
user_links = {}
pending_saves = {}
admin_states = {} # Memoria temporal para preguntas del panel

GENEROS_TMDB = {
    28: "Acción", 12: "Aventura", 16: "Animación", 35: "Comedia", 80: "Crimen",
    99: "Documental", 18: "Drama", 10751: "Familia", 14: "Fantasía", 36: "Historia",
    27: "Terror", 10402: "Música", 9648: "Misterio", 10749: "Romance",
    878: "Ciencia Ficción", 10770: "Película de TV", 53: "Suspenso", 10752: "Bélica", 37: "Western",
    10759: "Acción y Aventura", 10762: "Infantil", 10765: "Sci-Fi & Fantasía", 10768: "Guerra y Política"
}

# --- CONEXIÓN FIREBASE (SOPORTA LOCAL Y NUBE) ---
try:
    firebase_config = os.environ.get('FIREBASE_CONFIG')
    if not firebase_admin._apps:
        if firebase_config:
            # Si el bot está en la nube (Render), lee el JSON oculto
            cred_dict = json.loads(firebase_config)
            cred = credentials.Certificate(cred_dict)
        else:
            # Si lo estás corriendo en tu PC para pruebas
            cred = credentials.Certificate("firebase-key.json")
            
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
    print("✅ Firebase Conectado con éxito")
except Exception as e:
    print(f"❌ Error crítico al conectar Firebase: {e}")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- RUTAS WEB PARA MANTENER EL SERVIDOR DESPIERTO ---
@app.route('/')
def home():
    return "<h1>SunTV Cloud Server</h1><p>Sistemas de seguridad, Bot y API activos 24/7.</p>"

@app.route('/watch/<file_id>')
def stream_video(file_id):
    try:
        file_info = bot.get_file(file_id)
        return redirect(f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}")
    except:
        return "Error al reproducir el video", 404

# 🌟 ========================================== 🌟
# 🤖 HILOS DE FONDO (TRABAJADORES INVISIBLES)   🤖
# 🌟 ========================================== 🌟

# 1. VIGILANTE DE PEDIDOS DE PELÍCULAS
def escuchar_peticiones(event):
    try:
        if event.data and isinstance(event.data, dict):
            if event.path != '/':
                # Nuevo pedido individual
                key = event.path.replace('/', '')
                procesar_peticion(key, event.data)
            else:
                # Carga de varios pedidos acumulados
                for key, datos in event.data.items():
                    procesar_peticion(key, datos)
    except Exception as e:
        print(f"Error en el vigilante de peticiones: {e}")

def procesar_peticion(key, datos):
    if not isinstance(datos, dict): return
    pedido = datos.get('pedido', 'Desconocido')
    usuario = datos.get('usuario', 'Desconocido')
    
    mensaje = (f"🍿 **¡NUEVO PEDIDO DE PELÍCULA!** 🍿\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"👤 **Usuario:** `{usuario}`\n"
               f"🎬 **Quiere ver:** {pedido}")
    try:
        bot.send_message(ADMIN_IDS[0], mensaje, parse_mode="Markdown")
        db.reference(f'Peticiones/{key}').delete() # Borra de la base para no repetir
    except Exception as e: 
        print(f"Error avisando a Telegram: {e}")

# 2. RUTINA DE LIMPIEZA AUTOMÁTICA (EL BASURERO)
def limpiar_demos_vencidas():
    try:
        usuarios = db.reference('Usuarios').get()
        if not usuarios: return
        
        ahora = datetime.now()
        borrados = 0
        
        for uid, info in usuarios.items():
            estado = info.get('estado', '')
            
            # Borra las cuentas DEMO y PROMO que ya caducaron
            if estado.startswith("DEMO") or estado == "PROMO":
                v_str = info.get('vencimiento', '')
                try:
                    v_dt = datetime.strptime(v_str, '%Y-%m-%d %H:%M:%S')
                    # Damos 2 minutos de cortesía extra
                    if ahora > (v_dt + timedelta(minutes=2)):
                        db.reference(f'Usuarios/{uid}').delete()
                        try: auth.delete_user(uid)
                        except: pass
                        borrados += 1
                except: pass
                
        if borrados > 0:
            bot.send_message(ADMIN_IDS[0], f"🧹 *Limpieza Cloud:* `{borrados}` cuentas vencidas eliminadas automáticamente.", parse_mode="Markdown")
    except Exception as e: 
        print(f"Error en rutina de limpieza: {e}")

def bucle_limpieza():
    while True:
        limpiar_demos_vencidas()
        time.sleep(600) # Revisa silenciosamente cada 10 minutos

# 🌟 ========================================== 🌟
# 🎛️ PANEL DE CONTROL INTERACTIVO TELEGRAM      🎛️
# 🌟 ========================================== 🌟

@bot.message_handler(commands=['start', 'panel'])
def mostrar_panel(message):
    # 🛡️ SEGURIDAD: Expulsar intrusos
    if message.from_user.id not in ADMIN_IDS: return
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn_vender = telebot.types.InlineKeyboardButton("💰 Vender Cuenta", callback_data="cmd_vender")
    btn_promo = telebot.types.InlineKeyboardButton("🎁 Crear Promo (14d)", callback_data="cmd_promo") 
    btn_demo = telebot.types.InlineKeyboardButton("⏱️ Crear Demo", callback_data="cmd_demo_menu")
    btn_buscar = telebot.types.InlineKeyboardButton("🔍 Buscar/Renovar", callback_data="cmd_buscar")
    btn_stats = telebot.types.InlineKeyboardButton("📊 Estadísticas", callback_data="cmd_stats")
    btn_check = telebot.types.InlineKeyboardButton("📺 Check Serie", callback_data="cmd_check")
    btn_borrar = telebot.types.InlineKeyboardButton("🗑️ Borrar Peli", callback_data="cmd_borrar")
    btn_novedad = telebot.types.InlineKeyboardButton("📢 Novedad", callback_data="cmd_novedad")
    btn_posters = telebot.types.InlineKeyboardButton("🖼️ Arreglar Posters HD", callback_data="cmd_posters")
    btn_envivo = telebot.types.InlineKeyboardButton("🟢 Auditoría En Vivo", callback_data="cmd_envivo")
    
    markup.add(btn_vender, btn_promo, btn_demo, btn_buscar, btn_stats, btn_check, btn_borrar, btn_novedad, btn_posters, btn_envivo)
    
    texto = ("🎛 *PANEL SUNTV CLOUD* 🎛\n\n"
             "¡Hola Jefe! Todo encriptado y seguro.\n"
             "Tocá un botón para administrar o mandame un link de película para agregar al catálogo.")
    
    bot.reply_to(message, texto, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cmd_"))
def procesar_comandos_panel(call):
    cid = call.message.chat.id
    if call.from_user.id not in ADMIN_IDS: return
    
    cmd = call.data.replace("cmd_", "")
    bot.answer_callback_query(call.id) # Evita que el botón de Telegram quede cargando
    
    if cmd == "vender":
        admin_states[cid] = {}
        msg = bot.send_message(cid, "📝 Escribí el *EMAIL* del nuevo cliente:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_vender_email)
        
    elif cmd == "promo":
        admin_states[cid] = {}
        msg = bot.send_message(cid, "🎁 Escribí el *EMAIL* del promotor (14 días gratis):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_promo_email)
        
    elif cmd == "demo_menu":
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("⏳ 30 Minutos", callback_data="demo_30"),
                   telebot.types.InlineKeyboardButton("🚀 1 Hora", callback_data="demo_60"))
        bot.send_message(cid, "⏱️ *SELECTOR DE DEMO*\nElige el tiempo para el usuario:", reply_markup=markup, parse_mode="Markdown")
        
    elif cmd == "buscar":
        msg = bot.send_message(cid, "🔍 Escribí el *EMAIL o CELULAR* a buscar:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_buscar)
        
    elif cmd == "stats": 
        ejecutar_stats(cid)
        
    elif cmd == "check":
        msg = bot.send_message(cid, "📺 Escribí el *NOMBRE* de la serie a revisar:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_check)
        
    elif cmd == "borrar":
        msg = bot.send_message(cid, "🗑️ Escribí el *NOMBRE EXACTO* de la película o serie a borrar:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_borrar)
        
    elif cmd == "novedad":
        msg = bot.send_message(cid, "📢 Escribí el *MENSAJE* que saldrá en la app (o escribe 'apagar'):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_novedad)
        
    elif cmd == "posters": 
        actualizar_posters_hd(cid)
        
    elif cmd == "envivo": 
        ejecutar_auditoria_envivo(cid)

# --- FLUJOS DE CREACIÓN DE CUENTAS ---
def step_vender_email(message):
    cid = message.chat.id
    admin_states[cid]['email'] = message.text.strip()
    msg = bot.send_message(cid, "📱 Escribí el *CELULAR* del cliente:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_vender_celular)

def step_vender_celular(message):
    cid = message.chat.id
    admin_states[cid]['celular'] = message.text.strip()
    msg = bot.send_message(cid, "💻 ¿Cuántas *PANTALLAS* le vas a vender? (Ej: 1, 2, 3):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_vender_final)

def step_vender_final(message):
    cid = message.chat.id
    try: 
        pantallas = int(message.text.strip())
    except: 
        return bot.send_message(cid, "❌ Venta cancelada, debes enviar un número válido.")
        
    email = admin_states[cid]['email']
    celular = admin_states[cid]['celular']
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    vencimiento_dt = datetime.now() + timedelta(days=30)
    
    try:
        user = auth.create_user(email=email, password=password)
        perfiles_dict = {}
        colores = ["E50914", "0071EB", "00A65A", "F39C12", "8E44AD"] 
        for i in range(1, pantallas + 1):
            n = "Principal" if i == 1 else f"Perfil {i}"
            c = colores[(i-1) % len(colores)]
            perfiles_dict[f"perfil_{i}"] = {"nombre": n, "avatar": f"https://api.dicebear.com/7.x/bottts/png?seed={n}{random.randint(1,100)}&backgroundColor={c}"}
        
        db.reference(f'Usuarios/{user.uid}').set({
            'email': email, 'celular': celular, 'estado': 'ACTIVO',
            'vencimiento': vencimiento_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'limite_pantallas': pantallas, 'perfiles': perfiles_dict, 'sessions': {}
        })
        
        ticket = (f"✨ **ACTIVACIÓN EXITOSA** ✨\n"
                  f"📧 **Usuario:** `{email}`\n"
                  f"🔑 **Clave:** `{password}`\n"
                  f"💻 **Pantallas:** `{pantallas}`\n"
                  f"📅 **Vence:** `{vencimiento_dt.strftime('%d/%m/%Y')}`")
        bot.send_message(cid, ticket, parse_mode="Markdown")
    except Exception as e: 
        bot.send_message(cid, f"❌ Error de Firebase: {e}")

def step_promo_email(message):
    cid = message.chat.id
    admin_states[cid]['email'] = message.text.strip()
    msg = bot.send_message(cid, "📱 Escribí su *CELULAR*:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_promo_final)

def step_promo_final(message):
    cid = message.chat.id
    email = admin_states[cid]['email']
    celular = message.text.strip()
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    vencimiento_dt = datetime.now() + timedelta(days=14) # 14 días exactos
    
    try:
        user = auth.create_user(email=email, password=password)
        db.reference(f'Usuarios/{user.uid}').set({
            'email': email, 'celular': celular, 'estado': 'PROMO',
            'vencimiento': vencimiento_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'limite_pantallas': 1, 
            'perfiles': {"perfil_1": {"nombre": "Promotor", "avatar": "https://api.dicebear.com/7.x/bottts/png?seed=Promo&backgroundColor=F39C12"}}, 
            'sessions': {}
        })
        
        ticket = (f"🤝 **CUENTA EMBAJADOR CREADA**\n"
                  f"📧 `{email}`\n"
                  f"🔑 `{password}`\n"
                  f"⏰ Vence: `{vencimiento_dt.strftime('%d/%m/%Y')}`")
        bot.send_message(cid, ticket, parse_mode="Markdown")
    except Exception as e: 
        bot.send_message(cid, f"❌ Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("demo_"))
def callback_demo_duracion(call):
    minutos = int(call.data.replace("demo_", ""))
    bot.answer_callback_query(call.id)
    try:
        id_demo = random.randint(100, 999)
        email = f"demo{id_demo}@suntv.com"
        password = ''.join(random.choices(string.digits, k=6))
        vencimiento_dt = datetime.now() + timedelta(minutes=minutos)
        estado_demo = "DEMO1H" if minutos == 60 else "DEMO"
        
        user = auth.create_user(email=email, password=password)
        db.reference(f'Usuarios/{user.uid}').set({
            'email': email, 'estado': estado_demo, 'vencimiento': vencimiento_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'limite_pantallas': 1, 
            'perfiles': {"perfil_1": {"nombre": "Invitado", "avatar": "https://api.dicebear.com/7.x/bottts/png?seed=Guest&backgroundColor=808080"}}, 
            'sessions': {}
        })
        
        titulo = "🚀 DEMO 1 HORA" if minutos == 60 else "🎁 DEMO 30 MIN"
        ticket = (f"**{titulo}**\n"
                  f"📧 `{email}`\n"
                  f"🔑 `{password}`\n"
                  f"⏰ Vence: `{vencimiento_dt.strftime('%H:%M')} hs`")
        bot.send_message(call.message.chat.id, ticket, parse_mode="Markdown")
    except Exception as e: 
        bot.send_message(call.message.chat.id, f"❌ Error: {e}")

# --- BUSCADOR Y SISTEMA DE PREMIOS (CAJA REGISTRADORA) ---
def step_buscar(message):
    query = message.text.lower().strip()
    try:
        users = db.reference('Usuarios').get()
        encontrado = False
        
        if users:
            for uid, info in users.items():
                if query in info.get('email', '').lower() or query in info.get('celular', ''):
                    encontrado = True
                    s = info.get('sessions', {})
                    res = (f"👤 `{info.get('email')}`\n"
                           f"📅 Vence: `{info.get('vencimiento')}`\n"
                           f"📱 Pantallas: `{len(s)}/{info.get('limite_pantallas', 1)}`\n"
                           f"🚦 Estado: `{info.get('estado')}`")
                           
                    # Botones de renovación y premio
                    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
                    markup.add(telebot.types.InlineKeyboardButton("+7 Días", callback_data=f"premio_7_{uid}"),
                               telebot.types.InlineKeyboardButton("+15 Días", callback_data=f"premio_15_{uid}"),
                               telebot.types.InlineKeyboardButton("+30 Días", callback_data=f"premio_30_{uid}"))
                               
                    bot.send_message(message.chat.id, res, reply_markup=markup, parse_mode="Markdown")
                    
        if not encontrado: 
            bot.send_message(message.chat.id, "❌ Sin resultados en la base de datos.")
    except Exception as e: 
        bot.send_message(message.chat.id, f"❌ Error en búsqueda: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("premio_"))
def aplicar_premio_referido(call):
    partes = call.data.split("_")
    dias = int(partes[1])
    uid = partes[2]
    
    try:
        ref = db.reference(f'Usuarios/{uid}')
        user_data = ref.get()
        if not user_data: 
            return bot.answer_callback_query(call.id, "Error: El usuario no existe.")
            
        # Calcula el nuevo vencimiento
        f_actual_str = user_data.get('vencimiento', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        f_actual = datetime.strptime(f_actual_str, '%Y-%m-%d %H:%M:%S')
        ahora = datetime.now()
        
        # Si la cuenta ya había vencido, suma los días desde HOY. Si no, se los suma a su saldo restante.
        fecha_base = ahora if f_actual < ahora else f_actual
        nueva_fecha = fecha_base + timedelta(days=dias)
        
        ref.update({
            'vencimiento': nueva_fecha.strftime('%Y-%m-%d %H:%M:%S'), 
            'estado': 'ACTIVO' # Se convierte en cliente oficial blindado
        })
        
        bot.answer_callback_query(call.id, f"¡Sumados {dias} días!")
        mensaje = (f"✅ **DÍAS ACREDITADOS**\n"
                   f"La cuenta `{user_data['email']}` sumó {dias} días.\n"
                   f"📅 Nuevo vencimiento: `{nueva_fecha.strftime('%d/%m/%Y')}`")
        bot.edit_message_text(mensaje, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    except Exception as e: 
        bot.answer_callback_query(call.id, "Error interno del servidor Firebase.")

# --- HERRAMIENTAS DE AUDITORÍA Y ESTADÍSTICAS ---
def ejecutar_auditoria_envivo(cid):
    try:
        users = db.reference('Usuarios').get()
        conectados = 0
        texto = "🟢 *USUARIOS CONECTADOS AHORA*\n━━━━━━━━━━━━━━━━━━━━\n"
        
        if users:
            for uid, info in users.items():
                s = info.get('sessions', {})
                if s:
                    conectados += 1
                    for sid, sdata in s.items(): 
                        texto += f"👤 `{info.get('email')}`\n📱 Equipo: `{sdata.get('modelo', 'TV/Celu')}`\n\n"
                        
        if conectados == 0: 
            bot.send_message(cid, "😴 Nadie conectado viendo películas ahora mismo.")
        else: 
            bot.send_message(cid, f"{texto}Total Activos: `{conectados}`", parse_mode="Markdown")
    except Exception as e: 
        bot.send_message(cid, f"❌ Error de auditoría: {e}")

def ejecutar_stats(cid):
    try:
        p = db.reference('peliculas').get() or []
        s = db.reference('series').get() or {}
        
        tot_p = len(p) if isinstance(p, list) else len(p.keys())
        tot_s = len(s.keys())
        tot_c = sum([len(d.get('capitulos', {})) for d in s.values()])
        
        mensaje = (f"📊 *ESTADÍSTICAS DEL CATÁLOGO*\n\n"
                   f"🎬 Películas: `{tot_p}`\n"
                   f"📺 Series: `{tot_s}`\n"
                   f"📂 Capítulos totales: `{tot_c}`")
        bot.send_message(cid, mensaje, parse_mode="Markdown")
    except Exception as e: 
        bot.send_message(cid, "❌ Error al leer la base de datos.")

def step_check(message):
    nombre = message.text.strip()
    try:
        caps = db.reference(f'series/{nombre.replace(" ", "_")}/capitulos').get()
        if not caps: return bot.send_message(message.chat.id, f"⚠️ No encontré la serie {nombre}.")
        if isinstance(caps, dict): caps = list(caps.values())
        
        temps = {}
        for c in caps:
            if not c: continue
            tit = c.get('titulo', '')
            t = tit.split("-")[1].strip().split("x")[0] if "-" in tit and "x" in tit else "1"
            temps[t] = temps.get(t, 0) + 1
            
        res = f"📺 *Check de Serie:* {nombre}\n\n"
        for t, cant in sorted(temps.items()): 
            res += f"🔹 Temporada {t}: {cant} episodios\n"
        bot.send_message(message.chat.id, res, parse_mode="Markdown")
    except Exception as e: 
        bot.send_message(message.chat.id, "❌ Error leyendo capítulos.")

def step_borrar(message):
    nombre = message.text.strip()
    try:
        ref = db.reference('peliculas')
        p = ref.get()
        if p:
            if isinstance(p, list):
                ref.set([x for x in p if x and x.get('titulo') != nombre])
            elif isinstance(p, dict):
                for k, v in p.items():
                    if v.get('titulo') == nombre: 
                        db.reference(f'peliculas/{k}').delete()
                        
        db.reference(f'series/{nombre.replace(" ", "_")}').delete()
        bot.send_message(message.chat.id, f"🗑️ Se eliminó correctamente: {nombre}")
    except Exception as e: 
        bot.send_message(message.chat.id, "❌ Error al intentar borrar.")

def step_novedad(message):
    txt = message.text.strip()
    if txt.lower() == "apagar":
        db.reference('configuracion/ultima_novedad').delete()
        bot.send_message(message.chat.id, "🔇 Novedad apagada. Ya no saldrá el cartel en la app.")
    else:
        db.reference('configuracion/ultima_novedad').set({"mensaje": txt, "fecha": datetime.now().strftime('%d/%m/%Y')})
        bot.send_message(message.chat.id, "✅ Novedad enviada. Saldrá en las pantallas de todos los usuarios.")

def actualizar_posters_hd(cid):
    bot.send_message(cid, "🖼️ Iniciando actualización masiva de Pósters a resolución HD (1280px) y Sagas...")
    def proceso_hd():
        try:
            p_cont = 0
            pelis = db.reference('peliculas').get()
            if pelis:
                items = pelis.items() if isinstance(pelis, dict) else enumerate(pelis)
                for k, p in items:
                    if p and 'titulo' in p:
                        nombre_limpio = p['titulo'].split("-")[0].replace("2026", "").strip()
                        info = obtener_tmdb(nombre_limpio)
                        if info:
                            # Reemplaza w500 por w1280 para forzar máxima calidad
                            url_hd = info['urlPortada'].replace("w500", "w1280")
                            db.reference(f'peliculas/{k}').update({"urlPortada": url_hd, "saga": info['saga']})
                            p_cont += 1
            bot.send_message(cid, f"✅ ¡FIN DEL PROCESO! Se actualizaron {p_cont} películas a HD.")
        except Exception as e: 
            bot.send_message(cid, f"❌ Error actualizando HD: {e}")
            
    Thread(target=proceso_hd).start()

# 🌟 ========================================== 🌟
# 🎥 SISTEMA DE CARGA DE LINKS (TMDB API)       🎥
# 🌟 ========================================== 🌟

@bot.message_handler(func=lambda m: m.text and m.text.startswith("http") and "dicebear" not in m.text)
def detectar_link(message):
    if message.from_user.id not in ADMIN_IDS: return
    user_links[message.from_user.id] = message.text.strip()
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🎬 PELÍCULA", callback_data="tipo_Peli"),
               telebot.types.InlineKeyboardButton("📺 SERIE", callback_data="tipo_Serie"))
    bot.reply_to(message, "¡Link de video detectado! ¿Qué contenido quieres subir?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("tipo_"))
def procesar_tipo(call):
    tipo = call.data.replace("tipo_", "")
    msg = bot.send_message(call.message.chat.id, "📝 Escribí el nombre exacto (Ej: Batman 2026 o Serie - 1x01):")
    bot.register_next_step_handler(msg, lambda m: preparar_guardado(m, user_links.get(call.from_user.id), tipo))

def obtener_tmdb(nombre):
    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={nombre}&language=es-ES"
    try:
        r = requests.get(url).json()
        if r['results']:
            m = r['results'][0]
            saga_nombre = ""
            
            # Buscar si pertenece a una saga o colección
            if m.get('media_type') == 'movie' or 'title' in m:
                det_url = f"https://api.themoviedb.org/3/movie/{m.get('id')}?api_key={TMDB_API_KEY}&language=es-ES"
                det_r = requests.get(det_url).json()
                if det_r.get('belongs_to_collection'): 
                    saga_nombre = det_r['belongs_to_collection'].get('name', '')
                    
            generos_list = [GENEROS_TMDB.get(i, "") for i in m.get('genre_ids', []) if i in GENEROS_TMDB]
            genero_final = ", ".join(generos_list) if generos_list else "General"
            
            return {
                "descripcion": m.get('overview', 'Sin descripción disponible.'), 
                "urlPortada": f"https://image.tmdb.org/t/p/w1280{m.get('poster_path')}", 
                "genero": genero_final, 
                "saga": saga_nombre
            }
    except: pass
    return None

def preparar_guardado(message, url, tipo):
    cid = message.chat.id
    n_full = message.text
    n_limpio = n_full.split("-")[0].replace("2026", "").strip()
    
    bot.send_message(cid, "🔍 Buscando póster en HD y descripción en la base de datos TMDB...")
    info = obtener_tmdb(n_limpio)
    
    cat_base = f"Serie, {info['genero']}" if info and tipo == "Serie" else (info['genero'] if info else "General")
    
    datos = {
        "tipo": tipo, 
        "titulo": n_full, 
        "descripcion": info['descripcion'] if info else "Sin descripción.",
        "urlPortada": info['urlPortada'] if info else "https://i.postimg.cc/sgf0p9Lz/Canal-E.png",
        "urlVideo": url, 
        "calidad": "1080p HD", 
        "categoria": f"2026, {cat_base}" if "2026" in n_full else cat_base,
        "saga": info['saga'] if info else "", 
        "nombre_carpeta": n_limpio.replace(" ", "_")
    }
    
    pending_saves[cid] = datos
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("✅ Publicar", callback_data="accion_guardar"),
               telebot.types.InlineKeyboardButton("❌ Cancelar", callback_data="accion_cancelar"))
               
    preview = (f"🎬 **VISTA PREVIA**\n\n"
               f"📌 **Título:** {datos['titulo']}\n"
               f"📚 **Saga:** {datos['saga'] if datos['saga'] else 'Ninguna'}\n"
               f"🏷️ **Categoría:** {datos['categoria']}")
               
    bot.send_photo(cid, datos['urlPortada'], caption=preview, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("accion_"))
def accion_preview(call):
    if call.data == "accion_guardar":
        datos = pending_saves.pop(call.message.chat.id, None)
        if not datos: return
        
        payload = {k:v for k,v in datos.items() if k not in ['tipo', 'nombre_carpeta']}
        
        if datos['tipo'] == "Serie":
            db.reference(f"series/{datos['nombre_carpeta']}/capitulos").push(payload)
            db.reference(f"series/{datos['nombre_carpeta']}/info").set({
                "titulo": datos['titulo'].split("-")[0].strip(), 
                "urlPortada": datos['urlPortada'], 
                "categoria": datos['categoria']
            })
        else:
            ref = db.reference('peliculas')
            act = ref.get() or []
            if isinstance(act, dict): act = list(act.values())
            act.append(payload)
            ref.set(act)
            
        bot.edit_message_caption("✅ ¡Contenido publicado en la App con éxito!", chat_id=call.message.chat.id, message_id=call.message.message_id)
    else: 
        bot.delete_message(call.message.chat.id, call.message.message_id)

# 🌟 ========================================== 🌟
# 🚀 ARRANQUE DE LA APLICACIÓN (RENDER CLOUD)   🚀
# 🌟 ========================================== 🌟

def run_flask():
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=puerto)

if __name__ == "__main__":
    def procesos_fondo():
        # Espera a que Render estabilice la conexión de red
        time.sleep(10) 
        print("👀 Hilos de fondo encendidos y listos...")
        
        # Inicia el vigilante de pedidos de películas
        db.reference('Peticiones').listen(escuchar_peticiones)
        
        # Inicia el basurero automático
        bucle_limpieza() 

    # Arrancamos los hilos secundarios sin bloquear el bot
    Thread(target=procesos_fondo, daemon=True).start()
    Thread(target=run_flask).start()
    
    # Arrancamos el Bot de Telegram de forma continua
    bot.infinity_polling(skip_pending=True)
