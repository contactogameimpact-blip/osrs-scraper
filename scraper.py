import requests
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup

BASE = "https://oldschool.runescape.wiki"
CATEGORY = BASE + "/wiki/Category:Money_making_guides"
MAPPING = "https://prices.runescape.wiki/api/v1/osrs/mapping"

HEADERS = {
    "User-Agent": "OSRS-MoneyMaker-Scraper"
}


# ---------------------------------------------------------
# HTTP
# ---------------------------------------------------------

def fetch(url):
    print("Fetching:", url)
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    time.sleep(0.5)
    return r.text


# ---------------------------------------------------------
# CRAWLER — obtiene todos los métodos
# ---------------------------------------------------------

def get_all_methods():

    methods = []
    next_page = CATEGORY

    while next_page:

        html = fetch(next_page)
        soup = BeautifulSoup(html, "html.parser")

        category = soup.find("div", id="mw-pages")

        if not category:
            break

        for a in category.find_all("a"):

            href = a.get("href")
            title = a.get("title")

            if not href or not title:
                continue

            if "Money making guide/" in title:

                url = BASE + href

                if url not in methods:
                    methods.append(url)

        next_link = category.find("a", string="next page")

        if next_link:
            next_page = BASE + next_link.get("href")
        else:
            next_page = None

    print("Total métodos encontrados:", len(methods))

    return methods


# ---------------------------------------------------------
# PARSER — extrae items de tablas
# ---------------------------------------------------------

def parse_items_from_table(table):

    items = []

    rows = table.find_all("tr")

    for r in rows:

        text = r.get_text(" ", strip=True)

        if "×" not in text:
            continue

        try:

            parts = text.split("×")

            qty = float(parts[0].strip())

            name = parts[1].split("(")[0].strip()

            items.append({
                "item": name,
                "qty": qty
            })

        except:
            continue

    return items


# ---------------------------------------------------------
# PROFIT EXTRACTION
# ---------------------------------------------------------

def extract_profit(table):

    rows = table.find_all("tr")

    for r in rows:

        txt = r.get_text(" ", strip=True).lower()

        if "profit" in txt:

            nums = "".join(c for c in txt if c.isdigit() or c == ",")

            if nums:
                try:
                    return int(nums.replace(",", ""))
                except:
                    pass

    return None


# ---------------------------------------------------------
# PARSE METHOD PAGE
# ---------------------------------------------------------

def parse_method(url):

    print("Parsing:", url)

    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    tables = soup.find_all("table")

    inputs = []
    outputs = []
    profit = None

    for table in tables:

        text = table.get_text(" ", strip=True).lower()

        if "inputs" in text and not inputs:
            inputs = parse_items_from_table(table)

        if "outputs" in text and not outputs:
            outputs = parse_items_from_table(table)

        if "profit" in text and "inputs" in text:
            profit = extract_profit(table)

    if not profit:
        return None

    title = url.split("/")[-1].replace("_", " ")

    return {
        "name": title,
        "url": url,
        "wiki_profit": profit,
        "inputs": inputs,
        "outputs": outputs
    }


# ---------------------------------------------------------
# GE LIMITS
# ---------------------------------------------------------

def get_ge_limits():

    print("Downloading GE limits...")

    r = requests.get(MAPPING, headers=HEADERS)
    r.raise_for_status()

    data = r.json()

    limits = {}

    for item in data:

        name = item.get("name")
        iid = item.get("id")
        limit = item.get("limit")

        if name and iid:

            limits[name] = {
                "id": iid,
                "limit": limit
            }

    return limits


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    methods_urls = get_all_methods()

    limits = get_ge_limits()

    methods = []

    total = len(methods_urls)

    for i, url in enumerate(methods_urls, start=1):

        print(f"[{i}/{total}]")

        try:

            m = parse_method(url)

            if m:
                methods.append(m)

        except Exception as e:

            print("Error:", e)

    dataset = {
        "updated": datetime.utcnow().isoformat() + "Z",
        "methods": methods,
        "ge_limits": limits
    }

    with open("money_methods.json", "w", encoding="utf-8") as f:

        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print("JSON generado con", len(methods), "métodos.")


if __name__ == "__main__":
    main()
