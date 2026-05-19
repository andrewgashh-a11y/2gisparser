import time
import requests

GIS_BASE = "https://catalog.api.2gis.com"


def _extract_contacts(item: dict) -> dict:
    contacts = {"phone": [], "whatsapp": [], "telegram": [], "viber": [], "vk": [], "instagram": [], "email": []}

    for group in item.get("contact_groups", []):
        for c in group.get("contacts", []):
            ctype = c.get("type", "")
            value = c.get("value", "") or c.get("url", "")
            if ctype in contacts:
                contacts[ctype].append(value)

    return contacts


def _has_website(item: dict) -> bool:
    for group in item.get("contact_groups", []):
        for c in group.get("contacts", []):
            if c.get("type") == "website":
                return True
    return False


def _fetch_detail(item_id: str, key: str) -> dict:
    resp = requests.get(
        f"{GIS_BASE}/3.0/items/{item_id}",
        params={"key": key, "fields": "item.contact_groups"},
        timeout=10,
    )
    items = resp.json().get("result", {}).get("items", [])
    return items[0] if items else {}


def parse_businesses(category: str, city: str, pages: int, key: str) -> list[dict]:
    leads = []
    checked = 0

    for page in range(1, pages + 1):
        params = {
            "q": f"{category} {city}",
            "key": key,
            "page_size": 10,
            "page": page,
        }

        resp = requests.get(f"{GIS_BASE}/3.0/items", params=params, timeout=15)
        print("CATALOG статус:", resp.status_code, flush=True)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("result", {}).get("items", [])
        print(f"Найдено items на странице {page}:", len(items), flush=True)
        if not items:
            break

        for item in items:
            checked += 1
            detail = _fetch_detail(item["id"], key)
            print("DETAIL:", item.get("name"), "| contact_groups:", detail.get("contact_groups"), flush=True)

            if _has_website(detail):
                continue
            contacts = _extract_contacts(detail)
            if not any(contacts.values()):
                continue

            leads.append({
                "name": item.get("name", ""),
                "address": item.get("address_name", ""),
                "contacts": contacts,
            })
            time.sleep(0.3)

        if page < pages:
            time.sleep(0.4)

    return leads, checked
