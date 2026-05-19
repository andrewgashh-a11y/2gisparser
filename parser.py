import json
import time
import requests

GIS_BASE = "https://catalog.api.2gis.com"


def get_city_id(city: str, key: str) -> str | None:
    url = f"{GIS_BASE}/2.0/region/list"
    resp = requests.get(url, params={"q": city, "key": key}, timeout=10)
    print("REGIONS ответ:", resp.status_code)
    print("REGIONS json:", resp.json())
    resp.raise_for_status()
    items = resp.json().get("result", {}).get("items", [])
    city_id = None
    for item in items:
        if city.lower() in item.get("name", "").lower():
            city_id = item["id"]
            break
    print("CITY_ID:", city_id)
    return str(city_id) if city_id else None


def _extract_contacts(org: dict) -> dict:
    contacts = {"phone": [], "whatsapp": [], "telegram": [], "viber": [], "vk": [], "instagram": [], "email": []}

    for c in org.get("contacts", []):
        ctype = c.get("type", "")
        value = c.get("value", "") or c.get("url", "")
        if ctype in contacts:
            contacts[ctype].append(value)

    return contacts


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
                "fields": "org.website,org.contacts",
            }
        else:
            params = {
                "q": f"{category} {city}",
                "key": key,
                "page_size": 10,
                "page": page,
                "fields": "org.website,org.contacts",
            }

        resp = requests.get(url, params=params, timeout=15)
        print("CATALOG статус:", resp.status_code)
        print("CATALOG json:", resp.json())
        resp.raise_for_status()
        data = resp.json()

        items = data.get("result", {}).get("items", [])
        if not items:
            break

        for item in items:
            checked += 1
            print("ITEM:", item.get("name"), "contacts:", item.get("contact_groups"))
            org = item.get("org", {})
            contacts = _extract_contacts(org)
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
