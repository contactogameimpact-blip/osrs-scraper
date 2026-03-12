"""
profit_engine.py
================
Motor de cálculo real de profit para money making de OSRS.

Aplica:
  ✓ Precios reales de prices.runescape.wiki
  ✓ GE limits reales (límite por 4h → límite efectivo por hora)
  ✓ Volumen diario real (no puedes vender/comprar más de lo que existe)
  ✓ Acciones por hora humanas (no fantasías de la wiki)
  ✓ Bottleneck de inputs: si un input tiene límite de GE bajo, limita
    cuántas acciones puedes hacer por hora
  ✓ Detecta métodos que requieren prebuy (inversión previa)
  ✓ Score compuesto: profit × viabilidad real

Guarda → money_methods.json
"""

import json
import time
import requests

PRICES_URL  = "https://prices.runescape.wiki/api/v1/osrs/latest"
VOLUMES_URL = "https://prices.runescape.wiki/api/v1/osrs/volumes"  # volumen diario
MAPPING_URL = "https://prices.runescape.wiki/api/v1/osrs/mapping"  # id ↔ nombre
UA = {"User-Agent": "osrs-profit-engine/1.0 (github.com/contactogameimpact-blip/osrs-scraper)"}

# GE limit override manual para items clave (por 4 horas)
GE_LIMITS_OVERRIDE = {
    "Pie dish":          500,
    "Pie shell":       10000,
    "Bucket of sand":  10000,
    "Molten glass":    10000,
    "Flax":            10000,
    "Bow string":      10000,
    "Logs":            15000,
    "Oak logs":        15000,
    "Willow logs":     15000,
    "Maple logs":      15000,
    "Yew logs":        15000,
    "Magic logs":      15000,
    "Raw lobster":     10000,
    "Raw shark":       10000,
    "Shark":           10000,
    "Lobster":         10000,
    "Coal":            10000,
    "Iron ore":        10000,
    "Gold ore":        10000,
    "Silver ore":      10000,
    "Copper ore":      10000,
    "Tin ore":         10000,
    "Rune essence":    10000,
    "Pure essence":    10000,
    "Herbs":            2000,
    "Grimy herbs":      2000,
}

def load_json(path):
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_prices():
    """Devuelve dict {item_id: {high, low}} con precios reales."""
    try:
        r = requests.get(PRICES_URL, headers=UA, timeout=30)
        return r.json().get("data", {})
    except Exception as e:
        print(f"  WARN: could not fetch prices: {e}")
        return {}

def get_volumes():
    """Devuelve dict {item_id: volumen_diario}."""
    try:
        r = requests.get(VOLUMES_URL, headers=UA, timeout=30)
        return r.json().get("data", {})
    except Exception as e:
        print(f"  WARN: could not fetch volumes: {e}")
        return {}

def get_mapping():
    """Devuelve dict {nombre_normalizado: item_id}."""
    try:
        r = requests.get(MAPPING_URL, headers=UA, timeout=30)
        items = r.json()
        return {item["name"].strip().lower(): str(item["id"]) for item in items}
    except Exception as e:
        print(f"  WARN: could not fetch mapping: {e}")
        return {}

def get_ge_limits():
    """Carga GE limits del archivo local + overrides manuales."""
    try:
        with open("data/ge_limits.json") as f:
            limits = json.load(f)
    except Exception:
        limits = {}
    # Merge overrides
    for k, v in GE_LIMITS_OVERRIDE.items():
        if k not in limits:
            limits[k] = v
    return limits

def resolve_price(item_name, mapping, prices):
    """
    Dado un nombre de item, devuelve (buy_price, sell_price).
    buy_price  = high (lo que pagas al comprar)
    sell_price = low  (lo que recibes al vender, más conservador)
    """
    key = item_name.strip().lower()
    item_id = mapping.get(key)
    if not item_id:
        return None, None
    entry = prices.get(item_id) or prices.get(str(item_id))
    if not entry:
        return None, None
    high = entry.get("high") or entry.get("highTime") and None
    low  = entry.get("low")  or entry.get("lowTime")  and None
    # La API de precios tiene "high" y "low" directamente
    high = entry.get("high")
    low  = entry.get("low")
    return high, low

def resolve_volume(item_name, mapping, volumes):
    """Devuelve el volumen diario de un item, o 0 si no se conoce."""
    key = item_name.strip().lower()
    item_id = mapping.get(key)
    if not item_id:
        return 0
    return volumes.get(item_id) or volumes.get(str(item_id)) or 0

