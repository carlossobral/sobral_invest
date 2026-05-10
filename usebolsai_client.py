import os
import requests

BASE_URL = "https://api.usebolsai.com/stocks"

def buscar_acoes(tickers):
    api_key = os.getenv("USEBOLSAI_API_KEY")
    if not api_key:
        raise ValueError("API Key não encontrada. Configure USEBOLSAI_API_KEY nos Secrets do GitHub.")

    resultados = []
    # Divide em lotes de até 50 tickers
    for i in range(0, len(tickers), 50):
        lote = tickers[i:i+50]
        url = f"{BASE_URL}?tickers={','.join(lote)}"
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.get(url, headers=headers)

        if resp.status_code == 200:
            resultados.extend(resp.json())
        else:
            print(f"Erro {resp.status_code} ao buscar lote: {lote}")

    return resultados
