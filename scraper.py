import json
import re
import time

# ─────────────────────────────────────────────────────
# OSRS Money Making Scraper
# Lee el profit de los textos "aftertax" que ya vienen
# en el JSON scrapeado de la wiki.
# NO necesita item IDs. NO llama a la API de precios.
# ─────────────────────────────────────────────────────

print("Cargando money_methods.json...")
with open("money_methods.json", encoding="utf-8") as f:
    data = json.load(f)

methods = data.get("methods", [])
print(f"  {len(methods)} métodos encontrados")


def extraer_profit(m):
    """
    En tu JSON, el profit ya viene calculado dentro del campo 'name'
    de los inputs/outputs, con el formato:

        "1,248,000, aftertax"
        "641,574, aftertax"

    Este número ES el profit neto por hora que scrapeó la wiki.
    Solo hay que leerlo y convertirlo a entero.
    """

    # Buscar en outputs primero (campo "o")
    for item in m.get("o", []):
        nombre = item.get("name", "")
        if "aftertax" in nombre.lower():
            limpio = nombre.replace(",", "").strip()
            match = re.match(r"(\d+)", limpio)
            if match:
                return int(match.group(1))

    # Si no está en outputs, buscar en inputs (campo "i")
    for item in m.get("i", []):
        nombre = item.get("name", "")
        if "aftertax" in nombre.lower():
            limpio = nombre.replace(",", "").strip()
            match = re.match(r"(\d+)", limpio)
            if match:
                return int(match.group(1))

    # Si no se encontró ningún aftertax, retornar 0
    return 0


# ─────────────────────────────────────────────────────
# Calcular profit para cada método
# ─────────────────────────────────────────────────────
con_profit = 0

for m in methods:
    profit = extraer_profit(m)
    m["profit_per_hour"] = profit
    if profit > 0:
        con_profit += 1

# Ordenar de mayor a menor profit
methods.sort(key=lambda x: x["profit_per_hour"], reverse=True)

# Actualizar timestamp
data["updated"] = int(time.time())
data["methods"] = methods

# Guardar
with open("money_methods.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\nListo!")
print(f"  Total métodos     : {len(methods)}")
print(f"  Con profit > 0    : {con_profit}")
if methods:
    print(f"  Mejor método      : {methods[0].get('n', '?')} ({methods[0]['profit_per_hour']:,} gp/hr)")
