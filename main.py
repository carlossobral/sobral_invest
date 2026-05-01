from fastapi import FastAPI
import requests
import pandas as pd
import math
import os
import time
import sqlite3

app = FastAPI()

API_KEY = "esWXsXKkdh45gTmhS33aNK"  # sua chave da Brapi
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
def atualizar_dados(limit=20):
    url_tickers = f"https://brapi.dev/api/available?token={API_KEY}"
    try:
        resp = requests.get(url_tickers, timeout=10)
        tickers = resp.json().get("stocks", [])[:limit]
    except Exception as e:
        print("Erro ao buscar tickers:", e)
        return pd.DataFrame()

    dados = []
    for ticker in tickers:
        try:
            url = f"https://brapi.dev/api/quote/{ticker}?fundamental=true&token={API_KEY}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                info = r.json()
                if "results" in info:
                    resultado = info["results"][0]
                    fundamentals = resultado.get("fundamentals", {})
                    
                    # Coletando o preço atual da ação para o cálculo de Upside/Downside
                    preco_atual = resultado.get("regularMarketPrice", 0)

                    dados.append({
                        "Ticker": ticker,
                        "PrecoAtual": preco_atual,
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
                        "Ticker": ticker, "PrecoAtual": 0, "DY": 0, "P/L": 0, 
                        "P/VP": 0, "ROE": 0, "LPA": 0, "VPA": 0, "CrescimentoLucro": 0
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
    return {"msg": "API Sobral Invest com SQLite ativo e Valuations Integrados!"}

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
        
    df["ValorIntrinseco"] = df.apply(calc_graham, axis=1)
    
    # Cálculo de Upside / Downside
    def calc_margem(row):
        vi = row["ValorIntrinseco"]
        preco = row["PrecoAtual"]
        if vi > 0 and preco > 0:
            margem = (vi / preco) - 1
            tipo = "UPSIDE" if margem > 0 else "DOWNSIDE"
            return f"{tipo} ({abs(margem)*100:.2f}%)"
        return "N/A"
        
    df["Potencial"] = df.apply(calc_margem, axis=1)
    return df.sort_values(by="ValorIntrinseco", ascending=False).head(10).to_dict(orient="records")

@app.get("/ranking/bazin")
def ranking_bazin():
    df = carregar_dados()
    if df.empty:
        return {"error": "Nenhum dado disponível para Bazin."}
        
    def calc_bazin(row):
        dy = row["DY"]
        preco = row["PrecoAtual"]
        if dy > 0 and preco > 0:
            # Encontra o dividendo pago em reais para projetar o preço teto
            dividendo_reais = preco * dy
            preco_teto = dividendo_reais / 0.06
            
            # Cálculo de Upside / Downside
            margem = (preco_teto / preco) - 1
            tipo = "UPSIDE" if margem > 0 else "DOWNSIDE"
            potencial = f"{tipo} ({abs(margem)*100:.2f}%)"
            return pd.Series([preco_teto, potencial])
        return pd.Series([0, "N/A"])
        
    df[["PrecoTeto", "Potencial"]] = df.apply(calc_bazin, axis=1)
    
    # Mantém a filosofia de Décio Bazin: focar em empresas que pagam DY >= 6%
    df_bazin = df[df["DY"] >= 0.06].copy()
    return df_bazin.sort_values(by="PrecoTeto", ascending=False).head(10).to_dict(orient="records")

@app.get("/ranking/peterlynch")
def ranking_peterlynch():
    df = carregar_dados()
    if df.empty:
        return {"error": "Nenhum dado disponível para Peter Lynch."}
        
    def calc_lynch(row):
        pl = row["P/L"]
        # Converte o crescimento (que vem em decimal da Brapi) para o número inteiro usado na fórmula de Lynch
        crescimento = row["CrescimentoLucro"] * 100 
        if crescimento > 0:
            return pl / crescimento
        return float("inf")
        
    df["PEG_Ratio"] = df.apply(calc_lynch, axis=1)
    
    # Cálculo de Upside / Downside baseado no PEG Ratio (Abaixo de 1 = Descontada)
    def avaliacao_lynch(peg):
        if peg == float("inf"):
            return "N/A"
        if peg < 1:
            return "UPSIDE (Descontada)"
        elif peg == 1:
            return "Preço Justo"
        else:
            return "DOWNSIDE (Cara)"
            
    df["Potencial"] = df["PEG_Ratio"].apply(avaliacao_lynch)
    return df.sort_values(by="PEG_Ratio", ascending=True).head(10).to_dict(orient="records")

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
