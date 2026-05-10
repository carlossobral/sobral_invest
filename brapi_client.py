import requests
import yfinance as yf
from config import BRAPI_TOKEN

# Endpoint correto da BRAPI
BASE_URL = "https://brapi.dev/api/quote"

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
            print("Resposta bruta:", r.text[:200])  # debug
            return {}
    else:
        print(f"⚠️ Erro BRAPI {ticker}: {r.status_code} - {r.text}")
        return {}

def obter_dados_yfinance(ticker):
    acao = yf.Ticker(f"{ticker}.SA")
    info = acao.info
    return {
        "Cotacao": info.get("currentPrice"),
        "PL": info.get("forwardPE"),
        "LPA": info.get("trailingEps"),
        "DY": info.get("dividendYield"),
        "PVP": info.get("priceToBook"),
        "MarketCap": info.get("marketCap"),
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

        # Fallback: se BRAPI falhar, usa Yahoo Finance
        consolidado = {
            "Ticker": ticker,
            "Cotacao": dados_brapi.get("regularMarketPrice") or dados_yf.get("Cotacao", 0),
            "PL": dados_brapi.get("priceEarnings") or dados_yf.get("PL", 0),
            "LPA": dados_brapi.get("earningsPerShare") or dados_yf.get("LPA", 0),
            "DY": dados_brapi.get("dividendYield") or dados_yf.get("DY", 0),
            "PVP": dados_brapi.get("priceToBook") or dados_yf.get("PVP", 0),
            "MarketCap": dados_brapi.get("marketCap") or dados_yf.get("MarketCap", 0),
            "ROE": dados_yf.get("ROE"),
            "ROA": dados_yf.get("ROA"),
            "ROIC": dados_yf.get("ROIC"),
            "Margem_Bruta": dados_yf.get("Margem_Bruta"),
            "Margem_EBIT": dados_yf.get("Margem_EBIT"),
            "Margem_Liquida": dados_yf.get("Margem_Liquida"),
            "Divida_PL": dados_yf.get("Divida_PL"),
            "Liquidez_Corrente": dados_yf.get("Liquidez_Corrente"),
            "Receita_CAGR": dados_yf.get("Receita_CAGR"),
            "Lucro_CAGR": dados_yf.get("Lucro_CAGR"),
        }
        resultados.append(consolidado)

    print("TOTAL RESULTADOS:", len(resultados))
    return resultados
