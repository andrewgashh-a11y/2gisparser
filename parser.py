import time
import requests

GIS_BASE = "https://catalog.api.2gis.com"


def _extract_contacts(item: dict) -> dict:
    contacts = {"phone": [], "whatsapp": [], "telegram": [], "viber": [], "vk": [], "instagram": [], "email": []}

    for c in item.get("org", {}).get("contacts", []):
        ctype = c.get("type", "")
        value = c.get("value", "") or c.get("url", "")
        if ctype in contacts:
            contacts[ctype].append(value)

    return contacts


def _has_website(item: dict) -> bool:
    for c in item.get("org", {}).get("contacts", []):
        if c.get("type") == "website":
            return True
    return False


def parse_businesses(category: str, city: str, pages: int, key: str) -> list[dict]:
    leads = []
    checked = 0

    for page in range(1, pages + 1):
        url = f"{GIS_BASE}/3.0/items"
        params = {
            "q": f"{category} {city}",
            "key": key,
            "page_size": 10,
            "page": page,
        }

        resp = requests.get(url, params=params, timeout=15)
        print("CATALOG статус:", resp.status_code, flush=True)
        print("CATALOG json:", resp.json(), flush=True)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("result", {}).get("items", [])
        print(f"Найдено items на странице {page}:", len(items), flush=True)
        if not items:
            break

        print("ПЕРВЫЙ ITEM ЦЕЛИКОМ:", items[0], flush=True)

        for item in items:
            checked += 1
            contacts = _extract_contacts(item)
            print("ITEM:", item.get("name"), "| contacts:", contacts, flush=True)
            if not any(contacts.values()):
                continue

            leads.append({
                "name": item.get("name", ""),
                "address": item.get("address_name", ""),
                "contacts": contacts,
            })

        if page < pages:
            time.sleep(0.4)

    return leads, checked
