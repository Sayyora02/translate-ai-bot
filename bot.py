import os
import sqlite3
from threading import Thread
import telebot
from telebot import types
import google.generativeai as genai
from flask import Flask

# TOKEN VA SOZLAMALAR (O'zingiznikini qo'ying)
BOT_TOKEN = "8952654425:AAEdEI9S4DFFO1trKPa8GqFUwbv-nVANWd4"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ADMIN_ID = 6295909661  # Telegram ID raqamingizni yozing!

# Botni ishga tushirish
bot = telebot.TeleBot(BOT_TOKEN)

# Sun'iy intellektni (Gemini) sozlash
genai.configure(api_key=GEMINI_API_KEY, transport="rest")
ai_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=(
        "Siz universal va aqlli Translate AI botisiz. Foydalanuvchi matn, rasm, PDF yoki ovoz "
        "yuborganda uni tahlil qiling. Agar imlo xatolari bo'lsa, foydalanuvchining asl maqsadini "
        "tushunib, xatoni to'g'rilang va maqsadli tilga tarjima qiling. "
        "Matn tarkibidagi tildan boshqa tilga o'giring (Masalan: o'zbekcha bo'lsa inglizchaga, "
        "inglizcha bo'lsa o'zbekchaga). Javob faqat tarjima va aniqlangan matndan iborat bo'lsin, "
        "ortiqcha izohlar qo'shmang."
    )
)

