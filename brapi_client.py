import requests

from config import BRAPI_TOKEN, BASE_URL


def buscar_acoes(lista_tickers):

    tickers = ",".join(lista_tickers)

    url = f"{BASE_URL}/quote/{tickers}"

    params = {
        "token": BRAPI_TOKEN
    }

    print("===================================")
    print("URL:", url)
    print("TOKEN:", BRAPI_TOKEN)
    print("===================================")

    response = requests.get(
        url,
        params=params
    )

    print("STATUS CODE:", response.status_code)

    print("RESPOSTA API:")
    print(response.text[:3000])

    if response.status_code != 200:

        return []

    data = response.json()

    resultados = data.get("results", [])

    print("TOTAL RESULTADOS:", len(resultados))

    return resultados
