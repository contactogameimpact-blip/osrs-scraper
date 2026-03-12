import requests
from bs4 import BeautifulSoup
import json

BASE = "https://oldschool.runescape.wiki"
LIST = BASE + "/w/Money_making_guide"

HEADERS = {
 "User-Agent":"osrs-profit-engine"
}

def get_links():

 r = requests.get(LIST,headers=HEADERS)
 soup = BeautifulSoup(r.text,"html.parser")

 links = []

 for a in soup.select("table.wikitable tbody tr td:first-child a"):

  name = a.text.strip()
  href = a.get("href")

  if not href:
   continue

  links.append({
   "name":name,
   "url":BASE+href
  })

 return links


def parse_method(url,name):

 r = requests.get(url,headers=HEADERS)
 soup = BeautifulSoup(r.text,"html.parser")

 inputs=[]
 outputs=[]

 tables = soup.select("table")

 for t in tables:

  text=t.text.lower()

  if "materials" in text:

   for row in t.select("tr")[1:]:

    cols=row.select("td")

    if len(cols)<2:
     continue

    item=cols[0].text.strip()
    qty=cols[1].text.strip()

    try:
     qty=float(qty)
    except:
     qty=1

    inputs.append({
     "name":item,
     "qty":qty
    })

  if "product" in text or "output" in text:

   for row in t.select("tr")[1:]:

    cols=row.select("td")

    if len(cols)<2:
     continue

    item=cols[0].text.strip()
    qty=cols[1].text.strip()

    try:
     qty=float(qty)
    except:
     qty=1

    outputs.append({
     "name":item,
     "qty":qty
    })

 return {
  "name":name,
  "actions_per_hour_human":1200,
  "inputs":inputs,
  "outputs":outputs
 }


def main():

 methods=[]

 links=get_links()

 for m in links:

  try:
   data=parse_method(m["url"],m["name"])
   methods.append(data)
  except:
   continue

 final={
  "methods":methods
 }

 with open("methods_base.json","w",encoding="utf8") as f:
  json.dump(final,f,indent=2)

 print("scraped:",len(methods))


if __name__=="__main__":
 main()
