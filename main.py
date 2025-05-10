import os
import time
import threading
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from flask import Flask
from PIL import Image
from fpdf import FPDF
import aiohttp

# ===== إعدادات البوت =====
TOKEN = "7520587781:AAFov57Eaffq8qtILBQy1NHoBOdz1d3c1w4"
OWNER_USERNAME = "AL_hashmee"
CHANNELS = ["@tobtelegram", "@sjzbhzudmd", "@djhxbejeidhx"]

logging.basicConfig(level=logging.INFO)

user_sessions = {}
unique_users = set()

# ===== الكيبورد =====
def build_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Start"), KeyboardButton("Convert"), KeyboardButton("Clear")],
            [KeyboardButton("Stats"), KeyboardButton("Update")]
        ],
        resize_keyboard=True
    )

# ===== التحقق من الاشتراك =====
async def is_subscribed(user, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user.username == OWNER_USERNAME:
        return True
    async with aiohttp.ClientSession() as session:
        for ch in CHANNELS:
            url = f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={ch}&user_id={user.id}"
            async with session.get(url) as resp:
                data = await resp.json()
                status = data.get("result", {}).get("status")
                if status not in ("member", "administrator", "creator"):
                    return False
    return True

# ===== الأوامر =====
WELCOME = (
    "مرحباً في بوت تحويل الصور إلى PDF!\n"
    "1️⃣ أرسل صوراً (Photo أو File) ثم اضغط Convert\n"
    "2️⃣ Clear لمسح الصور المرسلة\n"
    "3️⃣ Stats لعدد المستخدمين\n"
    "4️⃣ Update لتحديث البوت\n"
)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    unique_users.add(user.id)
    if not await is_subscribed(user, context):
        await update.message.reply_text(
            "❗️ يلزمك الانضمام لهذه القنوات أولاً:\n" + "\n".join(CHANNELS)
        )
        return
    await update.message.reply_text(WELCOME, reply_markup=build_keyboard())

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_subscribed(user, context):
        return await start_cmd(update, context)

    uid = user.id
    txt = update.message.text.strip().lower()
    unique_users.add(uid)

    if uid not in user_sessions:
        user_sessions[uid] = []

    if txt == "start":
        return await start_cmd(update, context)

    if txt == "convert":
        imgs = user_sessions.get(uid, [])
        if not imgs:
            return await update.message.reply_text("❌ لا توجد صور للتحويل.")
        pdf = FPDF()
        for path in imgs:
            pdf.add_page()
            pdf.image(path, x=10, y=10, w=190)
        out = f"{uid}_output.pdf"
        pdf.output(out)
        await update.message.reply_document(open(out, "rb"))
        for p in imgs: os.remove(p)
        os.remove(out)
        user_sessions[uid] = []
        return await update.message.reply_text("✅ تم إنشاء PDF وإرساله.")

    if txt == "clear":
        for p in user_sessions.get(uid, []):
            if os.path.exists(p): os.remove(p)
        user_sessions[uid] = []
        return await update.message.reply_text("✅ تم مسح الصور الحالية.")

    if txt == "stats":
        return await update.message.reply_text(f"👥 عدد المستخدمين الفريدين: {len(unique_users)}")

    if txt == "update":
        return await update.message.reply_text("🔄 تم تحديث البوت بنجاح.")

    await update.message.reply_text("❓ استخدم الأزرار أدناه أو اكتب Start", reply_markup=build_keyboard())

# ===== التعامل مع الصور =====
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_subscribed(user, context):
        return await start_cmd(update, context)

    uid = user.id
    if uid not in user_sessions:
        user_sessions[uid] = []

    file = await update.message.photo[-1].get_file()
    path = f"{uid}_{file.file_id}.jpg"
    await file.download_to_drive(path)
    user_sessions[uid].append(path)
    unique_users.add(uid)

    await update.message.reply_text(
        "📌 تم استلام الصورة.\nإذا انتهيت من الإرسال، اكتب Convert لتحويلها إلى PDF.",
        reply_markup=build_keyboard()
    )

# ===== إبقاء Replit شغال =====
app = Flask("")
@app.route("/")
def home():
    return "I'm alive"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_flask, daemon=True).start()

# ===== تشغيل البوت =====
if __name__ == "__main__":
    app_builder = ApplicationBuilder().token(TOKEN).build()
    app_builder.add_handler(CommandHandler("start", start_cmd))
    app_builder.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app_builder.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logging.info("🚀 البوت بدأ العمل")
    app_builder.run_polling()
