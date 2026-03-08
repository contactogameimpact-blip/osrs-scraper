import json
import time
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

BASE = "https://oldschool.runescape.wiki"
UA = {"User-Agent": "OSRS-MoneyHub/1.0"}

# ---------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------

def fetch(url: str) -> str:
    resp = requests.get(url, headers=UA)
    resp.raise_for_status()
    return resp.text

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def is_item_name(text: str) -> bool:
    """Detecta si una celda parece un ítem real."""
    if not text:
        return False
    if re.match(r"^[\d\.\-]+$", text):
        return False
    if len(text) < 2:
        return False
    return True

def is_quantity(text: str) -> bool:
    """Detecta si una celda parece una cantidad."""
    return bool(re.match(r"^[\d,]+$", text))

# ---------------------------------------------------------
# 1. DESCUBRIR TODAS LAS SUBPÁGINAS
# ---------------------------------------------------------

SUBPAGES = [
    "/w/Money_making_guide/Combat",
    "/w/Money_making_guide/Skilling",
    "/w/Money_making_guide/Processing",
    "/w/Money_making_guide/Collecting",
    "/w/Money_making_guide/Recurring",
    "/w/Money_making_guide/Free-to-play"
]

def discover_method_links() -> List[str]:
    links = []

    for sub in SUBPAGES:
        html = fetch(BASE + sub)
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.select("a"):
            href = a.get("href", "")
            if not href.startswith("/w/Money_making_guide/"):
                continue
            if ":" in href:
                continue
            if "#" in href:
                continue
            if href.count("/") <= 2:
                continue

            full = BASE + href
            if full not in links:
                links.append(full)

    print(f"[discover] Métodos encontrados: {len(links)}")
    return links

# ---------------------------------------------------------
# 2. PARSEAR TABLAS DE ÍTEMS
# ---------------------------------------------------------

def parse_item_table(table) -> Dict[str, List[Dict[str, Any]]]:
    headers = [clean(th.get_text()) for th in table.select("tr th")]
    if not headers:
        return {"inputs": [], "outputs": []}

    # Detectar columnas relevantes
    item_col = None
    qty_col = None

    for i, h in enumerate(headers):
        h_low = h.lower()
        if any(x in h_low for x in ["item", "name", "material", "product"]):
            item_col = i
        if any(x in h_low for x in ["qty", "quantity", "amount"]):
            qty_col = i

    if item_col is None:
        return {"inputs": [], "outputs": []}

    rows = []
    for tr in table.select("tr")[1:]:
        cells = tr.select("td")
        if not cells or len(cells) <= item_col:
            continue

        item = clean(cells[item_col].get_text())
        if not is_item_name(item):
            continue

        qty = 1
        if qty_col is not None and len(cells) > qty_col:
            qtext = clean(cells[qty_col].get_text())
            if is_quantity(qtext):
                qty = int(qtext.replace(",", ""))

        rows.append({"name": item, "qty": qty})

    # Heurística: si la tabla tiene más de 1 ítem, es válida
    if len(rows) == 0:
        return {"inputs": [], "outputs": []}

    # Heurística: si el título de la tabla contiene "input", "material", etc.
    caption = table.find("caption")
    cap = clean(caption.get_text()) if caption else ""

    if any(x in cap.lower() for x in ["input", "material", "required"]):
        return {"inputs": rows, "outputs": []}

    if any(x in cap.lower() for x in ["output", "product", "result"]):
        return {"inputs": [], "outputs": rows}

    # Si no hay caption, asumimos que la primera tabla es inputs y la segunda outputs
    return {"inputs": rows, "outputs": []}

# ---------------------------------------------------------
# 3. PARSEAR UNA PÁGINA COMPLETA
# ---------------------------------------------------------

def parse_method_page(url: str) -> Dict[str, Any] | None:
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("#firstHeading")
    title = clean(title_el.get_text()) if title_el else url

    inputs = []
    outputs = []

    tables = soup.select("table")
    for table in tables:
        parsed = parse_item_table(table)
        if parsed["inputs"]:
            inputs.extend(parsed["inputs"])
        if parsed["outputs"]:
            outputs.extend(parsed["outputs"])

    # Si no hay inputs ni outputs → no es método real
    if not inputs and not outputs:
        print(f"[skip] {title} (sin ítems)")
        return None

    return {
        "n": title,
        "u": url,
        "type": "other",
        "actions_per_hour_wiki": 0,
        "actions_per_hour_human": 0,
        "inputs": inputs,
        "outputs": outputs,
        "ge_limits": {"inputs": {}, "outputs": {}},
        "volume": {"inputs": {}, "outputs": {}},
        "profit_per_hour": 0,
        "status": "raw"
    }

# ---------------------------------------------------------
# 4. MAIN
# ---------------------------------------------------------

def main():
    print("[scraper] Descubriendo métodos…")
    links = discover_method_links()

    methods = []

    for i, url in enumerate(links, 1):
        print(f"[scraper] ({i}/{len(links)}) {url}")
        try:
            m = parse_method_page(url)
            if m:
                methods.append(m)
        except Exception as e:
            print(f"[ERROR] {url}: {e}")

        time.sleep(1)

    data = {
        "updated": int(time.time()),
        "methods": methods
    }

    with open("money_methods.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n[scraper] COMPLETADO — Métodos finales: {len(methods)}")


if __name__ == "__main__":
    main()
