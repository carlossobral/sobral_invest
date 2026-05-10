import os
import requests

BASE_URL = "https://api.usebolsai.com/stocks"

def buscar_acoes(tickers):
    api_key = os.getenv("USEBOLSAI_API_KEY")
    if not api_key:
        raise ValueError("API Key não encontrada. Configure USEBOLSAI_API_KEY nos Secrets do GitHub.")

    url = f"{BASE_URL}?tickers={','.join(tickers)}"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Erro {resp.status_code} ao buscar tickers")
        return []
