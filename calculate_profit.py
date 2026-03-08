import json
import re
import time

print("Cargando money_methods.json...")
with open("money_methods.json", encoding="utf-8") as f:
    data = json.load(f)

methods = data.get("methods", [])
print(f"  {len(methods)} métodos encontrados")

def extraer_profit(m):
    for item in m.get("o", []):
        nombre = item.get("name", "")
        if "aftertax" in nombre.lower():
            limpio = nombre.replace(",", "").strip()
            match = re.match(r"(\d+)", limpio)
            if match:
                return int(match.group(1))

    for item in m.get("i", []):
        nombre = item.get("name", "")
        if "aftertax" in nombre.lower():
            limpio = nombre.replace(",", "").strip()
            match = re.match(r"(\d+)", limpio)
            if match:
                return int(match.group(1))

    return 0

con_profit = 0

for m in methods:
    profit = extraer_profit(m)
    m["profit_per_hour"] = profit
    if profit > 0:
        con_profit += 1

methods.sort(key=lambda x: x["profit_per_hour"], reverse=True)

data["updated"] = int(time.time())
data["methods"] = methods

with open("money_methods.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("\nListo!")
print(f"  Total métodos     : {len(methods)}")
print(f"  Con profit > 0    : {con_profit}")
if methods:
    print(f"  Mejor método      : {methods[0].get('n', '?')} ({methods[0]['profit_per_hour']:,} gp/hr)")
