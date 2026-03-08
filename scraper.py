import requests
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup

BASE = "https://oldschool.runescape.wiki"
CATEGORY = BASE + "/wiki/Category:Money_making_guides"
GE_MAPPING = "https://prices.runescape.wiki/api/v1/osrs/mapping"

HEADERS = {
    "User-Agent": "OSRS-Money-Making-Scraper"
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
# CRAWLER
# ---------------------------------------------------------

def get_all_methods():

    methods = []
    next_page = CATEGORY

    while next_page:

        html = fetch(next_page)
        soup = BeautifulSoup(html, "html.parser")

        cat = soup.find("div", id="mw-pages")

        if not cat:
            break

        for a in cat.find_all("a"):

            title = a.get("title")
            href = a.get("href")

            if not title or not href:
                continue

            if "Money making guide/" in title:

                url = BASE + href

                if url not in methods:
                    methods.append(url)

        next_btn = cat.find("a", string="next page")

        if next_btn:
            next_page = BASE + next_btn.get("href")
        else:
            next_page = None

    print("Métodos encontrados:", len(methods))

    return methods


# ---------------------------------------------------------
# PROFIT
# ---------------------------------------------------------

def extract_profit(soup):

    rows = soup.find_all("tr")

    for r in rows:

        th = r.find("th")

        if not th:
            continue

        label = th.get_text().lower()

        if "profit" in label:

            td = r.find("td")

            if not td:
                continue

            text = td.get_text()

            digits = "".join(c for c in text if c.isdigit())

            if digits:

                try:
                    val = int(digits)

                    if 0 < val < 50_000_000:
                        return val

                except:
                    pass

    return None


# ---------------------------------------------------------
# ITEMS
# ---------------------------------------------------------

def extract_items(section_table):

    items = []

    rows = section_table.find_all("tr")

    for r in rows:

        links = r.find_all("a")

        if not links:
            continue

        name = links[-1].get_text().strip()

        text = r.get_text()

        qty = 1

        digits = "".join(c for c in text if c.isdigit())

        if digits:

            try:
                q = int(digits)

                if q < 100000:
                    qty = q

            except:
                pass

        items.append({
            "item": name,
            "qty": qty
        })

    return items


# ---------------------------------------------------------
# FIND INPUTS / OUTPUTS
# ---------------------------------------------------------

def extract_io(soup):

    inputs = []
    outputs = []

    tables = soup.find_all("table")

    for table in tables:

        text = table.get_text().lower()

        if "inputs" in text and not inputs:
            inputs = extract_items(table)

        if "outputs" in text and not outputs:
            outputs = extract_items(table)

    return inputs, outputs


# ---------------------------------------------------------
# PARSE METHOD
# ---------------------------------------------------------

def parse_method(url):

    print("Parsing:", url)

    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    profit = extract_profit(soup)

    inputs, outputs = extract_io(soup)

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

    r = requests.get(GE_MAPPING, headers=HEADERS)
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

    print("Dataset generado con", len(methods), "métodos.")


if __name__ == "__main__":
    main()
