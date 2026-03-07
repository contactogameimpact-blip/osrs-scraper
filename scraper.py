import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime

BASE_WIKI = "https://oldschool.runescape.wiki"
CATEGORY_URL = f"{BASE_WIKI}/wiki/Category:Money_making_guides"
MAPPING_API = "https://prices.runescape.wiki/api/v1/osrs/mapping"


def fetch(url):
    """Descarga una URL con un pequeño delay para no abusar de la wiki."""
    print(f"Fetching: {url}")
    resp = requests.get(url, headers={"User-Agent": "OSRS-Money-Methods-Scraper"})
    resp.raise_for_status()
    time.sleep(0.3)  # más rápido pero respetuoso
    return resp.text


# ---------------------------------------------------------
# 🔥 CRAWLER NUEVO — SIN BUCLES INFINITOS
# ---------------------------------------------------------
def get_all_method_pages():
    """
    Recorre la categoría Money_making_guides con paginación real.
    La wiki usa 'mw-category-generated' para listar páginas.
    Este crawler:
    - detecta el final correctamente
    - evita bucles infinitos
    - limita a 20 páginas por seguridad
    """
    method_urls = []
    page = 0
    max_pages = 20  # límite de seguridad

    while page < max_pages:
        url = CATEGORY_URL if page == 0 else f"{CATEGORY_URL}?page={page}"
        print(f"\n=== Página de categoría {page} ===")
        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        category_div = soup.find("div", class_="mw-category-generated")
        if not category_div:
            print("No hay más páginas de categoría. Fin del crawler.")
            break

        links = category_div.find_all("a")
        nuevos = 0

        for a in links:
            title = a.get("title", "")
            href = a.get("href", "")

            if "Money making guide/" in title:
                full_url = BASE_WIKI + href
                if full_url not in method_urls:
                    method_urls.append(full_url)
                    nuevos += 1

        print(f"Página {page}: {nuevos} métodos nuevos.")

        if nuevos == 0:
            print("No se encontraron métodos nuevos. Fin del crawler.")
            break

        page += 1

    print(f"\nTotal métodos encontrados: {len(method_urls)}")
    return method_urls


# ---------------------------------------------------------
# PARSER DE ITEMS
# ---------------------------------------------------------
def parse_items_table(table):
    items = []
    rows = table.find_all("tr")
    for row in rows[1:]:
        cols = row.find_all(["td", "th"])
        if not cols:
            continue

        link = cols[0].find("a")
        if not link:
            continue

        item_name = link.get("title") or link.text.strip()
        if not item_name:
            continue

        qty = 1
        if len(cols) > 1:
            text = cols[1].get_text(strip=True)
            m = re.search(r"(\d+)", text.replace(",", ""))
            if m:
                qty = int(m.group(1))

        items.append({"item": item_name, "qty": qty})

    return items


# ---------------------------------------------------------
# EXTRACCIÓN DE RATE
# ---------------------------------------------------------
def extract_rate(text):
    patterns = [
        r"(\d[\d,]*)\s*(?:items|actions)?\s*(?:per hour|/hour|per hr|/hr)",
        r"(\d[\d,]*)\s*gp\s*(?:per hour|/hour|per hr|/hr)",
    ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                continue

    return None


# ---------------------------------------------------------
# PARSER DE MÉTODOS
# ---------------------------------------------------------
def parse_method_page(url):
    print(f"Parseando método: {url}")
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.find("h1", id="firstHeading")
    name = title_el.get_text(strip=True) if title_el else url

    page_text = soup.get_text(" ", strip=True)
    members = "Members only" in page_text or "members-only" in page_text.lower()

    category = None
    cat_links = soup.find("div", id="mw-normal-catlinks")
    if cat_links:
        cats = [a.get_text(strip=True) for a in cat_links.find_all("a")]
        for c in cats:
            lc = c.lower()
            if "combat" in lc or "boss" in lc:
                category = "combat"
                break
            if "skilling" in lc:
                category = "skilling"
                break
            if "processing" in lc or "crafting" in lc or "cooking" in lc:
                category = "processing"
                break

    inputs = []
    outputs = []

    tables = soup.find_all("table", class_="wikitable")
    for table in tables:
        caption = table.find("caption")
        caption_text = caption.get_text(strip=True).lower() if caption else ""

        if "items required" in caption_text or "requirements" in caption_text:
            inputs = parse_items_table(table)
        if "items produced" in caption_text or "output" in caption_text:
            outputs = parse_items_table(table)

    wiki_rate = extract_rate(page_text)

    return {
        "name": name,
        "url": url,
        "members": members,
        "category": category,
        "wiki_rate": wiki_rate,
        "inputs": inputs,
        "outputs": outputs,
    }


# ---------------------------------------------------------
# GE LIMITS
# ---------------------------------------------------------
def get_ge_limits():
    print("\nDescargando mapping de GE limits...")
    resp = requests.get(MAPPING_API, headers={"User-Agent": "OSRS-Money-Methods-Scraper"})
    resp.raise_for_status()
    data = resp.json()

    limits = {}
    for item in data:
        name = item.get("name")
        item_id = item.get("id")
        limit = item.get("limit")
        if name and item_id:
            limits[name] = {"id": item_id, "limit": limit}

    print(f"GE limits cargados: {len(limits)} items.")
    return limits


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    method_urls = get_all_method_pages()
    ge_limits = get_ge_limits()

    methods = []
    for i, url in enumerate(method_urls, start=1):
        print(f"[{i}/{len(method_urls)}]")
        try:
            m = parse_method_page(url)
            methods.append(m)
        except Exception as e:
            print(f"Error parseando {url}: {e}")

    output = {
        "updated": datetime.utcnow().isoformat() + "Z",
        "methods": methods,
        "ge_limits": ge_limits,
    }

    with open("money_methods.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\nmoney_methods.json generado correctamente.")


if __name__ == "__main__":
    main()
