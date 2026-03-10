import json
import time
import requests

PRICES_API = "https://prices.runescape.wiki/api/v1/osrs/latest"
VOLUMES_API = "https://prices.runescape.wiki/api/v1/osrs/volumes"
UA = {"User-Agent": "OSRS-MoneyHub/1.0"}

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def fetch_prices():
    r = requests.get(PRICES_API, headers=UA)
    r.raise_for_status()
    return r.json()["data"]

def fetch_volumes():
    r = requests.get(VOLUMES_API, headers=UA)
    r.raise_for_status()
    return r.json()["data"]

def get_price(item_name, prices):
    return 0

def compute_profit(method, prices, volumes, ge_limits):
    inputs = method.get("inputs", [])
    outputs = method.get("outputs", [])
    actions = method.get("actions_per_hour_human", 0)

    cost = 0
    for item in inputs:
        price = get_price(item["name"], prices)
        cost += price * item["qty"]

    value = 0
    for item in outputs:
        price = get_price(item["name"], prices)
        value += price * item["qty"]

    profit_per_action = value - cost
    profit_per_hour = profit_per_action * actions

    method["profit_per_hour"] = profit_per_hour
    method["status"] = "ok" if profit_per_hour > 0 else "dead"

def main():
    base = load_json("methods_base.json")
    ge_limits = load_json("ge_limits.json")

    prices = fetch_prices()
    volumes = fetch_volumes()

    methods = base["methods"]

    for m in methods:
        compute_profit(m, prices, volumes, ge_limits)

    methods.sort(key=lambda x: x.get("profit_per_hour", 0), reverse=True)

    final = {
        "updated": int(time.time()),
        "methods": methods
    }

    save_json("money_methods.json", final)

    print("[profit_engine] Listo.")
    print(f"Métodos procesados: {len(methods)}")
    if methods:
        print(f"Top: {methods[0]['n']} → {methods[0]['profit_per_hour']:,} gp/hr")

if __name__ == "__main__":
    main()
