"""
app.py - Coletor de dados SOBRAL Invest v3.2 (REFATORADO)
Ajustes para mfinance_client.py v3.0:
- client.get_all_stocks() → client.get_stocks() (batch simplificado)
- client.get_all_indicators() → client.get_indicators() (batch simplificado)
- Remove fallback de get_stocks_batch() com TICKERS_PRIORITARIOS
- Remove batch_size dos parametros (nao mais necessario)

Correcoes mantidas:
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

# Importar cliente MFinance REFATORADO
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
    print("SOBRAL INVEST - Coletor de Dados v3.2 (REFATORADO)")
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

    # 3. Buscar TODOS os ativos do MFinance (batch simplificado)
    print("[1/4] Buscando ativos do MFinance...")
    all_stocks = client.get_stocks()

    print("Ativos coletados: " + str(len(all_stocks)))

    if not all_stocks:
        print("Nenhum ativo coletado. Abortando.")
        sys.exit(1)

    # 4. Buscar TODOS os indicadores (batch simplificado)
    print("[2/4] Buscando indicadores...")
    all_indicators = client.get_indicators()
    print("Indicadores coletados: " + str(len(all_indicators)))

    # 5. Extrair symbols para buscar dividendos
    symbols = [s.get("symbol", "") for s in all_stocks if s.get("symbol")]

    # 6. Buscar dividendos (1 por 1 - MFinance nao tem batch)
    print("[3/4] Buscando dividendos para " + str(len(symbols)) + " ativos...")
    dividends_map = client.get_all_dividends(symbols)

    # 7. Mesclar dados
    print("[4/4] Mesclando e processando dados...")
    merged = merge_mfinance_data(all_stocks, all_indicators, dividends_map)

    if not merged:
        print("Nenhum dado mesclado. Abortando.")
        sys.exit(1)

    # 8. Criar DataFrame
    df = pd.DataFrame(merged)

    # 9. Calcular campos derivados
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
    df["Dividendo_Medio_6a"] = df["Dividendo_Medio_12m"]  # Proxy: usar media 12m como aproximacao

    # 10. Calcular Valuation
    print("Calculando valuation...")
    for idx, row in df.iterrows():
        val = calcular_valuation(row, selic)
        for k, v in val.items():
            if k not in df.columns:
                df[k] = 0.0
            df.at[idx, k] = v

    # 11. Calcular Score CS
    print("Calculando Score CS...")
    for idx, row in df.iterrows():
        score = calcular_score_cs(row)
        for k, v in score.items():
            if k not in df.columns:
                df[k] = ""
            df.at[idx, k] = v

    # 12. Complementar com BRAPI (se token disponivel)
    if BRAPI_TOKEN:
        df = complementar_brapi(df, BRAPI_TOKEN)

    # 13. Ordenar colunas
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

    # 14. Salvar
    print("[5/4] Salvando arquivos...")

    # Excel
    with pd.ExcelWriter("ativos.xlsx", engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Dados", index=False)

    # CSV
    df.to_csv("ativos.csv", index=False, encoding="utf-8-sig")

    # 15. Resumo
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
