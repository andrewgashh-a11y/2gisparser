import time
import sys
import requests

GIS_BASE = "https://catalog.api.2gis.com"


def get_city_id(city: str, key: str) -> str | None:
    url = f"{GIS_BASE}/2.0/region/list"
    resp = requests.get(url, params={"q": city, "key": key}, timeout=10)
    print("REGIONS статус:", resp.status_code, flush=True)
    print("REGIONS json:", resp.json(), flush=True)
    resp.raise_for_status()
    items = resp.json().get("result", {}).get("items", [])
    city_id = None
    for item in items:
        if city.lower() in item.get("name", "").lower():
            city_id = item["id"]
            break
    print("CITY_ID:", city_id, flush=True)
    return str(city_id) if city_id else None


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
    city_id = get_city_id(city, key)

    leads = []
    checked = 0

    for page in range(1, pages + 1):
        url = f"{GIS_BASE}/3.0/items"
        if city_id:
            params = {
                "q": category,
                "city_id": city_id,
                "key": key,
                "page_size": 10,
                "page": page,
                "fields": "org.contacts",
            }
        else:
            params = {
                "q": f"{category} {city}",
                "key": key,
                "page_size": 10,
                "page": page,
                "fields": "org.contacts",
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
