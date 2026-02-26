import os
import threading
import json
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

TOKEN = "8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870"
API_KEY = "f09d3949989a5e5812e964098939c381"

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ SunTV Bot activo y corriendo"

async def recolectar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("COMANDO RECIBIDO: /recolectar")  # Para ver en los logs de Render
    await update.message.reply_text("⏳ Generando catálogo de películas desde la API...")

    try:
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={API_KEY}&language=es-MX&page=1"
        data = requests.get(url).json()

        peliculas = []

        for peli in data.get("results", []):
            peliculas.append({
                "titulo": peli["title"],
                "urlPortada": f"https://image.tmdb.org/t/p/w500{peli['poster_path']}",
                "urlVideo": f"https://vidsrc.to/embed/movie/{peli['id']}",
                "calidad": "1080p",
                "categoria": "Tendencias"
            })

        # Guardamos el archivo
        with open("lista_suntv.json", "w", encoding="utf-8") as f:
            json.dump(peliculas, f, indent=2, ensure_ascii=False)

        # Enviamos el archivo asegurándonos de abrirlo y cerrarlo correctamente
        with open("lista_suntv.json", "rb") as doc:
            await update.message.reply_document(
                document=doc, 
                caption="✅ ¡Catálogo SunTV listo!\nCopia el contenido en tu nPoint."
            )
            
    except Exception as e:
        print(f"Error en la recolección: {e}")
        await update.message.reply_text("❌ Hubo un error técnico al conectarse a la API.")

# Movemos Flask al hilo secundario
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

if __name__ == "__main__":
    # 1. Arrancamos Flask en el fondo para que Render reconozca el puerto web
    threading.Thread(target=run_flask).start()
    
    # 2. Arrancamos el Bot en el hilo principal (Soluciona el error de asincronía)
    print("Iniciando Bot de Telegram...")
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("recolectar", recolectar))
    app_bot.run_polling()