# Ma'lumotlar bazasini yaratish va ulash
conn = sqlite3.connect("bot_users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)
""")
conn.commit()

# Foydalanuvchi tillarini saqlash uchun lug'at (Eski kodingizdan)
user_languages = {}
ALL_LANGS = {
    "uz": ("uz", "O'zbekcha 🇺🇿"),
    "en": ("en", "Inglizcha 🇬🇧"),
    "ru": ("ru", "Ruscha 🇷🇺")
}

# --- KLAVIATURALAR ---
def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(text=lang[1], callback_data=code) for code, lang in ALL_LANGS.items()]
    markup.add(*buttons)
    return markup

def get_reply_keyboard(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_help = types.KeyboardButton("✍️ Adminga savol yo'llash")
    markup.add(btn_help)
    if is_admin:
        btn_stat = types.KeyboardButton("📊 Statistika")
        markup.add(btn_stat)
    return markup


# --- BUYRUQLAR VA KONTROLLERLAR ---

# 1. START BUYRUG'I (Chiroyli tushuntirish va yo'riqnoma bilan)
@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    username = message.from_user.username

    try:  
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))  
        conn.commit()  
    except Exception as e:  
        print(f"Bazaga yozishda xato: {e}")      
    
    is_admin = (user_id == ADMIN_ID)
    
    salom_matni = (
        "👋 Translate AI botiga xush kelibsiz!\n\n"
        "🤖 Bu shunchaki tarjimon emas, balki Sun'iy Intellekt bilan ishlaydigan universal yordamchidir!\n\n"
        "✨ Bot nimalar qila oladi?\n"
        "➡️ Matn tarjimasi: Istalgan so'zni xato yozsangiz ham bot o'zi to'g'rilab tarjima qiladi.\n"
        "📸 Rasm tarjimasi: Rasmli matnlarni yuboring, ularni matnga aylantirib, tarjima qilib beradi.\n"
        "📄 PDF tarjimasi: PDF kitob yoki hujjat yuboring, ichidagi matnlarni tarjima qiladi.\n"
        "🎙 Ovozli xabar: Ovozli xabar yuboring, bot uni matnga o'giradi va tarjima qiladi.\n\n"
        "🌐 *Boshlash uchun pastdagi tugmalardan tarjima tilini tanlang:* "
    )
    bot.reply_to(message, salom_matni, parse_mode="Markdown", reply_markup=get_main_keyboard())
    # Asosiy menyu tugmalarini chiqarish
    bot.send_message(message.chat.id, "Pastdagi menyudan foydalanishingiz mumkin 👇", reply_markup=get_reply_keyboard(is_admin))

# 2. LANG BUYRUG'I
@bot.message_handler(commands=['lang'])
def change_language(message):
    bot.reply_to(message, "🔄 Yangi tarjima tilini tanlang:", reply_markup=get_main_keyboard())
    # 3. STATISTIKA BUYRUG'I (Matnlardan TEPADA turishi shart)
@bot.message_handler(func=lambda m: m.text == "📊 Statistika" or m.text == "/stat")
def send_stats(message):
    if message.from_user.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        bot.reply_to(message, f"📊 Bot statistikasi:\n\n👥 Jami foydalanuvchilar: {total_users} ta", parse_mode="Markdown")  
    else:  
        bot.reply_to(message, "Bu buyruq faqat bot admini uchun! ❌")

# 4. ADMINGA SAVOL YO'LLASH LOGIKASI
@bot.message_handler(func=lambda m: m.text == "✍️ Adminga savol yo'llash")
def ask_admin(message):
    msg = bot.reply_to(message, "📝 Adminga yubormoqchi bo'lgan xabaringiz yoki savolingizni yozib yuboring:")
    bot.register_next_step_handler(msg, forward_to_admin)

def forward_to_admin(message):
    if message.text:
        user_info = f"📩 Yangi xabar!\nKimdan: @{message.from_user.username} (ID: {message.from_user.id})\n\n"
        bot.send_message(ADMIN_ID, user_info + f"Matn: {message.text}", parse_mode="Markdown")
        bot.reply_to(message, "✅ Xabaringiz adminga muvaffaqiyatli yetkazildi!")
    else:
        bot.reply_to(message, "⚠️ Faqat matnli xabar yuborishingiz mumkin.")

# 5. RASM QABUL QILISH VA AI ORQALI O'QISH
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_chat_action(message.chat.id, 'typing')
    msg_wait = bot.reply_to(message, "📸 Rasm qabul qilindi. AI matnni aniqlamoqda... ⏳")
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image_data = {"mime_type": "image/jpeg", "data": downloaded_file}
        prompt = "Rasmdagi barcha yozuvlarni aniq ko'chirib ber va uni o'zbek/ingliz tiliga tarjima qil."
        
        response = ai_model.generate_content([prompt, image_data])
        bot.delete_message(message.chat.id, msg_wait.message_id)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, "❌ Rasmdagi matnni o'qishda xatolik yuz berdi.")

# 6. OVOZLI XABARLARNI (VOICE) QABUL QILISH VA TARJIMA QILISH
@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    bot.send_chat_action(message.chat.id, 'typing')
    msg_wait = bot.reply_to(message, "🎙 Ovozli xabar tahlil qilinmoqda... ⏳")
    
    try:
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        audio_data = {"mime_type": "audio/ogg" if message.voice else "audio/mp3", "data": downloaded_file}
        prompt = "Ushbu ovozli xabarni matnga o'gir (transcribe) va uni tarjima qilib ber."
        
        response = ai_model.generate_content([prompt, audio_data])
        bot.delete_message(message.chat.id, msg_wait.message_id)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, "❌ Ovozni qayta ishlashda xatolik yuz berdi.")

# 7. HUSUSIYAT: HJJATLAR VA PDF TARJIMASI
@bot.message_handler(content_types=['document'])
def handle_document(message):
    bot.send_chat_action(message.chat.id, 'typing')
    msg_wait = bot.reply_to(message, "📄 Hujjat yuklanmoqda va tarjima qilinmoqda... ⏳")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        doc_data = {"mime_type": "application/pdf", "data": downloaded_file}
        prompt = "Ushbu hujjat/pdf ichidagi matnlarni aniqla va tarjima qilib ber."
        
        response = ai_model.generate_content([prompt, doc_data])
        bot.delete_message(message.chat.id, msg_wait.message_id)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, "❌ Hujjatni o'qishda xatolik yuz berdi. Faqat kichikroq o'lchamdagi PDF fayllarni yuboring.")
        # 8. ODDIY MATNLAR VA AI TARJIMA (ENG PASTDA TURISHI SHART)
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')

    try:  
        # Gemini AI matnni xatolarini to'g'rilab tarjima qiladi
        response = ai_model.generate_content(message.text)
        bot.reply_to(message, response.text)  
    except Exception as e:  
        bot.reply_to(message, "❌ Tarjimada xatolik yuz berdi. Qayta urinib ko'ring.")

# --- CALLBACKS (Eski kodingizdan olingan qism) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id

    if call.data in ALL_LANGS:  
        user_languages[chat_id] = ALL_LANGS[call.data]  
        lang_name = ALL_LANGS[call.data][1]  
          
        tasdiq_matni = (  
            f"✅ Tarjima tili o'rnatildi: {lang_name}\n\n"  
            f"📝 Menga istalgan matn, rasm, ovoz yoki PDF yuboring, men uni AI yordamida tarjima qilaman."  
        )  
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=tasdiq_matni, parse_mode="Markdown")  
        bot.answer_callback_query(call.id, f"{lang_name} tanlandi!")


# --- FLASK SERVER (RENDER UCHUN KEEP-ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Men uyg'oqman!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()


# --- LOYIHANI ISHGA TUSHIRISH ---
if __name__ == "__main__":
    keep_alive()  # Kichik veb-serverni fonda ishga tushiradi
    print("Veb-server yondi! Bot yuklanmoqda...")
    bot.infinity_polling()