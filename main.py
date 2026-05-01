import requests
import pandas as pd
import sqlite3
import time
import math
import yfinance as yf
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import io

app = FastAPI()

DB_NAME = "acoes.db"
API_KEY = "SUA_CHAVE_BRAPI"

# Lista fixa de ativos (sua lista completa)
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
# Helper para respostas seguras
def resposta_segura(ticker, dados, tipo="indicadores"):
    if not dados or all(v == 0 or v is None for v in dados.values()):
        return {"Ticker": ticker.upper(), "msg": f"Sem dados válidos para {tipo}."}
    return {"Ticker": ticker.upper(), **dados}
##PARTE2a
def coletar_fundamentus(ticker):
    try:
        url = f"http://fundamentus.com.br/detalhes.php?papel={ticker}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            def pegar_valor(label):
                el = soup.find(text=label)
                if el:
                    val = el.find_next("td").text.strip().replace(",", ".")
                    try:
                        return float(val)
                    except:
                        return 0
                return 0
            return {
                "DY": pegar_valor("Div.Yield"),
                "P/L": pegar_valor("P/L"),
                "P/VP": pegar_valor("P/VP"),
                "ROE": pegar_valor("ROE"),
                "LPA": pegar_valor("LPA"),
                "VPA": pegar_valor("VPA"),
                "CrescimentoLucro": pegar_valor("Cres. Rec."),
                "EBITDA": pegar_valor("EBITDA"),
                "DividaLiquida": pegar_valor("Dív Líquida"),
                "ValorMercado": pegar_valor("Valor Mercado"),
                "ReceitaLiquida": pegar_valor("Receita Líquida"),
                "MargemLiquida": pegar_valor("Margem Líquida"),
                "Liquidez": pegar_valor("Liquidez Corr.")
            }
    except Exception as e:
        print(f"Erro Fundamentus {ticker}: {e}")
    return {}

def coletar_yfinance(ticker):
    try:
        yf_ticker = yf.Ticker(f"{ticker}.SA")
        info = yf_ticker.info
        return {
            "DY": info.get("dividendYield", 0) or 0,
            "P/L": info.get("forwardPE", 0) or 0,
            "P/VP": info.get("priceToBook", 0) or 0,
            "ROE": info.get("returnOnEquity", 0) or 0,
            "LPA": info.get("earningsPerShare", 0) or 0,
            "VPA": info.get("bookValue", 0) or 0,
            "CrescimentoLucro": info.get("earningsGrowth", 0) or 0,
            "EBITDA": info.get("ebitda", 0) or 0,
            "DividaLiquida": info.get("totalDebt", 0) or 0,
            "ValorMercado": info.get("enterpriseValue", 0) or 0,
            "ReceitaLiquida": info.get("totalRevenue", 0) or 0,
            "MargemLiquida": info.get("profitMargins", 0) or 0,
            "Liquidez": info.get("averageVolume", 0) or 0
        }
    except Exception as e:
        print(f"Erro yfinance {ticker}: {e}")
    return {}
## parte2b
def calcular_dividendos_historico(ticker, anos=6):
    try:
        yf_ticker = yf.Ticker(f"{ticker}.SA")
        dividends = yf_ticker.dividends
        history = yf_ticker.history(period=f"{anos}y")

        # Corrigir timezone
        if hasattr(dividends.index, "tz"):
            dividends.index = dividends.index.tz_localize(None)
        if hasattr(history.index, "tz"):
            history.index = history.index.tz_localize(None)

        resultados = {}
        ano_atual = pd.Timestamp.today().year

        for i in range(1, anos+1):
            ano = ano_atual - i
            div_ano = dividends[dividends.index.year == ano].sum()
            preco_medio = history[history.index.year == ano]["Close"].mean()
            dy = (div_ano / preco_medio * 100) if preco_medio and preco_medio > 0 else 0
            resultados[f"DY_{i}A"] = round(dy, 2)
            resultados[f"Div_{i}A"] = round(div_ano, 2)

        ultimos_12m = dividends[dividends.index >= pd.Timestamp.today() - pd.DateOffset(years=1)].sum()
        preco_medio_12m = history[history.index >= pd.Timestamp.today() - pd.DateOffset(years=1)]["Close"].mean()
        dy_12m = (ultimos_12m / preco_medio_12m * 100) if preco_medio_12m and preco_medio_12m > 0 else 0
        resultados["DY_12M"] = round(dy_12m, 2)
        resultados["Div_12M"] = round(ultimos_12m, 2)

        return resultados
    except Exception as e:
        print(f"Erro dividendos histórico {ticker}: {e}")
        return {}