def calc_method(m, mapping, prices, volumes, ge_limits):
    """
    Calcula el profit real de un método.

    Retorna el método enriquecido con:
      - profit_per_action
      - profit_per_hour (con acciones humanas y bottlenecks)
      - effective_actions_per_hour (limitado por GE + volumen)
      - requires_prebuy
      - market_saturated
      - bottleneck_item (qué item limita las acciones)
      - score
      - inputs/outputs con precios resueltos
    """
    name          = m.get("name", "")
    human_aph     = m.get("actions_per_hour_human", 900)
    inputs        = m.get("inputs", [])
    outputs       = m.get("outputs", [])

    # ── Resolver precios de inputs ──────────────────────────────────
    total_input_cost = 0.0
    requires_prebuy  = False
    bottleneck_aph   = human_aph  # se va reduciendo
    bottleneck_item  = None
    inputs_resolved  = []

    for inp in inputs:
        item  = inp.get("item", "")
        qty   = float(inp.get("qty", 1))
        buy_p, _ = resolve_price(item, mapping, prices)

        if buy_p is None:
            # sin precio → saltamos este input
            inputs_resolved.append({**inp, "price": None, "cost_per_action": None})
            continue

        cost_per_action = buy_p * qty
        total_input_cost += cost_per_action

        # ── GE limit bottleneck ──
        # GE limit es por 4 horas. items_por_hora = limit / 4
        ge_limit = ge_limits.get(item)
        if ge_limit is not None:
            max_items_per_hour = ge_limit / 4.0   # por hora
            # acciones posibles con este input
            max_actions = max_items_per_hour / qty if qty > 0 else human_aph
            if max_actions < bottleneck_aph:
                bottleneck_aph  = max_actions
                bottleneck_item = item
                requires_prebuy = True  # necesita stock previo si el GE no da abasto

        # ── Volume bottleneck ──
        daily_vol = resolve_volume(item, mapping, volumes)
        if daily_vol > 0:
            # si el volumen diario es bajo → no puedes comprar tanto
            hourly_vol = daily_vol / 24.0
            max_actions_by_vol = hourly_vol / qty if qty > 0 else human_aph
            if max_actions_by_vol < bottleneck_aph:
                bottleneck_aph  = max_actions_by_vol
                bottleneck_item = item

        inputs_resolved.append({
            **inp,
            "price":            buy_p,
            "cost_per_action":  round(cost_per_action, 2),
        })

    # ── Resolver precios de outputs ─────────────────────────────────
    total_output_value = 0.0
    market_saturated   = False
    outputs_resolved   = []

    for out in outputs:
        item  = out.get("item", "")
        qty   = float(out.get("qty", 1))
        _, sell_p = resolve_price(item, mapping, prices)

        # Para la venta usamos el precio bajo (conservador)
        if sell_p is None:
            buy_p2, _ = resolve_price(item, mapping, prices)
            sell_p = buy_p2  # fallback al precio de compra

        if sell_p is None:
            outputs_resolved.append({**out, "price": None, "value_per_action": None})
            continue

        value_per_action = sell_p * qty
        total_output_value += value_per_action

        # ── Volume bottleneck en outputs (¿puedes vender lo que produces?) ──
        daily_vol = resolve_volume(item, mapping, volumes)
        if daily_vol > 0:
            hourly_vol = daily_vol / 24.0
            max_sell_per_hour = hourly_vol / qty if qty > 0 else human_aph
            if max_sell_per_hour < bottleneck_aph:
                # Solo marcamos como saturado si el volumen es MUY bajo
                if daily_vol < 500:
                    market_saturated = True
                bottleneck_aph  = max_sell_per_hour
                bottleneck_item = bottleneck_item or item

        outputs_resolved.append({
            **out,
            "price":             sell_p,
            "value_per_action":  round(value_per_action, 2),
        })

    # ── Calcular profit ─────────────────────────────────────────────
    profit_per_action = total_output_value - total_input_cost

    # Acciones efectivas = mínimo entre humano, GE limit, volumen
    effective_aph = min(human_aph, max(1, bottleneck_aph))

    profit_per_hour = profit_per_action * effective_aph

    # ── Score compuesto ─────────────────────────────────────────────
    # profit_per_hour ajustado por:
    #   - penalización si requiere prebuy (-25%)
    #   - penalización si mercado saturado (-50%)
    #   - bonificación si no hay bottleneck (+10%)
    score = profit_per_hour
    if requires_prebuy:
        score *= 0.75
    if market_saturated:
        score *= 0.50
    if bottleneck_item is None:
        score *= 1.10

    return {
        "name":                    name,
        "url":                     m.get("url", ""),
        "wiki_actions_per_hour":   m.get("wiki_actions_per_hour", 0),
        "actions_per_hour_human":  human_aph,
        "effective_actions_per_hour": round(effective_aph, 1),
        "bottleneck_item":         bottleneck_item,
        "requires_prebuy":         requires_prebuy,
        "market_saturated":        market_saturated,
        "inputs":                  inputs_resolved,
        "outputs":                 outputs_resolved,
        "profit_per_action":       round(profit_per_action, 2),
        "profit_per_hour":         round(profit_per_hour, 2),
        "score":                   round(score, 2),
    }

def main():
    print("Loading base methods...")
    base    = load_json("methods_base.json")
    methods_raw = base.get("methods", [])
    print(f"  {len(methods_raw)} methods found")

    print("Fetching live prices...")
    prices  = get_prices()
    print(f"  {len(prices)} items priced")

    print("Fetching daily volumes...")
    volumes = get_volumes()
    print(f"  {len(volumes)} items with volume data")

    print("Building item name → ID mapping...")
    mapping = get_mapping()
    print(f"  {len(mapping)} items in mapping")

    print("Loading GE limits...")
    ge_limits = get_ge_limits()
    print(f"  {len(ge_limits)} GE limits loaded")

    print("Calculating profits...")
    methods_calc = []
    for i, m in enumerate(methods_raw):
        result = calc_method(m, mapping, prices, volumes, ge_limits)
        methods_calc.append(result)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(methods_raw)} done")

    # Ordenar por score descendente
    methods_calc.sort(key=lambda x: x["score"], reverse=True)

    output = {
        "updated":  int(time.time()),
        "methods":  methods_calc,
    }

    save_json("money_methods.json", output)
    print(f"\nDone. Saved {len(methods_calc)} methods to money_methods.json")

    # Stats rápidas
    with_profit = [m for m in methods_calc if m["profit_per_hour"] > 0]
    top5 = methods_calc[:5]
    print(f"Methods with profit > 0: {len(with_profit)}")
    print("Top 5:")
    for m in top5:
        print(f"  {m['name'][:45]:45s} {m['profit_per_hour']:>12,.0f} gp/hr")

if __name__ == "__main__":
    main()
