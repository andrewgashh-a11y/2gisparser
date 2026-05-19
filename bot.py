import os
import threading
import logging

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify

from parser import parse_businesses
from generator import generate_messages_for_leads

load_dotenv()

TOKEN = os.environ["TELEGRAM_TOKEN"]
GIS_KEY = os.environ["GIS_KEY"]
OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]
MY_SITE = os.environ.get("MY_SITE", "landify.art")
MY_TG = os.environ.get("MY_TG", "@landifyArt")
PORT = int(os.environ.get("PORT", 5000))

API = f"https://api.telegram.org/bot{TOKEN}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Flask healthcheck ──────────────────────────────────────────────────────────

flask_app = Flask(__name__)


@flask_app.get("/")
def healthcheck():
    return jsonify({"status": "ok"})


# ── Telegram helpers ───────────────────────────────────────────────────────────

def send(chat_id: int, text: str):
    requests.post(
        f"{API}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )


def get_updates(offset: int) -> list:
    try:
        resp = requests.get(
            f"{API}/getUpdates",
            params={"offset": offset, "timeout": 30},
            timeout=35,
        )
        resp.raise_for_status()
        return resp.json().get("result", [])
    except Exception as e:
        logger.warning("getUpdates error: %s", e)
        return []


# ── Contact formatting ─────────────────────────────────────────────────────────

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
            lines.append(f"{CHANNEL_EMOJI[key]} {CONTACT_LABELS[key]}: {', '.join(values)}")
    lines += ["", "💬 СООБЩЕНИЕ:", lead.get("message", ""), "———"]
    return "\n".join(lines)


# ── Command handlers ───────────────────────────────────────────────────────────

def handle_start(chat_id: int):
    send(chat_id,
         "👋 Привет! Я бот для поиска бизнесов без сайта в 2GIS.\n\n"
         "🔍 Команда парсинга:\n"
         "/parse &lt;категория&gt; &lt;город&gt; &lt;страниц&gt;\n\n"
         "Пример:\n"
         "/parse автосервис Краснодар 3\n\n"
         "Бот найдёт бизнесы без сайта и сгенерирует холодное сообщение для каждого.")


def handle_parse(chat_id: int, args: list[str]):
    if len(args) < 3:
        send(chat_id,
             "❌ Неверный формат.\n"
             "Используй: /parse &lt;категория&gt; &lt;город&gt; &lt;страниц&gt;\n"
             "Пример: /parse автосервис Краснодар 3")
        return

    *category_parts, city, pages_str = args
    category = " ".join(category_parts)

    if not pages_str.isdigit() or int(pages_str) < 1:
        send(chat_id, "❌ Количество страниц должно быть положительным числом.")
        return

    pages = min(int(pages_str), 20)
    send(chat_id, f"⏳ Парсю «{category}» в {city}, {pages} стр. Подожди...")

    try:
        leads, checked = parse_businesses(category, city, pages, GIS_KEY)
    except ValueError as e:
        send(chat_id, f"❌ {e}")
        return
    except Exception as e:
        logger.exception("parse error")
        send(chat_id, f"❌ Ошибка парсинга: {e}")
        return

    if not leads:
        send(chat_id,
             f"✅ Найдено 0 лидов из {checked} проверенных.\n"
             "Все бизнесы по этому запросу уже имеют сайт.")
        return

    send(chat_id, f"✅ Найдено {len(leads)} лидов. Генерирую сообщения...")

    try:
        leads_with_messages = generate_messages_for_leads(leads, OPENROUTER_KEY, MY_SITE, MY_TG)
    except Exception as e:
        logger.exception("generation error")
        send(chat_id, f"❌ Ошибка генерации: {e}")
        return

    for lead in leads_with_messages:
        send(chat_id, format_lead(lead)[:4096])

    send(chat_id, f"✅ Найдено {len(leads)} лидов из {checked} проверенных.")


# ── Long polling loop ──────────────────────────────────────────────────────────

def polling():
    offset = 0
    logger.info("Bot polling started")
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")
            if not chat_id or not text:
                continue
            parts = text.split()
            command = parts[0].split("@")[0]
            if command == "/start":
                handle_start(chat_id)
            elif command == "/parse":
                handle_parse(chat_id, parts[1:])


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    flask_thread = threading.Thread(
        target=lambda: flask_app.run(host="0.0.0.0", port=PORT),
        daemon=True,
    )
    flask_thread.start()
    logger.info("Flask healthcheck started on port %s", PORT)
    polling()
