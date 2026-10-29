import sqlite3
import logging
import os
import asyncio
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
            test_id TEXT PRIMARY KEY,
            question_text TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            test_id TEXT PRIMARY KEY,
            answer_key TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            user_id INTEGER,
            test_id TEXT,
            username TEXT,
            score INTEGER,
            total INTEGER,
            PRIMARY KEY (user_id, test_id)
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
            "✍️ **Test savollarini yuklash:**\n"
            "`/setquestions [test_id] [matn]` (masalan: `/setquestions 1 1-savol...`)\n\n"
            "🔑 **Kalit yuklash:**\n"
            "`/setanswers [test_id] [kalit]` (masalan: `/setanswers 1 a,b,c,503`)\n\n"
            "⏱ **Timer o'rnatish:** `/settimer 30`\n"
            "🏆 **Reytingni ko'rish:** `/rating`",
            parse_mode="Markdown"
        )
    else:
        conn = sqlite3.connect("test_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT test_id, question_text FROM questions ORDER BY rowid DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row:
            await update.message.reply_text("⚠️ Hozircha o'qituvchi tomonidan test savollari kiritilmagan.")
            return

        test_id, q_text = row
        await update.message.reply_text(
            f"Assalomu alaykum! Test ID: <b>{test_id}</b>\n\n"
            f"📋 **Test savollari:**\n{q_text}\n\n"
            f"✍️ **Javob yuborish usuli:**\n"
            f"Javoblarni vergul bilan (`a, b, c`) yoki pastma-past (`1 a`, `2 b`) qilib yuboring.",
            parse_mode="HTML"
        )

# Test savollarini yuklash (/setquestions)
async def set_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != TEACHER_ID:
        await update.message.reply_text("Bu buyruq faqat o'qituvchi uchun!")
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Xato! Format: `/setquestions [test_id] [savol matni]`", parse_mode="Markdown")
        return

    test_id = context.args[0]
    text = " ".join(context.args[1:])

    conn = sqlite3.connect("test_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO questions (test_id, question_text) VALUES (?, ?)", (test_id, text))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ {test_id}-raqamli test savollari saqlandi!")

# Test kalitlarini o'rnatish (/setanswers)
async def set_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != TEACHER_ID:
        await update.message.reply_text("Bu buyruq faqat o'qituvchi uchun!")
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Xato! Format: `/setanswers [test_id] [kalitlar]` (Masalan: `/setanswers 1 a,b,c`)", parse_mode="Markdown")
        return

    test_id = context.args[0]
    key = context.args[1]

    conn = sqlite3.connect("test_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO answers (test_id, answer_key) VALUES (?, ?)", (test_id, key))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ {test_id}-raqamli test kalitlari saqlandi!\nKalit: `{key}`", parse_mode="Markdown")

# Timer o'rnatish
async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != TEACHER_ID:
        await update.message.reply_text("Bu buyruq faqat o'qituvchi uchun!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Vaqtni daqiqada kiriting. Masalan: `/settimer 30`", parse_mode="Markdown")
        return

    try:
        minutes = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Faqat raqam kiriting!")
        return

    await update.message.reply_text(f"⏱ Timer {minutes} daqiqaga o'rnatildi.")

    chat_id = update.effective_chat.id
    async def timer_task():
        await asyncio.sleep(minutes * 60)
        await context.bot.send_message(chat_id=chat_id, text="⏰ Diqqat! Test uchun ajratilgan vaqt tugadi!")

    asyncio.create_task(timer_task())

# Xabarlarni qabul qilish (O'qituvchi matni yoki o'quvchi javobi)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id == TEACHER_ID:
        conn = sqlite3.connect("test_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT test_id FROM questions ORDER BY rowid DESC LIMIT 1")
        row = cursor.fetchone()
        test_id = row[0] if row else "1"
        
        cursor.execute("INSERT OR REPLACE INTO questions (test_id, question_text) VALUES (?, ?)", (test_id, text))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Matn {test_id}-testga saqlandi! Kalitni yuklash uchun `/setanswers {test_id} [kalit]` yuboring.")
    else:
        conn = sqlite3.connect("test_bot.db")
        cursor = conn.cursor()
        
        # Eng oxirgi test ID ni aniqlaymiz
        cursor.execute("SELECT test_id, answer_key FROM answers ORDER BY rowid DESC LIMIT 1")
        row = cursor.fetchone()
        
        if not row:
            await update.message.reply_text("⚠️ Hozircha o'qituvchi test kalitlarini kiritmagan.")
            conn.close()
            return

        test_id, raw_key = row
        correct_key = [k.strip().lower() for k in raw_key.replace(" ", "").split(",")]
        
        clean_text = text.replace("\r", "")
        user_answers = []
        
        if "," in clean_text:
            user_answers = [a.strip().lower() for a in clean_text.replace(" ", "").split(",")]
        else:
            for line in clean_text.split("\n"):
                line = line.strip()
                if line:
                    parts = line.split()
                    if len(parts) > 1 and (parts[0].endswith(")") or parts[0].isdigit()):
                        user_answers.append(parts[-1].lower())
                    else:
                        user_answers.append(line.lower())
        
        score = 0
        for i in range(min(len(correct_key), len(user_answers))):
            if correct_key[i] == user_answers[i]:
                score += 1
                
        total = len(correct_key)
        
        username = update.effective_user.username or update.effective_user.first_name
        cursor.execute("""
            INSERT OR REPLACE INTO results (user_id, test_id, username, score, total) 
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, test_id, username, score, total))
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"📊 **Test natijangiz (Test ID: {test_id}):**\n"
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
