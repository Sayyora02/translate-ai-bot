import os
import sqlite3
import telebot
from telebot import types
import google.generativeai as genai
from flask import Flask, request

# 1. Sozlamalar
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ADMIN_ID = 6295909661
RENDER_URL = "https://translate-ai-bot.onrender.com" 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(name)

# 2. AI va Baza
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel("gemini-1.5-flash")

conn = sqlite3.connect("bot_users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT)")
conn.commit()

# 3. Funksiyalar (Sizniki o'zgarishsiz qoldi)
def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    langs = [("uz", "O'zbekcha 🇺🇿"), ("en", "Inglizcha 🇬🇧"), ("ru", "Ruscha 🇷🇺")]
    buttons = [types.InlineKeyboardButton(text=l[1], callback_data=l[0]) for l in langs]
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['start'])
def start_message(message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", 
                   (message.from_user.id, message.from_user.username))
    conn.commit()
    bot.reply_to(message, "👋 Xush kelibsiz! Tilni tanlang:", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['stat'])
def send_stats(message):
    if message.from_user.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        bot.reply_to(message, f"👥 Jami foydalanuvchilar: {cursor.fetchone()[0]} ta")

# Rasm, Ovoz, PDF funksiyalari (Sizning kodingizdagi mantig'i bilan)
@bot.message_handler(content_types=['photo', 'voice', 'document'])
def handle_media(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        # Faylni yuklash va AIga yuborish
        file_id = message.photo[-1].file_id if message.photo else (message.voice.file_id if message.voice else message.document.file_id)
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        response = ai_model.generate_content(["Ushbu faylni tarjima qilib ber.", {"mime_type": "image/jpeg", "data": downloaded_file}])
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, "❌ Xatolik yuz berdi.")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        response = ai_model.generate_content(message.text)
        bot.reply_to(message, response.text)
    except:
        bot.reply_to(message, "❌ Tarjimada xatolik.")

# 4. WEBHOOK (Render uchun yagona to'g'ri yo'l)
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "Bot ishlamoqda!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)