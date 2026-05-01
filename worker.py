import time
import sqlite3
import requests
import pandas as pd
import os

API_KEY = os.getenv("BRAPI_KEY", "MINHA_CHAVE_API")
DB_NAME = "dados.db"

def salvar_dados(df):
    conn = sqlite3.connect(DB_NAME)
    df.to_sql("acoes", conn, if_exists="replace", index=False)
    conn.close()

def atualizar_dados(limit=100):
    url_tickers = f"https://brapi.dev/api/available?token={API_KEY}"
    try:
        resp = requests.get(url_tickers, timeout=10)
        tickers = resp.json().get("stocks", [])[:limit]
    except Exception as e:
        print("Erro ao buscar tickers:", e)
        return

    dados = []
    for ticker in tickers:
        try:
            url = f"https://brapi.dev/api/quote/{ticker}?fundamental=true&token={API_KEY}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                info = r.json()
                fundamentals = info["results"][0]["fundamentals"]
                dados.append({
                    "Ticker": ticker,
                    "DY": fundamentals.get("dividendYield") or 0,
                    "P/L": fundamentals.get("priceToEarningsRatio") or 0,
                    "P/VP": fundamentals.get("priceToBookRatio") or 0,
                    "ROE": fundamentals.get("returnOnEquity") or 0,
                    "LPA": fundamentals.get("earningsPerShare") or 0,
                    "VPA": fundamentals.get("bookValuePerShare") or 0,
                    "CrescimentoLucro": fundamentals.get("earningsGrowth") or 0
                })
        except Exception as e:
            print(f"Erro em {ticker}: {e}")

    df = pd.DataFrame(dados)
    if not df.empty:
        salvar_dados(df)
        print(f"Banco atualizado com {len(df)} registros.")
    else:
        print("Nenhum dado coletado.")

if __name__ == "__main__":
    while True:
        atualizar_dados()
        # Atualiza a cada 1 hora
        time.sleep(3600)
