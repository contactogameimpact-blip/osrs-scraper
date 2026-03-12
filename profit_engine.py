import json
import requests
import time

PRICES="https://prices.runescape.wiki/api/v1/osrs/latest"

UA={"User-Agent":"osrs-engine"}

def load(path):
 with open(path) as f:
  return json.load(f)

def save(path,data):
 with open(path,"w") as f:
  json.dump(data,f,indent=2)

def get_prices():

 r=requests.get(PRICES,headers=UA)
 return r.json()["data"]

def main():

 base=load("methods_base.json")

 prices=get_prices()

 methods=[]

 for m in base["methods"]:

  m["profit_per_action"]=0
  m["profit_per_hour"]=0
  m["score"]=0

  methods.append(m)

 methods.sort(key=lambda x:x["profit_per_hour"],reverse=True)

 save("money_methods.json",{
  "updated":int(time.time()),
  "methods":methods
 })


if __name__=="__main__":
 main()
