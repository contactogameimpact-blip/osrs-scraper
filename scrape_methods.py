import json
import requests
from bs4 import BeautifulSoup

URL = "https://oldschool.runescape.wiki/w/Money_making_guide"

def scrape():

    r = requests.get(URL)
    soup = BeautifulSoup(r.text,"html.parser")

    tables = soup.find_all("table",{"class":"wikitable"})

    methods=[]

    for table in tables:

        rows=table.find_all("tr")

        for row in rows[1:]:

            cols=row.find_all("td")

            if len(cols)<2:
                continue

            name=cols[0].get_text(strip=True)

            methods.append({
                "name":name,
                "actions_per_hour_human":900,
                "inputs":[],
                "outputs":[]
            })

    data={"methods":methods}

    with open("methods_base.json","w") as f:
        json.dump(data,f,indent=2)

    print("methods scraped:",len(methods))

if __name__=="__main__":
    scrape()
