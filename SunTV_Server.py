import telebot
import os
import json
import random
import string
import time
from flask import Flask
from threading import Thread
import firebase_admin
from firebase_admin import credentials, db, auth
from datetime import datetime, timedelta

# 🌟 ========================================== 🌟
# 🛡️ CONFIGURACIÓN SEGURA PARA NUBE / GITHUB 🛡️
# 🌟 ========================================== 🌟

TOKEN = os.environ.get('TOKEN', '8685460740:AAEFnbdbd7T0VTARP8f5Y3X1zF4_jtAqpDQ') 
FIREBASE_URL = os.environ.get('FIREBASE_URL', 'https://suntv-app-33e92-default-rtdb.firebaseio.com/')

# 🛡️ SEGURIDAD ESTRICTA: Solo tu cuenta de Telegram puede usar el bot
ADMIN_IDS = [8090944258]

# Memoria temporal para preguntas del panel
admin_states = {} 

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
    return "<h1>SunTV Gestor de Cuentas</h1><p>Sistema de administración activo 24/7.</p>"

# 🌟 ========================================== 🌟
# 🤖 RUTINA DE LIMPIEZA (EL BASURERO AUTOMÁTICO)🤖
# 🌟 ========================================== 🌟

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
            bot.send_message(ADMIN_IDS[0], f"🧹 *Limpieza Cloud:* `{borrados}` cuentas de prueba vencidas eliminadas automáticamente.", parse_mode="Markdown")
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
    if message.from_user.id not in ADMIN_IDS: return
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn_vender = telebot.types.InlineKeyboardButton("💰 Vender Cuenta", callback_data="cmd_vender")
    btn_promo = telebot.types.InlineKeyboardButton("🎁 Crear Promo (14d)", callback_data="cmd_promo") 
    btn_demo = telebot.types.InlineKeyboardButton("⏱️ Crear Demo", callback_data="cmd_demo_menu")
    btn_buscar = telebot.types.InlineKeyboardButton("🔍 Buscar / Editar Cliente", callback_data="cmd_buscar")
    btn_stats = telebot.types.InlineKeyboardButton("📊 Estadísticas de Usuarios", callback_data="cmd_stats")
    btn_envivo = telebot.types.InlineKeyboardButton("🟢 Auditoría En Vivo", callback_data="cmd_envivo")
    
    markup.add(btn_vender, btn_promo, btn_demo, btn_buscar, btn_stats, btn_envivo)
    
    texto = ("🎛 *GESTOR DE CLIENTES SUNTV* 🎛\n\n"
             "¡Hola! Sistema optimizado y listo.\n"
             "Tocá un botón para administrar las cuentas de Firebase.")
    
    bot.reply_to(message, texto, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cmd_"))
def procesar_comandos_panel(call):
    cid = call.message.chat.id
    if call.from_user.id not in ADMIN_IDS: return
    
    cmd = call.data.replace("cmd_", "")
    bot.answer_callback_query(call.id) 
    
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
    vencimiento_dt = datetime.now() + timedelta(days=14) 
    
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

# --- BUSCADOR Y EDICIÓN DE ESTADO (CAJA REGISTRADORA) ---
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
                           f"🚦 Estado actual: `{info.get('estado')}`")
                           
                    # 🚀 ACÁ ESTÁ EL NUEVO BOTÓN PREMIUM
                    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
                    markup.add(telebot.types.InlineKeyboardButton("+7 Días", callback_data=f"premio_7_{uid}"),
                               telebot.types.InlineKeyboardButton("+15 Días", callback_data=f"premio_15_{uid}"),
                               telebot.types.InlineKeyboardButton("+30 Días", callback_data=f"premio_30_{uid}"))
                    
                    markup.add(telebot.types.InlineKeyboardButton("⭐ Hacer PREMIUM", callback_data=f"premium_{uid}"))
                               
                    bot.send_message(message.chat.id, res, reply_markup=markup, parse_mode="Markdown")
                    
        if not encontrado: 
            bot.send_message(message.chat.id, "❌ Sin resultados en la base de datos.")
    except Exception as e: 
        bot.send_message(message.chat.id, f"❌ Error en búsqueda: {e}")

