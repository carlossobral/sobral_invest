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
    """
    Retorna resposta segura para endpoints.
    Se não houver dados válidos, devolve mensagem clara em vez de zeros.
    """
    if not dados or all(v == 0 or v is None for v in dados.values()):
        return {"Ticker": ticker.upper(), "msg": f"Sem dados válidos para {tipo}."}
    return {"Ticker": ticker.upper(), **dados}
##PARTE2a
def coletar_fundamentus(ticker):
    try:
        url = f"https://fundamentus.com.br/detalhes.php?papel={ticker}"
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        dados = {}
        # Exemplo de coleta: P/L, ROE, DY
        for linha in soup.find_all("tr"):
            cols = linha.find_all("td")
            if len(cols) == 2:
                chave = cols[0].text.strip()
                valor = cols[1].text.strip().replace(",", ".").replace("%", "")
                try:
                    dados[chave] = float(valor)
                except:
                    dados[chave] = valor
        return dados
    except Exception as e:
        print(f"Erro ao coletar Fundamentus {ticker}: {e}")
        return {}

def coletar_yfinance(ticker):
    try:
        yf_ticker = yf.Ticker(f"{ticker}.SA")
        info = yf_ticker.info
        dados = {
            "Setor": info.get("sector", ""),
            "Subsetor": info.get("industry", ""),
            "ValorMercado": info.get("marketCap", 0),
            "EBITDA": info.get("ebitda", 0),
            "Liquidez": info.get("averageVolume", 0),
        }
        return dados
    except Exception as e:
        print(f"Erro ao coletar yfinance {ticker}: {e}")
        return {}

def calcular_dividendos_historico(ticker, anos=6):
    try:
        yf_ticker = yf.Ticker(f"{ticker}.SA")
        dividends = yf_ticker.dividends
        history = yf_ticker.history(period=f"{anos}y")

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

def salvar_dados(df):
    if df.empty:
        print("Nenhum dado coletado, não salvando no banco.")
        return False
    conn = sqlite3.connect(DB_NAME)
    df.to_sql("acoes", conn, if_exists="replace", index=False)
    conn.close()
    return True

