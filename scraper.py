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
        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        category_div = soup.find("div", class_="mw-category-generated")
        if not category_div:
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

        if nuevos == 0:
            break

        page += 1

    print(f"Total métodos encontrados: {len(method_urls)}")
    return method_urls


# ---------------------------------------------------------
# NORMALIZAR NOMBRES DE ITEMS
# ---------------------------------------------------------
def clean_item_name(raw):
    raw = raw.strip()
    raw = re.sub(r"

\[

\[(.*?)\]

\]

", r"\1", raw)  # remove [[ ]]
    raw = raw.split("|")[-1]  # remove alias
    raw = raw.replace("]]", "").replace("[[", "")
    return raw.strip()


# ---------------------------------------------------------
# PARSEAR ITEMS DESDE WIKITEXT
# ---------------------------------------------------------
def parse_items_from_wikitext(wikitext, section_name):
    items = []

    # Buscar sección Inputs o Outputs
    pattern_section = rf"==*\s*{section_name}\s*\(.*?\)\s*==*"
    sections = re.split(pattern_section, wikitext, flags=re.IGNORECASE)

    if len(sections) < 2:
        return items

    # Tomar la parte después del título
    content = sections[1]

    # Buscar líneas tipo:
    # * 4 × [[Redwood logs]] (3,200)
    pattern_item = r"\*\s*([\d\.]+)\s*×\s*(.*?)\s*\(([\d,]+)\)"

    for qty, name, price in re.findall(pattern_item, content):
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
    resp = requests.get(API_URL, params=params, headers={"User-Agent": "OSRS-Money-Methods-Scraper"})
    resp.raise_for_status()
    data = resp.json()

    try:
        return data["parse"]["wikitext"]["*"]
    except:
        return ""


# ---------------------------------------------------------
# EXTRAER RATE REAL
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
    print(f"Parseando método: {url}")

    # Extraer título
    title = url.split("/")[-1]

    # Obtener wikitext real
    wikitext = get_wikitext(f"Money_making_guide/{title}")

    if not wikitext:
        print("No wikitext encontrado.")
        return None

    # Inputs y outputs desde wikitext
    inputs = parse_items_from_wikitext(wikitext, "Inputs")
    outputs = parse_items_from_wikitext(wikitext, "Outputs")

    # Rate
    wiki_rate = extract_rate(wikitext)

    if not inputs and not outputs and not wiki_rate:
        return None

    return {
        "name": title.replace("_", " "),
        "url": url,
        "wiki_rate": wiki_rate,
        "inputs": inputs,
        "outputs": outputs,
        "wikitext": wikitext  # debugging
    }


# ---------------------------------------------------------
# GE LIMITS
# ---------------------------------------------------------
def get_ge_limits():
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

    print("money_methods.json generado correctamente.")


if __name__ == "__main__":
    main()
