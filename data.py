import pandas as pd
import streamlit as st

def load_data():
    """Carrega dados do data/ativos.xlsx com conversao correta."""
    try:
        df = pd.read_excel("data/ativos.xlsx", sheet_name="Dados")
    except:
        try:
            df = pd.read_csv("data/ativos.csv", encoding="utf-8-sig")
        except:
            st.error("Erro ao carregar dados. Verifique se data/ativos.xlsx ou data/ativos.csv existem.")
            return pd.DataFrame()

    # Converter colunas numericas
    numeric_cols = [
        "Cotacao", "Variacao", "Volume", "Volume_Medio", "Market_Cap",
        "PE", "EPS", "DY", "DY_12m",
        "PL", "PVP", "PSR", "PAtivo", "PCapGiro", "PAtivoCircLiq",
        "PEBIT", "PEBITDA", "EV_EBIT", "EV_EBITDA",
        "LPA", "VPA", "Patrimonio", "Lucro_Liquido", "EBIT", "Receita_Liquida",
        "ROE", "ROA", "ROIC", "GiroAtivos",
        "MargemBruta", "MargemEBITDA", "MargemEBIT", "MargemLiquida",
        "DivLiquida_Ativos", "DivLiquida_PL", "DivLiquida_EBIT", "DivLiquida_EBITDA",
        "LiquidezCorrente", "Passivos_Ativos", "PL_Ativos",
        "CAGR_Receitas_5a", "CAGR_Lucros_5a",
        "Dividendo_Medio_12m", "Dividendo_Total_12m", "Dividendo_Ultimo",
        "Dividendo_Medio_6a",
        "Graham", "Graham_BR", "Bazin", "Lynch", "AGF_Medio",
        "Upside_Graham", "Upside_Graham_BR", "Upside_Bazin", "Upside_Lynch", "Upside_AGF_Medio",
        "Score_CS",
        "Beta", "Media_50d", "Media_200d", "FCO", "FCL"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Garantir que Ticker seja string
    if "Ticker" in df.columns:
        df["Ticker"] = df["Ticker"].astype(str)

    return df
