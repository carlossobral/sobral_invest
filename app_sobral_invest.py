"""
app_sobral_invest.py - Dashboard SOBRAL Invest v3.0
Lê ativos.xlsx como fonte principal de dados.
MFinance/BRAPI/UseBolsai apenas para complementos em tempo real.
"""

import os
import json
from datetime import date, datetime
from typing import Dict, List, Any, Optional

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração da página
st.set_page_config(
    page_title="SOBRAL Invest",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .score-excelente { color: #00cc00; font-weight: bold; }
    .score-bom { color: #66cc00; font-weight: bold; }
    .score-regular { color: #ffcc00; font-weight: bold; }
    .score-fraco { color: #ff6600; font-weight: bold; }
    .score-pessimo { color: #ff0000; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


def load_data() -> pd.DataFrame:
    """Carrega ativos.xlsx da raiz do projeto."""
    try:
        df = pd.read_excel("ativos.xlsx", sheet_name="Dados")
        df["Cotacao"] = pd.to_numeric(df["Cotacao"], errors="coerce").fillna(0)
        df["Score_CS"] = pd.to_numeric(df["Score_CS"], errors="coerce").fillna(0)
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar ativos.xlsx: {e}")
        return pd.DataFrame()


def get_selic() -> float:
    """Lê SELIC do selic.json."""
    try:
        with open("selic.json", "r") as f:
            return json.load(f).get("selic", 10.75)
    except:
        return 10.75


def score_class_css(classificacao: str) -> str:
    """Retorna classe CSS para a classificação do Score CS."""
    mapping = {
        "Excelente": "score-excelente",
        "Bom": "score-bom",
        "Regular": "score-regular",
        "Fraco": "score-fraco",
        "Péssimo": "score-pessimo",
    }
    return mapping.get(classificacao, "")


# ==================== SIDEBAR ====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/stocks.png", width=60)
    st.title("SOBRAL Invest")
    st.markdown("---")

    menu = st.radio(
        "Navegação",
        ["🏠 Dashboard", "🔍 Análise de Ativo", "📊 Rankings", "📈 Comparativo", "⚙️ Configurações"]
    )

    st.markdown("---")
    st.markdown("**Dados:** `ativos.xlsx`")
    st.markdown("**Fonte:** MFinance + BRAPI")

    selic = get_selic()
    st.markdown(f"**SELIC:** {selic}% a.a.")


# ==================== DASHBOARD ====================
if menu == "🏠 Dashboard":
    st.markdown('<div class="main-header">📈 SOBRAL Invest</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Plataforma de Análise Fundamentalista</div>', unsafe_allow_html=True)

    df = load_data()

    if df.empty:
        st.warning("⚠️ Nenhum dado disponível. Execute `app.py` localmente para gerar `ativos.xlsx`.")
        st.stop()

    # KPIs
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Ativos", len(df))
    with col2:
        st.metric("Score CS Médio", f"{df['Score_CS'].mean():.1f}/9")
    with col3:
        st.metric("Score CS Max", int(df['Score_CS'].max()))
    with col4:
        excelentes = len(df[df["Score_CS_Classificacao"] == "Excelente"])
        st.metric("Excelentes", excelentes)
    with col5:
        st.metric("SELIC", f"{selic}%")

    st.markdown("---")

    # Gráficos
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 Distribuição Score CS")
        score_counts = df["Score_CS_Classificacao"].value_counts()
        fig = px.pie(
            values=score_counts.values,
            names=score_counts.index,
            color=score_counts.index,
            color_discrete_map={
                "Excelente": "#00cc00",
                "Bom": "#66cc00",
                "Regular": "#ffcc00",
                "Fraco": "#ff6600",
                "Péssimo": "#ff0000",
            }
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("🏆 Top 10 Score CS")
        top10 = df.nlargest(10, "Score_CS")[["Ticker", "Nome", "Score_CS", "Score_CS_Classificacao", "Cotacao", "DY"]]
        st.dataframe(top10, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Tabela completa com filtros
    st.subheader("📋 Todos os Ativos")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        setores = ["Todos"] + sorted(df["Setor"].dropna().unique().tolist())
        filtro_setor = st.selectbox("Setor", setores)
    with col_f2:
        scores = ["Todos"] + ["Excelente", "Bom", "Regular", "Fraco", "Péssimo"]
        filtro_score = st.selectbox("Score CS", scores)
    with col_f3:
        min_dy = st.slider("DY Mínimo (%)", 0.0, 20.0, 0.0, 0.5)
    with col_f4:
        max_pl = st.slider("P/L Máximo", 0.0, 50.0, 50.0, 1.0)

    df_filt = df.copy()
    if filtro_setor != "Todos":
        df_filt = df_filt[df_filt["Setor"] == filtro_setor]
    if filtro_score != "Todos":
        df_filt = df_filt[df_filt["Score_CS_Classificacao"] == filtro_score]
    df_filt = df_filt[(df_filt["DY"] >= min_dy) & (df_filt["PL"] <= max_pl)]

    # Colunas visíveis
    cols_vis = [
        "Ticker", "Nome", "Setor", "Cotacao", "Variacao",
        "PL", "PVP", "DY", "ROE", "ROIC", "MargemLiquida",
        "Score_CS", "Score_CS_Classificacao",
        "Graham", "Bazin", "Upside_Graham", "Upside_Bazin"
    ]
    cols_vis = [c for c in cols_vis if c in df_filt.columns]

    st.dataframe(
        df_filt[cols_vis].sort_values("Score_CS", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Cotacao": st.column_config.NumberColumn(format="R$ %.2f"),
            "Variacao": st.column_config.NumberColumn(format="%.2f%%"),
            "PL": st.column_config.NumberColumn(format="%.2f"),
            "PVP": st.column_config.NumberColumn(format="%.2f"),
            "DY": st.column_config.NumberColumn(format="%.2f%%"),
            "ROE": st.column_config.NumberColumn(format="%.2f%%"),
            "ROIC": st.column_config.NumberColumn(format="%.2f%%"),
            "MargemLiquida": st.column_config.NumberColumn(format="%.2f%%"),
            "Score_CS": st.column_config.NumberColumn(format="%d/9"),
            "Upside_Graham": st.column_config.NumberColumn(format="%.1f%%"),
            "Upside_Bazin": st.column_config.NumberColumn(format="%.1f%%"),
        }
    )


# ==================== ANÁLISE DE ATIVO ====================
elif menu == "🔍 Análise de Ativo":
    st.markdown('<div class="main-header">🔍 Análise Fundamentalista</div>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("⚠️ Nenhum dado disponível.")
        st.stop()

    ticker = st.selectbox("Selecione o ativo", sorted(df["Ticker"].tolist()))

    if not ticker:
        st.stop()

    ativo = df[df["Ticker"] == ticker].iloc[0]

    # Header do ativo
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.header(f"{ticker} - {ativo.get('Nome', '')}")
        st.caption(f"{ativo.get('Setor', '')} > {ativo.get('SubSetor', '')} > {ativo.get('Segmento', '')}")
    with col2:
        score = int(ativo.get("Score_CS", 0))
        classif = ativo.get("Score_CS_Classificacao", "")
        st.metric("Score CS", f"{score}/9", classif)
    with col3:
        st.metric("Cotação", f"R$ {ativo.get('Cotacao', 0):.2f}")

    st.markdown("---")

    # Indicadores principais
    st.subheader("📊 Indicadores Principais")

    cols = st.columns(4)
    metrics = [
        ("P/L", ativo.get("PL", 0), "x"),
        ("P/VP", ativo.get("PVP", 0), "x"),
        ("DY", ativo.get("DY", 0), "%"),
        ("ROE", ativo.get("ROE", 0), "%"),
        ("ROIC", ativo.get("ROIC", 0), "%"),
        ("Margem Líquida", ativo.get("MargemLiquida", 0), "%"),
        ("EV/EBIT", ativo.get("EV_EBIT", 0), "x"),
        ("EV/EBITDA", ativo.get("EV_EBITDA", 0), "x"),
    ]

    for i, (nome, valor, unidade) in enumerate(metrics):
        with cols[i % 4]:
            if unidade == "%":
                st.metric(nome, f"{valor:.2f}%")
            else:
                st.metric(nome, f"{valor:.2f}{unidade}")

    st.markdown("---")

    # Valuation
    st.subheader("💰 Valuation")

    col_v1, col_v2 = st.columns(2)

    with col_v1:
        st.markdown("**Preços Alvo**")
        valuation_data = {
            "Método": ["Graham", "Graham BR", "Bazin", "Lynch", "AGF"],
            "Preço Alvo": [
                ativo.get("Graham", 0),
                ativo.get("Graham_BR", 0),
                ativo.get("Bazin", 0),
                ativo.get("Lynch_Preco_Teto", 0),
                ativo.get("AGF", 0),
            ],
            "Upside": [
                ativo.get("Upside_Graham", 0),
                ativo.get("Upside_Graham_BR", 0),
                ativo.get("Upside_Bazin", 0),
                ativo.get("Upside_Lynch_Preco_Teto", 0),
                ativo.get("Upside_AGF", 0),
            ]
        }
        df_val = pd.DataFrame(valuation_data)
        df_val["Preço Alvo"] = df_val["Preço Alvo"].apply(lambda x: f"R$ {x:.2f}" if x > 0 else "N/A")
        df_val["Upside"] = df_val["Upside"].apply(lambda x: f"{x:.1f}%" if x != 0 else "N/A")
        st.dataframe(df_val, use_container_width=True, hide_index=True)

    with col_v2:
        st.markdown("**Composição Score CS**")
        score_details = {
            "Critério": [
                "ROE > 15%", "DY > 3%", "Dív/PL < 0.5", "P/L < 15",
                "P/VP < 2", "Margem > 10%", "Liq. Corr. > 1", "CAGR > 5%", "ROIC > 10%"
            ],
            "Status": [
                "✅" if ativo.get("ROE_15pct", 0) == 1 else "❌",
                "✅" if ativo.get("DY_3pct", 0) == 1 else "❌",
                "✅" if ativo.get("DivPL_0_5", 0) == 1 else "❌",
                "✅" if ativo.get("PL_15", 0) == 1 else "❌",
                "✅" if ativo.get("PVP_2", 0) == 1 else "❌",
                "✅" if ativo.get("Margem_10pct", 0) == 1 else "❌",
                "✅" if ativo.get("LiqCorrente_1", 0) == 1 else "❌",
                "✅" if ativo.get("CAGR_5pct", 0) == 1 else "❌",
                "✅" if ativo.get("ROIC_10pct", 0) == 1 else "❌",
            ],
            "Valor": [
                f"{ativo.get('ROE', 0):.2f}%",
                f"{ativo.get('DY', 0):.2f}%",
                f"{ativo.get('DivLiquida_PL', 0):.2f}",
                f"{ativo.get('PL', 0):.2f}",
                f"{ativo.get('PVP', 0):.2f}",
                f"{ativo.get('MargemLiquida', 0):.2f}%",
                f"{ativo.get('LiquidezCorrente', 0):.2f}",
                f"{ativo.get('CAGR_Lucros_5a', 0):.2f}%",
                f"{ativo.get('ROIC', 0):.2f}%",
            ]
        }
        df_score = pd.DataFrame(score_details)
        st.dataframe(df_score, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Radar de indicadores
    st.subheader("🎯 Radar de Indicadores")

    radar_metrics = {
        "ROE": min(ativo.get("ROE", 0) / 30 * 100, 100),
        "DY": min(ativo.get("DY", 0) / 10 * 100, 100),
        "Margem Líq.": min(ativo.get("MargemLiquida", 0) / 20 * 100, 100),
        "ROIC": min(ativo.get("ROIC", 0) / 20 * 100, 100),
        "Liquidez": min(ativo.get("LiquidezCorrente", 0) / 2 * 100, 100),
    }

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=list(radar_metrics.values()) + [list(radar_metrics.values())[0]],
        theta=list(radar_metrics.keys()) + [list(radar_metrics.keys())[0]],
        fill='toself',
        name=ticker
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        height=400
    )
    st.plotly_chart(fig_radar, use_container_width=True)


# ==================== RANKINGS ====================
elif menu == "📊 Rankings":
    st.markdown('<div class="main-header">📊 Rankings</div>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("⚠️ Nenhum dado disponível.")
        st.stop()

    ranking_tipo = st.selectbox(
        "Tipo de Ranking",
        ["🏆 Score CS", "💰 Maior DY", "📉 Menor P/L", "📈 Maior ROE", "🚀 Maior Upside (Graham)",
         "💵 Maior Upside (Bazin)", "📊 Maior Margem Líquida", "🔥 Maior ROIC"]
    )

    n = st.slider("Quantidade", 5, 50, 20)

    mapping = {
        "🏆 Score CS": ("Score_CS", False),
        "💰 Maior DY": ("DY", False),
        "📉 Menor P/L": ("PL", True),
        "📈 Maior ROE": ("ROE", False),
        "🚀 Maior Upside (Graham)": ("Upside_Graham", False),
        "💵 Maior Upside (Bazin)": ("Upside_Bazin", False),
        "📊 Maior Margem Líquida": ("MargemLiquida", False),
        "🔥 Maior ROIC": ("ROIC", False),
    }

    col, asc = mapping.get(ranking_tipo, ("Score_CS", False))

    # Filtrar valores válidos
    df_rank = df[df[col] > 0].copy() if col not in ["PL", "PVP"] else df[df[col] > 0].copy()

    top = df_rank.nsmallest(n, col) if asc else df_rank.nlargest(n, col)

    cols_display = ["Ticker", "Nome", "Setor", col, "Cotacao", "Score_CS", "Score_CS_Classificacao"]
    cols_display = [c for c in cols_display if c in top.columns]

    st.dataframe(
        top[cols_display],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Cotacao": st.column_config.NumberColumn(format="R$ %.2f"),
            col: st.column_config.NumberColumn(format="%.2f"),
            "Score_CS": st.column_config.NumberColumn(format="%d/9"),
        }
    )

    # Gráfico de barras
    fig = px.bar(
        top,
        x="Ticker",
        y=col,
        color="Score_CS_Classificacao",
        color_discrete_map={
            "Excelente": "#00cc00",
            "Bom": "#66cc00",
            "Regular": "#ffcc00",
            "Fraco": "#ff6600",
            "Péssimo": "#ff0000",
        },
        title=f"Top {n} - {ranking_tipo}"
    )
    st.plotly_chart(fig, use_container_width=True)


# ==================== COMPARATIVO ====================
elif menu == "📈 Comparativo":
    st.markdown('<div class="main-header">📈 Comparativo de Ativos</div>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("⚠️ Nenhum dado disponível.")
        st.stop()

    tickers = st.multiselect(
        "Selecione até 5 ativos",
        sorted(df["Ticker"].tolist()),
        max_selections=5,
        default=sorted(df["Ticker"].tolist())[:3] if len(df) >= 3 else []
    )

    if not tickers:
        st.info("Selecione ativos para comparar.")
        st.stop()

    df_comp = df[df["Ticker"].isin(tickers)].copy()

    # Tabela comparativa
    metrics = ["Cotacao", "PL", "PVP", "DY", "ROE", "ROIC", "MargemLiquida",
               "EV_EBIT", "EV_EBITDA", "Score_CS"]
    metrics = [m for m in metrics if m in df_comp.columns]

    comp_table = df_comp.set_index("Ticker")[metrics].T
    st.dataframe(comp_table, use_container_width=True)

    # Gráfico comparativo
    metric_comp = st.selectbox("Métrica para comparar", metrics)

    fig = px.bar(
        df_comp,
        x="Ticker",
        y=metric_comp,
        color="Score_CS_Classificacao",
        color_discrete_map={
            "Excelente": "#00cc00",
            "Bom": "#66cc00",
            "Regular": "#ffcc00",
            "Fraco": "#ff6600",
            "Péssimo": "#ff0000",
        }
    )
    st.plotly_chart(fig, use_container_width=True)

    # Radar comparativo
    st.subheader("🎯 Radar Comparativo")

    radar_cols = ["ROE", "DY", "MargemLiquida", "ROIC", "LiquidezCorrente"]
    radar_cols = [c for c in radar_cols if c in df_comp.columns]

    fig_radar = go.Figure()
    for _, row in df_comp.iterrows():
        values = [min(row.get(c, 0) / 30 * 100, 100) for c in radar_cols]
        values += [values[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=values,
            theta=radar_cols + [radar_cols[0]],
            fill='toself',
            name=row["Ticker"]
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=500
    )
    st.plotly_chart(fig_radar, use_container_width=True)


# ==================== CONFIGURAÇÕES ====================
elif menu == "⚙️ Configurações":
    st.markdown('<div class="main-header">⚙️ Configurações</div>', unsafe_allow_html=True)

    st.subheader("📁 Dados")

    if os.path.exists("ativos.xlsx"):
        import os as os_mod
        size = os_mod.path.getsize("ativos.xlsx")
        st.write(f"**ativos.xlsx:** {size/1024:.1f} KB")

        df = load_data()
        if not df.empty:
            st.write(f"**Ativos:** {len(df)}")
            st.write(f"**Colunas:** {len(df.columns)}")
            st.write(f"**Última atualização:** {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")
    else:
        st.warning("❌ ativos.xlsx não encontrado.")

    st.markdown("---")

    st.subheader("📊 Estatísticas")
    df = load_data()
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Setores:**")
            st.write(df["Setor"].value_counts().head(10))
        with col2:
            st.write("**Score CS Distribuição:**")
            st.write(df["Score_CS"].value_counts().sort_index())

    st.markdown("---")

    st.subheader("🔧 Parâmetros de Valuation")
    st.write(f"**SELIC atual:** {selic}%")
    st.write("**Mínimo DY Bazin:** 6%")
    st.write("**Multiplicador Graham BR:** 1/SELIC")
    st.write("**Threshold Score CS:** 8=Excelente, 6=Bom, 4=Regular, 2=Fraco, 0=Péssimo")
