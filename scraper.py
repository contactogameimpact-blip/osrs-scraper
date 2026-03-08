import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

BASE_URL = "https://oldschool.runescape.wiki"
CATEGORY_URL = BASE_URL + "/w/Category:Money_making_guides"

HEADERS = {
    "User-Agent": "osrs-money-scraper"
}

# paginas indice que NO son metodos
SKIP_PAGES = [
    "Money making guide/Collecting",
    "Money making guide/Combat",
    "Money making guide/Processing",
    "Money making guide/Recurring",
    "Money making guide/Skilling"
]

def get_method_urls():
    urls = []

    url = CATEGORY_URL

    while True:

        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")

        for link in soup.select("#mw-pages a"):

            title = link.get("title")

            if not title:
                continue

            if not title.startswith("Money making guide/"):
                continue

            if title in SKIP_PAGES:
                continue

            page_url = BASE_URL + link.get("href")

            urls.append(page_url)

        next_link = soup.select_one("a:contains('next page')")

        if not next_link:
            break

        url = BASE_URL + next_link.get("href")

        time.sleep(1)

    # eliminar duplicados
    urls = list(set(urls))

    return urls


def parse_items(table):

    items = []

    for row in table.select("tr")[1:]:

        cols = row.find_all("td")

        if len(cols) < 2:
            continue

        name = cols[0].get_text(strip=True)

        qty_text = cols[1].get_text(strip=True)

        try:
            qty = int(qty_text.replace(",", ""))
        except:
            qty = 1

        items.append({
            "name": name,
            "qty": qty
        })

    return items


def parse_method(url):

    r = requests.get(url, headers=HEADERS)

    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.select_one("#firstHeading").text.replace("Money making guide/", "")

    tables = soup.select("table")

    inputs = []
    outputs = []

    for table in tables:

        headers = [th.get_text(strip=True).lower() for th in table.select("th")]

        if any("input" in h or "required" in h or "cost" in h for h in headers):
            inputs = parse_items(table)

        if any("output" in h or "profit" in h or "reward" in h for h in headers):
            outputs = parse_items(table)

    return {
        "n": title,
        "u": url,
        "i": inputs,
        "o": outputs
    }


def scrape():

    urls = get_method_urls()

    print("Found methods:", len(urls))

    methods = []

    for i, url in enumerate(urls):

        print("Scraping", i + 1, "/", len(urls))

        try:
            method = parse_method(url)
            methods.append(method)
        except Exception as e:
            print("Error:", e)

        time.sleep(1)

    data = {
        "updated": datetime.utcnow().isoformat(),
        "methods": methods
    }

    with open("money_methods.json", "w", encoding="utf8") as f:
        json.dump(data, f, indent=2)

    print("Saved:", len(methods), "methods")


if __name__ == "__main__":
    scrape()
