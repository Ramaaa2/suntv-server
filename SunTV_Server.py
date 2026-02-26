import os
import threading
import json
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# ===== CONFIG =====
TOKEN = "8756442233:AAGiQseBVPNjv9qTJyBQVdmAQZVYG8gf870"
API_KEY = "f09d3949989a5e5812e964098939c381"

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ SunTV Bot activo"

# ===== BOT =====
async def recolectar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Generando catálogo SunTV...")

    try:
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={API_KEY}&language=es-MX&page=1"
        data = requests.get(url, timeout=20).json()

        peliculas = []

        for peli in data.get("results", []):
            titulo = peli.get("title")
            peli_id = peli.get("id")
            poster = f"https://image.tmdb.org/t/p/w500{peli.get('poster_path')}"
            video = f"https://vidsrc.to/embed/movie/{peli_id}"

            peliculas.append({
                "titulo": titulo,
                "urlPortada": poster,
                "urlVideo": video,
                "calidad": "1080p",
                "categoria": "Tendencias"
            })

        with open("lista_suntv.json", "w", encoding="utf-8") as f:
            json.dump(peliculas, f, indent=2, ensure_ascii=False)

        await update.message.reply_document(
            document=open("lista_suntv.json", "rb"),
            filename="lista_suntv.json",
            caption=f"✅ Catálogo generado ({len(peliculas)} pelis)"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

def iniciar_bot():
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("recolectar", recolectar))
    app_bot.run_polling()

# ===== MAIN =====
if __name__ == "__main__":
    threading.Thread(target=iniciar_bot).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)






