import json
import requests
import time
from datetime import datetime

PRICES_URL = "https://prices.runescape.wiki/api/v1/osrs/latest"

with open("money_methods.json") as f:
    data = json.load(f)

with open("ge_limits.json") as f:
    ge_limits = json.load(f)

print("Fetching prices...")
prices = requests.get(PRICES_URL).json()["data"]

def get_price(item_id, buy=False):
    p = prices.get(str(item_id), {})
    if buy:
        return p.get("high",0)
    return p.get("low",0)

def expected_drop_value(drops):
    total = 0
    for d in drops:
        price = get_price(d["id"])
        chance = d.get("chance",1)
        qty = d.get("qty",1)
        total += price * qty * chance
    return total

def input_cost(inputs):
    total = 0
    for i in inputs:
        price = get_price(i["id"],True)
        total += price * i.get("qty",1)
    return total

def apply_ge_limit(method_profit, outputs):
    cap = method_profit

    for o in outputs:
        item_id = str(o["id"])
        qty = o.get("qty",1)

        if item_id in ge_limits:
            limit = ge_limits[item_id] / 4
            max_gp = get_price(o["id"]) * limit
            cap = min(cap, max_gp)

    return cap

results = []

for m in data["methods"]:

    inputs = m.get("inputs",[])
    drops = m.get("drops",[])
    actions = m.get("actions_per_hour",1)

    drop_value = expected_drop_value(drops)
    cost = input_cost(inputs)

    profit_action = drop_value - cost
    profit_hour = profit_action * actions

    profit_hour = apply_ge_limit(profit_hour,drops)

    m["profit_per_hour"] = int(profit_hour)

    results.append(m)

data["updated"] = int(time.time())
data["methods"] = results

with open("money_methods.json","w") as f:
    json.dump(data,f,indent=2)

print("Updated",len(results),"methods")
