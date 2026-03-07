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
    time.sleep(1)  # ser amable con la wiki
    return resp.text


def get_all_method_pages():
    """
    Recorre TODAS las páginas de la categoría:
    Category:Money_making_guides
    incluyendo paginación (?page=1,2,3...)
    y devuelve una lista de URLs de métodos.
    """
    method_urls = []
    page = 0

    while True:
        if page == 0:
            url = CATEGORY_URL
        else:
            url = f"{CATEGORY_URL}?page={page}"

        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        # Lista de páginas en la categoría
        pages_div = soup.find("div", class_="mw-category")
        if not pages_div:
            # No hay más páginas
            break

        links = pages_div.find_all("a")
        count_before = len(method_urls)

        for a in links:
            href = a.get("href", "")
            title = a.get("title", "")

            # Filtrar solo páginas de money making guide
            if "Money making guide/" in title:
                full_url = BASE_WIKI + href
                if full_url not in method_urls:
                    method_urls.append(full_url)

        count_after = len(method_urls)
        print(f"Página {page}: encontrados {count_after - count_before} métodos nuevos.")

        # Ver si hay enlace a la siguiente página
        next_link = soup.find("a", string=re.compile(r"next page", re.IGNORECASE))
        if not next_link:
            break

        page += 1

    print(f"Total métodos encontrados: {len(method_urls)}")
    return method_urls


def parse_items_table(table):
    """
    Intenta extraer items y cantidades de una tabla de la wiki.
    Busca filas con enlaces a items y cantidades en columnas.
    """
    items = []
    rows = table.find_all("tr")
    for row in rows[1:]:
        cols = row.find_all(["td", "th"])
        if not cols:
            continue

        # Buscar enlace al item
        link = cols[0].find("a")
        if not link:
            continue

        item_name = link.get("title") or link.text.strip()
        if not item_name:
            continue

        # Intentar encontrar cantidad en la segunda columna
        qty = 1
        if len(cols) > 1:
            text = cols[1].get_text(strip=True)
            m = re.search(r"(\d+)", text.replace(",", ""))
            if m:
                qty = int(m.group(1))

        items.append({"item": item_name, "qty": qty})

    return items


def extract_rate(text):
    """
    Intenta encontrar un número 'por hora' en el texto de la página.
    Ej: '2450 items per hour', '400k gp/hr', etc.
    Devuelve un número aproximado o None.
    """
    # Buscar patrones tipo '2450 ... per hour' o '2450 .../hour'
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


def parse_method_page(url):
    """
    Parsea una página individual de money making guide.
    Extrae:
    - name
    - members (best effort)
    - category (best effort)
    - wiki_rate
    - inputs
    - outputs
    """
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    # Nombre del método
    title_el = soup.find("h1", id="firstHeading")
    name = title_el.get_text(strip=True) if title_el else url

    # Miembro o no (best effort: buscar 'Members only' en la página)
    page_text = soup.get_text(" ", strip=True)
    members = "Members only" in page_text or "members-only" in page_text.lower()

    # Categoría (best effort: leer categorías al final de la página)
    category = None
    cat_links = soup.find("div", id="mw-normal-catlinks")
    if cat_links:
        cats = [a.get_text(strip=True) for a in cat_links.find_all("a")]
        # Ejemplos de categorías que nos interesan
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

    # Tablas de inputs / outputs
    inputs = []
    outputs = []

    # Buscar tablas con títulos tipo 'Items required', 'Items produced'
    tables = soup.find_all("table", class_="wikitable")
    for table in tables:
        caption = table.find("caption")
        caption_text = caption.get_text(strip=True).lower() if caption else ""

        if "items required" in caption_text or "requirements" in caption_text:
            inputs = parse_items_table(table)
        if "items produced" in caption_text or "output" in caption_text:
            outputs = parse_items_table(table)

    # Rate aproximado
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


def get_ge_limits():
    """
    Descarga el mapping de la API de precios y construye
    un diccionario:
    { "Item name": { "id": ..., "limit": ... }, ... }
    """
    print("Descargando mapping de GE limits...")
    resp = requests.get(MAPPING_API, headers={"User-Agent": "OSRS-Money-Methods-Scraper"})
    resp.raise_for_status()
    data = resp.json()

    limits = {}
    for item in data:
        name = item.get("name")
        item_id = item.get("id")
        limit = item.get("limit")
        if name and item_id:
            limits[name] = {
                "id": item_id,
                "limit": limit,
            }

    print(f"GE limits cargados: {len(limits)} items.")
    return limits


def main():
    # 1) Descubrir todos los métodos
    method_urls = get_all_method_pages()

    # 2) Descargar GE limits una sola vez
    ge_limits = get_ge_limits()

    # 3) Parsear cada método
    methods = []
    for i, url in enumerate(method_urls, start=1):
        print(f"[{i}/{len(method_urls)}] Parseando método: {url}")
        try:
            m = parse_method_page(url)
            methods.append(m)
        except Exception as e:
            print(f"Error parseando {url}: {e}")

    # 4) Construir JSON final
    output = {
        "updated": datetime.utcnow().isoformat() + "Z",
        "methods": methods,
        "ge_limits": ge_limits,
    }

    with open("money_methods.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("money_methods.json generado correctamente.")


if __name__ == "__main__":
    main()
