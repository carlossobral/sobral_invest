import os
import requests

BASE_URL = "https://api.usebolsai.com/api/v1/stocks/"

def buscar_acoes_usebolsai(tickers):
    api_key = os.getenv("USEBOLSAI_API_KEY")
    if not api_key:
        print("⚠️ USEBOLSAI_API_KEY não configurada.")
        return []

    resultados = []
    # Divide em lotes de até 30 tickers
    for i in range(0, len(tickers), 30):
        lote = tickers[i:i+30]
        url = f"{BASE_URL}?tickers={','.join(lote)}"
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.get(url, headers=headers)

        if resp.status_code == 200:
            resultados.extend(resp.json())
        else:
            print(f"Erro {resp.status_code} ao buscar lote: {lote}")

    return resultados
