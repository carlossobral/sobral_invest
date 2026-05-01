from fastapi import FastAPI
import requests
import pandas as pd

app = FastAPI()

@app.get("/")
def home():
    return {"msg": "API de indicadores online!"}

@app.get("/ranking/dy")
def ranking_dy():
    url_tickers = "https://brapi.dev/api/available"
    resp = requests.get(url_tickers)
    tickers = resp.json().get("stocks", [])
    dados = []
    for ticker in tickers[:50]:  # limite para teste
        url = f"https://brapi.dev/api/quote/{ticker}?fundamental=true"
        r = requests.get(url)
        if r.status_code == 200:
            info = r.json()
            try:
                fundamentals = info["results"][0]["fundamentals"]
                dados.append({
                    "Ticker": ticker,
                    "DY": fundamentals.get("dividendYield", None),
                    "ROE": fundamentals.get("returnOnEquity", None)
                })
            except:
                pass
    df = pd.DataFrame(dados)
    top_dy = df.sort_values(by="DY", ascending=False).head(10)
    return top_dy.to_dict(orient="records")

