import json
import requests

API="https://prices.runescape.wiki/api/v1/osrs/latest"

def main():

    r=requests.get(API)
    data=r.json()["data"]

    flips=[]

    for id,item in data.items():

        high=item.get("high")
        low=item.get("low")

        if not high or not low:
            continue

        margin=high-low

        if margin<100:
            continue

        flips.append({
            "id":id,
            "buy":low,
            "sell":high,
            "margin":margin
        })

    flips.sort(key=lambda x:x["margin"],reverse=True)

    with open("flips.json","w") as f:
        json.dump(flips[:100],f,indent=2)

    print("flips done")

if __name__=="__main__":
    main()
