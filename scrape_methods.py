"""
scrape_methods.py
=================
Lee la lista de money making de la wiki OSRS y para cada método
raspa: inputs (items necesarios + cantidades), outputs (items producidos +
cantidades), acciones_por_hora de la wiki, nombre, URL.

Guarda → methods_base.json
"""

import requests
import json
import re
import time
from bs4 import BeautifulSoup

BASE    = "https://oldschool.runescape.wiki"
INDEX   = BASE + "/w/Money_making_guide"
HEADERS = {"User-Agent": "osrs-profit-engine/1.0 (github.com/contactogameimpact-blip/osrs-scraper)"}

# Acciones humanas realistas por categoría (la wiki exagera)
# Se aplican como tope máximo sobre lo que dice la wiki
HUMAN_CAPS = {
    "Making":    2000,
    "Smithing":  2200,
    "Cooking":   2000,
    "Crafting":  2200,
    "Fletching": 2500,
    "Fishing":   1000,
    "Killing":   600,
    "Farming":   200,
    "Thieving":  1800,
    "default":   1800,
}

def human_cap(name):
    for keyword, cap in HUMAN_CAPS.items():
        if name.lower().startswith(keyword.lower()):
            return cap
    return HUMAN_CAPS["default"]

def get_links():
    r = requests.get(INDEX, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    seen = set()
    for row in soup.select("table.wikitable tbody tr"):
        a = row.select_one("td a[href]")
        if not a:
            continue
        name = a.text.strip()
        href = a.get("href", "")
        if not href.startswith("/w/") or name in seen:
            continue
        seen.add(name)
        links.append({"name": name, "url": BASE + href})
    return links

def parse_qty(text):
    """Parse quantity strings like '1,000', '2.5', '500' → float"""
    text = text.strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return 0.0

def scrape_method(name, url):
    """
    Raspa una página de método individual.
    Busca la tabla de inputs/outputs tipo 'infobox-money-making'.
    Devuelve dict con inputs, outputs, wiki_actions_per_hour.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None

    result = {
        "inputs":  [],
        "outputs": [],
        "wiki_actions_per_hour": 0,
    }

    # ── Buscar la infobox de money making ──────────────────────────
    # Estructura típica: div.money-making-infobox o table.infobox
    infobox = soup.find("div", class_=re.compile(r"money.making", re.I))
    if not infobox:
        infobox = soup.find("table", class_=re.compile(r"infobox", re.I))

    if infobox:
        # Acciones por hora de la wiki
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = th.get_text(strip=True).lower()
            value = td.get_text(strip=True)
            if "action" in label and "hour" in label:
                result["wiki_actions_per_hour"] = int(parse_qty(value))

    # ── Buscar tabla de inputs ──────────────────────────────────────
    # La wiki tiene secciones "Input" y "Output" con tablas
    for heading in soup.find_all(["h2", "h3", "th"]):
        text = heading.get_text(strip=True).lower()
        if "input" in text:
            tbl = heading.find_next("table")
            if tbl:
                for row in tbl.find_all("tr")[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    item_name = cells[0].get_text(strip=True)
                    qty_text  = cells[1].get_text(strip=True) if len(cells) > 1 else "1"
                    qty = parse_qty(qty_text) or 1.0
                    if item_name:
                        result["inputs"].append({"item": item_name, "qty": qty})
            break

    for heading in soup.find_all(["h2", "h3", "th"]):
        text = heading.get_text(strip=True).lower()
        if "output" in text:
            tbl = heading.find_next("table")
            if tbl:
                for row in tbl.find_all("tr")[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    item_name = cells[0].get_text(strip=True)
                    qty_text  = cells[1].get_text(strip=True) if len(cells) > 1 else "1"
                    qty = parse_qty(qty_text) or 1.0
                    if item_name:
                        result["outputs"].append({"item": item_name, "qty": qty})
            break

    # ── Fallback: buscar tabla MMG con columnas item/qty ────────────
    if not result["inputs"] and not result["outputs"]:
        for tbl in soup.find_all("table", class_=re.compile(r"wikitable", re.I)):
            headers = [th.get_text(strip=True).lower() for th in tbl.find_all("th")]
            if any("input" in h for h in headers) or any("output" in h for h in headers):
                for row in tbl.find_all("tr")[1:]:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        item_name = cells[0].get_text(strip=True)
                        qty = parse_qty(cells[1].get_text(strip=True)) or 1.0
                        if item_name:
                            result["outputs"].append({"item": item_name, "qty": qty})

    return result

def main():
    print("Scraping money making guide index...")
    links = get_links()
    print(f"Found {len(links)} methods")

    methods = []
    for i, m in enumerate(links):
        print(f"  [{i+1}/{len(links)}] {m['name']}")
        data = scrape_method(m["name"], m["url"])

        wiki_aph = 0
        inputs   = []
        outputs  = []

        if data:
            wiki_aph = data.get("wiki_actions_per_hour", 0)
            inputs   = data.get("inputs",  [])
            outputs  = data.get("outputs", [])

        # Acciones humanas reales: mínimo entre la wiki y nuestro tope
        cap = human_cap(m["name"])
        if wiki_aph > 0:
            human_aph = min(wiki_aph, cap)
        else:
            human_aph = cap // 2  # sin datos → estimación conservadora

        methods.append({
            "name":                    m["name"],
            "url":                     m["url"],
            "wiki_actions_per_hour":   wiki_aph,
            "actions_per_hour_human":  human_aph,
            "inputs":                  inputs,
            "outputs":                 outputs,
        })

        time.sleep(0.5)  # respetar la wiki

    with open("methods_base.json", "w") as f:
        json.dump({"methods": methods}, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(methods)} methods to methods_base.json")

if __name__ == "__main__":
    main()
