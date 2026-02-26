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
    return "SunTV Bot activo"

async def recolectar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("COMANDO RECIBIDO")  # 👈 ver en logs

    await update.message.reply_text("Generando catálogo...")

    url = f"https://api.themoviedb.org/3/movie/popular?api_key={API_KEY}&language=es-MX&page=1"
    data = requests.get(url).json()

    peliculas = []

    for peli in data.get("results", []):
        peliculas.append({
            "titulo": peli["title"],
            "urlPortada": f"https://image.tmdb.org/t/p/w500{peli['poster_path']}",
            "urlVideo": f"https://vidsrc.to/embed/movie/{peli['id']}"
        })

    with open("lista_suntv.json", "w", encoding="utf-8") as f:
        json.dump(peliculas, f, indent=2, ensure_ascii=False)

    await update.message.reply_document(open("lista_suntv.json", "rb"))

def run_bot():
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("recolectar", recolectar))
    print("BOT INICIADO")
    app_bot.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), use_reloader=False)