def carregar_dados():
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql("SELECT * FROM acoes", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def atualizar_dados():
    resultados = []
    for ticker in TICKERS_FIXOS:
        try:
            dados_fund = coletar_fundamentus(ticker)
            dados_yf = coletar_yfinance(ticker)
            dados_div = calcular_dividendos_historico(ticker)
            dados_payout = calcular_payout_historico(ticker)

            dados = {**dados_fund, **dados_yf, **dados_div, **dados_payout}
            dados["Ticker"] = ticker

            # Padronização de nomes de colunas para os rankings
            if "Div.Yield" in dados:
                dados["DY"] = dados.pop("Div.Yield")
            if "DividendYield" in dados:
                dados["DY"] = dados.pop("DividendYield")

            if "ReturnOnEquity" in dados:
                dados["ROE"] = dados.pop("ReturnOnEquity")
            if "ROE (%)" in dados:
                dados["ROE"] = dados.pop("ROE (%)")

            if "LucroPorAcao" in dados:
                dados["LPA"] = dados.pop("LucroPorAcao")
            if "EPS" in dados:
                dados["LPA"] = dados.pop("EPS")

            if "ValorPatrimonialPorAcao" in dados:
                dados["VPA"] = dados.pop("ValorPatrimonialPorAcao")
            if "BookValuePerShare" in dados:
                dados["VPA"] = dados.pop("BookValuePerShare")

            if "NetMargin" in dados:
                dados["MargemLiquida"] = dados.pop("NetMargin")

            if "Revenue" in dados:
                dados["ReceitaLiquida"] = dados.pop("Revenue")

            if "NetDebt" in dados:
                dados["DividaLiquida"] = dados.pop("NetDebt")

            resultados.append(dados)
            print(f"Coletado {ticker}")
            time.sleep(1)

        except Exception as e:
            print(f"Erro ao coletar {ticker}: {e}")

    df = pd.DataFrame(resultados)
    sucesso = salvar_dados(df)
    return df if sucesso else pd.DataFrame()

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

@app.get("/acao/{ticker}")
def buscar_acao(ticker: str):
    df = carregar_dados()
    ticker = ticker.upper()
    dados = df[df["Ticker"] == ticker]
    if not dados.empty:
        registro = dados.to_dict(orient="records")[0]
        return resposta_segura(ticker, registro, tipo="indicadores")
    return {"error": f"Ação {ticker} não encontrada."}

@app.get("/acao/{ticker}/dividendos")
def dividendos_acao(ticker: str):
    resultados = calcular_dividendos_historico(ticker)
    return resposta_segura(ticker, resultados, tipo="dividendos")

@app.get("/acao/{ticker}/payout")
def payout_acao(ticker: str):
    resultados = calcular_payout_historico(ticker)
    return resposta_segura(ticker, resultados, tipo="payout")

@app.get("/acao/{ticker}/agenda_dividendos")
def agenda_dividendos(ticker: str):
    # Se você tiver função buscar_agenda_dividendos implementada
    try:
        resultados = buscar_agenda_dividendos(ticker)
    except:
        resultados = {}
    if not resultados:
        return {"Ticker": ticker.upper(), "msg": "Sem dados válidos para agenda de dividendos."}
    return {"Ticker": ticker.upper(), "AgendaDividendos": resultados}

@app.get("/atualizar")
def atualizar():
    df = atualizar_dados()
    if df.empty:
        return {"msg": "Falha ao atualizar, nenhum dado coletado."}
    return {"msg": f"Dados atualizados com sucesso ({len(df)} ativos)."}
# ============================
# Parte 4 - Endpoints Rankings
# ============================

@app.get("/ranking/dy")
def ranking_dy():
    df = carregar_dados()
    if df.empty or "DY" not in df or df["DY"].sum() == 0:
        return {"msg": "Sem dados válidos para ranking DY."}
    return df.sort_values(by="DY", ascending=False).head(30).to_dict(orient="records")


@app.get("/ranking/roe")
def ranking_roe():
    df = carregar_dados()
    if df.empty or "ROE" not in df or df["ROE"].sum() == 0:
        return {"msg": "Sem dados válidos para ranking ROE."}
    return df.sort_values(by="ROE", ascending=False).head(30).to_dict(orient="records")


@app.get("/ranking/graham")
def ranking_graham():
    df = carregar_dados()
    if df.empty or "LPA" not in df or "VPA" not in df:
        return {"msg": "Sem dados válidos para ranking Graham."}
    df["Graham"] = df.apply(
        lambda row: math.sqrt(22.5 * row["LPA"] * row["VPA"]) if row["LPA"] > 0 and row["VPA"] > 0 else 0,
        axis=1
    )
    return df.sort_values(by="Graham", ascending=False).head(30).to_dict(orient="records")


@app.get("/ranking/bazin")
def ranking_bazin():
    df = carregar_dados()
    if df.empty or "DY" not in df:
        return {"msg": "Sem dados válidos para ranking Bazin."}
    df["Bazin"] = df["DY"].apply(lambda x: x if x >= 6 else 0)
    return df.sort_values(by="Bazin", ascending=False).head(30).to_dict(orient="records")


@app.get("/ranking/peterlynch")
def ranking_peterlynch():
    df = carregar_dados()
    if df.empty or "P/L" not in df or "CrescimentoLucro" not in df:
        return {"msg": "Sem dados válidos para ranking Peter Lynch."}
    def calc_lynch(row):
        pl = row["P/L"]
        crescimento = row["CrescimentoLucro"]
        return pl / crescimento if crescimento > 0 else float("inf")
    df["Lynch"] = df.apply(calc_lynch, axis=1)
    return df.sort_values(by="Lynch", ascending=True).head(30).to_dict(orient="records")


@app.get("/ranking/ebitda")
def ranking_ebitda():
    df = carregar_dados()
    if df.empty or "EBITDA" not in df:
        return {"msg": "Sem dados válidos para ranking EBITDA."}
    df["EBITDA_Milhoes"] = df["EBITDA"] / 1_000_000
    return df.sort_values(by="EBITDA", ascending=False).head(30)[["Ticker", "EBITDA_Milhoes"]].to_dict(orient="records")


@app.get("/ranking/valor_mercado")
def ranking_valor_mercado():
    df = carregar_dados()
    if df.empty or "ValorMercado" not in df:
        return {"msg": "Sem dados válidos para ranking Valor de Mercado."}
    df["ValorMercado_Milhoes"] = df["ValorMercado"] / 1_000_000
    return df.sort_values(by="ValorMercado", ascending=False).head(30)[["Ticker", "ValorMercado_Milhoes"]].to_dict(orient="records")


@app.get("/ranking/liquidez")
def ranking_liquidez():
    df = carregar_dados()
    if df.empty or "Liquidez" not in df:
        return {"msg": "Sem dados válidos para ranking Liquidez."}
    df["Liquidez_Milhoes"] = df["Liquidez"] / 1_000_000
    return df.sort_values(by="Liquidez", ascending=False).head(30)[["Ticker", "Liquidez_Milhoes"]].to_dict(orient="records")


@app.get("/ranking/receita_liquida")
def ranking_receita_liquida():
    df = carregar_dados()
    if df.empty or "ReceitaLiquida" not in df:
        return {"msg": "Sem dados válidos para ranking Receita Líquida."}
    df["ReceitaLiquida_Milhoes"] = df["ReceitaLiquida"] / 1_000_000
    return df.sort_values(by="ReceitaLiquida", ascending=False).head(30)[["Ticker", "ReceitaLiquida_Milhoes"]].to_dict(orient="records")


@app.get("/ranking/divida_liquida")
def ranking_divida_liquida():
    df = carregar_dados()
    if df.empty or "DividaLiquida" not in df:
        return {"msg": "Sem dados válidos para ranking Dívida Líquida."}
    df["DividaLiquida_Milhoes"] = df["DividaLiquida"] / 1_000_000
    return df.sort_values(by="DividaLiquida", ascending=True).head(30)[["Ticker", "DividaLiquida_Milhoes"]].to_dict(orient="records")


@app.get("/ranking/margem_liquida")
def ranking_margem_liquida():
    df = carregar_dados()
    if df.empty or "MargemLiquida" not in df:
        return {"msg": "Sem dados válidos para ranking Margem Líquida."}
    df["MargemLiquida_Milhoes"] = df["MargemLiquida"] / 1_000_000
    return df.sort_values(by="MargemLiquida", ascending=False).head(30)[["Ticker", "MargemLiquida_Milhoes"]].to_dict(orient="records")


@app.get("/ranking/dy_consistente")
def ranking_dy_consistente(periodo: int = 3):
    df = carregar_dados()
    if df.empty or periodo not in [3, 5]:
        return {"msg": "Sem dados válidos para ranking DY Consistente."}
    colunas = [f"DY_{i}A" for i in range(1, periodo+1) if f"DY_{i}A" in df]
    if not colunas:
        return {"msg": "Sem dados válidos para ranking DY Consistente."}
    df["DYConsistente"] = df[colunas].mean(axis=1)
    return df.sort_values(by="DYConsistente", ascending=False).head(30).to_dict(orient="records")


@app.get("/ranking/payout_consistente")
def ranking_payout_consistente(periodo: int = 3):
    df = carregar_dados()
    if df.empty or periodo not in [3, 5]:
        return {"msg": "Sem dados válidos para ranking Payout Consistente."}
    colunas = [f"Payout_{i}A" for i in range(1, periodo+1) if f"Payout_{i}A" in df]
    if not colunas:
        return {"msg": "Sem dados válidos para ranking Payout Consistente."}
    df["PayoutConsistente"] = df[colunas].mean(axis=1)
    return df.sort_values(by="PayoutConsistente", ascending=False).head(30).to_dict(orient="records")


@app.get("/ranking/consistente")
def ranking_consistente(periodo: int = 3):
    df = carregar_dados()
    if df.empty or periodo not in [3, 5]:
        return {"msg": "Sem dados válidos para ranking Consistente."}
    colunas_dy = [f"DY_{i}A" for i in range(1, periodo+1) if f"DY_{i}A" in df]
    colunas_payout = [f"Payout_{i}A" for i in range(1, periodo+1) if f"Payout_{i}A" in df]
    if not colunas_dy or not colunas_payout:
        return {"msg": "Sem dados válidos para ranking Consistente."}
    df["DYConsistente"] = df[colunas_dy].mean(axis=1)
    df["PayoutConsistente"] = df[colunas_payout].mean(axis=1)
    df["ConsistenciaTotal"] = (df["DYConsistente"] + df["PayoutConsistente"]) / 2
    return df.sort_values(by="ConsistenciaTotal", ascending=False).head(30).to_dict(orient="records")


@app.get("/health")
def health():
    df = carregar_dados()
    if df.empty:
        return {"status": "offline", "msg": "Banco vazio, nenhum dado carregado."}
    return {"status": "online", "msg": f"Banco com {len(df)} ativos carregados."}

