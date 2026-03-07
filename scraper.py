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
# LIMPIAR NOMBRE DE ITEM
# -----------------------------
def clean_name(x):
    x = x.strip()
    x = re.sub(r"

\[

\[(.*?)\]

\]

", r"\1", x)
    if "|" in x:
        x = x.split("|")[-1]
    x = x.replace("[[", "").replace("]]", "")
    return x.strip()


# -----------------------------
# PARSEAR ITEMS DESDE WIKITEXT
# -----------------------------
def parse_items(wikitext, section):
    items = []

    # Buscar sección
    sec = re.split(r"==+\s*" + section + r".*?==+", wikitext, flags=re.IGNORECASE)
    if len(sec) < 2:
        return items

    block = sec[1]
    block = re.split(r"\n==+", block)[0]

    # Patrón simple y corto
    pat = r"\*\s*([\d\.]+)\s*×\s*(.*?)\s*\(([\d,]+)\)"

    for qty, name, price in re.findall(pat, block):
        items.append({
            "item": clean_name(name),
            "qty": float(qty),
            "price": int(price.replace(",", ""))
        })

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
    r = requests.get(API, params=params, headers={"User-Agent": "OSRS-Scraper"})
    r.raise_for_status()
    data = r.json()
    try:
        return data["parse"]["wikitext"]["*"]
    except:
        return ""


# -----------------------------
# EXTRAER RATE
# -----------------------------
def extract_rate(wikitext):
    m = re.search(r"([\d,]+)\s*per hour", wikitext, re.IGNORECASE)
    if m:
        return int(m.group(1).replace(",", ""))
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
    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}]")
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
