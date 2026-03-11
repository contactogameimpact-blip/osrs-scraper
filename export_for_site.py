import json

methods=json.load(open("money_methods.json"))
flips=json.load(open("flips.json"))

site={
 "updated":methods["updated"],
 "methods":methods["methods"][:200],
 "flips":flips[:100]
}

with open("site_data.json","w") as f:
 json.dump(site,f,indent=2)

print("site data exported")
