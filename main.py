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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            answer_key TEXT
        )
    """)
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

# /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == TEACHER_ID:
        await update.message.reply_text(
            "Assalomu alaykum, ustoz Shaxriyor!\n\n"
            "👨‍🏫 **O'qituvchi boshqaruv paneli**\n\n"
            "✍️ Test savollarini yuborish uchun shunchaki matn yuboring yoki `/setquestions [matn]` buyrug'idan foydalaning.\n"
            "🔑 Kalit yuklash uchun: `/setanswers 503,360,12,...`\n"
            "⏱ Timer o'rnatish uchun: `/settimer 30`\n"
            "🏆 Reytingni ko'rish uchun: `/rating`",
            parse_mode="Markdown"
        )
    else:
        # O'quvchi uchun: bazadan savol va kalitni o'qib olamiz
        conn = sqlite3.connect("test_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT question_text FROM questions LIMIT 1")
        row = cursor.fetchone()
        
        cursor.execute("SELECT answer_key FROM answers LIMIT 1")
        key_row = cursor.fetchone()
        conn.close()

        if not row or not key_row:
            await update.message.reply_text(
                "⚠️ Hozircha o'qituvchi tomonidan test savollari yoki kalitlari kiritilmagan. Biroz kuting!"
            )
            return

        q_text = row[0]

        await update.message.reply_text(
            f"Assalomu alaykum! Test savollari quyidagicha:\n\n"
            f"📋 **Test savollari:**\n{q_text}\n\n"
            f"✍️ Javoblaringizni har birini alohida qatorda (Enter bosib) yoki vergul bilan yuboring.",
            parse_mode="Markdown"
        )

# Test savollarini yuklash (/setquestions)
async def set_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != TEACHER_ID:
        await update.message.reply_text("Bu buyruq faqat o'qituvchi uchun!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Xato! Savol matnini kiriting.")
        return

    text = " ".join(context.args)
    conn = sqlite3.connect("test_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions")
    cursor.execute("INSERT INTO questions (question_text) VALUES (?)", (text,))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Test savollari muvaffaqiyatli saqlandi!")

# Test kalitlarini o'rnatish (/setanswers)
async def set_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != TEACHER_ID:
        await update.message.reply_text("Bu buyruq faqat o'qituvchi uchun!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Xato! Kalitlarni kiriting: `/setanswers 503,360,12,...`", parse_mode="Markdown")
        return

    key = context.args[0]
    conn = sqlite3.connect("test_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM answers")
    cursor.execute("INSERT INTO answers (answer_key) VALUES (?)", (key,))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Test kalitlari saqlandi!\nKalit: `{key}`", parse_mode="Markdown")

# Timer o'rnatish (/settimer)
async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != TEACHER_ID:
        await update.message.reply_text("Bu buyruq faqat o'qituvchi uchun!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Vaqtni kiriting. Masalan: `/settimer 30`", parse_mode="Markdown")
        return

    time_val = context.args[0]
    await update.message.reply_text(f"⏱ Timer {time_val} daqiqaga o'rnatildi!")

# Xabarlarni qabul qilish (O'qituvchi yuborgan savol yoki o'quvchi javobi)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id == TEACHER_ID:
        # O'qituvchi to'g'ridan-to'g'ri matn yuborsa ham savol sifatida saqlaymiz
        conn = sqlite3.connect("test_bot.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM questions")
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
            await update.message.reply_text("⚠️ Hozircha o'qituvchi test kalitlarini kiritmagan.")
            conn.close()
            return

        correct_key = [k.strip().lower() for k in row[0].replace(" ", "").split(",")]
        
        clean_text = text.replace("\r", "")
        if "," in clean_text:
            user_answers = [a.strip().lower() for a in clean_text.replace(" ", "").split(",")]
        else:
            user_answers = [a.strip().lower() for a in clean_text.split("\n") if a.strip()]
        
        score = 0
        for i in range(min(len(correct_key), len(user_answers))):
            if correct_key[i] == user_answers[i]:
                score += 1
                
        total = len(correct_key)
        
        username = update.effective_user.username or update.effective_user.first_name
        cursor.execute("INSERT OR REPLACE INTO results (user_id, username, score, total) VALUES (?, ?, ?, ?)",
                       (user_id, username, score, total))
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"📊 **Sizning natijangiz:**\n"
            f"To'g'ri javoblar: {score} / {total}"
        )

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
    app.add_handler(CommandHandler("setquestions", set_questions))
    app.add_handler(CommandHandler("setanswers", set_answers))
    app.add_handler(CommandHandler("settimer", set_timer))
    app.add_handler(CommandHandler("rating", rating))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
