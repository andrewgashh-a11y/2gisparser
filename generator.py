import time
import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.3-8b-instruct:free"

CHANNEL_PRIORITY = ["telegram", "whatsapp", "instagram", "vk", "phone"]


def pick_channel(contacts: dict) -> tuple[str, str]:
    for channel in CHANNEL_PRIORITY:
        values = contacts.get(channel, [])
        if values:
            return channel, values[0]
    return "", ""


def generate_message(business_name: str, contacts: dict, openrouter_key: str, my_site: str, my_tg: str) -> str:
    channel, _ = pick_channel(contacts)
    channel_hint = f"через {channel}" if channel else "напрямую"

    prompt = (
        f"Напиши короткое холодное сообщение (3-4 предложения) для бизнеса «{business_name}». "
        f"Упомяни, что без сайта они теряют клиентов. "
        f"Предложи сделать лендинг за 2-4 дня. "
        f"Упомяни портфолио {my_site} и контакт {my_tg}. "
        f"Сообщение будет отправлено {channel_hint}. Пиши на русском, без вступлений и подписи."
    )

    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
    }

    resp = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def generate_messages_for_leads(leads: list[dict], openrouter_key: str, my_site: str, my_tg: str) -> list[dict]:
    results = []
    for i, lead in enumerate(leads):
        msg = generate_message(lead["name"], lead["contacts"], openrouter_key, my_site, my_tg)
        results.append({**lead, "message": msg})
        if i < len(leads) - 1:
            time.sleep(1)
    return results