# Lógica para sumar días normales
@bot.callback_query_handler(func=lambda call: call.data.startswith("premio_"))
def aplicar_premio_referido(call):
    partes = call.data.split("_")
    dias = int(partes[1])
    uid = partes[2]
    
    try:
        ref = db.reference(f'Usuarios/{uid}')
        user_data = ref.get()
        if not user_data: return bot.answer_callback_query(call.id, "Error: El usuario no existe.")
            
        f_actual_str = user_data.get('vencimiento', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        f_actual = datetime.strptime(f_actual_str, '%Y-%m-%d %H:%M:%S')
        ahora = datetime.now()
        
        fecha_base = ahora if f_actual < ahora else f_actual
        nueva_fecha = fecha_base + timedelta(days=dias)
        
        ref.update({
            'vencimiento': nueva_fecha.strftime('%Y-%m-%d %H:%M:%S'), 
            'estado': 'ACTIVO'
        })
        
        bot.answer_callback_query(call.id, f"¡Sumados {dias} días!")
        mensaje = (f"✅ **DÍAS ACREDITADOS**\n"
                   f"La cuenta `{user_data['email']}` sumó {dias} días.\n"
                   f"📅 Nuevo vencimiento: `{nueva_fecha.strftime('%d/%m/%Y')}`")
        bot.edit_message_text(mensaje, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    except Exception as e: 
        bot.answer_callback_query(call.id, "Error interno del servidor Firebase.")

# 🚀 NUEVA LÓGICA: Transformar en Premium
@bot.callback_query_handler(func=lambda call: call.data.startswith("premium_"))
def aplicar_estado_premium(call):
    uid = call.data.replace("premium_", "")
    
    try:
        ref = db.reference(f'Usuarios/{uid}')
        user_data = ref.get()
        if not user_data: return bot.answer_callback_query(call.id, "Error: El usuario no existe.")
            
        # Le damos 1 año (365 días) de acceso desde hoy
        nueva_fecha = datetime.now() + timedelta(days=365)
        
        ref.update({
            'vencimiento': nueva_fecha.strftime('%Y-%m-%d %H:%M:%S'), 
            'estado': 'PREMIUM'
        })
        
        bot.answer_callback_query(call.id, "¡Cuenta ascendida a PREMIUM!")
        mensaje = (f"⭐ **CUENTA ASCENDIDA A PREMIUM** ⭐\n"
                   f"👤 Cliente: `{user_data['email']}`\n"
                   f"📅 Nuevo vencimiento: `{nueva_fecha.strftime('%d/%m/%Y')}`")
        bot.edit_message_text(mensaje, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    except Exception as e: 
        bot.answer_callback_query(call.id, "Error interno al hacer Premium.")

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
            bot.send_message(cid, "😴 Nadie conectado a la app ahora mismo.")
        else: 
            bot.send_message(cid, f"{texto}Total Activos: `{conectados}`", parse_mode="Markdown")
    except Exception as e: 
        bot.send_message(cid, f"❌ Error de auditoría: {e}")

def ejecutar_stats(cid):
    try:
        usuarios = db.reference('Usuarios').get() or {}
        
        totales = len(usuarios)
        activos = sum(1 for u in usuarios.values() if u.get('estado') == 'ACTIVO')
        premiums = sum(1 for u in usuarios.values() if u.get('estado') == 'PREMIUM')
        demos = sum(1 for u in usuarios.values() if u.get('estado', '').startswith('DEMO'))
        
        mensaje = (f"📊 *ESTADÍSTICAS DE CLIENTES*\n\n"
                   f"👥 Total Registrados: `{totales}`\n"
                   f"🟢 Clientes Activos: `{activos}`\n"
                   f"⭐ Clientes Premium: `{premiums}`\n"
                   f"⏳ Demos rodando: `{demos}`")
        bot.send_message(cid, mensaje, parse_mode="Markdown")
    except Exception as e: 
        bot.send_message(cid, "❌ Error al leer la base de datos.")

# 🌟 ========================================== 🌟
# 🚀 ARRANQUE DE LA APLICACIÓN (RENDER CLOUD)   🚀
# 🌟 ========================================== 🌟

def run_flask():
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=puerto)

if __name__ == "__main__":
    def procesos_fondo():
        time.sleep(10) 
        print("👀 Basurero de cuentas encendido...")
        bucle_limpieza() 

    # Arrancamos los hilos secundarios
    Thread(target=procesos_fondo, daemon=True).start()
    Thread(target=run_flask).start()
    
    # Arrancamos el Bot de Telegram
    bot.infinity_polling(skip_pending=True)
