import requests
import yfinance as yf
from config import BRAPI_TOKEN, BASE_URL

def obter_dados_brapi(ticker):
    url = f"{BASE_URL}/{ticker}"
    params = {"token": BRAPI_TOKEN}
    r = requests.get(url, params=params)

    if r.status_code == 200 and r.text.strip():
        try:
            data = r.json()
            results = data.get("results", [])
            if results:
                return results[0]
            else:
                print(f"⚠️ Nenhum resultado BRAPI para {ticker}")
                return {}
        except Exception as e:
            print(f"⚠️ Erro ao decodificar JSON para {ticker}: {e}")
            return {}
    else:
        print(f"⚠️ Erro BRAPI {ticker}: {r.status_code} - {r.text}")
        return {}

def obter_dados_yfinance(ticker):
    acao = yf.Ticker(f"{ticker}.SA")
    info = acao.info
    return {
        "ROE": info.get("returnOnEquity"),
        "ROA": info.get("returnOnAssets"),
        "ROIC": calcular_roic(info),
        "Margem_Bruta": info.get("grossMargins"),
        "Margem_EBIT": info.get("operatingMargins"),
        "Margem_Liquida": info.get("profitMargins"),
        "Divida_PL": info.get("debtToEquity"),
        "Liquidez_Corrente": info.get("currentRatio"),
        "Receita_CAGR": info.get("revenueGrowth"),
        "Lucro_CAGR": info.get("earningsGrowth"),
    }

def calcular_roic(info):
    ebit = info.get("ebitda", 0)  # aproximação
    taxa_imposto = info.get("taxRate", 0)
    total_debt = info.get("totalDebt", 0)
    total_cash = info.get("totalCash", 0)
    total_equity = info.get("totalStockholderEquity", 0)

    capital_investido = (total_debt - total_cash) + total_equity
    if ebit and capital_investido:
        return (ebit * (1 - taxa_imposto)) / capital_investido
    return None

def buscar_acoes(lista_tickers):
    resultados = []
    for ticker in lista_tickers:
        print(f"Buscando {ticker}...")
        dados_brapi = obter_dados_brapi(ticker)
        dados_yf = obter_dados_yfinance(ticker)

        consolidado = {
            "Ticker": ticker,
            "Cotacao": dados_brapi.get("regularMarketPrice"),
            "PL": dados_brapi.get("priceEarnings"),
            "LPA": dados_brapi.get("earningsPerShare"),
            "DY": dados_brapi.get("dividendYield"),
            "PVP": dados_brapi.get("priceToBook"),
            "MarketCap": dados_brapi.get("marketCap"),
            **dados_yf
        }
        resultados.append(consolidado)

    print("TOTAL RESULTADOS:", len(resultados))
    return resultados
