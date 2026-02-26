import os
import threading
import json
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

TOKEN = "8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870"
# Tu clave personal de TMDB insertada aquí:
API_KEY = "f89f1b10ba76c14e544f07a1473f7d08"

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Motor SunTV API Activo"

async def recolectar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("COMANDO RECIBIDO: /recolectar")
    await update.message.reply_text("⏳ Generando catálogo de películas desde tu API personal...")

    try:
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={API_KEY}&language=es-MX&page=1"
        respuesta = requests.get(url)
        data = respuesta.json()

        # Verificamos si la API nos dio acceso correctamente
        if "results" not in data:
            mensaje_error = data.get("status_message", "Error desconocido en la API.")
            await update.message.reply_text(f"⚠️ Error de TMDB:\n{mensaje_error}")
            return

        peliculas = []

        # Recolectamos las películas
        for peli in data["results"]:
            peliculas.append({
                "titulo": peli["title"],
                "urlPortada": f"https://image.tmdb.org/t/p/w500{peli['poster_path']}",
                "urlVideo": f"https://embed.su/embed/movie/{peli['id']}",
                "calidad": "1080p",
                "categoria": "Tendencias"
            })

        # Guardamos el JSON localmente
        with open("lista_suntv.json", "w", encoding="utf-8") as f:
            json.dump(peliculas, f, indent=2, ensure_ascii=False)

        # Te enviamos el documento por Telegram
        with open("lista_suntv.json", "rb") as doc:
            await update.message.reply_document(
                document=doc, 
                caption=f"✅ ¡Catálogo SunTV listo!\nSe encontraron {len(peliculas)} películas en alta calidad."
            )
            
    except Exception as e:
        print(f"Error en la recolección: {e}")
        await update.message.reply_text("❌ Hubo un error técnico al conectarse a la base de datos.")

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    
    print("Iniciando Bot de Telegram...")
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("recolectar", recolectar))
    app_bot.run_polling()







