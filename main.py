from fastapi import FastAPI
import requests
import pandas as pd
import math
import os

app = FastAPI()

API_KEY = os.getenv("BRAPI_KEY", "MINHA_CHAVE_API")  # usa variável de ambiente ou valor fixo

def coletar_dados():
    url_tickers = f"https://brapi.dev/api/available?token={API_KEY}"
    resp = requests.get(url_tickers)
    tickers = resp.json().get("stocks", [])
    dados = []

    for ticker in tickers:
        url = f"https://brapi.dev/api/quote/{ticker}?fundamental=true&token={API_KEY}"
        r = requests.get(url)
        if r.status_code == 200:
            info = r.json()
            try:
                fundamentals = info["results"][0]["fundamentals"]
                dados.append({
                    "Ticker": ticker,
                    "DY": fundamentals.get("dividendYield", None),
                    "P/L": fundamentals.get("priceToEarningsRatio", None),
                    "P/VP": fundamentals.get("priceToBookRatio", None),
                    "ROE": fundamentals.get("returnOnEquity", None),
                    "LPA": fundamentals.get("earningsPerShare", None),
                    "VPA": fundamentals.get("bookValuePerShare", None),
                    "CrescimentoLucro": fundamentals.get("earningsGrowth", None)
                })
            except:
                pass
    return pd.DataFrame(dados)

@app.get("/")
def home():
    return {"msg": "API Sobral Invest online!"}

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
    df["Graham"] = df.apply(lambda x: math.sqrt(22.5 * (x["LPA"] or 0) * (x["VPA"] or 0)), axis=1)
    top_graham = df.sort_values(by="Graham", ascending=False).head(10)
    return top_graham.to_dict(orient="records")

@app.get("/ranking/bazin")
def ranking_bazin():
    df = coletar_dados()
    df["Bazin"] = df["DY"].apply(lambda x: x if x and x >= 0.06 else 0)
    top_bazin = df.sort_values(by="Bazin", ascending=False).head(10)
    return top_bazin.to_dict(orient="records")

@app.get("/ranking/peterlynch")
def ranking_peterlynch():
    df = coletar_dados()
    df["Lynch"] = df.apply(lambda x: (x["P/L"] or 0) / (x["CrescimentoLucro"] or 1), axis=1)
    top_lynch = df.sort_values(by="Lynch", ascending=True).head(10)
    return top_lynch.to_dict(orient="records")
