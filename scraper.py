import requests
import json
import time
from bs4 import BeautifulSoup
from datetime import datetime

BASE = "https://oldschool.runescape.wiki"
CATEGORY = BASE + "/wiki/Category:Money_making_guides"

HEADERS = {
    "User-Agent": "osrs-money-hub-bot"
}

MAPPING_URL = "https://prices.runescape.wiki/api/v1/osrs/mapping"


# --------------------------------
# HTTP
# --------------------------------

def fetch(url):

    r = requests.get(url, headers=HEADERS)

    r.raise_for_status()

    time.sleep(0.4)

    return r.text


# --------------------------------
# LOAD ITEM ID MAP
# --------------------------------

def load_item_mapping():

    print("Downloading item mapping")

    r = requests.get(MAPPING_URL)

    data = r.json()

    name_to_id = {}

    ge_limits = {}

    for item in data:

        name = item["name"]

        name_to_id[name] = item["id"]

        ge_limits[name] = item.get("limit")

    with open("ge_limits.json","w") as f:

        json.dump(ge_limits,f)

    return name_to_id


# --------------------------------
# GET MONEY METHOD URLS
# --------------------------------

def get_method_urls():

    urls = []

    next_page = CATEGORY

    while next_page:

        html = fetch(next_page)

        soup = BeautifulSoup(html,"html.parser")

        container = soup.find("div",id="mw-pages")

        if not container:
            break

        for a in container.find_all("a"):

            title = a.get("title")
            href = a.get("href")

            if not title:
                continue

            if not title.startswith("Money making guide/"):
                continue

            url = BASE + href

            if url not in urls:

                urls.append(url)

        next_btn = container.find("a",string="next page")

        if next_btn:

            next_page = BASE + next_btn["href"]

        else:

            next_page = None

    print("Methods found:",len(urls))

    return urls


# --------------------------------
# PARSE ITEMS
# --------------------------------

def parse_items(table, mapping):

    rows = table.find_all("tr")

    items = []

    for r in rows:

        link = r.find("a")

        if not link:
            continue

        name = link.text.strip()

        item_id = mapping.get(name)

        if not item_id:
            continue

        text = r.get_text()

        digits = "".join(c for c in text if c.isdigit())

        qty = 1

        if digits:

            try:

                val = int(digits)

                if val < 100000:

                    qty = val

            except:
                pass

        items.append({
            "id": item_id,
            "qty": qty
        })

    return items


# --------------------------------
# PARSE METHOD PAGE
# --------------------------------

def parse_method(url, mapping):

    html = fetch(url)

    soup = BeautifulSoup(html,"html.parser")

    tables = soup.find_all("table")

    inputs = []
    outputs = []

    for t in tables:

        text = t.get_text().lower()

        if "inputs" in text and not inputs:

            inputs = parse_items(t, mapping)

        if "outputs" in text and not outputs:

            outputs = parse_items(t, mapping)

    name = url.split("/")[-1].replace("_"," ")

    return {

        "n": name,
        "u": url,
        "i": inputs,
        "o": outputs

    }


# --------------------------------
# SCRAPE ALL METHODS
# --------------------------------

def scrape_methods():

    mapping = load_item_mapping()

    urls = get_method_urls()

    methods = []

    for url in urls:

        try:

            m = parse_method(url, mapping)

            methods.append(m)

        except Exception as e:

            print("Error:",e)

    return methods


# --------------------------------
# MAIN
# --------------------------------

def main():

    methods = scrape_methods()

    dataset = {

        "updated": datetime.utcnow().isoformat(),

        "methods": methods

    }

    with open("money_methods.json","w") as f:

        json.dump(dataset,f)

    print("Saved:",len(methods),"methods")


if __name__ == "__main__":

    main()
