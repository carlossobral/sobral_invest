import pandas as pd
import streamlit as st

def load_data():
    """Carrega dados do data/ativos.xlsx com conversão correta."""
    try:
        # Ajustado para ler a aba DADOS! criada pelo novo app.py
        df = pd.read_excel("data/ativos.xlsx", sheet_name="DADOS!")
    except:
        try:
            df = pd.read_csv("data/ativos.csv", encoding="utf-8-sig")
        except:
            st.error("Erro ao carregar dados. Verifique se data/ativos.xlsx ou data/ativos.csv existem.")
            return pd.DataFrame()

    # Lista atualizada com os NOVOS nomes de colunas definidos no app.py
    numeric_cols = [
        "Preco_Atual", "Volume", "Valor_Mercado", "Qtd_Acoes", "DY_Atual",
        "P_L", "P_VP", "P_Receita", "P_Ativo", "P_Cap_Giro", "P_Ativo_Circ_Liq",
        "P_EBIT", "P_EBITDA", "EV_EBIT", "EV_EBITDA",
        "ROE", "ROA", "ROIC", "Giro_Ativos",
        "Margem_Bruta", "Margem_EBITDA", "Margem_EBIT", "Margem_Liquida",
        "Div_Liq_Ativos", "Div_Liq_PL", "Div_Liq_EBIT", "Div_Liq_EBITDA",
        "Liquidez_Corrente", "Passivos_Ativos", "PL_Ativos",
        "CAGR_Receitas_5a", "CAGR_Lucros_5a", "Receita_Liquida", "Lucro_Liquido", "EBIT",
        "Div_1A", "Div_2A", "Div_3A", "Div_4A", "Div_5A", "Consistencia_5A",
        "Anos_Listagem", "Score_CS"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Garantir que Ticker seja string
    if "Ticker" in df.columns:
        df["Ticker"] = df["Ticker"].astype(str)

    return df
