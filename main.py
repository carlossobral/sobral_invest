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

# Lista fixa de ativos
TICKERS_FIXOS = [
    "AALR3","ABCB4","ABEV3","AERI3","AGRO3","AGXY3","ALLD3","ALOS3","ALPA4","ALPK3",
    "ALUP11","ALUP4","AMAR3","AMBP3","AMER3","AMOB3","ANIM3","ARML3","ASAI3","ATED3",
    "AURA33","AURE3","AZEV4","AZTE3","AZZA3","B3SA3","BAZA3","BBAS3","BBDC3","BBDC4",
    "BBSE3","BEEF3","BEES4","BGIP4","BHIA3","BIOM3","BLAU3","BMEB4","BMGB4","BMOB3",
    "BPAC11","BRAP3","BRAP4","BRAV3","BRBI11","BRKM3","BRKM5","BRSR6","BRST3","BSLI4",
    "CAMB3","CAML3","CASH3","CBAV3","CEAB3","CGRA4","CLSC4","CMIG3","CMIG4","CMIN3",
    "COCE5","COGN3","CPFE3","CPLE3","CSAN3","CSED3","CSMG3","CSNA3","CURY3","CVCB3",
    "CXSE3","CYRE3","DASA3","DESK3","DEXP3","DEXP4","DIRR3","DMVF3","DOTZ3","DXCO3",
    "EALT4","ECOR3","EGIE3","EMAE4","ENEV3","ENGI11","ENGI3","ENJU3","EQPA3","EQTL3",
    "ESPA3","EUCA3","EUCA4","EVEN3","EZTC3","FESA4","FHER3","FICT3","FIQE3","FLRY3",
    "FRAS3","G2DI33","GFSA3","GGBR3","GGBR4","GGPS3","GMAT3","GOAU3","GOAU4","GRND3",
    "HAPV3","HBOR3","HBRE3","HBSA3","HYPE3","IFCM3","IGTI11","IGTI3","INTB3","IRBR3",
    "ISAE4","ITSA4","ITUB4","JALL3","JHSF3","JSLG3","KEPL3","KLBN11","KLBN4","LAND3",
    "LAVV3","LEVE3","LIGT3","LJQQ3","LOGG3","LOGN3","LPSB3","LREN3","LUPA3","LWSA3",
    "MATD3","MBRF3","MDIA3","MDNE3","MEAL3","MELK3","MGLU3","MILS3","MLAS3","MOTV3",
    "MOVI3","MRVE3","MTRE3","MULT3","MYPK3","NATU3","NEOE3","NGRD3","ODPV3","OFSA3",
    "OIBR3","ONCO3","OPCT3","ORVR3","PCAR3","PDGR3","PDTC3","PETR3","PETR4","PFRM3",
    "PGMN3","PINE4","PLPL3","PMAM3","PNVL3","POMO3","POMO4","POSI3","PRIO3","PRNR3",
    "PSSA3","PTBL3","PTNT4","QUAL3","RADL3","RAIL3","RAIZ4","RANI3","RAPT3","RAPT4",
    "RCSL4","RDOR3","RECV3","RENT3","ROMI3","SANB11","SAPR11","SAPR4","SBFG3","SBSP3",
    "SCAR3","SEER3","SEQL3","SHOW3","SHUL4","SIMH3","SLCE3","SMFT3","SMTO3","SOJA3",
    "SUZB3","SYNE3","TAEE11","TAEE4","TCSA3","TECN3","TEND3","TFCO4","TGMA3","TIMS3",
    "TOTS3","TPIS3","TRAD3","TRIS3","TTEN3","TUPY3","UCAS3","UGPA3","UNIP6","USIM3",
    "USIM5","VALE3","VAMO3","VBBR3","VITT3","VIVA3","VIVR3","VIVT3","VLID3","VSTE3",
    "VTRU3","VULC3","VVEO3","WEGE3","WEST3","WIZC3","YDUQ3"
]

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

def atualizar_dados():
    dados = []
    for ticker in TICKERS_FIXOS:
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
    return {"msg": "API Sobral Invest com SQLite ativos!"}

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
def ranking_b
