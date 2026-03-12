import requests
from bs4 import BeautifulSoup
import json
import re

BASE="https://oldschool.runescape.wiki"
LIST=BASE+"/w/Money_making_guide"

HEADERS={"User-Agent":"osrs-engine"}

def clean_item(text):

 text=re.sub(r"\(.*?\)","",text)
 text=text.replace("×","x")
 text=text.strip()

 return text


def parse_items(text):

 items=[]

 matches=re.findall(r"(\d+\.?\d*)\s*x\s*([A-Za-z0-9 '\-\(\)]+)",text)

 for m in matches:

  qty=float(m[0])
  name=clean_item(m[1])

  items.append({
   "name":name,
   "qty":qty
  })

 return items


def get_links():

 r=requests.get(LIST,headers=HEADERS)
 soup=BeautifulSoup(r.text,"html.parser")

 links=[]

 for a in soup.select("table.wikitable tbody tr td:first-child a"):

  name=a.text.strip()
  href=a.get("href")

  if not href:
   continue

  links.append({
   "name":name,
   "url":BASE+href
  })

 return links


def parse_method(url,name):

 r=requests.get(url,headers=HEADERS)
 soup=BeautifulSoup(r.text,"html.parser")

 inputs=[]
 outputs=[]

 tables=soup.select("table")

 for t in tables:

  text=t.get_text(" ",strip=True)

  if "Materials" in text:

   inputs+=parse_items(text)

  if "Product" in text or "Output" in text:

   outputs+=parse_items(text)

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
   pass

 with open("methods_base.json","w",encoding="utf8") as f:
  json.dump({"methods":methods},f,indent=2)

 print("scraped:",len(methods))


if __name__=="__main__":
 main()
