import requests
import json
import time
from bs4 import BeautifulSoup
from datetime import datetime

BASE = "https://oldschool.runescape.wiki"
CATEGORY = BASE + "/wiki/Category:Money_making_guides"

HEADERS = {
    "User-Agent": "osrs-money-scraper"
}


def fetch(url):

    r = requests.get(url, headers=HEADERS)

    r.raise_for_status()

    time.sleep(0.4)

    return r.text


def get_method_urls():

    urls = []

    next_page = CATEGORY

    while next_page:

        print("Fetching category:", next_page)

        html = fetch(next_page)

        soup = BeautifulSoup(html, "html.parser")

        container = soup.find("div", id="mw-pages")

        if not container:
            break

        for a in container.find_all("a"):

            title = a.get("title")
            href = a.get("href")

            if not title or not href:
                continue

            if "Money making guide/" in title:

                url = BASE + href

                if url not in urls:

                    urls.append(url)

        next_btn = container.find("a", string="next page")

        if next_btn:

            next_page = BASE + next_btn["href"]

        else:

            next_page = None

    print("Total methods:", len(urls))

    return urls


def parse_items(table):

    items = []

    rows = table.find_all("tr")

    for r in rows:

        link = r.find("a")

        if not link:
            continue

        name = link.text.strip()

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
            "item": name,
            "qty": qty
        })

    return items


def parse_method(url):

    print("Parsing:", url)

    html = fetch(url)

    soup = BeautifulSoup(html, "html.parser")

    tables = soup.find_all("table")

    inputs = []
    outputs = []

    for t in tables:

        text = t.get_text().lower()

        if "inputs" in text and not inputs:

            inputs = parse_items(t)

        if "outputs" in text and not outputs:

            outputs = parse_items(t)

    name = url.split("/")[-1].replace("_", " ")

    return {
        "name": name,
        "url": url,
        "inputs": inputs,
        "outputs": outputs
    }


def download_ge_limits():

    print("Downloading GE limits")

    url = "https://prices.runescape.wiki/api/v1/osrs/mapping"

    r = requests.get(url)

    data = r.json()

    limits = {}

    for item in data:

        name = item["name"]

        limit = item.get("limit")

        limits[name] = limit

    with open("ge_limits.json", "w") as f:

        json.dump(limits, f)

    print("GE limits:", len(limits))


def scrape_methods():

    urls = get_method_urls()

    methods = []

    for url in urls:

        try:

            m = parse_method(url)

            methods.append(m)

        except Exception as e:

            print("Error:", e)

    return methods


def main():

    methods = scrape_methods()

    dataset = {
        "updated": datetime.utcnow().isoformat(),
        "methods": methods
    }

    with open("money_methods.json", "w", encoding="utf-8") as f:

        json.dump(dataset, f)

    print("Saved methods:", len(methods))

    download_ge_limits()


if __name__ == "__main__":
    main()
