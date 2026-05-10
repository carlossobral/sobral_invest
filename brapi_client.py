import requests
from config import BRAPI_TOKEN, BASE_URL

def buscar_acoes(lista_tickers):
    resultados = []
    for ticker in lista_tickers:
        url = f"{BASE_URL}/quote/{ticker}"
        params = {
            "token": BRAPI_TOKEN,
            "dividends": "true",
            "modules": "defaultKeyStatistics,financialData"
        }

        response = requests.get(url, params=params)

        print(f"Buscando {ticker} - STATUS {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            resultados.extend(data.get("results", []))
        else:
            print("Erro:", response.text)

    print("TOTAL RESULTADOS:", len(resultados))
    return resultados
