import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime

BASE_WIKI = "https://oldschool.runescape.wiki"
CATEGORY_URL = f"{BASE_WIKI}/wiki/Category:Money_making_guides"
API_URL = "https://oldschool.runescape.wiki/api.php"
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
# NORMALIZAR NOMBRES DE ITEMS
# ---------------------------------------------------------
def clean_item_name(raw):
    raw = raw.strip()
    # Quitar [[...]]
    raw = re.sub(r"

\[

\[(.*?)\]

\]

", r"\1", raw)
    # Si hay alias con |, quedarse con la parte visible
    raw = raw.split("|")[-1]
    # Limpiar corchetes sueltos por si acaso
    raw = raw.replace("[[", "").replace("]]", "")
    return raw.strip()


# ---------------------------------------------------------
# PARSEAR ITEMS DESDE WIKITEXT (SECCIÓN)
# ---------------------------------------------------------
def parse_items_from_wikitext(wikitext, section_name):
    items = []

    # Buscar sección tipo "== Inputs (3,534) ==", "=== Inputs ===", etc.
    pattern_section = rf"==+\s*{section_name}\s*\(?.*?\)?\s*==+"
    parts = re.split(pattern_section, wikitext, flags=re.IGNORECASE)

    if len(parts) < 2:
        return items

    # Tomar el contenido después del título de la sección
    content = parts[1]

    # Cortar antes de la siguiente sección grande (== Algo ==)
    content = re.split(r"\n==+", content)[0]

    # Líneas tipo:
    # * 4 × [[Redwood logs]] (3,200)
    pattern_item = r"\*\s*([\d\.]+)\s*×\s*(.*?)\s*\(([\d,]+)\)"

    for match in re.findall(pattern_item, content):
        qty, name, price = match
        items.append({
            "item": clean_item_name(name),
            "qty": float(qty),
            "price": int(price.replace(",", ""))
        })

    return items


# ---------------------------------------------------------
# EXTRAER WIKITEXT REAL
# ---------------------------------------------------------
def get_wikitext(page_title):
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "wikitext",
        "format": "json"
    }
    print(f"Fetching wikitext: {page_title}")
    resp = requests.get(API_URL, params=params, headers={"User-Agent": "OSRS-Money-Methods-Scraper"})
    resp.raise_for_status()
    data = resp.json()

    try:
        return data["parse"]["wikitext"]["*"]
    except Exception as e:
        print(f"Error obteniendo wikitext para {page_title}: {e}")
        return ""


# ---------------------------------------------------------
# EXTRAER RATE REAL DESDE WIKITEXT
# ---------------------------------------------------------
def extract_rate(wikitext):
    m = re.search(r"([\d,]+)\s*per hour", wikitext, re.IGNORECASE)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


# ---------------------------------------------------------
# PARSEAR MÉTODO COMPLETO
# ---------------------------------------------------------
def parse_method_page(url):
    print(f"\nParseando método: {url}")

    # Título de la página (parte final de la URL)
    title = url.split("/")[-1]  # Money_making_guide/Bird_house_trapping -> Bird_house_trapping

    # Nombre completo de la página en la wiki
    page_title = f"Money_making_guide/{title}"

    # Obtener wikitext real
    wikitext = get_wikitext(page_title)

    if not wikitext:
        print("No wikitext encontrado, se omite.")
        return None

    # Inputs y outputs desde wikitext
    inputs = parse_items_from_wikitext(wikitext, "Inputs")
    outputs = parse_items_from_wikitext(wikitext, "Outputs")

    # Rate
    wiki_rate = extract_rate(wikitext)

    # Si no hay nada útil, descartar
    if not inputs and not outputs and not wiki_rate:
        print("Sin inputs/outputs/rate, se omite.")
        return None

    return {
        "name": title.replace("_", " "),
        "url": url,
        "wiki_rate": wiki_rate,
        "inputs": inputs,
        "outputs": outputs,
        "wikitext": wikitext
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
    total = len(method_urls)

    for i, url in enumerate(method_urls, start=1):
        print(f"[{i}/{total}] {url}")
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
    print(f"Métodos válidos: {len(methods)}")


if __name__ == "__main__":
    main()
