"""
Sobral Invest - Coletor de Dados
Busca todos os ativos do MFinance, calcula valuation e score,
e gera ativos.xlsx com 1 aba "Dados"
"""
import os
import sys
import json
import pandas as pd
from datetime import datetime

# Adicionar diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mfinance_client import MFinanceClient, parse_mfinance_data
from valuation import (
    calcular_graham, calcular_graham_br, calcular_bazin,
    calcular_lynch, calcular_agf_medio, calcular_agf_projetivo
)
from checklist import checklist_buy_hold
from indicadores import calcular_indicadores
from brapi_client import obter_dados_brapi


def carregar_selic() -> float:
    """Carrega taxa SELIC do selic.json"""
    try:
        with open("selic.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return float(data.get("selic_atual", 0.1075))
    except Exception:
        return 0.1075  # Fallback 10.75%


def complementar_com_brapi(df: pd.DataFrame, brapi_token: str = "") -> pd.DataFrame:
    """
    Complementa dados do MFinance com BRAPI para campos faltantes:
    - Beta, Media_50d, Media_200d
    - FCO, FCL
    - Recomendacao_Analysts, Preco_Alvo_Medio
    """
    print("\nComplementando com BRAPI...")

    for idx, row in df.iterrows():
        ticker = row["Ticker"]
        try:
            brapi_data = obter_dados_brapi(ticker, token=brapi_token)
            if brapi_data:
                info = brapi_data.get("results", [{}])[0]

                # Atualizar campos se disponíveis
                if not row["Beta"] and info.get("beta"):
                    df.at[idx, "Beta"] = info["beta"]
                if not row["Media_50d"] and info.get("fiftyDayAverage"):
                    df.at[idx, "Media_50d"] = info["fiftyDayAverage"]
                if not row["Media_200d"] and info.get("twoHundredDayAverage"):
                    df.at[idx, "Media_200d"] = info["twoHundredDayAverage"]
                if not row["FCO"] and info.get("operatingCashflow"):
                    df.at[idx, "FCO"] = info["operatingCashflow"]
                if not row["FCL"] and info.get("freeCashflow"):
                    df.at[idx, "FCL"] = info["freeCashflow"]
                if not row["Recomendacao_Analysts"] and info.get("recommendationKey"):
                    df.at[idx, "Recomendacao_Analysts"] = info["recommendationKey"]
                if not row["Qtd_Analysts"] and info.get("numberOfAnalystOpinions"):
                    df.at[idx, "Qtd_Analysts"] = info["numberOfAnalystOpinions"]
                if not row["Preco_Alvo_Medio"] and info.get("targetMeanPrice"):
                    df.at[idx, "Preco_Alvo_Medio"] = info["targetMeanPrice"]
        except Exception as e:
            print(f"  Erro BRAPI {ticker}: {e}")
            continue

    return df


def calcular_valuation_e_score(df: pd.DataFrame, selic: float) -> pd.DataFrame:
    """
    Calcula preços alvo (Graham, Bazin, etc.) e Score CS para cada ativo
    """
    print("\nCalculando valuation e Score CS...")

    graham_list = []
    graham_br_list = []
    bazin_list = []
    lynch_list = []
    agf_medio_list = []
    agf_proj_list = []
    score_list = []

    for idx, row in df.iterrows():
        ticker = row["Ticker"]

        # Preparar dados para valuation
        dados_val = {
            "lpa": row["LPA"],
            "vpa": row["VPA"],
            "dy": row["DY"] / 100 if row["DY"] else 0,
            "cotacao": row["Cotacao"],
            "pl": row["PL"],
            "pvp": row["PVP"],
            "roic": row["ROIC"] / 100 if row["ROIC"] else 0,
            "margem_liquida": row["Margem_Liquida"] / 100 if row["Margem_Liquida"] else 0,
            "divida_patrimonio": row["Divida_PL"],
            "cagr_receitas": row["Receita_CAGR"] / 100 if row["Receita_CAGR"] else 0,
            "cagr_lucros": row["Lucro_CAGR"] / 100 if row["Lucro_CAGR"] else 0,
        }

        # Calcular preços alvo
        try:
            graham = calcular_graham(dados_val)
            graham_br = calcular_graham_br(dados_val, selic)
            bazin = calcular_bazin(dados_val)
            lynch = calcular_lynch(dados_val)
            agf_medio = calcular_agf_medio(dados_val, selic)
            agf_proj = calcular_agf_projetivo(dados_val, selic)
        except Exception as e:
            print(f"  Erro valuation {ticker}: {e}")
            graham = graham_br = bazin = lynch = agf_medio = agf_proj = 0

        graham_list.append(graham)
        graham_br_list.append(graham_br)
        bazin_list.append(bazin)
        lynch_list.append(lynch)
        agf_medio_list.append(agf_medio)
        agf_proj_list.append(agf_proj)

        # Calcular Score CS
        try:
            dados_check = {
                "ticker": ticker,
                "roe": row["ROE"],
                "dy": row["DY"],
                "divida_patrimonio": row["Divida_PL"],
                "margem_liquida": row["Margem_Liquida"],
                "roic": row["ROIC"],
                "cagr_receitas": row["Receita_CAGR"],
                "cagr_lucros": row["Lucro_CAGR"],
                "pl": row["PL"],
                "pvp": row["PVP"],
                "liquidez_corrente": row["Liquidez_Corrente"],
            }
            score_result = checklist_buy_hold(dados_check)
            score = score_result.get("score", 0)
        except Exception as e:
            print(f"  Erro score {ticker}: {e}")
            score = 0

        score_list.append(score)

    df["Graham"] = graham_list
    df["Graham_BR"] = graham_br_list
    df["Bazin"] = bazin_list
    df["Lynch"] = lynch_list
    df["AGF_Medio"] = agf_medio_list
    df["AGF_Projetivo"] = agf_proj_list
    df["Score_CS"] = score_list

    return df


def main():
    print("=" * 70)
    print("SOBRAL INVEST - COLETOR DE DADOS")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. Carregar SELIC
    selic = carregar_selic()
    print(f"\nSELIC atual: {selic*100:.2f}%")

    # 2. Buscar todos os ativos do MFinance
    print("\n[1/4] Buscando ativos do MFinance...")
    client = MFinanceClient(delay=0.3)
    raw_data = client.get_all_stocks_full(batch_size=50)
    print(f"Ativos coletados: {len(raw_data)}")

    # 3. Parsear dados
    print("\n[2/4] Parseando dados...")
    parsed = parse_mfinance_data(raw_data)
    df = pd.DataFrame(parsed)
    print(f"Registros parseados: {len(df)}")

    # 4. Complementar com BRAPI (campos faltantes)
    print("\n[3/4] Complementando com BRAPI...")
    brapi_token = os.getenv("BRAPI_TOKEN", "")
    df = complementar_com_brapi(df, brapi_token)

    # 5. Calcular valuation e Score CS
    print("\n[4/4] Calculando valuation e Score CS...")
    df = calcular_valuation_e_score(df, selic)

    # 6. Ordenar colunas
    colunas_ordem = [
        # IDENTIFICAÇÃO
        "Ticker", "Nome_Empresa", "Nome_Curto", "CNPJ", "Segmento_Listagem",
        # COTAÇÃO
        "Cotacao", "Abertura", "Maxima", "Minima", "Variacao", 
        "Volume", "Volume_Medio", "Qtd_Acoes",
        # VALUATION
        "PL", "PVP", "PSR", "P_EBIT", "P_EBITDA", 
        "EV_EBIT", "EV_EBITDA", "DY", "DY_TTM", "Payout",
        # RENTABILIDADE
        "ROE", "ROA", "ROIC", 
        "Margem_Bruta", "Margem_EBIT", "Margem_EBITDA", "Margem_Liquida",
        # ENDIVIDAMENTO
        "Divida_PL", "Divida_Liquida", "DL_EBITDA", "DL_EBIT", "Liquidez_Corrente",
        # EFICIÊNCIA
        "Giro_Ativos", "Receita_CAGR", "Lucro_CAGR",
        # FINANCEIROS
        "Market_Cap", "Receita_TTM", "Lucro_Liquido", "Patrimonio",
        "EBITDA", "EBIT", "FCO", "FCL", "Caixa",
        # TÉCNICO
        "Maxima_52s", "Minima_52s", "Media_50d", "Media_200d", "Beta",
        # CLASSIFICAÇÃO
        "Setor", "SubSetor", "Segmento", "Descricao",
        # VALUATION CS
        "Graham", "Graham_BR", "Bazin", "Lynch", "AGF_Medio", "AGF_Projetivo",
        # SCORE
        "Score_CS",
        # ANALYSTS
        "Recomendacao_Analysts", "Qtd_Analysts", "Preco_Alvo_Medio",
    ]

    # Garantir que todas as colunas existam
    for col in colunas_ordem:
        if col not in df.columns:
            df[col] = 0 if col not in ["Nome_Empresa", "Nome_Curto", "CNPJ", 
                                         "Segmento_Listagem", "Setor", "SubSetor", 
                                         "Segmento", "Descricao", "Recomendacao_Analysts"] else ""

    df = df[colunas_ordem]

    # 7. Salvar Excel (1 aba apenas)
    print("\nSalvando ativos.xlsx...")
    with pd.ExcelWriter("ativos.xlsx", engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Dados", index=False)

    # 8. Salvar CSV backup
    df.to_csv("ativos.csv", index=False, encoding="utf-8-sig")

    # 9. Estatísticas
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"Total de ativos: {len(df)}")
    print(f"Colunas: {len(df.columns)}")
    print(f"Score CS médio: {df['Score_CS'].mean():.2f}")
    print(f"Score CS max: {df['Score_CS'].max()}")
    print(f"Score CS min: {df['Score_CS'].min()}")
    print(f"Arquivos gerados: ativos.xlsx, ativos.csv")
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
