import requests
from bs4 import BeautifulSoup
import json

BASE="https://oldschool.runescape.wiki"
URL=BASE+"/w/Money_making_guide"

HEADERS={"User-Agent":"osrs-engine"}

def get_links():

 r=requests.get(URL,headers=HEADERS)
 soup=BeautifulSoup(r.text,"html.parser")

 links=[]

 for row in soup.select("table.wikitable tbody tr"):

  a=row.select_one("td a")

  if not a:
   continue

  name=a.text.strip()
  href=a.get("href")

  links.append({
   "name":name,
   "url":BASE+href
  })

 return links


def main():

 methods=[]

 for m in get_links():

  methods.append({
   "name":m["name"],
   "actions_per_hour_human":900,
   "inputs":[],
   "outputs":[]
  })

 with open("methods_base.json","w") as f:
  json.dump({"methods":methods},f,indent=2)


if __name__=="__main__":
 main()
