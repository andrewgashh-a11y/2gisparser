import time
import requests

GIS_BASE = "https://catalog.api.2gis.com"


def get_city_id(city: str, key: str) -> str | None:
    url = f"{GIS_BASE}/2.0/region/list"
    resp = requests.get(url, params={"q": city, "key": key}, timeout=10)
    resp.raise_for_status()
    items = resp.json().get("result", {}).get("items", [])
    if not items:
        return None
    return str(items[0]["id"])


def _extract_contacts(org: dict) -> dict:
    contacts = {"phone": [], "whatsapp": [], "telegram": [], "viber": [], "vk": [], "instagram": [], "email": []}
    has_website = False

    for c in org.get("contacts", []):
        ctype = c.get("type", "")
        value = c.get("value", "") or c.get("url", "")
        if ctype == "website":
            has_website = True
        elif ctype in contacts:
            contacts[ctype].append(value)

    if has_website:
        return None
    return contacts


def parse_businesses(category: str, city: str, pages: int, key: str) -> list[dict]:
    city_id = get_city_id(city, key)
    if not city_id:
        raise ValueError(f"Город «{city}» не найден в 2GIS")

    leads = []
    checked = 0

    for page in range(1, pages + 1):
        url = f"{GIS_BASE}/3.0/items"
        params = {
            "q": category,
            "city_id": city_id,
            "key": key,
            "page_size": 50,
            "page": page,
            "fields": "org.website,org.contacts",
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("result", {}).get("items", [])
        if not items:
            break

        for item in items:
            checked += 1
            org = item.get("org", {})
            contacts = _extract_contacts(org)
            if contacts is None:
                continue

            leads.append({
                "name": item.get("name", ""),
                "address": item.get("address_name", ""),
                "contacts": contacts,
            })

        if page < pages:
            time.sleep(0.4)

    return leads, checked
