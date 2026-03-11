import json

methods=json.load(open("money_methods.json"))
flips=json.load(open("flips.json"))

site={
    "methods":methods["methods"],
    "flips":flips
}

json.dump(site,open("site_data.json","w"),indent=2)
