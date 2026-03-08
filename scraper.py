import json
import requests
import time
from datetime import datetime

PRICES_URL = "https://prices.runescape.wiki/api/v1/osrs/latest"

print("Loading methods...")
with open("money_methods.json") as f:
    data = json.load(f)

with open("ge_limits.json") as f:
    ge_limits = json.load(f)

print("Fetching prices...")
prices = requests.get(PRICES_URL).json()["data"]

def get_buy_price(id):
    p = prices.get(str(id), {})
    return p.get("high",0)

def get_sell_price(id):
    p = prices.get(str(id), {})
    return p.get("low",0)

def calc_input_cost(inputs):
    total = 0
    for i in inputs:
        total += get_buy_price(i["id"]) * i.get("qty",1)
    return total

def calc_expected_drops(drops):
    total = 0
    for d in drops:
        price = get_sell_price(d["id"])
        chance = d.get("chance",1)
        qty = d.get("qty",1)
        total += price * qty * chance
    return total

def apply_ge_limit(outputs, profit):
    capped_profit = profit
    for o in outputs:
        item_id = str(o["id"])
        if item_id in ge_limits:
            limit_per_hour = ge_limits[item_id] / 4
            item_price = get_sell_price(o["id"])
            max_gp = item_price * limit_per_hour
            capped_profit = min(capped_profit, max_gp)
    return capped_profit

methods = data["methods"]

for m in methods:

    inputs = m.get("inputs",[])
    drops = m.get("drops",[])
    actions = m.get("actions_per_hour",1)

    cost = calc_input_cost(inputs)
    expected = calc_expected_drops(drops)

    profit_action = expected - cost
    profit_hour = profit_action * actions

    profit_hour = apply_ge_limit(drops,profit_hour)

    m["profit_per_hour"] = int(profit_hour)

data["updated"] = int(time.time())

with open("money_methods.json","w") as f:
    json.dump(data,f,indent=2)

print("Methods updated:",len(methods))
