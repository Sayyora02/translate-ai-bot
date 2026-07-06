import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot onlayn rejimda ishlamoqda!"

def run():
    # Render beradigan portni avtomatik aniqlaydi
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from deep_translator import GoogleTranslator

# O'zingizning maxfiy tokengingizni yozing
TOKEN = "8952654425:AAEdEI9S4DFFO1trKPa8GqFUwbv-nVANWd4"
bot = telebot.TeleBot(TOKEN)

# Foydalanuvchilarning tanlagan tillarini eslab qolish uchun lug'at
user_languages = {}

# 1-sahifa: Eng ommabop tillar
MAIN_LANGS = {
    "to_uz": ("uz", "🇺🇿 O'zbekcha"),
    "to_en": ("en", "🇬🇧 English"),
    "to_ru": ("ru", "🇷🇺 Русский"),
    "to_tr": ("tr", "🇹🇷 Türkçe"),
    "to_ko": ("ko", "🇰🇷 Koreyscha"),
    "to_ar": ("ar", "🇦🇪 Arabcha")
}

# 2-sahifa: Qo'shimcha tillar (Boshqa tillar tugmasi bosilganda)
EXTRA_LANGS = {
    "to_de": ("de", "🇩🇪 Nemischa"),
    "to_fr": ("fr", "🇫🇷 Fransuzcha"),
    "to_es": ("es", "🇪🇸 Ispancha"),
    "to_zh": ("zh-CN", "🇨🇳 Xitoycha"),
    "to_ja": ("ja", "🇯🇵 Yaponcha"),
    "to_it": ("it", "🇮🇹 Italiyancha"),
    "to_fa": ("fa", "🇮🇷 Forscha"),
    "to_tg": ("tg", "🇹🇯 Tojikcha"),
    "to_kk": ("kk", "🇰🇿 Qozoqcha"),
    "to_ky": ("ky", "🇰🇬 Qirg'izcha"),
    "to_az": ("az", "🇦🇿 Ozarbayjoncha"),
    "to_hi": ("hi", "🇮🇳 Hindcha"),
    "to_id": ("id", "🇮🇩 Indonezcha"),
    "to_ms": ("ms", "🇲🇾 Malayziyancha"),
    "to_nl": ("nl", "🇳🇱 Gollandcha"),
    "to_pl": ("pl", "🇵🇱 Polyakcha"),
    "to_pt": ("pt", "🇵🇹 Portugalcha"),
    "to_sv": ("sv", "🇸🇪 Shvedcha"),
    "to_uk": ("uk", "🇺🇦 Ukraincha"),
    "to_vi": ("vi", "🇻🇳 Vyetnamcha"),
    "to_hi": ("hi", "🇮🇳 Hindcha"),
    "to_ur": ("ur", "🇵🇰 Pokistoncha (Urdu)")
}

# Barcha tillarni bitta umumiy lug'atga birlashtiramiz
ALL_LANGS = {**MAIN_LANGS, **EXTRA_LANGS}

# Menu sozlamalari
def set_bot_menu():
    commands = [
        BotCommand("start", "Botni qayta ishga tushirish"),
        BotCommand("lang", "Tarjima tilini o'zgartirish")
    ]
    bot.set_my_commands(commands)

# Asosiy tillar klaviaturasi
def get_main_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="to_uz"), InlineKeyboardButton("🇬🇧 English", callback_data="to_en"))
    markup.row(InlineKeyboardButton("🇷🇺 Русский", callback_data="to_ru"), InlineKeyboardButton("🇹🇷 Türkçe", callback_data="to_tr"))
    markup.row(InlineKeyboardButton("🇰🇷 Koreyscha", callback_data="to_ko"), InlineKeyboardButton("🇦🇪 Arabcha", callback_data="to_ar"))
    markup.row(InlineKeyboardButton("🌐 Boshqa tillar... 👉", callback_data="more_languages"))
    return markup

# Qo'shimcha tillar klaviaturasi (Sahifalangan)
def get_extra_keyboard():
    markup = InlineKeyboardMarkup()
    # Tillarni 2 tadan qator qilib joylashtiramiz
    items = list(EXTRA_LANGS.keys())
    for i in range(0, len(items), 2):
        row_buttons = []
        row_buttons.append(InlineKeyboardButton(EXTRA_LANGS[items[i]][1], callback_data=items[i]))
        if i+1 < len(items):
            row_buttons.append(InlineKeyboardButton(EXTRA_LANGS[items[i+1]][1], callback_data=items[i+1]))
        markup.row(*row_buttons)
    
    markup.row(InlineKeyboardButton("👈 Orqaga", callback_data="back_to_main"))
    return markup

@bot.message_handler(commands=['start'])
def start_message(message):
    salom_matni = "👋 Translate AI botiga xush kelibsiz!\n\n🌍 Matnlarni qaysi tilga tarjima qilishni tanlang:"
    bot.reply_to(message, salom_matni, parse_mode="Markdown", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['lang'])
def change_language(message):
    bot.reply_to(message, "🔄 Yangi tarjima tilini tanlang:", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    if chat_id not in user_languages:
        bot.reply_to(message, "⚠️ Tarjima tilini tanlamagansiz!\nIltimos, tilni tanlang:", reply_markup=get_main_keyboard())
        return
    target_lang, lang_name = user_languages[chat_id]
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(message.text)
        javob = f"🌍 Tarjima ({lang_name}):\n\n{translated}"
        bot.reply_to(message, javob, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "❌ Tarjimada xatolik yuz berdi. Qayta urinib ko'ring.")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    
    # "Boshqa tillar" tugmasi bosilganda
    if call.data == "more_languages":
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🌐 Qo'shimcha tillardan birini tanlang:", reply_markup=get_extra_keyboard())
        bot.answer_callback_query(call.id)
        return
        
    # "Orqaga" tugmasi bosilganda
    if call.data == "back_to_main":
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🌍 Matnlarni qaysi tilga tarjima qilishni tanlang:", reply_markup=get_main_keyboard())
        bot.answer_callback_query(call.id)
        return

    # Til tugmalari bosilganda
    if call.data in ALL_LANGS:
        user_languages[chat_id] = ALL_LANGS[call.data]
        lang_name = ALL_LANGS[call.data][1]
        
        tasdiq_matni = (
            f"✅ Tarjima tili o'rnatildi: {lang_name}\n\n"
            f"📝 Endi menga istalgan matnni yuboring, men uni to'g'ridan-to'g'ri shu tilga o'girib beraman."
        )
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=tasdiq_matni, parse_mode="Markdown")
        bot.answer_callback_query(call.id, f"{lang_name} tanlandi!")

set_bot_menu()
print("Translate AI: Ko'p tilli versiya ishga tushdi...")
keep_alive()
bot.infinity_polling()