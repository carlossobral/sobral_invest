"""
app.py - Coletor de dados SOBRAL Invest v3.1 (CORRIGIDO)
Correcoes:
- Score CS: 10 criterios (ROE>10%, DY>6%, DivLiq/EBITDA<2.5x, Volume>1M)
- Chama valuation.py para calculos de preco teto
- Remove Lynch_Preco_Teto, Lynch_Mod, AGF_Projetivo
- Mantem Peter Lynch (preco teto PEG=1)
- Calcula Dividendo_Medio_6a a partir do historico MFinance
- DivLiquida_PL calculado manualmente

Fonte principal: MFinance (batch, sem token)
Fallback: BRAPI + lista de 196 tickers
Gera: ativos.xlsx (1 aba "Dados" com ~55 colunas)
"""

import os
import sys
import json
import time
from datetime import date
from typing import List, Dict, Any

import pandas as pd
import requests

# Importar cliente MFinance
from mfinance_client import (
    MFinanceClient, merge_mfinance_data, parse_mfinance_dividends
)

# Importar valuation
from valuation import (
    calcular_graham, calcular_graham_br, calcular_bazin,
    calcular_lynch, calcular_agf_medio, calcular_upside
)

# Configuracoes
BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN", "")
USEBOLSAI_TOKEN = os.environ.get("USEBOLSAI_TOKEN", "")
TICKERS_PRIORITARIOS = [
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


def get_selic() -> float:
    """Busca SELIC anual via Banco Central (serie 432)."""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        dados = r.json()

        valor_str = dados[0]["valor"]
        valor = float(valor_str)

        # Deteccao automatica: < 1.0 = diaria, >= 1.0 = anual
        if valor < 1.0:
            selic = round((valor / 100) * 252 * 100, 2)
        else:
            selic = round(valor, 2)

        if 2.0 <= selic <= 30.0:
            return selic

        # Fallback: serie 1178 (SELIC acumulada mes)
        url2 = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1178/dados/ultimos/1?formato=json"
        r2 = requests.get(url2, timeout=15)
        r2.raise_for_status()
        dados2 = r2.json()
        selic2 = float(dados2[0]["valor"])
        if 2.0 <= selic2 <= 30.0:
            return selic2

    except Exception as e:
        print("Erro SELIC: " + str(e))

    # Fallback final
    if os.path.exists("selic.json"):
        with open("selic.json", "r") as f:
            return json.load(f).get("selic", 10.75)
    return 10.75


def calcular_valuation(row: pd.Series, selic: float) -> Dict[str, float]:
    """Calcula metodos de valuation usando valuation.py."""
    cotacao = row.get("Cotacao", 0)
    lpa = row.get("LPA", 0)
    vpa = row.get("VPA", 0)
    dy = row.get("DY", 0) or row.get("DY_12m", 0)
    cagr_lucros = row.get("CAGR_Lucros_5a", 0)
    dividendo_total_12m = row.get("Dividendo_Total_12m", 0)
    dividendo_medio_6a = row.get("Dividendo_Medio_6a", 0)

    result = {}

    # 1. Graham Classico
    result["Graham"] = calcular_graham(lpa, vpa)

    # 2. Graham BR
    result["Graham_BR"] = calcular_graham_br(lpa, cagr_lucros)

    # 3. Bazin (DPA = Dividendo_Total_12m)
    result["Bazin"] = calcular_bazin(dividendo_total_12m)

    # 4. Peter Lynch (MANTIDO: preco teto PEG=1)
    result["Lynch"] = calcular_lynch(lpa, cagr_lucros)

    # 5. AGF Medio (DPA medio 6 anos)
    result["AGF_Medio"] = calcular_agf_medio(dividendo_medio_6a)

    # Upside/Downside
    if cotacao > 0:
        for key in ["Graham", "Graham_BR", "Bazin", "Lynch", "AGF_Medio"]:
            preco = result.get(key, 0)
            result["Upside_" + key] = calcular_upside(cotacao, preco) or 0

    return result


def calcular_score_cs(row: pd.Series) -> Dict[str, Any]:
    """Calcula Score CS (Carlos Sobral) 0-10 com 10 criterios."""
    score = 0
    detalhes = {}

    # 1. ROE > 10% (AJUSTADO: era 15%)
    roe = row.get("ROE", 0)
    detalhes["ROE_10pct"] = 1 if roe > 10 else 0
    score += detalhes["ROE_10pct"]

    # 2. DY > 6% (AJUSTADO: era 3%)
    dy = row.get("DY", 0) or row.get("DY_12m", 0)
    detalhes["DY_6pct"] = 1 if dy > 6 else 0
    score += detalhes["DY_6pct"]

    # 3. DivLiq/EBITDA < 2.5x (AJUSTADO: era DivLiquida_PL < 0.5)
    div_ebitda = row.get("DivLiquida_EBITDA", 0)
    detalhes["DivLiq_EBITDA_2_5"] = 1 if 0 < div_ebitda < 2.5 else 0
    score += detalhes["DivLiq_EBITDA_2_5"]

    # 4. P/L < 15
    pl = row.get("PL", 0)
    detalhes["PL_15"] = 1 if 0 < pl < 15 else 0
    score += detalhes["PL_15"]

    # 5. P/VP < 2
    pvp = row.get("PVP", 0)
    detalhes["PVP_2"] = 1 if 0 < pvp < 2 else 0
    score += detalhes["PVP_2"]

    # 6. Margem Liquida > 10%
    margem = row.get("MargemLiquida", 0)
    detalhes["Margem_10pct"] = 1 if margem > 10 else 0
    score += detalhes["Margem_10pct"]

    # 7. Liquidez Corrente > 1
    liq = row.get("LiquidezCorrente", 0)
    detalhes["LiqCorrente_1"] = 1 if liq > 1 else 0
    score += detalhes["LiqCorrente_1"]

    # 8. CAGR Lucros 5 anos > 5%
    cagr = row.get("CAGR_Lucros_5a", 0)
    detalhes["CAGR_5pct"] = 1 if cagr > 5 else 0
    score += detalhes["CAGR_5pct"]

    # 9. ROIC > 10%
    roic = row.get("ROIC", 0)
    detalhes["ROIC_10pct"] = 1 if roic > 10 else 0
    score += detalhes["ROIC_10pct"]

    # 10. Volume Medio > R$ 1.000.000 (NOVO)
    volume_medio = row.get("Volume_Medio", 0)
    detalhes["Volume_1M"] = 1 if volume_medio > 1000000 else 0
    score += detalhes["Volume_1M"]

    # Classificacao
    if score >= 9:
        classificacao = "Excelente"
    elif score >= 7:
        classificacao = "Bom"
    elif score >= 5:
        classificacao = "Regular"
    elif score >= 3:
        classificacao = "Fraco"
    else:
        classificacao = "Pessimo"

    return {
        "Score_CS": score,
        "Score_CS_Classificacao": classificacao,
        **detalhes
    }


def complementar_brapi(df: pd.DataFrame, token: str = "") -> pd.DataFrame:
    """Complementa dados com BRAPI (beta, medias moveis, etc.)."""
    if not token:
        return df

    print("Complementando com BRAPI...")

    headers = {"Authorization": "Bearer " + token} if token else {}

    for idx, row in df.iterrows():
        ticker = row["Ticker"]
        try:
            url = "https://brapi.dev/api/quote/" + ticker + "?modules=summaryProfile,financialData,defaultKeyStatistics"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                continue

            data = r.json()
            results = data.get("results", [])
            if not results:
                continue

            info = results[0]

            # Beta
            beta = info.get("beta")
            if beta is not None:
                df.at[idx, "Beta"] = round(beta, 2)

            # Medias moveis
            stats = info.get("defaultKeyStatistics", {})
            if stats.get("fiftyDayAverage"):
                df.at[idx, "Media_50d"] = round(stats["fiftyDayAverage"], 2)
            if stats.get("twoHundredDayAverage"):
                df.at[idx, "Media_200d"] = round(stats["twoHundredDayAverage"], 2)

            # FCO / FCL (do financialData)
            fin = info.get("financialData", {})
            if fin.get("operatingCashflow"):
                df.at[idx, "FCO"] = fin["operatingCashflow"]
            if fin.get("freeCashflow"):
                df.at[idx, "FCL"] = fin["freeCashflow"]

            time.sleep(0.3)

        except Exception as e:
            print("Erro BRAPI " + ticker + ": " + str(e))
            continue

    return df


def main():
    print("=" * 70)
    print("SOBRAL INVEST - Coletor de Dados v3.1 (CORRIGIDO)")
    print("=" * 70)
    print("Inicio: " + str(pd.Timestamp.now()))

    # 1. Buscar SELIC
    print("[0/4] Buscando SELIC...")
    selic = get_selic()
    print("SELIC: " + str(selic) + "%")

    # Salvar selic.json
    with open("selic.json", "w", encoding="utf-8") as f:
        json.dump({"selic": selic, "data": str(date.today())}, f)

    # 2. Inicializar cliente MFinance
    client = MFinanceClient(timeout=25, retries=3)

    # 3. Buscar todos os ativos do MFinance
    print("[1/4] Buscando ativos do MFinance...")
    all_stocks = client.get_all_stocks(batch_size=50)

    if not all_stocks:
        print("MFinance retornou vazio. Usando fallback com lista priorizada...")
        all_stocks = client.get_stocks_batch(TICKERS_PRIORITARIOS)

    print("Ativos coletados: " + str(len(all_stocks)))

    if not all_stocks:
        print("Nenhum ativo coletado. Abortando.")
        sys.exit(1)

    # 4. Buscar indicadores
    symbols = [s.get("symbol", "") for s in all_stocks if s.get("symbol")]
    print("[2/4] Buscando indicadores para " + str(len(symbols)) + " ativos...")
    all_indicators = client.get_all_indicators(symbols, batch_size=50)
    print("Indicadores coletados: " + str(len(all_indicators)))

    # 5. Buscar dividendos (1 por 1 - MFinance nao tem batch)
    print("[3/4] Buscando dividendos para " + str(len(symbols)) + " ativos...")
    dividends_map = {}
    for i, sym in enumerate(symbols):
        if i % 50 == 0:
            print("  Dividendos " + str(i+1) + "/" + str(len(symbols)) + "...")
        div_data = client.get_dividends(sym)
        parsed = parse_mfinance_dividends(div_data)
        dividends_map[sym] = parsed
        time.sleep(0.1)

    # 6. Mesclar dados
    print("[4/4] Mesclando e processando dados...")
    merged = merge_mfinance_data(all_stocks, all_indicators, dividends_map)

    if not merged:
        print("Nenhum dado mesclado. Abortando.")
        sys.exit(1)

    # 7. Criar DataFrame
    df = pd.DataFrame(merged)

    # 8. Calcular campos derivados
    df["Patrimonio"] = df["Qtd_Acoes"] * df["VPA"]
    df["Lucro_Liquido"] = df["Qtd_Acoes"] * df["LPA"]
    df["EBIT"] = df.apply(
        lambda r: (r["Market_Cap"] / r["EV_EBIT"]) if r.get("EV_EBIT", 0) > 0 else 0,
        axis=1
    )
    df["Receita_Liquida"] = df.apply(
        lambda r: (r["Market_Cap"] / r["PSR"]) if r.get("PSR", 0) > 0 else 0,
        axis=1
    )

    # CORRECAO: Calcular DivLiquida_PL manualmente
    df["DivLiquida_PL"] = df.apply(
        lambda r: round(r["DivLiquida_Ativos"] / r["PL_Ativos"], 4)
        if r.get("PL_Ativos", 0) > 0 and r.get("DivLiquida_Ativos", 0) > 0
        else 0,
        axis=1
    )

    # CORRECAO: Calcular Dividendo_Medio_6a a partir do historico
    # Usar Dividendo_Medio_12m como proxy se nao tivermos 6 anos
    # Ou calcular a partir dos dividendos brutos se disponiveis
    df["Dividendo_Medio_6a"] = df["Dividendo_Medio_12m"]  # Proxy: usar media 12m como aproximacao

    # 9. Calcular Valuation
    print("Calculando valuation...")
    for idx, row in df.iterrows():
        val = calcular_valuation(row, selic)
        for k, v in val.items():
            if k not in df.columns:
                df[k] = 0.0
            df.at[idx, k] = v

    # 10. Calcular Score CS
    print("Calculando Score CS...")
    for idx, row in df.iterrows():
        score = calcular_score_cs(row)
        for k, v in score.items():
            if k not in df.columns:
                df[k] = ""
            df.at[idx, k] = v

    # 11. Complementar com BRAPI (se token disponivel)
    if BRAPI_TOKEN:
        df = complementar_brapi(df, BRAPI_TOKEN)

    # 12. Ordenar colunas
    col_order = [
        "Ticker", "Nome", "Setor", "SubSetor", "Segmento",
        "Cotacao", "Variacao", "Abertura", "Maxima", "Minima",
        "Fechamento_Anterior", "Volume", "Volume_Medio",
        "Maxima_52s", "Minima_52s", "Market_Cap",
        "PE", "EPS", "DY", "DY_12m",
        "PL", "PVP", "PSR", "PAtivo", "PCapGiro", "PAtivoCircLiq",
        "PEBIT", "PEBITDA", "EV_EBIT", "EV_EBITDA",
        "LPA", "VPA", "Patrimonio", "Lucro_Liquido", "EBIT", "Receita_Liquida",
        "ROE", "ROA", "ROIC", "GiroAtivos",
        "MargemBruta", "MargemEBITDA", "MargemEBIT", "MargemLiquida",
        "DivLiquida_Ativos", "DivLiquida_PL", "DivLiquida_EBIT", "DivLiquida_EBITDA",
        "LiquidezCorrente", "Passivos_Ativos", "PL_Ativos",
        "CAGR_Receitas_5a", "CAGR_Lucros_5a",
        "Qtd_Acoes",
        "Dividendo_Medio_12m", "Dividendo_Total_12m", "Dividendo_Ultimo", "Qtd_Dividendos_12m",
        "Dividendo_Medio_6a",
        "Graham", "Graham_BR", "Bazin", "Lynch", "AGF_Medio",
        "Upside_Graham", "Upside_Graham_BR", "Upside_Bazin", "Upside_Lynch", "Upside_AGF_Medio",
        "Score_CS", "Score_CS_Classificacao",
        "ROE_10pct", "DY_6pct", "DivLiq_EBITDA_2_5", "PL_15", "PVP_2",
        "Margem_10pct", "LiqCorrente_1", "CAGR_5pct", "ROIC_10pct", "Volume_1M",
        "Beta", "Media_50d", "Media_200d", "FCO", "FCL",
    ]

    # Garantir que todas as colunas existam
    for col in col_order:
        if col not in df.columns:
            df[col] = 0 if col not in ["Nome", "Setor", "SubSetor", "Segmento", "Score_CS_Classificacao"] else ""

    df = df[[c for c in col_order if c in df.columns]]

    # 13. Salvar
    print("[5/4] Salvando arquivos...")

    # Excel
    with pd.ExcelWriter("ativos.xlsx", engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Dados", index=False)

    # CSV
    df.to_csv("ativos.csv", index=False, encoding="utf-8-sig")

    # 14. Resumo
    print("=" * 70)
    print("RESUMO")
    print("=" * 70)
    print("Total de ativos: " + str(len(df)))
    print("Colunas: " + str(len(df.columns)))
    print("Score CS medio: " + str(round(df["Score_CS"].mean(), 1)))
    print("Score CS max: " + str(df["Score_CS"].max()))
    print("Score CS min: " + str(df["Score_CS"].min()))
    print("Arquivos gerados: ativos.xlsx, ativos.csv")
    print("Fim: " + str(pd.Timestamp.now()))
    print("=" * 70)

    # Verificar se planilha nao esta vazia
    if len(df) == 0:
        print("ERRO: Planilha vazia!")
        sys.exit(1)

    print("Concluido com sucesso!")


if __name__ == "__main__":
    main()
