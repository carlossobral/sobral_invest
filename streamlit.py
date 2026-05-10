import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

from usebolsai_client import buscar_acoes_usebolsai
from indicadores import calcular_indicadores
from checklist import checklist_buy_hold
from valuation import calcular_graham, calcular_graham_br, calcular_bazin, calcular_lynch, calcular_agf

# ─── Configuração ────────────────────────────────
st.set_page_config(
    page_title="Sobral Invest",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar para escolher tema
tema = st.sidebar.radio("Escolha o tema:", ["Claro", "Escuro"])

# CSS para temas
tema_claro = """
    <style>
        .main { background-color: #f9f9f9; }
        h1, h2, h3 { color: #003366; }
        .stDataFrame { background-color: #ffffff; }
    </style>
"""

tema_escuro = """
    <style>
        .main { background-color: #1e1e1e; }
        h1, h2, h3 { color: #66ccff; }
        .stDataFrame { background-color: #2b2b2b; color: #ffffff; }
    </style>
"""

# Aplica o tema escolhido
if tema == "Claro":
    st.markdown(tema_claro, unsafe_allow_html=True)
else:
    st.markdown(tema_escuro, unsafe_allow_html=True)

# Logo e título
st.image("https://sobralinvest.streamlit.app/logo.png", width=120)  # substitua pelo link real do seu logo
st.title("📊 Sobral Invest - Plataforma de Análise Fundamentalista")

# ─── Dashboard Inicial ────────────────────────────────
st.header("📌 Dashboard Inicial")

# Bloco 1: Indicadores macro (cards simulados)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Ibovespa", "118.500", "+0,85%")
with col2:
    st.metric("Dólar", "R$ 5,12", "-0,20%")
with col3:
    st.metric("Selic", "10,50%", "estável")
with col4:
    st.metric("IPCA (12m)", "4,2%", "-0,1pp")

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

    # Bloco 2: Altas e baixas do dia
    st.subheader("📈 Maiores Altas e Baixas")
    colA, colB = st.columns(2)
    with colA:
        st.dataframe(df.sort_values("DY", ascending=False).head(5)[["Ticker","DY","ROE"]])
    with colB:
        st.dataframe(df.sort_values("DY", ascending=True).head(5)[["Ticker","DY","ROE"]])

    # Bloco 3: Ranking dinâmico
    st.subheader("🏆 Ranking Dividend Yield")
    ranking_dy = df.sort_values("DY", ascending=False).head(10)
    st.bar_chart(ranking_dy.set_index("Ticker")["DY"])

    # Bloco 4: Agenda de dividendos (mock)
    st.subheader("📅 Agenda de Dividendos")
    agenda = pd.DataFrame({
        "Ticker": ["ITSA4","VALE3","PETR4"],
        "Data Ex": ["2026-05-15","2026-05-20","2026-05-25"],
        "Pagamento": ["2026-06-01","2026-06-05","2026-06-10"],
        "Valor por ação": ["R$ 0,35","R$ 2,10","R$ 1,25"]
    })
    st.dataframe(agenda)

    # Bloco 5: Radar de oportunidades
    st.subheader("🎯 Radar de Oportunidades")
    radar = px.line_polar(df.head(10), r="Score_BH", theta="Ticker", line_close=True)
    st.plotly_chart(radar, use_container_width=True)

    # ─── Abas ────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Indicadores", 
        "🏆 Ranking", 
        "📈 Radar", 
        "💰 Valuation", 
        "🏢 Empresas"
    ])

    with tab1:
        st.subheader("Indicadores Fundamentais")
        st.dataframe(df[["Ticker","PL","PVP","ROE","DY","Margem_Liquida","Divida_PL"]], use_container_width=True)

    with tab2:
        st.subheader("Ranking Buy & Hold")
        st.dataframe(df.sort_values("Score_BH", ascending=False).head(20), use_container_width=True)
        st.bar_chart(df.sort_values("Score_BH", ascending=False).head(20).set_index("Ticker")["Score_BH"])

    with tab3:
        st.subheader("Radar de Indicadores")
        radar_ind = px.line_polar(df.head(10), r="ROE", theta="Ticker", line_close=True)
        st.plotly_chart(radar_ind, use_container_width=True)

    with tab4:
        st.subheader("Modelos de Valuation")
        st.dataframe(df[["Ticker","Graham","Graham_BR","Bazin","Lynch_PEG","AGF"]], use_container_width=True)

    with tab5:
        st.subheader("Logos das Empresas")
        for ticker in df["Ticker"].head(10):
            st.image(f"https://logo.clearbit.com/{ticker.lower()}.com", width=100, caption=ticker)
