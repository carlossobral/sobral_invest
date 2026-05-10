import requests

def buscar_acoes(lista_tickers):

    token = "SEU_TOKEN_AQUI"

    url = "https://brapi.dev/api/quote/PETR4"

    response = requests.get(
        url,
        params={
            "token": token
        }
    )

    print("STATUS:", response.status_code)
    print("RESPOSTA:")
    print(response.text)

    return []
