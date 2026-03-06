import json

data = {
    "status": "ok",
    "message": "El scraper está funcionando correctamente.",
    "example": {
        "method": "Making pie shells",
        "rate": 2450
    }
}

with open("money_methods.json", "w") as f:
    json.dump(data, f, indent=4)

print("JSON generado correctamente.")
