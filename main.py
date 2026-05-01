from fastapi import FastAPI
import requests
import pandas as pd
import math
import os
import time
import sqlite3
import random

app = FastAPI()

API_KEY = "esWXsXKkdh45gTmhS33aNK"  # sua chave da Brapi
DB_NAME = "dados.db"

def salvar_dados(df):
    conn = sqlite3.connect(DB_NAME)
    df.to_sql("acoes", conn, if_exists="replace", index=False)
    conn.close()

def carregar_dados():
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql("SELECT * FROM acoes", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def atualizar_dados(limit=20):
    url_tickers = f"https://brapi.dev/api/available?token={API_KEY}"
    try:
        resp = requests.get(url_tickers, timeout=10)
        tickers = resp.json().get("stocks", [])
        # embaralha e seleciona aleatoriamente
        selecionados = random.sample(tickers, min(limit, len(tickers)))
    except Exception as e:
        print("Erro ao buscar tickers:", e)
        return pd.DataFrame()

    dados = []
    for ticker in selecionados:
        try:
            url = f"https://brapi.dev/api/quote/{ticker}?fundamental=true&token={API_KEY}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                info = r.json()
                if "results" in info:
                    fundamentals = info["results"][0].get("fundamentals", {})
                    dados.append({
                        "Ticker": ticker,
                        "DY": fundamentals.get("dividendYield", 0),
                        "P/L": fundamentals.get("priceToEarningsRatio", 0),
                        "P/VP": fundamentals.get("priceToBookRatio", 0),
                        "ROE": fundamentals.get("returnOnEquity", 0),
                        "LPA": fundamentals.get("earningsPerShare", 0),
                        "VPA": fundamentals.get("bookValuePerShare", 0),
                        "CrescimentoLucro": fundamentals.get("earningsGrowth", 0)
                    })
                else:
                    print(f"Ticker {ticker} sem dados, salvando zerado")
                    dados.append({
                        "Ticker": ticker,
                        "DY": 0, "P/L": 0, "P/VP": 0,
                        "ROE": 0, "LPA": 0, "VPA": 0,
                        "CrescimentoLucro": 0
                    })
        except Exception as e:
            print(f"Erro em {ticker}: {e}")

    df = pd.DataFrame(dados)
    if not df.empty:
        salvar_dados(df)
        print(f"Banco atualizado com {len(df)} registros.")
    else:
        print("Nenhum dado coletado.")
    return df

@app.get("/")
def home():
    return {"msg": "API Sobral Invest com SQLite ativo_!"}

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
    return df.sort_values(by="DY", ascending=False).head(10).to_dict(orient="records")

@app.get("/ranking/roe")
def ranking_roe():
    df = carregar_dados()
    if df.empty:
        return {"error": "Nenhum dado disponível para ROE."}
    return df.sort_values(by="ROE", ascending=False).head(10).to_dict(orient="records")

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
    return df.sort_values(by="Graham", ascending=False).head(10).to_dict(orient="records")

@app.get("/ranking/bazin")
def ranking_bazin():
    df = carregar_dados()
    if df.empty:
        return {"error": "Nenhum dado disponível para Bazin."}
    df["Bazin"] = df["DY"].apply(lambda x: x if x >= 0.06 else 0)
    return df.sort_values(by="Bazin", ascending=False).head(10).to_dict(orient="records")

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
    return df.sort_values(by="Lynch", ascending=True).head(10).to_dict(orient="records")

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
