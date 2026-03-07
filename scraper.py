import requests
import json
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup

BASE = "https://oldschool.runescape.wiki"
CAT = BASE + "/wiki/Category:Money_making_guides"
API = BASE + "/api.php"
MAP = "https://prices.runescape.wiki/api/v1/osrs/mapping"


def fetch(url):
    print("Fetching:", url)
    r = requests.get(url, headers={"User-Agent": "OSRS-Scraper"})
    r.raise_for_status()
    time.sleep(0.3)
    return r.text


def get_all_methods():
    urls = []
    page = 0

    blacklist = {
        "Money making guide/Combat",
        "Money making guide/Skilling",
        "Money making guide/Recurring",
        "Money making guide/Collecting",
        "Money making guide/Processing",
        "Money making guide/Guides"
    }

    while True:
        url = CAT if page == 0 else CAT + "?page=" + str(page)
        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div", class_="mw-category-generated")
        if not div:
            break

        found = 0
        for a in div.find_all("a"):
            title = a.get("title", "")
            href = a.get("href", "")
            if title in blacklist:
                continue
            if "Money making guide/" in title:
                full = BASE + href
                if full not in urls:
                    urls.append(full)
                    found += 1

        if found == 0:
            break

        page += 1

    print("Métodos encontrados:", len(urls))
    return urls


# -----------------------------
# LIMPIAR NOMBRE DE ITEM (SIN REGEX LARGAS)
# -----------------------------
def clean_name(x):
    x = x.strip()

    # quitar [[ ]]
    if "[[" in x and "]]" in x:
        x = x.replace("[[", "")
        x = x.replace("]]", "")

    # quitar alias con |
    if "|" in x:
        parts = x.split("|")
        x = parts[-1]

    return x.strip()


# -----------------------------
# PARSEAR ITEMS DESDE WIKITEXT (SIN REGEX LARGAS)
# -----------------------------
def parse_items(wikitext, section):
    items = []

    # dividir por secciones
    sec_marker = "==" + section
    parts = wikitext.split(sec_marker)
    if len(parts) < 2:
        return items

    block = parts[1]

    # cortar antes de la siguiente sección
    block = block.split("\n==")[0]

    # procesar línea por línea
    lines = block.split("\n")

    for line in lines:
        line = line.strip()
        if not line.startswith("*"):
            continue

        # ejemplo:
        # * 4 × [[Redwood logs]] (3,200)

        if "×" not in line:
            continue
        if "(" not in line or ")" not in line:
            continue

        try:
            # cantidad
            qty_part = line.split("×")[0].replace("*", "").strip()
            qty = float(qty_part)

            # nombre
            name_part = line.split("×")[1].split("(")[0].strip()
            name = clean_name(name_part)

            # precio
            price_part = line.split("(")[1].split(")")[0]
            price = int(price_part.replace(",", "").strip())

            items.append({
                "item": name,
                "qty": qty,
                "price": price
            })

        except:
            continue

    return items


# -----------------------------
# OBTENER WIKITEXT
# -----------------------------
def get_wikitext(title):
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json"
    }
    print("Fetching wikitext:", title)
    r = requests.get(API, params=params, headers={"User-Agent": "OSRS-Scraper"})
    r.raise_for_status()
    data = r.json()

    try:
        return data["parse"]["wikitext"]["*"]
    except:
        return ""


# -----------------------------
# EXTRAER RATE (SIN REGEX LARGAS)
# -----------------------------
def extract_rate(wikitext):
    lines = wikitext.split("\n")
    for line in lines:
        if "per hour" in line.lower():
            nums = "".join([c for c in line if c.isdigit() or c == ","])
            if nums:
                return int(nums.replace(",", ""))
    return None


# -----------------------------
# PARSEAR MÉTODO COMPLETO
# -----------------------------
def parse_method(url):
    print("Parseando:", url)

    title = url.split("/")[-1]
    page = "Money_making_guide/" + title

    wikitext = get_wikitext(page)
    if not wikitext:
        return None

    inputs = parse_items(wikitext, "Inputs")
    outputs = parse_items(wikitext, "Outputs")
    rate = extract_rate(wikitext)

    if not inputs and not outputs and not rate:
        return None

    return {
        "name": title.replace("_", " "),
        "url": url,
        "wiki_rate": rate,
        "inputs": inputs,
        "outputs": outputs,
        "wikitext": wikitext
    }


# -----------------------------
# GE LIMITS
# -----------------------------
def get_limits():
    print("Descargando GE limits...")
    r = requests.get(MAP, headers={"User-Agent": "OSRS-Scraper"})
    r.raise_for_status()
    data = r.json()

    out = {}
    for item in data:
        name = item.get("name")
        iid = item.get("id")
        lim = item.get("limit")
        if name and iid:
            out[name] = {"id": iid, "limit": lim}

    return out


# -----------------------------
# MAIN
# -----------------------------
def main():
    urls = get_all_methods()
    limits = get_limits()

    methods = []
    total = len(urls)

    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{total}]")
        try:
            m = parse_method(url)
            if m:
                methods.append(m)
        except Exception as e:
            print("Error:", e)

    out = {
        "updated": datetime.utcnow().isoformat() + "Z",
        "methods": methods,
        "ge_limits": limits
    }

    with open("money_methods.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("JSON generado:", len(methods), "métodos válidos.")


if __name__ == "__main__":
    main()
