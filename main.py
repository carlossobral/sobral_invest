from fastapi import FastAPI
import requests
import pandas as pd
import math
import os
import time
import sqlite3

app = FastAPI()

API_KEY = os.getenv("BRAPI_KEY", "MINHA_CHAVE_API")
DB_NAME = "dados.db"

# Função para salvar dados no SQLite
def salvar_dados(df):
    conn = sqlite3.connect(DB_NAME)
    df.to_sql("acoes", conn, if_exists="replace", index=False)
    conn.close()

# Função para carregar dados do SQLite
def carregar_dados():
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql("SELECT * FROM acoes", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

# Função para coletar dados da Brapi e salvar no banco
def atualizar_dados(limit=100):
    url_tickers = f"https://brapi.dev/api/available?token={API_KEY}"
    resp = requests.get(url_tickers)
    tickers = resp.json().get("stocks", [])[:limit]
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
    return df

@app.get("/")
def home():
    return {"msg": "API Sobral Invest com SQLite ativo!"}

@app.get("/atualizar")
def atualizar():
    df = atualizar_dados()
    if df.empty:
        return {"error": "Não foi possível atualizar dados da Brapi."}
    return {"msg": f"Dados atualizados com {len(df)} registros."}

@app.get("/ranking/dy")
def ranking_dy():
    df = carregar_dados()
    if df.empty:
        return {"error": "Nenhum dado disponível para Dividend Yield."}
    top_dy = df.sort_values(by="DY", ascending=False).head(10)
    return top_dy.to_dict(orient="records")

@app.get("/ranking/roe")
def ranking_roe():
    df = carregar_dados()
    if df.empty:
        return {"error": "Nenhum dado disponível para ROE."}
    top_roe = df.sort_values(by="ROE", ascending=False).head(10)
    return top_roe.to_dict(orient="records")

@app.get("/ranking/graham")
def ranking_graham():
    df = carregar_dados()
    if df.empty:
        return {"error": "Nenhum dado disponível para Graham."}
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
    df = carregar_dados()
    if df.empty:
        return {"error": "Nenhum dado disponível para Bazin."}
    df["Bazin"] = df["DY"].apply(lambda x: x if x >= 0.06 else 0)
    top_bazin = df.sort_values(by="Bazin", ascending=False).head(10)
    return top_bazin.to_dict(orient="records")

@app.get("/ranking/peterlynch")
def ranking_peterlynch():
    df = carregar_dados()
    if df.empty:
        return {"error": "Nenhum dado disponível para Peter Lynch."}
    def calc_lynch(row):
        pl = row["P/L"]
        crescimento = row["CrescimentoLucro"]
        if crescimento > 0:
            return pl / crescimento
        return float("inf")
    df["Lynch"] = df.apply(calc_lynch, axis=1)
    top_lynch = df.sort_values(by="Lynch", ascending=True).head(10)
    return top_lynch.to_dict(orient="records")

@app.get("/health")
def health():
    df = carregar_dados()
    if df.empty:
        return {"status": "offline", "msg": "Sem dados no banco"}
    return {
        "status": "online",
        "ultima_atualizacao": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "total_registros": len(df)
    }
