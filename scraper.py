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
    print(f"Fetching: {url}")
    resp = requests.get(url, headers={"User-Agent": "OSRS-Money-Methods-Scraper"})
    resp.raise_for_status()
    time.sleep(0.3)
    return resp.text


# ---------------------------------------------------------
# CRAWLER SEGURO + FILTRO DE CATEGORÍAS
# ---------------------------------------------------------
def get_all_method_pages():
    method_urls = []
    page = 0
    max_pages = 20

    blacklist = {
        "Money making guide/Combat",
        "Money making guide/Skilling",
        "Money making guide/Recurring",
        "Money making guide/Collecting",
        "Money making guide/Processing",
        "Money making guide/Guides"
    }

    while page < max_pages:
        url = CATEGORY_URL if page == 0 else f"{CATEGORY_URL}?page={page}"
        print(f"\n=== Página de categoría {page} ===")
        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        category_div = soup.find("div", class_="mw-category-generated")
        if not category_div:
            print("No hay más páginas.")
            break

        links = category_div.find_all("a")
        nuevos = 0

        for a in links:
            title = a.get("title", "")
            href = a.get("href", "")

            if title in blacklist:
                continue

            if "Money making guide/" in title:
                full_url = BASE_WIKI + href
                if full_url not in method_urls:
                    method_urls.append(full_url)
                    nuevos += 1

        print(f"Página {page}: {nuevos} métodos nuevos.")

        if nuevos == 0:
            break

        page += 1

    print(f"\nTotal métodos encontrados: {len(method_urls)}")
    return method_urls


# ---------------------------------------------------------
# PARSER DE LISTAS (Inputs/Outputs)
# ---------------------------------------------------------
def parse_list_items(lines):
    items = []
    pattern = r"([\d\.]+)\s*×\s*(.*?)\s*\(([\d,]+)\)"

    for line in lines:
        m = re.search(pattern, line)
        if m:
            qty = float(m.group(1))
            name = m.group(2).strip()
            price = int(m.group(3).replace(",", ""))
            items.append({"item": name, "qty": qty, "price": price})

    return items


# ---------------------------------------------------------
# EXTRACCIÓN DE RATE REAL
# ---------------------------------------------------------
def extract_rate(text):
    m = re.search(r"([\d,]+)\s*per hour", text, re.IGNORECASE)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


# ---------------------------------------------------------
# PARSER DE MÉTODOS (INTELIGENTE)
# ---------------------------------------------------------
def parse_method_page(url):
    print(f"Parseando método: {url}")
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.find("h1", id="firstHeading")
    name = title_el.get_text(strip=True) if title_el else url

    page_text = soup.get_text(" ", strip=True)
    members = "Members only" in page_text or "members-only" in page_text.lower()

    # Categoría
    category = None
    cat_links = soup.find("div", id="mw-normal-catlinks")
    if cat_links:
        cats = [a.get_text(strip=True).lower() for a in cat_links.find_all("a")]
        if any("combat" in c for c in cats):
            category = "combat"
        elif any("skilling" in c for c in cats):
            category = "skilling"
        elif any("processing" in c for c in cats):
            category = "processing"

    # Buscar secciones Inputs / Outputs
    text_blocks = soup.get_text("\n", strip=True).split("\n")

    inputs_section = []
    outputs_section = []
    current = None

    for line in text_blocks:
        if line.lower().startswith("inputs"):
            current = "inputs"
            continue
        if line.lower().startswith("outputs"):
            current = "outputs"
            continue

        if current == "inputs":
            inputs_section.append(line)
        elif current == "outputs":
            outputs_section.append(line)

    inputs = parse_list_items(inputs_section)
    outputs = parse_list_items(outputs_section)

    wiki_rate = extract_rate(page_text)

    # FILTRO: si no tiene nada útil, descartar
    if not inputs and not outputs and not wiki_rate:
        print("Página descartada (vacía).")
        return None

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
    print("\nDescargando GE limits...")
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
            if m:
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
