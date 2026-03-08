import json
import time
import re
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://oldschool.runescape.wiki"
MM_GUIDE_URL = f"{BASE_URL}/w/Money_making_guide"


def fetch(url: str) -> str:
    print(f"[fetch] {url}")
    resp = requests.get(url, headers={"User-Agent": "OSRS-MoneyHub/1.0"})
    resp.raise_for_status()
    return resp.text


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_method_links(html: str) -> List[str]:
    """
    Extrae SOLO métodos reales:
    /w/Money_making_guide/NOMBRE_DEL_MÉTODO
    Ignora talk pages, categorías, índices, secciones, etc.
    """
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []

    for a in soup.select("a"):
        href = a.get("href", "")
        if not href.startswith("/w/Money_making_guide/"):
            continue

        # Filtrar basura: Talk:, Special:, File:, Category:, etc.
        if ":" in href:
            continue
        # Anclas internas
        if "#" in href:
            continue
        # /w/Money_making_guide (sin método)
        if href.count("/") <= 2:
            continue

        full = BASE_URL + href
        if full not in links:
            links.append(full)

    print(f"[parse_method_links] Métodos REALES encontrados: {len(links)}")
    return links


def parse_table_rows(table) -> List[Dict[str, Any]]:
    """
    Intenta leer filas de una tabla de inputs/outputs.
    Busca columnas tipo 'Item' y 'Quantity'.
    """
    rows_data: List[Dict[str, Any]] = []
    headers = [clean_text(th.get_text()) for th in table.select("tr th")]
    if not headers:
        return rows_data

    item_idx = None
    qty_idx = None
    for i, h in enumerate(headers):
        h_low = h.lower()
        if "item" in h_low or "name" in h_low:
            item_idx = i
        if "qty" in h_low or "quantity" in h_low or "amount" in h_low:
            qty_idx = i

    if item_idx is None:
        return rows_data

    for tr in table.select("tr")[1:]:
        cells = tr.select("td")
        if not cells:
            continue
        if len(cells) <= item_idx:
            continue
        name = clean_text(cells[item_idx].get_text())
        if not name:
            continue
        qty = 1
        if qty_idx is not None and len(cells) > qty_idx:
            qty_text = clean_text(cells[qty_idx].get_text())
            m = re.search(r"([\d,]+)", qty_text)
            if m:
                qty = int(m.group(1).replace(",", ""))
        rows_data.append({
            "name": name,
            "qty": qty
        })

    return rows_data


def detect_type_from_title(title: str) -> str:
    t = title.lower()
    if "killing" in t or "kill" in t:
        return "kill"
    if any(x in t for x in ["crafting", "fletching", "smithing", "cooking", "herblore", "making"]):
        return "craft"
    if any(x in t for x in ["gathering", "mining", "woodcutting", "fishing", "collecting"]):
        return "gather"
    return "other"


def parse_actions_per_hour(text: str) -> int:
    """
    Intenta encontrar algo tipo '2,450 per hour' y extraer ese número.
    """
    m = re.search(r"([\d,]+)\s+per hour", text, flags=re.IGNORECASE)
    if not m:
        return 0
    return int(m.group(1).replace(",", ""))


def parse_method_page(url: str) -> Dict[str, Any] | None:
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("#firstHeading")
    title = clean_text(title_el.get_text()) if title_el else url

    page_text = clean_text(soup.get_text(" "))

    actions_wiki = parse_actions_per_hour(page_text)

    inputs: List[Dict[str, Any]] = []
    outputs: List[Dict[str, Any]] = []

    # Heurística: tablas con caption que contenga 'Input' o 'Output'
    for table in soup.select("table"):
        caption = table.find("caption")
        caption_text = clean_text(caption.get_text()) if caption else ""
        cap_low = caption_text.lower()
        if "input" in cap_low:
            inputs.extend(parse_table_rows(table))
        elif "output" in cap_low or "profit" in cap_low:
            outputs.extend(parse_table_rows(table))

    # Si no tiene inputs ni outputs, no lo consideramos método real
    if not inputs and not outputs:
        print(f"[parse_method_page] Ignorado (sin inputs/outputs): {url}")
        return None

    method_type = detect_type_from_title(title)

    data: Dict[str, Any] = {
        "n": title,
        "u": url,
        "type": method_type,
        "actions_per_hour_wiki": actions_wiki,
        "actions_per_hour_human": 0,  # se ajustará en el motor de profit
        "inputs": inputs,
        "outputs": outputs,
        "ge_limits": {
            "inputs": {},
            "outputs": {}
        },
        "volume": {
            "inputs": {},
            "outputs": {}
        },
        "profit_per_hour": 0,
        "status": "raw"
    }

    print(f"[parse_method_page] {title} | inputs={len(inputs)} outputs={len(outputs)} wiki_actions={actions_wiki}")
    return data


def main():
    print("[scraper] Cargando Money Making Guide...")
    index_html = fetch(MM_GUIDE_URL)
    links = parse_method_links(index_html)

    methods: List[Dict[str, Any]] = []
    for i, url in enumerate(links, start=1):
        print(f"\n[scraper] ({i}/{len(links)}) Procesando método: {url}")
        try:
            m = parse_method_page(url)
            if not m:
                continue
            methods.append(m)
        except Exception as e:
            print(f"[scraper] ERROR en {url}: {e}")

        time.sleep(1)  # ser amable con la wiki

    data = {
        "updated": int(time.time()),
        "methods": methods
    }

    with open("money_methods.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("\n[scraper] Listo.")
    print(f"  Total métodos: {len(methods)}")


if __name__ == "__main__":
    main()
