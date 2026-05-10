import requests

from config import BRAPI_TOKEN, BASE_URL

headers = {
    "Authorization": f"Bearer {BRAPI_TOKEN}"
}


def buscar_acoes(lista_tickers):

    tickers = ",".join(lista_tickers)

    url = f"{BASE_URL}/quote/{tickers}"

    params = {
        "modules": (
            "summaryProfile,"
            "defaultKeyStatistics,"
            "financialData"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        params=params
    )

    if response.status_code != 200:

        print("Erro BRAPI:", response.text)

        return []

    data = response.json()

    return data.get("results", [])
