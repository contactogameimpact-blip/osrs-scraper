import json
import time
from typing import Dict, Any, List
import requests

PRICES_API = "https://prices.runescape.wiki/api/v1/osrs/latest"
VOLUMES_API = "https://prices.runescape.wiki/api/v1/osrs/volumes"
USER_AGENT = "OSRS-MoneyHub/1.0"


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fetch_prices() -> Dict[str, Dict[str, Any]]:
    print("[prices] Descargando precios...")
    resp = requests.get(PRICES_API, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    data = resp.json().get("data", {})
    return data  # { "item_id": { "high": ..., "low": ... }, ... }


def fetch_volumes() -> Dict[str, int]:
    print("[volumes] Descargando volúmenes...")
    resp = requests.get(VOLUMES_API, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    data = resp.json().get("data", {})
    return data  # { "item_id": volume, ... }


def build_name_to_limit(ge_limits: Dict[str, Any]) -> Dict[str, int]:
    """
    Tu ge_limits.json viene como { "Item name": limit, ... }
    """
    out: Dict[str, int] = {}
    for name, limit in ge_limits.items():
        if limit is None:
            continue
        out[name.lower()] = int(limit)
    return out


def get_price_for_name(name: str, prices: Dict[str, Dict[str, Any]]) -> int:
    """
    Placeholder: sin mapping nombre→ID, no podemos usar bien la API.
    De momento devuelve 0 para no romper el flujo.
    Cuando tengas mapping, aquí se conecta.
    """
    return 0


def default_human_actions(method: Dict[str, Any]) -> int:
    t = method.get("type", "other")
    wiki = method.get("actions_per_hour_wiki") or 0

    if t == "craft":
        return min(wiki, 2000) if wiki > 0 else 2000
    if t == "kill":
        return min(wiki, 80) if wiki > 0 else 80
    if t == "gather":
        return min(wiki, 1200) if wiki > 0 else 1200
    return wiki if wiki > 0 else 1000


def compute_profit_for_method(
    m: Dict[str, Any],
    ge_limits_by_name: Dict[str, int],
    prices: Dict[str, Dict[str, Any]],
    volumes: Dict[str, int]
) -> None:
    inputs = m.get("inputs", [])
    outputs = m.get("outputs", [])

    input_cost = 0
    for item in inputs:
        name = item.get("name", "")
        qty = item.get("qty", 1)
        price = get_price_for_name(name, prices)
        input_cost += price * qty

    output_value = 0
    for item in outputs:
        name = item.get("name", "")
        qty = item.get("qty", 1)
        price = get_price_for_name(name, prices)
        output_value += price * qty

    profit_per_action = output_value - input_cost

    human_actions = default_human_actions(m)
    m["actions_per_hour_human"] = human_actions

    caps: List[int] = []

    for item in inputs:
        name = item.get("name", "")
        qty = item.get("qty", 1)
        limit = ge_limits_by_name.get(name.lower())
        if limit:
            max_actions = (limit / 4) / max(qty, 1)
            caps.append(int(max_actions))

    for item in outputs:
        name = item.get("name", "")
        qty = item.get("qty", 1)
        limit = ge_limits_by_name.get(name.lower())
        if limit:
            max_actions = (limit / 4) / max(qty, 1)
            caps.append(int(max_actions))

    if caps:
        actions_final = min(human_actions, max(caps))
        capped = True
    else:
        actions_final = human_actions
        capped = False

    if actions_final <= 0 or profit_per_action <= 0:
        m["profit_per_hour"] = 0
        m["status"] = "dead"
        return

    profit_per_hour = int(profit_per_action * actions_final)
    m["profit_per_hour"] = profit_per_hour
    m["status"] = "capped_by_limit" if capped else "ok"


def main():
    print("[profit_engine] Cargando JSON crudo...")
    data = load_json("money_methods.json")
    methods = data.get("methods", [])

    print("[profit_engine] Cargando GE limits...")
    ge_limits = load_json("ge_limits.json")
    ge_limits_by_name = build_name_to_limit(ge_limits)

    print("[profit_engine] Descargando precios y volúmenes...")
    prices = fetch_prices()
    volumes = fetch_volumes()

    con_profit = 0

    for m in methods:
        compute_profit_for_method(m, ge_limits_by_name, prices, volumes)
        if m.get("profit_per_hour", 0) > 0:
            con_profit += 1

    methods.sort(key=lambda x: x.get("profit_per_hour", 0), reverse=True)

    data["updated"] = int(time.time())
    data["methods"] = methods

    save_json("money_methods.json", data)

    print("\n[profit_engine] Listo.")
    print(f"  Total métodos     : {len(methods)}")
    print(f"  Con profit > 0    : {con_profit}")
    if methods:
        best = methods[0]
        print(f"  Mejor método      : {best.get('n', '?')} ({best.get('profit_per_hour', 0):,} gp/hr)")


if __name__ == "__main__":
    main()
