import json
import re
import time
import requests
from bs4 import BeautifulSoup

WIKI_BASE   = "https://oldschool.runescape.wiki"
WIKI_MMG    = "https://oldschool.runescape.wiki/w/Money_making_guide"
PRICES_URL  = "https://prices.runescape.wiki/api/v1/osrs/latest"
HEADERS     = {"User-Agent": "OSRSMoneyHub/2.0 (github.com/contactogameimpact-blip)"}

# ─────────────────────────────────────────
# 1. Fetch live GE prices
# ─────────────────────────────────────────
print("Fetching live prices...")
prices = requests.get(PRICES_URL, headers=HEADERS).json().get("data", {})
print(f"  {len(prices)} items loaded")

def get_price(item_id):
    p = prices.get(str(item_id), {})
    high = p.get("high") or 0
    low  = p.get("low")  or 0
    if high and low:
        return (high + low) // 2
    return high or low

# ─────────────────────────────────────────
# 2. Scrape the MMG table from the wiki
# ─────────────────────────────────────────
print("Scraping OSRS wiki money making guide...")
resp = requests.get(WIKI_MMG, headers=HEADERS, timeout=30)
soup = BeautifulSoup(resp.text, "html.parser")

methods = []

# The wiki MMG page has tables with rows for each method
for table in soup.select("table.wikitable"):
    for row in table.select("tr"):
        cols = row.select("td")
        if len(cols) < 3:
            continue

        # Column 0: method name + link
        name_cell = cols[0]
        a_tag = name_cell.find("a")
        if not a_tag:
            continue

        name = a_tag.get_text(strip=True)
        href = a_tag.get("href", "")
        url  = WIKI_BASE + href if href.startswith("/") else href

        # Column: profit per hour (look for a cell with "gp" or number)
        profit_per_hour = 0
        for col in cols:
            text = col.get_text(strip=True).replace(",", "").replace(" ", "")
            # Look for profit column (usually contains a plain number)
            match = re.match(r"^-?(\d+)$", text)
            if match:
                val = int(match.group(1))
                if val > 1000:  # skip small numbers like skill levels
                    profit_per_hour = val
                    break

        if not name:
            continue

        methods.append({
            "n": name,
            "u": url,
            "profit_per_hour": profit_per_hour,
            "inputs":  [],
            "outputs": []
        })

print(f"  {len(methods)} methods scraped from wiki table")

# ─────────────────────────────────────────
# 3. If wiki scrape got 0 methods, fall back
#    to parsing the existing JSON profit text
# ─────────────────────────────────────────
if len(methods) == 0:
    print("Wiki table scrape returned 0 — falling back to existing JSON...")
    with open("money_methods.json") as f:
        existing = json.load(f)

    methods = []
    for m in existing.get("methods", []):
        profit = parse_profit_from_existing(m)
        methods.append({
            "n": m.get("n") or m.get("name") or "Unknown",
            "u": m.get("u") or m.get("url") or "#",
            "profit_per_hour": profit,
            "inputs":  m.get("i") or m.get("inputs") or [],
            "outputs": m.get("o") or m.get("outputs") or []
        })

def parse_profit_from_existing(m):
    """
    The current JSON stores aftertax profit as a name string like:
    '1,248,000, aftertax'
    We extract the number from that string.
    """
    for field in ["o", "outputs", "i", "inputs"]:
        items = m.get(field) or []
        for item in items:
            name = item.get("name", "")
            if "aftertax" in name.lower():
                clean = name.replace(",", "")
                match = re.match(r"(\d+)", clean.strip())
                if match:
                    return int(match.group(1))
    return 0

# ─────────────────────────────────────────
# 4. If wiki scrape got methods but profit=0,
#    parse profit from existing JSON aftertax
# ─────────────────────────────────────────
zero_count = sum(1 for m in methods if m["profit_per_hour"] == 0)
if zero_count > len(methods) * 0.5:
    print(f"  {zero_count} methods have 0 profit — reading aftertax from existing JSON...")
    with open("money_methods.json") as f:
        existing = json.load(f)

    # Build lookup by name
    existing_map = {}
    for m in existing.get("methods", []):
        key = (m.get("n") or m.get("name") or "").lower().strip()
        existing_map[key] = m

    for m in methods:
        if m["profit_per_hour"] == 0:
            key = m["n"].lower().strip()
            ex  = existing_map.get(key)
            if ex:
                m["profit_per_hour"] = parse_profit_from_existing(ex)
                m["inputs"]  = ex.get("i") or ex.get("inputs") or []
                m["outputs"] = ex.get("o") or ex.get("outputs") or []

# ─────────────────────────────────────────
# 5. Sort by profit descending
# ─────────────────────────────────────────
methods.sort(key=lambda x: x["profit_per_hour"], reverse=True)

# ─────────────────────────────────────────
# 6. Save
# ─────────────────────────────────────────
output = {
    "updated": int(time.time()),
    "methods": methods
}

with open("money_methods.json", "w") as f:
    json.dump(output, f, indent=2)

non_zero = sum(1 for m in methods if m["profit_per_hour"] > 0)
print(f"\nDone!")
print(f"  Total methods    : {len(methods)}")
print(f"  With profit > 0  : {non_zero}")
print(f"  Top method       : {methods[0]['n']} ({methods[0]['profit_per_hour']:,} gp/hr)")
