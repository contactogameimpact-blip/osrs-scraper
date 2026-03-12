"""
export_for_site.py
==================
Toma money_methods.json (calculado por profit_engine.py)
y genera site_data.json listo para el frontend de Blogger.

Limpia campos innecesarios para reducir tamaño,
añade metadata y asegura que los campos que espera el JS están presentes.
"""

import json
import time

def load_json(path):
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    print("Loading money_methods.json...")
    raw = load_json("money_methods.json")
    methods_raw = raw.get("methods", [])
    updated     = raw.get("updated", int(time.time()))

    methods_out = []
    for m in methods_raw:
        # Campos que el frontend necesita exactamente
        methods_out.append({
            "name":                        m.get("name", ""),
            "url":                         m.get("url", ""),

            # Acciones
            "wiki_actions_per_hour":       m.get("wiki_actions_per_hour", 0),
            "actions_per_hour_human":      m.get("actions_per_hour_human", 0),
            "effective_actions_per_hour":  m.get("effective_actions_per_hour", 0),

            # Profit
            "profit_per_action":           m.get("profit_per_action", 0),
            "profit_per_hour":             m.get("profit_per_hour", 0),
            "score":                       m.get("score", 0),

            # Flags
            "requires_prebuy":             m.get("requires_prebuy", False),
            "market_saturated":            m.get("market_saturated", False),
            "bottleneck_item":             m.get("bottleneck_item", None),

            # Inputs/outputs (resumen ligero para el frontend)
            "inputs":  [
                {
                    "item":            i.get("item", ""),
                    "qty":             i.get("qty", 1),
                    "price":           i.get("price"),
                    "cost_per_action": i.get("cost_per_action"),
                }
                for i in m.get("inputs", [])
            ],
            "outputs": [
                {
                    "item":             o.get("item", ""),
                    "qty":              o.get("qty", 1),
                    "price":            o.get("price"),
                    "value_per_action": o.get("value_per_action"),
                }
                for o in m.get("outputs", [])
            ],
        })

    site_data = {
        "updated":  updated,
        "methods":  methods_out,
        "meta": {
            "total":            len(methods_out),
            "with_profit":      sum(1 for m in methods_out if m["profit_per_hour"] > 0),
            "with_prebuy":      sum(1 for m in methods_out if m["requires_prebuy"]),
            "market_saturated": sum(1 for m in methods_out if m["market_saturated"]),
            "generated_at":     updated,
        }
    }

    save_json("site_data.json", site_data)

    print(f"Exported {len(methods_out)} methods to site_data.json")
    print(f"  With real profit:  {site_data['meta']['with_profit']}")
    print(f"  Requires prebuy:   {site_data['meta']['with_prebuy']}")
    print(f"  Market saturated:  {site_data['meta']['market_saturated']}")

if __name__ == "__main__":
    main()
