import json
import time
import re
import requests
from typing import Dict, Any, List

API = "https://oldschool.runescape.wiki/api.php"
UA = {"User-Agent": "OSRS-MoneyHub/1.0"}

# ---------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------

def api_get(params: Dict[str, Any]) -> Dict[str, Any]:
    params["format"] = "json"
    resp = requests.get(API, params=params, headers=UA)
    resp.raise_for_status()
    return resp.json()

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

# ---------------------------------------------------------
# 1. DESCUBRIR TODAS LAS SUBPÁGINAS DE MONEY MAKING
# ---------------------------------------------------------

def discover_method_pages() -> List[str]:
    pages = []
    apcontinue = None

    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "apnamespace": 0,
            "aplimit": "500",
            "apprefix": "Money_making_guide/"
        }
        if apcontinue:
            params["apcontinue"] = apcontinue

        data = api_get(params)
        for p in data["query"]["allpages"]:
            title = p["title"]
            # Filtrar páginas índice
            if title.count("/") < 2:
                continue
            pages.append(title)

        if "continue" in data:
            apcontinue = data["continue"]["apcontinue"]
        else:
            break

    print(f"[discover] Encontradas {len(pages)} páginas de métodos")
    return pages

# ---------------------------------------------------------
# 2. OBTENER WIKITEXT DE CADA PÁGINA
# ---------------------------------------------------------

def get_wikitext(title: str) -> str:
    data = api_get({
        "action": "parse",
        "page": title,
        "prop": "wikitext"
    })
    return data["parse"]["wikitext"]["*"]

# ---------------------------------------------------------
# 3. PARSEAR PLANTILLAS DE MÉTODOS
# ---------------------------------------------------------

TEMPLATE_ROW = re.compile(
    r"\{\{Money making guide/Row(.*?)\}\}",
    re.DOTALL | re.IGNORECASE
)

FIELD = re.compile(
    r"\|\s*([a-zA-Z0-9_]+)\s*=\s*(.*?)\s*(?=\n\||\n\}\}|$)",
    re.DOTALL
)

def parse_row_template(block: str) -> Dict[str, Any]:
    fields = dict(FIELD.findall(block))

    name = clean(fields.get("title", fields.get("name", "")))

    inputs = []
    outputs = []

    # Detectar inputs item1, qty1, item2, qty2...
    for i in range(1, 10):
        item = fields.get(f"item{i}")
        qty = fields.get(f"qty{i}")
        if item:
            try:
                qty = int(qty.replace(",", "")) if qty else 1
            except:
                qty = 1
            inputs.append({"name": clean(item), "qty": qty})

    # Detectar producto
    product = fields.get("product")
    if product:
        outputs.append({"name": clean(product), "qty": 1})

    # Acciones por hora
    actions = fields.get("actions") or fields.get("rate") or "0"
    try:
        actions = int(actions.replace(",", ""))
    except:
        actions = 0

    return {
        "n": name,
        "inputs": inputs,
        "outputs": outputs,
        "actions_per_hour_wiki": actions
    }

# ---------------------------------------------------------
# 4. PARSEAR UNA PÁGINA COMPLETA
# ---------------------------------------------------------

def parse_method_page(title: str) -> List[Dict[str, Any]]:
    wikitext = get_wikitext(title)

    rows = TEMPLATE_ROW.findall(wikitext)
    methods = []

    for block in rows:
        m = parse_row_template(block)
        if not m["inputs"] and not m["outputs"]:
            continue
        m["u"] = f"https://oldschool.runescape.wiki/w/{title.replace(' ', '_')}"
        m["type"] = "other"
        m["actions_per_hour_human"] = 0
        m["ge_limits"] = {"inputs": {}, "outputs": {}}
        m["volume"] = {"inputs": {}, "outputs": {}}
        m["profit_per_hour"] = 0
        m["status"] = "raw"
        methods.append(m)

    print(f"[parse] {title}: {len(methods)} métodos")
    return methods

# ---------------------------------------------------------
# 5. MAIN
# ---------------------------------------------------------

def main():
    print("[scraper] Descubriendo métodos…")
    pages = discover_method_pages()

    all_methods = []

    for i, title in enumerate(pages, 1):
        print(f"\n[scraper] ({i}/{len(pages)}) {title}")
        try:
            methods = parse_method_page(title)
            all_methods.extend(methods)
        except Exception as e:
            print(f"[scraper] ERROR en {title}: {e}")
        time.sleep(1)

    data = {
        "updated": int(time.time()),
        "methods": all_methods
    }

    with open("money_methods.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("\n[scraper] COMPLETADO")
    print(f"Total métodos: {len(all_methods)}")


if __name__ == "__main__":
    main()
