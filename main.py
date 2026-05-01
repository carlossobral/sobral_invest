from fastapi import FastAPI
import requests
import pandas as pd
import math
import os

app = FastAPI()

API_KEY = os.getenv("BRAPI_KEY", "MINHA_CHAVE_API")  # configure no Render

def coletar_dados(limit=100):
    """Coleta dados da Brapi com limite de tickers para evitar timeout"""
    url_tickers = f"https://brapi.dev/api/available?token={API_KEY}"
    resp = requests.get(url_tickers)
    tickers = resp.json().get("stocks", [])[:limit]  # pega só os primeiros N
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
    return pd.DataFrame(dados)

@app.get("/")
def home():
    return {"msg": "API Sobral Invest online_a!"}

@app.get("/ranking/dy")
def ranking_dy():
    df = coletar_dados()
    top_dy = df.sort_values(by="DY", ascending=False).head(10)
    return top_dy.to_dict(orient="records")

@app.get("/ranking/roe")
def ranking_roe():
    df = coletar_dados()
    top_roe = df.sort_values(by="ROE", ascending=False).head(10)
    return top_roe.to_dict(orient="records")

@app.get("/ranking/graham")
def ranking_graham():
    df = coletar_dados()
    def calc_graham(row):
        lpa = row["LPA"]
        vpa = row["VPA"]
        if lpa > 0 and vpa > 0:
            return math.sqrt(22.5 * lpa * vpa)
        return 0
    df["Graham"] = df.apply(calc_graham, axis=1)
    top_graham = df.sort_values(by="Graham", ascending=False).head(10)
    return top_graham.to_dict(orient="records")

@app.get("/ranking/bazin")
def ranking_bazin():
    df = coletar_dados()
    df["Bazin"] = df["DY"].apply(lambda x: x if x >= 0.06 else 0)
    top_bazin = df.sort_values(by="Bazin", ascending=False).head(10)
    return top_bazin.to_dict(orient="records")

@app.get("/ranking/peterlynch")
def ranking_peterlynch():
    df = coletar_dados()
    def calc_lynch(row):
        pl = row["P/L"]
        crescimento = row["CrescimentoLucro"]
        if crescimento > 0:
            return pl / crescimento
        return float("inf")  # se não tiver crescimento, joga pro fim
    df["Lynch"] = df.apply(calc_lynch, axis=1)
    top_lynch = df.sort_values(by="Lynch", ascending=True).head(10)
    return top_lynch.to_dict(orient="records")
