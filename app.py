import pandas as pd

from brapi_client import buscar_acao
from indicadores import calcular_indicadores
from valuation import *
from checklist import checklist_buy_hold
from export_excel import salvar_excel

ativos = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBAS3",
    "WEGE3"
]

dados_finais = []

for ticker in ativos:

    print(f"Buscando {ticker}")

    data = buscar_acao(ticker)

    if not data:
        continue

    ind = calcular_indicadores(data)

    lpa = data.get("earningsPerShare", 0)
    vpa = data.get("bookValue", 0)

    dividendos = (
        data.get("dividendRate", 0)
    )

    crescimento = (
        ind.get("Lucro_CAGR", 0)
    )

    graham = calcular_graham(lpa, vpa)

    graham_br = calcular_graham_br(
        graham,
        ind["ROE"],
        ind["Divida_PL"],
        ind["Margem_Liquida"],
        ind["Receita_CAGR"]
    )

    bazin = calcular_bazin(dividendos)

    lynch = calcular_lynch(
        ind["PL"],
        crescimento
    )

    agf = calcular_agf(
        dividendos,
        crescimento
    )

    checklist, score = checklist_buy_hold(ind)

    linha = {

        "Ticker": ticker,

        **ind,

        "Graham": graham,
        "Graham_BR": graham_br,
        "Bazin": bazin,
        "Lynch_PEG": lynch,
        "AGF": agf,

        "Score_BH": score
    }

    dados_finais.append(linha)

df = pd.DataFrame(dados_finais)

salvar_excel(df)

print(df)
