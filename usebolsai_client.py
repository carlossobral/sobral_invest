import os
import requests

BASE_URL = "https://api.usebolsai.com/api/v1/stocks/quotes"

def buscar_acoes_usebolsai(tickers):
    api_key = os.getenv("USEBOLSAI_API_KEY")
    if not api_key:
        print("⚠️ USEBOLSAI_API_KEY não configurada.")
        return []

    headers = {"X-API-Key": api_key}
    url = f"{BASE_URL}?tickers={','.join(tickers)}"
    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        data = resp.json()
        if "results" in data:
            return data["results"]
        else:
            print("⚠️ Resposta inesperada:", data)
            return []
    else:
        print(f"Erro {resp.status_code} ao buscar tickers: {resp.text}")
        return []
