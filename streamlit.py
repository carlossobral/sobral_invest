import streamlit as st
import pandas as pd

from usebolsai_client import buscar_acoes_usebolsai
from indicadores import calcular_indicadores
from checklist import checklist_buy_hold
from valuation import calcular_graham, calcular_graham_br, calcular_bazin, calcular_lynch, calcular_agf

# ─── Configuração ────────────────────────────────
st.set_page_config(page_title="Plataforma de Análise", layout="wide")

st.title("📊 Plataforma de Análise Fundamentalista")

# Entrada de tickers
tickers_input = st.text_area("Digite os tickers separados por vírgula:", "PETR4,VALE3,ITSA4")
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if st.button("Buscar dados"):
    resultados, _ = buscar_acoes_usebolsai(tickers)

    dados = []
    for r in resultados:
        ind = calcular_indicadores(r)
        chk, score = checklist_buy_hold(ind)
        graham = calcular_graham(ind["LPA"], ind["VPA"])
        graham_br = calcular_graham_br(graham, ind["ROE"], ind["Divida_PL"], ind["Margem_Liquida"], ind["Receita_CAGR"])
        bazin = calcular_bazin(ind["DY"])
        lynch = calcular_lynch(ind["PL"], ind["Lucro_CAGR"])
        agf = calcular_agf(ind["DY"], ind["Lucro_CAGR"])

        dados.append({
            "Ticker": r["Ticker"],
            **ind,
            "Score_BH": score,
            "Graham": graham,
            "Graham_BR": graham_br,
            "Bazin": bazin,
            "Lynch_PEG": lynch,
            "AGF": agf
        })

    df = pd.DataFrame(dados)

    # ─── Abas ────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Ativos", "Checklist", "Valuation", "Rankings", "Radar"])

    with tab1:
        st.subheader("📑 Dados Consolidados")
        st.dataframe(df, use_container_width=True)

    with tab2:
        st.subheader("✅ Checklist Buy & Hold")
        st.dataframe(df[["Ticker","ROE","DY","Divida_PL","Liquidez_Corrente","Score_BH"]], use_container_width=True)

    with tab3:
        st.subheader("💰 Valuation")
        st.dataframe(df[["Ticker","Graham","Graham_BR","Bazin","Lynch_PEG","AGF","Score_BH"]], use_container_width=True)

    with tab4:
        st.subheader("🏆 Ranking Top 20")
        st.dataframe(df.sort_values("Score_BH", ascending=False).head(20), use_container_width=True)
        st.bar_chart(df.sort_values("Score_BH", ascending=False).head(20).set_index("Ticker")["Score_BH"])

    with tab5:
        st.subheader("📈 Radar de Indicadores")
        st.bar_chart(df.set_index("Ticker")[["ROE","DY","Margem_Liquida","ROIC","Liquidez_Corrente"]])
