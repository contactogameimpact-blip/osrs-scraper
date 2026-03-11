import json
import time
import requests

PRICES="https://prices.runescape.wiki/api/v1/osrs/latest"
VOLUMES="https://prices.runescape.wiki/api/v1/osrs/volumes"

HEADERS={"User-Agent":"OSRS-MoneyEngine"}

GE_TAX=0.01


def load(path):
    with open(path,encoding="utf8") as f:
        return json.load(f)

def save(path,data):
    with open(path,"w",encoding="utf8") as f:
        json.dump(data,f,indent=2)

def fetch(url):
    r=requests.get(url,headers=HEADERS)
    r.raise_for_status()
    return r.json()["data"]

def price(name,prices,map):

    id=map.get(name)

    if not id:
        return 0

    p=prices.get(str(id))

    if not p:
        return 0

    return p.get("high",0)

def volume(name,volumes,map):

    id=map.get(name)

    if not id:
        return 0

    v=volumes.get(str(id))

    if isinstance(v,int):
        return v

    if isinstance(v,dict):
        return v.get("volume",0)

    return 0

def compute(method,prices,volumes,limits,map):

    inputs=method["inputs"]
    outputs=method["outputs"]

    actions=method["actions_per_hour_human"]

    cost=0

    for i in inputs:

        cost+=price(i["name"],prices,map)*i["qty"]

    value=0

    for o in outputs:

        value+=price(o["name"],prices,map)*o["qty"]

    value=value*(1-GE_TAX)

    profit_action=value-cost

    requires_prebuy=False

    for i in inputs:

        name=i["name"]

        if name in limits:

            limit=limits[name]/4

            possible=limit/i["qty"]

            if possible<actions:
                requires_prebuy=True

            actions=min(actions,possible)

    market_saturated=False
    liquidity=1

    if outputs:

        out=outputs[0]["name"]

        vol=volume(out,volumes,map)

        if vol>0:

            sell_hour=vol/24

            if sell_hour<actions:
                market_saturated=True

            actions=min(actions,sell_hour)

            liquidity=min(1,sell_hour/500)

    profit_hour=int(profit_action*actions)

    risk=1

    if market_saturated:
        risk*=0.5

    if requires_prebuy:
        risk*=0.7

    score=profit_hour*liquidity*risk

    method["profit_per_action"]=int(profit_action)
    method["profit_per_hour"]=profit_hour
    method["actions_real"]=int(actions)
    method["liquidity"]=round(liquidity,2)
    method["risk"]=round(risk,2)
    method["score"]=int(score)
    method["requires_prebuy"]=requires_prebuy
    method["market_saturated"]=market_saturated


def main():

    base=load("methods_base.json")

    limits=load("data/ge_limits.json")

    items=load("data/items_map.json")

    prices=fetch(PRICES)

    volumes=fetch(VOLUMES)

    methods=base["methods"]

    for m in methods:

        compute(m,prices,volumes,limits,items)

    methods.sort(key=lambda x:x["score"],reverse=True)

    out={
        "updated":int(time.time()),
        "methods":methods
    }

    save("money_methods.json",out)

    print("engine done")

if __name__=="__main__":
    main()
