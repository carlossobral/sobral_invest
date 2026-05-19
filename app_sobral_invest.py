"""
Sobral Invest v3.0 - Plataforma Profissional de Análise de Ativos
Lê dados do ativos.xlsx (cache local) + BRAPI/UseBolsai para tempo real
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mfinance_client import MFinanceClient
from brapi_client import obter_dados_brapi
from usebolsai_client import buscar_acoes_usebolsai

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Sobral Invest v3.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS CUSTOMIZADO - TERMINAL ESCURO
# ============================================================
st.markdown("""
<style>
    .main { background-color: #0a0a0a; color: #e0e0e0; }
    .stApp { background-color: #0a0a0a; }
    h1, h2, h3 { color: #00ff88 !important; font-family: 'Courier New', monospace; }
    .stMetric { background-color: #1a1a1a; border-radius: 8px; padding: 10px; }
    .stDataFrame { background-color: #1a1a1a; }
    .css-1d391kg { background-color: #0f0f0f; }
    div[data-testid="stSidebar"] { background-color: #0f0f0f; }
    .stButton>button { background-color: #00ff88; color: #000; font-weight: bold; }
    .stButton>button:hover { background-color: #00cc6a; }
    .highlight-green { color: #00ff88; font-weight: bold; }
    .highlight-red { color: #ff4444; font-weight: bold; }
    .highlight-yellow { color: #ffaa00; font-weight: bold; }
    .card { background-color: #1a1a1a; border-radius: 10px; padding: 15px; margin: 10px 0; border-left: 3px solid #00ff88; }
    .card-red { border-left-color: #ff4444; }
    .card-yellow { border-left-color: #ffaa00; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
@st.cache_data(ttl=3600)
def carregar_dados() -> pd.DataFrame:
    """Carrega ativos.xlsx do cache local"""
    try:
        df = pd.read_excel("ativos.xlsx", sheet_name="Dados")
        return df
    except Exception as e:
        st.error(f"Erro ao carregar ativos.xlsx: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def buscar_cotacao_tempo_real(ticker: str) -> dict:
    """Busca cotação em tempo real via BRAPI"""
    try:
        token = os.getenv("BRAPI_TOKEN", "")
        data = obter_dados_brapi(ticker, token=token)
        if data and "results" in data:
            return data["results"][0]
    except Exception:
        pass
    return {}

def formatar_moeda(valor: float) -> str:
    if pd.isna(valor) or valor == 0:
        return "—"
    if abs(valor) >= 1e9:
        return f"R$ {valor/1e9:.2f}B"
    elif abs(valor) >= 1e6:
        return f"R$ {valor/1e6:.2f}M"
    elif abs(valor) >= 1e3:
        return f"R$ {valor/1e3:.2f}K"
    return f"R$ {valor:.2f}"

def formatar_pct(valor: float) -> str:
    if pd.isna(valor):
        return "—"
    cor = "highlight-green" if valor > 0 else "highlight-red" if valor < 0 else ""
    return f'<span class="{cor}">{valor:.2f}%</span>'

def cor_score(score: float) -> str:
    if score >= 7: return "🟢"
    elif score >= 4: return "🟡"
    else: return "🔴"

# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div style="text-align: center; padding: 20px 0;">
    <h1 style="font-size: 3em; margin-bottom: 0;">📈 SOBRAL INVEST</h1>
    <p style="color: #888; font-size: 1.2em; margin-top: 5px;">Plataforma Profissional de Análise de Ativos</p>
    <p style="color: #00ff88; font-size: 0.9em;">v3.0 | Dados via MFinance + BRAPI + UseBolsai</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# CARREGAR DADOS
# ============================================================
df = carregar_dados()

if df.empty:
    st.error("""
    ❌ **ativos.xlsx não encontrado!**

    Execute o script `app.py` localmente para gerar o arquivo:
    ```bash
    python app.py
    ```

    Ou faça upload do arquivo na raiz do projeto.
    """)
    st.stop()

# Sidebar
st.sidebar.markdown("### 🎯 Menu")
aba = st.sidebar.radio("", [
    "🏠 Dashboard",
    "🔍 Análise de Ativo",
    "📊 Rankings",
    "💰 Carteira",
    "📥 Importar B3"
])

st.sidebar.markdown("---")
st.sidebar.markdown(f"**📁 Ativos carregados:** {len(df)}")
st.sidebar.markdown(f"**🕐 Atualizado:** {datetime.now().strftime('%d/%m/%Y')}")

# ============================================================
# ABA 1: DASHBOARD
# ============================================================
if aba == "🏠 Dashboard":
    st.markdown("## 🏠 Dashboard")

    # KPIs
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Ativos", len(df))
    with col2:
        dy_medio = df["DY"].replace(0, np.nan).mean()
        st.metric("DY Médio", f"{dy_medio:.2f}%")
    with col3:
        pl_medio = df["PL"].replace(0, np.nan).mean()
        st.metric("P/L Médio", f"{pl_medio:.2f}x")
    with col4:
        roe_medio = df["ROE"].replace(0, np.nan).mean()
        st.metric("ROE Médio", f"{roe_medio:.2f}%")
    with col5:
        score_medio = df["Score_CS"].mean()
        st.metric("Score CS Médio", f"{score_medio:.1f}/9")

    st.markdown("---")

    # Top 10 por Score CS
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏆 Top 10 - Score CS")
        top_score = df.nlargest(10, "Score_CS")[["Ticker", "Nome_Empresa", "Cotacao", "Score_CS", "DY", "PL"]]
        top_score["Score"] = top_score["Score_CS"].apply(lambda x: f"{cor_score(x)} {x:.1f}")
        st.dataframe(
            top_score[["Ticker", "Nome_Empresa", "Cotacao", "Score", "DY", "PL"]],
            use_container_width=True,
            hide_index=True
        )

    with col2:
        st.markdown("### 💎 Top 10 - Dividend Yield")
        top_dy = df.nlargest(10, "DY")[["Ticker", "Nome_Empresa", "Cotacao", "DY", "Score_CS", "Payout"]]
        st.dataframe(top_dy, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Distribuição por Setor
    st.markdown("### 🏭 Distribuição por Setor")
    setores = df[df["Setor"] != ""]["Setor"].value_counts().head(15)
    fig = px.bar(
        x=setores.index, y=setores.values,
        labels={"x": "Setor", "y": "Quantidade"},
        color=setores.values,
        color_continuous_scale="Greens"
    )
    fig.update_layout(
        plot_bgcolor="#1a1a1a", paper_bgcolor="#0a0a0a",
        font_color="#e0e0e0", xaxis_tickangle=-45
    )
    st.plotly_chart(fig, use_container_width=True)

    # Distribuição do Score CS
    st.markdown("### 📊 Distribuição do Score CS")
    fig2 = px.histogram(
        df, x="Score_CS", nbins=10,
        labels={"Score_CS": "Score CS", "count": "Quantidade"},
        color_discrete_sequence=["#00ff88"]
    )
    fig2.update_layout(
        plot_bgcolor="#1a1a1a", paper_bgcolor="#0a0a0a",
        font_color="#e0e0e0"
    )
    st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# ABA 2: ANÁLISE DE ATIVO
# ============================================================
elif aba == "🔍 Análise de Ativo":
    st.markdown("## 🔍 Análise de Ativo")

    # Busca de ativo
    ticker_input = st.selectbox(
        "Selecione o ativo:",
        options=[""] + sorted(df["Ticker"].tolist()),
        format_func=lambda x: f"{x} - {df[df['Ticker']==x]['Nome_Empresa'].values[0] if x and len(df[df['Ticker']==x]) > 0 else ''}" if x else "🔍 Digite ou selecione..."
    )

    if not ticker_input:
        st.info("👆 Selecione um ativo acima para análise detalhada.")
        st.stop()

    # Dados do ativo
    ativo = df[df["Ticker"] == ticker_input]
    if ativo.empty:
        st.error(f"Ativo {ticker_input} não encontrado no cache.")
        st.stop()

    ativo = ativo.iloc[0]

    # Buscar cotação em tempo real
    cotacao_real = buscar_cotacao_tempo_real(ticker_input)
    cotacao_atual = cotacao_real.get("regularMarketPrice", ativo["Cotacao"])
    variacao_atual = cotacao_real.get("regularMarketChangePercent", ativo["Variacao"])

    # Header do ativo
    st.markdown(f"""
    <div class="card">
        <h2>{ativo["Nome_Empresa"]} <span style="color:#888;">({ticker_input})</span></h2>
        <p>{ativo["Descricao"] or "Sem descrição disponível"}</p>
        <p>📍 {ativo["Setor"]} → {ativo["SubSetor"]} → {ativo["Segmento"]}</p>
    </div>
    """)

    # Cards principais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Cotação", f"R$ {cotacao_atual:.2f}", f"{variacao_atual:.2f}%")
    with col2:
        st.metric("P/L", f"{ativo['PL']:.2f}x")
    with col3:
        st.metric("DY", f"{ativo['DY']:.2f}%")
    with col4:
        st.metric("Score CS", f"{ativo['Score_CS']:.1f}/9")

    st.markdown("---")

    # Tabs de análise
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Indicadores", "💰 Valuation", "📈 Técnico", "🏛️ Setorial"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Rentabilidade")
            st.markdown(f"- **ROE:** {ativo['ROE']:.2f}%")
            st.markdown(f"- **ROA:** {ativo['ROA']:.2f}%")
            st.markdown(f"- **ROIC:** {ativo['ROIC']:.2f}%")
            st.markdown(f"- **Margem Bruta:** {ativo['Margem_Bruta']:.2f}%")
            st.markdown(f"- **Margem EBITDA:** {ativo['Margem_EBITDA']:.2f}%")
            st.markdown(f"- **Margem Líquida:** {ativo['Margem_Liquida']:.2f}%")
        with col2:
            st.markdown("### Endividamento & Eficiência")
            st.markdown(f"- **Dívida/PL:** {ativo['Divida_PL']:.2f}x")
            st.markdown(f"- **Dívida Líquida:** {formatar_moeda(ativo['Divida_Liquida'])}")
            st.markdown(f"- **DL/EBITDA:** {ativo['DL_EBITDA']:.2f}x")
            st.markdown(f"- **Liquidez Corrente:** {ativo['Liquidez_Corrente']:.2f}x")
            st.markdown(f"- **Giro Ativos:** {ativo['Giro_Ativos']:.2f}x")
            st.markdown(f"- **CAGR Receita (5a):** {ativo['Receita_CAGR']:.2f}%")
            st.markdown(f"- **CAGR Lucro (5a):** {ativo['Lucro_CAGR']:.2f}%")

    with tab2:
        st.markdown("### Preços Alvo")

        metodos = [
            ("Graham", ativo["Graham"]),
            ("Graham BR", ativo["Graham_BR"]),
            ("Bazin", ativo["Bazin"]),
            ("Lynch", ativo["Lynch"]),
            ("AGF Médio", ativo["AGF_Medio"]),
            ("AGF Projetivo", ativo["AGF_Projetivo"]),
        ]

        cols = st.columns(3)
        for i, (nome, preco) in enumerate(metodos):
            with cols[i % 3]:
                if preco > 0:
                    upside = ((preco - cotacao_atual) / cotacao_atual) * 100
                    cor = "highlight-green" if upside > 0 else "highlight-red"
                    st.markdown(f"""
                    <div class="card">
                        <h4>{nome}</h4>
                        <p style="font-size:1.5em;">R$ {preco:.2f}</p>
                        <p class="{cor}">{upside:+.1f}%</p>
                    </div>
                    """)
                else:
                    st.markdown(f"""
                    <div class="card card-red">
                        <h4>{nome}</h4>
                        <p>N/A</p>
                    </div>
                    """)

        # Preço alvo médio dos analysts
        if ativo["Preco_Alvo_Medio"] > 0:
            upside_analysts = ((ativo["Preco_Alvo_Medio"] - cotacao_atual) / cotacao_atual) * 100
            st.markdown(f"""
            <div class="card card-yellow">
                <h4>🎯 Preço Alvo Analysts ({ativo["Qtd_Analysts"]:.0f} analistas)</h4>
                <p style="font-size:1.5em;">R$ {ativo["Preco_Alvo_Medio"]:.2f}</p>
                <p>{upside_analysts:+.1f}% upside | Recomendação: {ativo["Recomendacao_Analysts"]}</p>
            </div>
            """)

    with tab3:
        st.markdown("### Análise Técnica")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"- **Máxima 52s:** R$ {ativo['Maxima_52s']:.2f}")
            st.markdown(f"- **Mínima 52s:** R$ {ativo['Minima_52s']:.2f}")
            st.markdown(f"- **Média 50d:** R$ {ativo['Media_50d']:.2f}")
            st.markdown(f"- **Média 200d:** R$ {ativo['Media_200d']:.2f}")
            st.markdown(f"- **Beta:** {ativo['Beta']:.2f}")
        with col2:
            # Distância das médias
            if ativo["Media_50d"] > 0:
                dist_50 = ((cotacao_atual - ativo["Media_50d"]) / ativo["Media_50d"]) * 100
                st.markdown(f"- **Dist. Média 50d:** {dist_50:+.1f}%")
            if ativo["Media_200d"] > 0:
                dist_200 = ((cotacao_atual - ativo["Media_200d"]) / ativo["Media_200d"]) * 100
                st.markdown(f"- **Dist. Média 200d:** {dist_200:+.1f}%")

            # Tendência
            if ativo["Media_50d"] > ativo["Media_200d"] > 0:
                st.markdown("- **Tendência:** 🟢 Alta (MM50 > MM200)")
            elif ativo["Media_50d"] < ativo["Media_200d"] > 0:
                st.markdown("- **Tendência:** 🔴 Baixa (MM50 < MM200)")
            else:
                st.markdown("- **Tendência:** ⚪ Indefinida")

    with tab4:
        st.markdown("### Benchmark Setorial")
        setor = ativo["Setor"]
        if setor:
            df_setor = df[df["Setor"] == setor]
            st.markdown(f"**Setor:** {setor} ({len(df_setor)} ativos)")

            medias = {
                "P/L": df_setor["PL"].replace(0, np.nan).mean(),
                "P/VP": df_setor["PVP"].replace(0, np.nan).mean(),
                "DY": df_setor["DY"].replace(0, np.nan).mean(),
                "ROE": df_setor["ROE"].replace(0, np.nan).mean(),
                "Margem Liq.": df_setor["Margem_Liquida"].replace(0, np.nan).mean(),
            }

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Médias do Setor")
                for k, v in medias.items():
                    st.markdown(f"- **{k}:** {v:.2f}")
            with col2:
                st.markdown("#### Ativo vs Setor")
                comparativos = [
                    ("P/L", ativo["PL"], medias["P/L"], "menor"),
                    ("P/VP", ativo["PVP"], medias["P/VP"], "menor"),
                    ("DY", ativo["DY"], medias["DY"], "maior"),
                    ("ROE", ativo["ROE"], medias["ROE"], "maior"),
                ]
                for nome, val_ativo, val_setor, melhor in comparativos:
                    if val_setor > 0:
                        diff = ((val_ativo - val_setor) / val_setor) * 100
                        cor = "highlight-green" if (melhor == "menor" and diff < 0) or (melhor == "maior" and diff > 0) else "highlight-red"
                        st.markdown(f"- **{nome}:** {diff:+.1f}% vs setor", unsafe_allow_html=True)
        else:
            st.info("Setor não classificado para este ativo.")

# ============================================================
# ABA 3: RANKINGS
# ============================================================
elif aba == "📊 Rankings":
    st.markdown("## 📊 Rankings")

    tipo_ranking = st.selectbox("Ordenar por:", [
        "Score CS (Maior)",
        "Dividend Yield (Maior)",
        "P/L (Menor)",
        "ROE (Maior)",
        "ROIC (Maior)",
        "Margem Líquida (Maior)",
        "Upside Graham (Maior)",
        "Upside Bazin (Maior)",
    ])

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        setor_filtro = st.multiselect("Setor:", options=["Todos"] + sorted(df["Setor"].unique().tolist()))
    with col2:
        min_score = st.slider("Score CS mínimo:", 0.0, 9.0, 0.0, 0.5)
    with col3:
        min_dy = st.slider("DY mínimo (%):", 0.0, 20.0, 0.0, 0.5)

    # Aplicar filtros
    df_rank = df.copy()
    if setor_filtro and "Todos" not in setor_filtro:
        df_rank = df_rank[df_rank["Setor"].isin(setor_filtro)]
    df_rank = df_rank[df_rank["Score_CS"] >= min_score]
    df_rank = df_rank[df_rank["DY"] >= min_dy]

    # Ordenar
    if "Score CS" in tipo_ranking:
        df_rank = df_rank.sort_values("Score_CS", ascending=False)
    elif "Dividend Yield" in tipo_ranking:
        df_rank = df_rank.sort_values("DY", ascending=False)
    elif "P/L" in tipo_ranking:
        df_rank = df_rank[df_rank["PL"] > 0].sort_values("PL", ascending=True)
    elif "ROE" in tipo_ranking:
        df_rank = df_rank.sort_values("ROE", ascending=False)
    elif "ROIC" in tipo_ranking:
        df_rank = df_rank.sort_values("ROIC", ascending=False)
    elif "Margem" in tipo_ranking:
        df_rank = df_rank.sort_values("Margem_Liquida", ascending=False)
    elif "Graham" in tipo_ranking:
        df_rank["Upside_Graham"] = ((df_rank["Graham"] - df_rank["Cotacao"]) / df_rank["Cotacao"]) * 100
        df_rank = df_rank[df_rank["Graham"] > 0].sort_values("Upside_Graham", ascending=False)
    elif "Bazin" in tipo_ranking:
        df_rank["Upside_Bazin"] = ((df_rank["Bazin"] - df_rank["Cotacao"]) / df_rank["Cotacao"]) * 100
        df_rank = df_rank[df_rank["Bazin"] > 0].sort_values("Upside_Bazin", ascending=False)

    # Mostrar
    colunas_display = ["Ticker", "Nome_Empresa", "Cotacao", "Score_CS", "DY", "PL", "ROE", "ROIC", "Setor"]
    st.dataframe(df_rank[colunas_display].head(50), use_container_width=True, hide_index=True)

    st.markdown(f"**Mostrando top 50 de {len(df_rank)} ativos filtrados**")

# ============================================================
# ABA 4: CARTEIRA
# ============================================================
elif aba == "💰 Carteira":
    st.markdown("## 💰 Carteira")
    st.info("🚧 Em desenvolvimento. Use a aba 'Importar B3' para carregar sua carteira.")

# ============================================================
# ABA 5: IMPORTAR B3
# ============================================================
elif aba == "📥 Importar B3":
    st.markdown("## 📥 Importar Nota de Negociação B3")
    st.info("🚧 Em desenvolvimento. Integração com parser_negociacao_b3.py em andamento.")
