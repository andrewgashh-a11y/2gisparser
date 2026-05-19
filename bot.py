import os
import threading
import logging

from dotenv import load_dotenv
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from parser import parse_businesses
from generator import generate_messages_for_leads, pick_channel

load_dotenv()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GIS_KEY = os.environ["GIS_KEY"]
OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]
MY_SITE = os.environ.get("MY_SITE", "landify.art")
MY_TG = os.environ.get("MY_TG", "@landifyArt")
PORT = int(os.environ.get("PORT", 5000))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Flask healthcheck ──────────────────────────────────────────────────────────

flask_app = Flask(__name__)


@flask_app.get("/")
def healthcheck():
    return jsonify({"status": "ok"})


def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT)


# ── Telegram handlers ──────────────────────────────────────────────────────────

CHANNEL_EMOJI = {
    "phone": "📞",
    "whatsapp": "💬",
    "telegram": "✈️",
    "viber": "📳",
    "vk": "🔵",
    "instagram": "📷",
    "email": "✉️",
}

CONTACT_LABELS = {
    "phone": "Телефон",
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "viber": "Viber",
    "vk": "VK",
    "instagram": "Instagram",
    "email": "Email",
}


def format_lead(lead: dict) -> str:
    lines = [
        f"🏢 {lead['name']}",
        f"📍 {lead['address']}",
    ]
    for key in ["phone", "whatsapp", "telegram", "viber", "vk", "instagram", "email"]:
        values = lead["contacts"].get(key, [])
        if values:
            emoji = CHANNEL_EMOJI[key]
            label = CONTACT_LABELS[key]
            lines.append(f"{emoji} {label}: {', '.join(values)}")

    lines.append("")
    lines.append("💬 СООБЩЕНИЕ:")
    lines.append(lead.get("message", ""))
    lines.append("———")
    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Привет! Я бот для поиска бизнесов без сайта в 2GIS.\n\n"
        "🔍 Команда парсинга:\n"
        "/parse <категория> <город> <страниц>\n\n"
        "Пример:\n"
        "/parse автосервис Краснодар 3\n\n"
        "Бот найдёт бизнесы без сайта и сгенерирует холодное сообщение для каждого."
    )
    await update.message.reply_text(text)


async def cmd_parse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "❌ Неверный формат.\nИспользуй: /parse <категория> <город> <страниц>\n"
            "Пример: /parse автосервис Краснодар 3"
        )
        return

    *category_parts, city, pages_str = args
    category = " ".join(category_parts)

    if not pages_str.isdigit() or int(pages_str) < 1:
        await update.message.reply_text("❌ Количество страниц должно быть положительным числом.")
        return

    pages = min(int(pages_str), 20)

    await update.message.reply_text(
        f"⏳ Парсю «{category}» в {city}, {pages} стр. Подожди..."
    )

    try:
        leads, checked = parse_businesses(category, city, pages, GIS_KEY)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    except Exception as e:
        logger.exception("parse error")
        await update.message.reply_text(f"❌ Ошибка парсинга: {e}")
        return

    if not leads:
        await update.message.reply_text(
            f"✅ Найдено 0 лидов из {checked} проверенных.\n"
            "Все бизнесы по этому запросу уже имеют сайт."
        )
        return

    await update.message.reply_text(
        f"✅ Найдено {len(leads)} лидов. Генерирую сообщения..."
    )

    try:
        leads_with_messages = generate_messages_for_leads(leads, OPENROUTER_KEY, MY_SITE, MY_TG)
    except Exception as e:
        logger.exception("generation error")
        await update.message.reply_text(f"❌ Ошибка генерации: {e}")
        return

    for lead in leads_with_messages:
        text = format_lead(lead)
        try:
            await update.message.reply_text(text)
        except Exception:
            await update.message.reply_text(text[:4000])

    await update.message.reply_text(
        f"✅ Найдено {len(leads)} лидов из {checked} проверенных."
    )


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask healthcheck started on port %s", PORT)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("parse", cmd_parse))

    logger.info("Bot polling started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
