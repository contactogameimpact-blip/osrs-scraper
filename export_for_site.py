import json

with open("money_methods.json") as f:
 data=json.load(f)

with open("site_data.json","w") as f:
 json.dump(data,f,indent=2)
