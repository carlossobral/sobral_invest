import requests

from config import BRAPI_TOKEN, BASE_URL


def buscar_acoes(lista_tickers):

    tickers = ",".join(lista_tickers)

    url = f"{BASE_URL}/quote/{tickers}"

    params = {
        "token": BRAPI_TOKEN
    }

    print("URL:", url)

    response = requests.get(
        url,
        params=params
    )

    print("STATUS:", response.status_code)

    print("RESPOSTA:", response.text[:1000])

    if response.status_code != 200:

        return []

    data = response.json()

    return data.get("results", [])
