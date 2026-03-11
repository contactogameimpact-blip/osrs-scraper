import json
import time
import requests

PRICES_API = "https://prices.runescape.wiki/api/v1/osrs/latest"
VOLUMES_API = "https://prices.runescape.wiki/api/v1/osrs/volumes"

HEADERS = {
    "User-Agent": "OSRS-MoneyHub/1.0"
}

def load_json(path):
    with open(path,encoding="utf-8") as f:
        return json.load(f)

def save_json(path,data):
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=2)

def fetch_prices():
    r=requests.get(PRICES_API,headers=HEADERS)
    r.raise_for_status()
    return r.json()["data"]

def fetch_volumes():
    r=requests.get(VOLUMES_API,headers=HEADERS)
    r.raise_for_status()
    return r.json()["data"]

def get_price(name,prices,items_map):

    item_id=items_map.get(name)

    if not item_id:
        return 0

    info=prices.get(str(item_id))

    if not info:
        return 0

    return info.get("high",0)

def get_volume(name,volumes,items_map):

    item_id=items_map.get(name)

    if not item_id:
        return 0

    info=volumes.get(str(item_id))

    if not info:
        return 0

    if isinstance(info,int):
        return info

    if isinstance(info,dict):
        return info.get("volume",0)

    return 0

def compute_profit(method,prices,volumes,ge_limits,items_map):

    inputs=method.get("inputs",[])
    outputs=method.get("outputs",[])

    actions=method.get("actions_per_hour_human",0)

    cost=0

    for item in inputs:

        p=get_price(item["name"],prices,items_map)

        cost+=p*item["qty"]

    value=0

    for item in outputs:

        p=get_price(item["name"],prices,items_map)

        value+=p*item["qty"]

    profit_action=value-cost

    for item in inputs:

        name=item["name"]

        if name in ge_limits:

            limit=ge_limits[name]/4

            possible=limit/item["qty"]

            actions=min(actions,possible)

    if outputs:

        out_name=outputs[0]["name"]

        daily=get_volume(out_name,volumes,items_map)

        if daily>0:

            sell_hour=daily/24

            actions=min(actions,sell_hour)

    profit_hour=int(profit_action*actions)

    if profit_hour<=0:

        status="dead"

    elif actions<10:

        status="slow_volume"

    else:

        status="ok"

    method["profit_per_action"]=int(profit_action)
    method["profit_per_hour"]=profit_hour
    method["real_actions_per_hour"]=int(actions)
    method["status"]=status

def main():

    base=load_json("methods_base.json")

    ge_limits=load_json("data/ge_limits.json")

    items_map=load_json("data/items_map.json")

    prices=fetch_prices()

    volumes=fetch_volumes()

    methods=base.get("methods",[])

    for m in methods:

        compute_profit(m,prices,volumes,ge_limits,items_map)

    methods.sort(key=lambda x:x.get("profit_per_hour",0),reverse=True)

    final={
        "updated":int(time.time()),
        "methods":methods
    }

    save_json("money_methods.json",final)

    print("engine terminado")
    print("metodos:",len(methods))

if __name__=="__main__":
    main()
