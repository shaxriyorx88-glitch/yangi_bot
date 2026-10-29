
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Loggingni sozlash
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# O'qituvchining Telegram ID raqami
TEACHER_ID = 8691474457

# Vaqtinchalik ma'lumotlar bazasi
DATABASE = {
    "answers": "",          # Test kalitlari
    "results": {},          # O'quvchilar natijalari
    "timer": "O'rnatilmagan"
}

# /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if user_id == TEACHER_ID:
        keyboard = [
            [InlineKeyboardButton("📝 Kalitni yuklash", callback_data="set_key")],
            [InlineKeyboardButton("📂 Testni yuklash", callback_data="set_test")],
            [InlineKeyboardButton("⏱ Timer o'rnatish", callback_data="set_timer")],
            [InlineKeyboardButton("🏆 O'quvchilar reytingi", callback_data="show_rating")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Assalomu alaykum, ustoz {user_name}!\n\n"
            "👨‍🏫 **O'qituvchi boshqaruv paneli**ga xush kelibsiz. Kerakli amalni tanlang:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"Assalomu alaykum, {user_name}!\n\n"
            "🤖 Bu test tekshiruvchi bot.\n"
            "📝 Test topshirish uchun javoblaringizni bitta xabarda yuboring.\n"
            "🏆 Umumiy reytingni ko'rish uchun /rating buyrug'ini bosing."
        )

# Tugmalar bosilganda ishlaydigan funksiya
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data

    if data == "set_key":
        await query.message.reply_text(
            "📝 Test kalitlarini yuklash uchun quyidagi formatda yuboring:\n"
            "`/setanswers abcdab...`"
        )
    elif data == "set_test":
        await query.message.reply_text(
            "📂 Test savollarini (fayl yoki matn ko'rinishida) yuboring:"
        )
    elif data == "set_timer":
        await query.message.reply_text(
            "⏱ Timer o'rnatish uchun quyidagi formatda yuboring:\n"
            "`/settimer 45` (daqiqada)"
        )
    elif data == "show_rating":
        if not DATABASE["results"]:
            await query.message.reply_text("🏆 Hozircha reytingda o'quvchilar yo'q.")
        else:
            text = "🏆 **O'quvchilar reytingi:**\n\n"
            for idx, (uid, data_dict) in enumerate(DATABASE["results"].items(), 1):
                text += f"{idx}. {data_dict['name']} — {data_dict['score']} ball\n"
            await query.message.reply_text(text)

# Kalitlarni o'rnatish (/setanswers)
async def set_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != TEACHER_ID:
        await update.message.reply_text("⚠️ Bu buyruq faqat o'qituvchi uchun!")
        return

    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Xato! Kalitlarni kiriting. Masalan: `/setanswers abcd...`")
        return

    key = "".join(args).strip().lower()
    DATABASE["answers"] = key
    await update.message.reply_text(f"✅ Test kalitlari muvaffaqiyatli saqlandi!\nKalit: `{key}`")

# Timer o'rnatish (/settimer)
async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != TEACHER_ID:
        await update.message.reply_text("⚠️ Bu buyruq faqat o'qituvchi uchun!")
        return

    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Vaqtni kiriting. Masalan: `/settimer 30`")
        return

    timer_val = args[0]
    DATABASE["timer"] = f"{timer_val} daqiqa"
    await update.message.reply_text(f"⏱ Timer muvaffaqiyatli o'rnatildi: {timer_val} daqiqa.")

# Reytingni ko'rsatish (/rating)
async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not DATABASE["results"]:
        await update.message.reply_text("🏆 Hozircha reyting bo'sh.")
        return

    text = "🏆 **O'quvchilar reytingi:**\n\n"
    for idx, (uid, data_dict) in enumerate(DATABASE["results"].items(), 1):
        text += f"{idx}. {data_dict['name']} — {data_dict['score']} ball\n"
    await update.message.reply_text(text)

# O'quvchi javoblarini tekshirish funksiyasi
async def check_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    text = update.message.text.strip().lower()

    if user_id == TEACHER_ID:
        return

    if not DATABASE["answers"]:
        await update.message.reply_text("⚠️ Hozircha o'qituvchi tomonidan test kalitlari kiritilmagan.")
        return

    correct_key = DATABASE["answers"]
    
    score = 0
    min_len = min(len(text), len(correct_key))
    for i in range(min_len):
        if text[i] == correct_key[i]:
            score += 1

    DATABASE["results"][user_id] = {
        "name": user_name,
        "score": score
    }

    await update.message.reply_text(
        f"📊 **Sizning natijangiz:**\n"
        f"To'g'ri javoblar soni: {score} ta / Jami: {len(correct_key)} ta"
    )

def main():
    token = os.environ.get("TOKEN")
    
    if not token:
        print("Xatolik: TOKEN topilmadi!")
        return

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setanswers", set_answers))
    app.add_handler(CommandHandler("settimer", set_timer))
    app.add_handler(CommandHandler("rating", rating))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answers))

    print("Bot muvaffaqiyatli ishga tushdi...")
    app.run_polling()

if __name__ == '__main__':
    main()