
import sqlite3
import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Loggingni sozlash
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Konfiguratsiya
TOKEN = os.environ.get("TOKEN", "9078968898:AAHsT8Kt4iQAyYbxEM0v6AMWXj3XI4MCSdU")
TEACHER_ID = 8691474457  # O'qituvchining Telegram ID si

# Bazani sozlash
def init_db():
    conn = sqlite3.connect("test_bot.db")
    cursor = conn.cursor()
    # Savollar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT
        )
    """)
    # Kalitlar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            answer_key TEXT
        )
    """)
    # Natijalar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            score INTEGER,
            total INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Holatni saqlash uchun oddiy flag (o'qituvchi test yuboryaptimi yoki yo'q)
teacher_state = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == TEACHER_ID:
        await update.message.reply_text(
            "Assalomu alaykum, ustoz Shaxriyor!\n\n"
            "👨‍🏫 **O'qituvchi boshqaruv paneli**ga xush kelibsiz. Kerakli amalni tanlang:\n\n"
            "✍️ Test savollarini yuborish uchun **Testni yuklash** tugmasini bosing yoki shunchaki matn yuboring.\n"
            "🔑 Kalit yuklash uchun: `/setanswers abcd...` formatidan foydalaning.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "Assalomu alaykum! Testni yechish uchun o'z javoblaringizni yuboring."
        )

# Test kalitlarini o'rnatish (/setanswers)
async def set_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != TEACHER_ID:
        await update.message.reply_text("Bu buyruq faqat o'qituvchi uchun!")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ Xato! Format quyidagicha bo'lishi kerak:\n`/setanswers 42,72,55,9,...` yoki `abccb...`",
            parse_mode="Markdown"
        )
        return

    key = context.args[0]
    
    conn = sqlite3.connect("test_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM answers") # Eskisini o'chirish
    cursor.execute("INSERT INTO answers (answer_key) VALUES (?)", (key,))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Test kalitlari muvaffaqiyatli saqlandi!\nKalit: `{key}`", parse_mode="Markdown")

# Matnli xabarlarni qabul qilish (Savollarni saqlash yoki o'quvchi javobini tekshirish)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id == TEACHER_ID:
        # O'qituvchi test savollarini yuboryapti deb qabul qilamiz
        conn = sqlite3.connect("test_bot.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM questions") # Oldingi savol matnini tozalash
        cursor.execute("INSERT INTO questions (question_text) VALUES (?)", (text,))
        conn.commit()
        conn.close()

        await update.message.reply_text("✅ Test savollari muvaffaqiyatli saqlandi! Endi kalitlarni `/setanswers` orqali kiriting.")
    else:
        # O'quvchi javob yuboryapti
        conn = sqlite3.connect("test_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT answer_key FROM answers LIMIT 1")
        row = cursor.fetchone()
        
        if not row:
            await update.message.reply_text("⚠️ Hozircha o'qituvchi tomonidan test kalitlari kiritilmagan.")
            conn.close()
            return

        correct_key = row[0].split(",") # Vergul bilan ajratilgan deb qaraymiz
        user_answers = text.replace(" ", "").split(",")
        
        score = 0
        for i in range(min(len(correct_key), len(user_answers))):
            if correct_key[i].strip().lower() == user_answers[i].strip().lower():
                score += 1
                
        total = len(correct_key)
        
        # Natijani saqlash
        username = update.effective_user.username or update.effective_user.first_name
        cursor.execute("INSERT OR REPLACE INTO results (user_id, username, score, total) VALUES (?, ?, ?, ?)",
                       (user_id, username, score, total))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"📊 Sizning natijangiz:\nTo'g'ri javoblar: {score} / {total}")

# Reytingni ko'rsatish (/rating)
async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("test_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, score, total FROM results ORDER BY score DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Hozircha natijalar mavjud emas.")
        return

    text = "🏆 **O'quvchilar reytingi:**\n\n"
    for idx, (uname, score, total) in enumerate(rows, 1):
        text += f"{idx}. {uname} — {score}/{total} ta\n"

    await update.message.reply_text(text, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setanswers", set_answers))
    app.add_handler(CommandHandler("rating", rating))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