def calcular_payout_historico(ticker, anos=6):
    try:
        yf_ticker = yf.Ticker(f"{ticker}.SA")
        dividends = yf_ticker.dividends
        financials = yf_ticker.financials.T

        if hasattr(dividends.index, "tz"):
            dividends.index = dividends.index.tz_localize(None)

        resultados = {}
        ano_atual = pd.Timestamp.today().year

        for i in range(1, anos+1):
            ano = ano_atual - i
            div_ano = dividends[dividends.index.year == ano].sum()
            try:
                net_income = financials.loc[str(ano)]["Net Income"]
                shares_outstanding = yf_ticker.info.get("sharesOutstanding", 0)
                lpa = net_income / shares_outstanding if shares_outstanding > 0 else 0
                if isinstance(lpa, (pd.Series, pd.DataFrame)):
                    lpa = float(lpa.values[0])
            except:
                lpa = 0
            payout = (div_ano / lpa * 100) if lpa and lpa > 0 else 0
            resultados[f"Payout_{i}A"] = round(payout, 2)
            resultados[f"Div_{i}A"] = round(div_ano, 2)

        ultimos_12m = dividends[dividends.index >= pd.Timestamp.today() - pd.DateOffset(years=1)].sum()
        try:
            net_income_ttm = yf_ticker.get_income_stmt(freq="quarterly").sum().loc["Net Income"].sum()
            shares_outstanding = yf_ticker.info.get("sharesOutstanding", 0)
            lpa_ttm = net_income_ttm / shares_outstanding if shares_outstanding > 0 else 0
            if isinstance(lpa_ttm, (pd.Series, pd.DataFrame)):
                lpa_ttm = float(lpa_ttm.values[0])
        except:
            lpa_ttm = 0
        payout_12m = (ultimos_12m / lpa_ttm * 100) if lpa_ttm and lpa_ttm > 0 else 0
        resultados["Payout_12M"] = round(payout_12m, 2)
        resultados["Div_12M"] = round(ultimos_12m, 2)

        return resultados
    except Exception as e:
        print(f"Erro payout histórico {ticker}: {e}")
        return {}
##parte2c
def buscar_agenda_dividendos(ticker):
    try:
        url = f"https://brapi.dev/api/quote/{ticker}?dividends=true&token={API_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            info = r.json()
            if "results" in info and "dividendsData" in info["results"][0]:
                agenda = info["results"][0]["dividendsData"]
                dados = []
                for item in agenda:
                    dados.append({
                        "DataCom": item.get("dateWith", ""),
                        "DataEx": item.get("dateWithout", ""),
                        "DataPagamento": item.get("paymentDate", ""),
                        "ValorPorAcao": item.get("value", 0)
                    })
                return dados
    except Exception as e:
        print(f"Erro agenda dividendos {ticker}: {e}")
    return []

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
    for i in range(0, len(TICKERS_FIXOS), 50):
        lote = TICKERS_FIXOS[i:i+50]
        for ticker in lote:
            fundamentals = coletar_fundamentus(ticker)
            if not fundamentals:
                time.sleep(1)
                fundamentals = coletar_yfinance(ticker)
            if not fundamentals:
                fundamentals = {
                    "DY":0,"P/L":0,"P/VP":0,"ROE":0,"LPA":0,"VPA":0,"CrescimentoLucro":0,
                    "EBITDA":0,"DividaLiquida":0,"ValorMercado":0,"ReceitaLiquida":0,
                    "MargemLiquida":0,"Liquidez":0
                }
            div_hist = calcular_dividendos_historico(ticker)
            payout_hist = calcular_payout_historico(ticker)
            dados.append({"Ticker": ticker, **fundamentals, **div_hist, **payout_hist})
        print(f"Lote {i//50+1} atualizado com {len(lote)} ativos.")
        time.sleep(2)
    df = pd.DataFrame(dados)
    if not df.empty:
        salvar_dados(df)
        print(f"Banco atualizado com {len(df)} registros.")
    return df
##parte3
# Endpoint raiz
@app.get("/")
def home():
    return {
        "msg": "Bem-vindo à API Sobral Invest!",
        "endpoints_disponiveis": {
            "Ações": [
                "/acao/{ticker}",
                "/acao/{ticker}/dividendos",
                "/acao/{ticker}/payout",
                "/acao/{ticker}/agenda_dividendos"
            ],
            "Rankings (Top 30)": [
                "/ranking/dy",
                "/ranking/roe",
                "/ranking/graham",
                "/ranking/bazin",
                "/ranking/peterlynch",
                "/ranking/ebitda",
                "/ranking/valor_mercado",
                "/ranking/margem_liquida",
                "/ranking/receita_liquida",
                "/ranking/divida_liquida",
                "/ranking/liquidez",
                "/ranking/dy_consistente?periodo=3",
                "/ranking/payout_consistente?periodo=3",
                "/ranking/consistente?periodo=3"
            ]
        }
    }

