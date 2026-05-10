import requests
from config import BRAPI_TOKEN, BASE_URL

headers = {
    "Authorization": f"Bearer {BRAPI_TOKEN}"
}


def buscar_acao(ticker):
    url = f"{BASE_URL}/quote/{ticker}"

    params = {
        "modules": (
            "summaryProfile,"
            "defaultKeyStatistics,"
            "financialData,"
            "incomeStatementHistoryQuarterly,"
            "balanceSheetHistoryQuarterly,"
            "cashflowStatementHistoryQuarterly"
        )
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Erro ao buscar {ticker}")
        return None

    data = response.json()

    if "results" not in data:
        return None

    return data["results"][0]
