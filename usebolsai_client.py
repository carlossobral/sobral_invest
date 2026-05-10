import os
import requests

BASE_URL = "https://api.usebolsai.com/api/v1/stocks/"

def buscar_acoes_usebolsai(tickers):
    api_key = os.getenv("USEBOLSAI_API_KEY")
    if not api_key:
        print("⚠️ USEBOLSAI_API_KEY não configurada.")
        return []

    url = f"{BASE_URL}?tickers={','.join(tickers)}"
    headers = {"X-API-Key": api_key}
    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        data = resp.json()
        return data.get("results", [])
    else:
        print(f"Erro {resp.status_code} ao buscar tickers")
        return []