# Endpoint indicadores gerais
@app.get("/acao/{ticker}")
def buscar_acao(ticker: str):
    df = carregar_dados()
    ticker = ticker.upper()
    dados = df[df["Ticker"] == ticker]
    if not dados.empty:
        registro = dados.to_dict(orient="records")[0]
        registro["PrecoAtual"] = preco_atual(ticker)
        return resposta_segura(ticker, registro, tipo="indicadores")
    return {"error": f"Ação {ticker} não encontrada."}

# Endpoint dividendos
@app.get("/acao/{ticker}/dividendos")
def dividendos_acao(ticker: str):
    resultados = calcular_dividendos_historico(ticker)
    return resposta_segura(ticker, resultados, tipo="dividendos")

# Endpoint payout
@app.get("/acao/{ticker}/payout")
def payout_acao(ticker: str):
    resultados = calcular_payout_historico(ticker)
    return resposta_segura(ticker, resultados, tipo="payout")

# Endpoint agenda de dividendos
@app.get("/acao/{ticker}/agenda_dividendos")
def agenda_dividendos(ticker: str):
    resultados = buscar_agenda_dividendos(ticker)
    if not resultados:
        return {"Ticker": ticker.upper(), "msg": "Sem dados válidos para agenda de dividendos."}
    return {"Ticker": ticker.upper(), "AgendaDividendos": resultados}

##parte4
@app.get("/ranking/divida_liquida")
def ranking_divida_liquida():
    df = carregar_dados()
    if df.empty or df["DividaLiquida"].sum() == 0:
        return {"msg": "Sem dados válidos para ranking Dívida Líquida."}
    return df.sort_values(by="DividaLiquida", ascending=True).head(30).to_dict(orient="records")

@app.get("/ranking/liquidez")
def ranking_liquidez():
    df = carregar_dados()
    if df.empty or df["Liquidez"].sum() == 0:
        return {"msg": "Sem dados válidos para ranking Liquidez."}
    return df.sort_values(by="Liquidez", ascending=False).head(30).to_dict(orient="records")

@app.get("/ranking/dy_consistente")
def ranking_dy_consistente(periodo: int = 3):
    df = carregar_dados()
    if df.empty or periodo not in [3,5]:
        return {"msg":"Sem dados válidos para ranking DY Consistente."}
    colunas = [f"DY_{i}A" for i in range(1, periodo+1)]
    df["DYConsistente"] = df[colunas].mean(axis=1)
    if df["DYConsistente"].sum() == 0:
        return {"msg":"Sem dados válidos para ranking DY Consistente."}
    return df.sort_values(by="DYConsistente", ascending=False).head(30).to_dict(orient="records")

@app.get("/ranking/payout_consistente")
def ranking_payout_consistente(periodo: int = 3):
    df = carregar_dados()
    if df.empty or periodo not in [3,5]:
        return {"msg":"Sem dados válidos para ranking Payout Consistente."}
    colunas = [f"Payout_{i}A" for i in range(1, periodo+1)]
    df["PayoutConsistente"] = df[colunas].mean(axis=1)
    if df["PayoutConsistente"].sum() == 0:
        return {"msg":"Sem dados válidos para ranking Payout Consistente."}
    return df.sort_values(by="PayoutConsistente", ascending=False).head(30).to_dict(orient="records")

@app.get("/ranking/consistente")
def ranking_consistente(periodo: int = 3):
    df = carregar_dados()
    if df.empty or periodo not in [3,5]:
        return {"msg":"Sem dados válidos para ranking Consistente."}
    colunas_dy = [f"DY_{i}A" for i in range(1, periodo+1)]
    colunas_payout = [f"Payout_{i}A" for i in range(1, periodo+1)]
    df["DYConsistente"] = df[colunas_dy].mean(axis=1)
    df["PayoutConsistente"] = df[colunas_payout].mean(axis=1)
    df["ConsistenciaTotal"] = (df["DYConsistente"] + df["PayoutConsistente"]) / 2
    if df["ConsistenciaTotal"].sum() == 0:
        return {"msg":"Sem dados válidos para ranking Consistente."}
    return df.sort_values(by="ConsistenciaTotal", ascending=False).head(30).to_dict(orient="records")

