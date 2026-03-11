import json
import time
import requests

PRICES_API = "https://prices.runescape.wiki/api/v1/osrs/latest"
VOLUMES_API = "https://prices.runescape.wiki/api/v1/osrs/volumes"

HEADERS = {
    "User-Agent": "OSRS-MoneyEngine"
}

GE_TAX = 0.01


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def fetch_prices():
    r = requests.get(PRICES_API, headers=HEADERS)
    r.raise_for_status()
    return r.json()["data"]


def fetch_volumes():
    r = requests.get(VOLUMES_API, headers=HEADERS)
    r.raise_for_status()
    return r.json()["data"]


def get_price(name, prices, items_map):

    item_id = items_map.get(name)

    if not item_id:
        return 0

    info = prices.get(str(item_id))

    if not info:
        return 0

    return info.get("high", 0)


def get_volume(name, volumes, items_map):

    item_id = items_map.get(name)

    if not item_id:
        return 0

    info = volumes.get(str(item_id))

    if not info:
        return 0

    if isinstance(info, int):
        return info

    if isinstance(info, dict):
        return info.get("volume", 0)

    return 0


def apply_ge_tax(value):

    return value * (1 - GE_TAX)


def compute_profit(method, prices, volumes, ge_limits, items_map):

    inputs = method.get("inputs", [])
    outputs = method.get("outputs", [])
    actions = method.get("actions_per_hour_human", 0)

    cost = 0

    for item in inputs:

        price = get_price(item["name"], prices, items_map)
        cost += price * item["qty"]

    value = 0

    for item in outputs:

        price = get_price(item["name"], prices, items_map)
        value += price * item["qty"]

    value = apply_ge_tax(value)

    profit_action = value - cost

    requires_prebuy = False

    for item in inputs:

        name = item["name"]

        if name in ge_limits:

            limit = ge_limits[name] / 4
            possible = limit / item["qty"]

            if possible < actions:
                requires_prebuy = True

            actions = min(actions, possible)

    market_saturated = False

    if outputs:

        out_name = outputs[0]["name"]

        daily_volume = get_volume(out_name, volumes, items_map)

        if daily_volume > 0:

            sell_hour = daily_volume / 24

            if sell_hour < actions:
                market_saturated = True

            actions = min(actions, sell_hour)

    profit_hour = int(profit_action * actions)

    score = profit_hour / 1000

    if market_saturated:
        score *= 0.5

    if requires_prebuy:
        score *= 0.7

    if profit_hour <= 0:
        status = "dead"

    elif market_saturated:
        status = "market_saturated"

    elif requires_prebuy:
        status = "requires_prebuy"

    else:
        status = "ok"

    method["profit_per_action"] = int(profit_action)
    method["profit_per_hour"] = profit_hour
    method["real_actions_per_hour"] = int(actions)
    method["requires_prebuy"] = requires_prebuy
    method["market_saturated"] = market_saturated
    method["score"] = round(score, 2)
    method["status"] = status


def main():

    base = load_json("methods_base.json")
    ge_limits = load_json("data/ge_limits.json")
    items_map = load_json("data/items_map.json")

    prices = fetch_prices()
    volumes = fetch_volumes()

    methods = base.get("methods", [])

    for m in methods:

        compute_profit(m, prices, volumes, ge_limits, items_map)

    methods.sort(key=lambda x: x.get("score", 0), reverse=True)

    final = {
        "updated": int(time.time()),
        "methods": methods
    }

    save_json("money_methods.json", final)

    print("engine completo")
    print("metodos:", len(methods))


if __name__ == "__main__":
    main()
