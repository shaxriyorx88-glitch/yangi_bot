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

TOKEN = os.environ.get("TOKEN", "9078968898:AAHsT8Kt4iQAyYbxEM0v6AMWXj3XI4MCSdU")
TEACHER_ID = 8691474457  # O'qituvchi ID si

# Bazani yaratish
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
            "Assalomu alaykum, Ustoz!\n\n"
            "📋 **O'qituvchi buyruqlari:**\n"
            "• `/savol [raqam] [matn]` — Test savollarini kiritish\n"
            "*(Misol: `/savol 1 1-savol matni...`)*\n\n"
            "• `/javob [raqam] [kalit]` — Test kalitini kiritish\n"
            "*(Misol: `/javob 1 a,b,c,d`)*\n\n"
            "• `/timer [minut]` — Vaqt belgilash\n"
            "• `/rating` — Reytingni ko'rish",
            parse_mode="Markdown"
        )
    else:
        conn = sqlite3.connect("test_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT test_id, question_text FROM questions ORDER BY rowid DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row:
            await update.message.reply_text("⚠️ Hozircha o'qituvchi test kiritmagan.")
            return

        test_id, q_text = row
        await update.message.reply_text(
            f"Test raqami: <b>{test_id}</b>\n\n"
            f"<b>Savollar:</b>\n{q_text}\n\n"
            f"Javoblaringizni vergul bilan (`a, b, c`) yoki pastma-past (`1 a`, `2 b`) qilib yuboring.",
            parse_mode="HTML"
        )

# /savol buyrug'i
async def set_savol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != TEACHER_ID:
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Xato! Ishlatish: `/savol 1 Savollar matni...`", parse_mode="Markdown")
        return

    test_id = context.args[0]
    text = " ".join(context.args[1:])

    conn = sqlite3.connect("test_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO questions (test_id, question_text) VALUES (?, ?)", (test_id, text))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ {test_id}-sonli test savollari saqlandi!")

# /javob buyrug'i
async def set_javob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != TEACHER_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Xato! Ishlatish: `/javob 1 a,b,c,d`", parse_mode="Markdown")
        return

    test_id = context.args[0]
    key = context.args[1]

    conn = sqlite3.connect("test_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO answers (test_id, answer_key) VALUES (?, ?)", (test_id, key))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ {test_id}-sonli test kaliti saqlandi: `{key}`", parse_mode="Markdown")

# /timer buyrug'i
async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != TEACHER_ID:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Xato! Ishlatish: `/timer 30`", parse_mode="Markdown")
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
        await context.bot.send_message(chat_id=chat_id, text="⏰ Vaqt tugadi!")

    asyncio.create_task(timer_task())

# /rating buyrug'i
async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("test_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, score, total FROM results ORDER BY score DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Hozircha natijalar yo'q.")
        return

    text = "🏆 **O'quvchilar reytingi:**\n\n"
    for idx, (uname, score, total) in enumerate(rows, 1):
        text += f"{idx}. {uname} — {score}/{total}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

# Xabarlarni qabul qilish (O'quvchi javoblari)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == TEACHER_ID:
        return  # O'qituvchi matn yuborsa e'tibor bermaymiz, buyruqdan foydalanadi

    text = update.message.text
    conn = sqlite3.connect("test_bot.db")
    cursor = conn.cursor()
    
    # Eng oxirgi kiritilgan test kalitini qidiramiz (o'qituvchi xohlagan payt oldin kalit yoki savol kiritgan bo'lishidan qat'i nazar)
    cursor.execute("SELECT test_id, answer_key FROM answers ORDER BY rowid DESC LIMIT 1")
    row = cursor.fetchone()
    
    if not row:
        await update.message.reply_text("⚠️ Hozircha o'qituvchi test kalitini kiritmagan. Iltimos, kuting!")
        conn.close()
        return

    test_id, raw_key = row
    
    # Tekshiramiz: shu test_id bo'yicha savollar ham mavjudmi?
    cursor.execute("SELECT question_text FROM questions WHERE test_id = ?", (test_id,))
    q_row = cursor.fetchone()
    
    if not q_row:
        await update.message.reply_text("⚠️ Bu test uchun hali savollar kiritilmagan!")
        conn.close()
        return

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
        f"📊 <b>Natijangiz (Test #{test_id}):</b>\n"
        f"To'g'ri javoblar: {score} / {total}",
        parse_mode="HTML"
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savol", set_savol))
    app.add_handler(CommandHandler("javob", set_javob))
    app.add_handler(CommandHandler("timer", set_timer))
    app.add_handler(CommandHandler("rating", rating))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
