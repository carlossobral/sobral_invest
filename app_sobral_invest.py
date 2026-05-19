"""
app_sobral_invest.py - SOBRAL Invest v4.0
Dashboard com yfinance para Ibovespa e Maiores Altas/Baixas
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

# Configuracao da pagina
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
    .ibov-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 15px;
        padding: 2rem;
        color: white;
        margin-bottom: 2rem;
    }
    .ibov-value {
        font-size: 3rem;
        font-weight: bold;
        color: #10b981;
    }
    .ibov-var {
        font-size: 1.2rem;
        margin-top: 0.5rem;
    }
    .ticker-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #ddd;
        transition: all 0.3s;
    }
    .ticker-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .ticker-card.alta { border-left-color: #10b981; }
    .ticker-card.baixa { border-left-color: #ef4444; }
</style>
""", unsafe_allow_html=True)


def load_data() -> pd.DataFrame:
    """Carrega ativos.xlsx da raiz do projeto."""
    try:
        df = pd.read_excel("ativos.xlsx", sheet_name="Dados")
        df["Cotacao"] = pd.to_numeric(df["Cotacao"], errors="coerce").fillna(0)
        df["Variacao"] = pd.to_numeric(df["Variacao"], errors="coerce").fillna(0)
        df["Score_CS"] = pd.to_numeric(df["Score_CS"], errors="coerce").fillna(0)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar ativos.xlsx: {e}")
        return pd.DataFrame()


def get_selic() -> float:
    """Le SELIC do selic.json."""
    try:
        with open("selic.json", "r") as f:
            return json.load(f).get("selic", 10.75)
    except:
        return 10.75


# ==================== YFINANCE - IBovespa e Altas/Baixas ====================
def get_ibov_hgbrasil() -> Dict[str, Any]:
    """Busca dados do Ibovespa via HG Brasil API (gratuita)."""
    try:
        import requests
        # HG Brasil API - endpoint finance (gratuito, sem key necessária para dados básicos)
        r = requests.get("https://api.hgbrasil.com/finance", timeout=15)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", {})
            stocks = results.get("stocks", {})

            if "IBOVESPA" in stocks:
                ibov = stocks["IBOVESPA"]
                return {
                    "valor": ibov.get("points", 176975.82),
                    "variacao": ibov.get("variation", -0.17),
                    "abertura": ibov.get("points", 176975.82) * (1 - ibov.get("variation", -0.17)/100),
                    "historico": None,  # HG não fornece histórico no plano free
                    "status": "aberto" if ibov.get("variation", 0) != 0 else "fechado"
                }
    except Exception as e:
        st.warning(f"HG Brasil indisponivel para IBOV: {e}")

    # Fallback: usar dados estáticos
    return {
        "valor": 176975.82,
        "variacao": -0.17,
        "abertura": 177283.83,
        "historico": None,
        "status": "fallback"
    }


def get_maiores_altas_baixas_hgbrasil() -> Dict[str, List[Dict]]:
    """Busca maiores altas e baixas do dia via HG Brasil API."""
    try:
        import requests
        import time

        # Lista de tickers prioritários (top 50 mais líquidos)
        tickers = [
            "PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3",
            "WEGE3", "BBAS3", "BPAC11", "ITSA4", "B3SA3",
            "RAIZ4", "PRIO3", "VBBR3", "EQTL3", "SUZB3",
            "RAIL3", "GGBR4", "CMIG4", "CPLE3", "CSNA3",
            "USIM5", "GOAU4", "JBSS3", "BRFS3", "MRFG3",
            "AZUL4", "GOLL4", "CVCB3", "MULT3", "CYRE3",
            "EZTC3", "JHSF3", "MRVE3", "TRIS3", "TEND3",
            "ALPA4", "AMAR3", "GUAR3", "LREN3", "MGLU3",
            "PETZ3", "ALSO3", "BRAP4", "CCRO3", "ECOR3",
            "EMBR3", "ENBR3", "ENEV3", "EGIE3", "TAEE11",
            "TRPL4", "SAPR11", "SBSP3", "CSMG3", "AESB3"
        ]

        altas = []
        baixas = []

        for ticker in tickers:
            try:
                # HG Brasil API - stock_price (gratuito, até 10 requests/dia sem key)
                r = requests.get(f"https://api.hgbrasil.com/finance/stock_price?key=free&symbol={ticker}", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    results = data.get("results", {})

                    if ticker in results:
                        stock = results[ticker]
                        change = stock.get("change_percent", 0)
                        price = stock.get("price", 0)
                        name = stock.get("name", ticker)

                        info = {
                            "ticker": ticker,
                            "nome": name,
                            "preco": price,
                            "variacao": change,
                            "volume": stock.get("volume", 0)
                        }

                        if change > 0:
                            altas.append(info)
                        elif change < 0:
                            baixas.append(info)

                time.sleep(0.2)  # Respeitar rate limit
            except:
                continue

        # Ordenar
        altas = sorted(altas, key=lambda x: x["variacao"], reverse=True)[:7]
        baixas = sorted(baixas, key=lambda x: x["variacao"])[:7]

        return {"altas": altas, "baixas": baixas}

    except Exception as e:
        st.warning(f"HG Brasil indisponivel para altas/baixas: {e}")

    # Fallback: usar dados do ativos.xlsx
    return {"altas": [], "baixas": []}


# ==================== PAGINA INICIAL - DASHBOARD ====================
def pagina_inicial():
    st.markdown('<div class="main-header">📈 SOBRAL Invest</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Acompanhe em tempo real o mercado da B3</div>', unsafe_allow_html=True)

    # IBOVESPA via yfinance
    st.markdown("---")
    ibov_data = get_ibov_hgbrasil()

    col_ibov, col_chart = st.columns([1, 1.5])

    with col_ibov:
        st.markdown(f"""
        <div class="ibov-card">
            <div style="font-size: 0.9rem; color: #888; margin-bottom: 0.5rem;">Ibovespa</div>
            <div class="ibov-value">{ibov_data["valor"]:,.2f}</div>
            <div style="font-size: 0.9rem; color: #888;">pts</div>
            <div class="ibov-var" style="color: {'#10b981' if ibov_data['variacao'] >= 0 else '#ef4444'};">
                {'+' if ibov_data['variacao'] >= 0 else ''}{ibov_data['variacao']:.2f}% ({ibov_data['variacao'] * ibov_data['valor'] / 100:,.0f} pts)
            </div>
            <div style="font-size: 0.8rem; color: #666; margin-top: 1rem;">
                {'Mercado aberto' if ibov_data['status'] == 'aberto' else 'Mercado fechado' if ibov_data['status'] == 'fechado' else 'Dados de fallback'}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        if ibov_data["historico"] is not None:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=ibov_data["historico"].index,
                y=ibov_data["historico"]["Close"],
                mode='lines',
                line=dict(color='#10b981', width=2),
                fill='tozeroy',
                fillcolor='rgba(16,185,129,0.1)'
            ))
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=False,
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, showticklabels=False),
                height=250
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Grafico do Ibovespa indisponivel (API indisponivel no momento)")

    st.markdown("---")

    # MAIORES ALTAS E BAIXAS via yfinance
    st.markdown("## 📊 Maiores Altas / Maiores Baixas")

    altas_baixas = get_maiores_altas_baixas_hgbrasil()

    col_altas, col_baixas = st.columns(2)

    with col_altas:
        st.markdown("<h3 style='color: #10b981;'>Maiores Altas</h3>", unsafe_allow_html=True)

        if altas_baixas["altas"]:
            for acao in altas_baixas["altas"]:
                st.markdown(f"""
                <div class="ticker-card alta">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="font-size: 1.1rem;">{acao['ticker']}</strong><br>
                            <span style="color: #666; font-size: 0.85rem;">{acao['nome'][:30]}</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #10b981; font-size: 1.2rem; font-weight: bold;">+{acao['variacao']:.1f}%</div>
                            <div style="color: #888; font-size: 0.85rem;">R$ {acao['preco']:.2f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Dados de altas indisponiveis (API indisponivel no momento)")

    with col_baixas:
        st.markdown("<h3 style='color: #ef4444;'>Maiores Baixas</h3>", unsafe_allow_html=True)

        if altas_baixas["baixas"]:
            for acao in altas_baixas["baixas"]:
                st.markdown(f"""
                <div class="ticker-card baixa">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="font-size: 1.1rem;">{acao['ticker']}</strong><br>
                            <span style="color: #666; font-size: 0.85rem;">{acao['nome'][:30]}</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #ef4444; font-size: 1.2rem; font-weight: bold;">{acao['variacao']:.1f}%</div>
                            <div style="color: #888; font-size: 0.85rem;">R$ {acao['preco']:.2f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Dados de baixas indisponiveis (API indisponivel no momento)")

    st.markdown("---")

    # RANKINGS RAPIDOS do ativos.xlsx
    st.markdown("## 🏆 Rankings Destaque")

    df = load_data()
    if not df.empty:
        tabs = st.tabs(["💰 Maior DY", "📉 Menor P/L", "📈 Maior ROE", "🚀 Score CS", "💎 Graham"])

        with tabs[0]:
            top_dy = df.nlargest(5, "DY")[["Ticker", "Nome", "DY", "Cotacao"]]
            st.dataframe(top_dy, use_container_width=True, hide_index=True,
                        column_config={"DY": st.column_config.NumberColumn(format="%.2f%%"),
                                      "Cotacao": st.column_config.NumberColumn(format="R$ %.2f")})

        with tabs[1]:
            top_pl = df[df["PL"] > 0].nsmallest(5, "PL")[["Ticker", "Nome", "PL", "Cotacao"]]
            st.dataframe(top_pl, use_container_width=True, hide_index=True,
                        column_config={"PL": st.column_config.NumberColumn(format="%.2f"),
                                      "Cotacao": st.column_config.NumberColumn(format="R$ %.2f")})

        with tabs[2]:
            top_roe = df.nlargest(5, "ROE")[["Ticker", "Nome", "ROE", "Cotacao"]]
            st.dataframe(top_roe, use_container_width=True, hide_index=True,
                        column_config={"ROE": st.column_config.NumberColumn(format="%.2f%%"),
                                      "Cotacao": st.column_config.NumberColumn(format="R$ %.2f")})

        with tabs[3]:
            top_score = df.nlargest(5, "Score_CS")[["Ticker", "Nome", "Score_CS", "Score_CS_Classificacao", "Cotacao"]]
            st.dataframe(top_score, use_container_width=True, hide_index=True,
                        column_config={"Score_CS": st.column_config.NumberColumn(format="%d/9"),
                                      "Cotacao": st.column_config.NumberColumn(format="R$ %.2f")})

        with tabs[4]:
            top_graham = df[df["Upside_Graham"] > 0].nlargest(5, "Upside_Graham")[["Ticker", "Nome", "Graham", "Upside_Graham", "Cotacao"]]
            st.dataframe(top_graham, use_container_width=True, hide_index=True,
                        column_config={"Upside_Graham": st.column_config.NumberColumn(format="%.1f%%"),
                                      "Graham": st.column_config.NumberColumn(format="R$ %.2f"),
                                      "Cotacao": st.column_config.NumberColumn(format="R$ %.2f")})


# ==================== ANÁLISE DE ATIVO ====================
def pagina_analise():
    st.markdown('<div class="main-header">🔍 Análise Fundamentalista</div>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Nenhum dado disponivel.")
        return

    ticker = st.selectbox("Selecione o ativo", sorted(df["Ticker"].tolist()))

    if not ticker:
        return

    ativo = df[df["Ticker"] == ticker].iloc[0]

    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.header(f"{ticker} - {ativo.get('Nome', '')}")
        st.caption(f"{ativo.get('Setor', '')} > {ativo.get('SubSetor', '')} > {ativo.get('Segmento', '')}")
    with col2:
        score = int(ativo.get("Score_CS", 0))
        classif = ativo.get("Score_CS_Classificacao", "")
        st.metric("Score CS", f"{score}/9", classif)
    with col3:
        st.metric("Cotacao", f"R$ {ativo.get('Cotacao', 0):.2f}")

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
        ("Margem Liquida", ativo.get("MargemLiquida", 0), "%"),
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
        st.markdown("**Precos Alvo**")
        valuation_data = {
            "Metodo": ["Graham", "Graham BR", "Bazin", "Lynch", "AGF"],
            "Preco Alvo": [
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
        df_val["Preco Alvo"] = df_val["Preco Alvo"].apply(lambda x: f"R$ {x:.2f}" if x > 0 else "N/A")
        df_val["Upside"] = df_val["Upside"].apply(lambda x: f"{x:.1f}%" if x != 0 else "N/A")
        st.dataframe(df_val, use_container_width=True, hide_index=True)

    with col_v2:
        st.markdown("**Composicao Score CS**")
        score_details = {
            "Criterio": [
                "ROE > 15%", "DY > 3%", "Div/PL < 0.5", "P/L < 15",
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

    # Radar
    st.subheader("🎯 Radar de Indicadores")

    radar_metrics = {
        "ROE": min(ativo.get("ROE", 0) / 30 * 100, 100),
        "DY": min(ativo.get("DY", 0) / 10 * 100, 100),
        "Margem Liq.": min(ativo.get("MargemLiquida", 0) / 20 * 100, 100),
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
def pagina_rankings():
    st.markdown('<div class="main-header">🏆 Rankings</div>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Nenhum dado disponivel.")
        return

    ranking_tipo = st.selectbox(
        "Tipo de Ranking",
        ["🏆 Score CS", "💰 Maior DY", "📉 Menor P/L", "📈 Maior ROE", "🚀 Maior Upside (Graham)",
         "💵 Maior Upside (Bazin)", "📊 Maior Margem Liquida", "🔥 Maior ROIC"]
    )

    n = st.slider("Quantidade", 5, 50, 20)

    mapping = {
        "🏆 Score CS": ("Score_CS", False),
        "💰 Maior DY": ("DY", False),
        "📉 Menor P/L": ("PL", True),
        "📈 Maior ROE": ("ROE", False),
        "🚀 Maior Upside (Graham)": ("Upside_Graham", False),
        "💵 Maior Upside (Bazin)": ("Upside_Bazin", False),
        "📊 Maior Margem Liquida": ("MargemLiquida", False),
        "🔥 Maior ROIC": ("ROIC", False),
    }

    col, asc = mapping.get(ranking_tipo, ("Score_CS", False))

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
            "Pessimo": "#ff0000",
        },
        title=f"Top {n} - {ranking_tipo}"
    )
    st.plotly_chart(fig, use_container_width=True)


# ==================== COMPARATIVO ====================
def pagina_comparativo():
    st.markdown('<div class="main-header">📈 Comparativo de Ativos</div>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Nenhum dado disponivel.")
        return

    tickers = st.multiselect(
        "Selecione ate 5 ativos",
        sorted(df["Ticker"].tolist()),
        max_selections=5,
        default=sorted(df["Ticker"].tolist())[:3] if len(df) >= 3 else []
    )

    if not tickers:
        st.info("Selecione ativos para comparar.")
        return

    df_comp = df[df["Ticker"].isin(tickers)].copy()

    metrics = ["Cotacao", "PL", "PVP", "DY", "ROE", "ROIC", "MargemLiquida", "Score_CS"]
    metrics = [m for m in metrics if m in df_comp.columns]

    comp_table = df_comp.set_index("Ticker")[metrics].T
    st.dataframe(comp_table, use_container_width=True)

    metric_comp = st.selectbox("Metrica para comparar", metrics)

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
            "Pessimo": "#ff0000",
        }
    )
    st.plotly_chart(fig, use_container_width=True)

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


# ==================== CONFIGURACOES ====================
def pagina_configuracoes():
    st.markdown('<div class="main-header">⚙️ Configuracoes</div>', unsafe_allow_html=True)

    st.subheader("📁 Dados")

    if os.path.exists("ativos.xlsx"):
        import os as os_mod
        size = os_mod.path.getsize("ativos.xlsx")
        st.write(f"**ativos.xlsx:** {size/1024:.1f} KB")

        df = load_data()
        if not df.empty:
            st.write(f"**Ativos:** {len(df)}")
            st.write(f"**Colunas:** {len(df.columns)}")
            st.write(f"**Ultima atualizacao:** {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")
    else:
        st.warning("ativos.xlsx nao encontrado.")

    st.markdown("---")

    st.subheader("🔧 Parametros de Valuation")
    selic = get_selic()
    st.write(f"**SELIC atual:** {selic}%")
    st.write("**Minimo DY Bazin:** 6%")
    st.write("**Multiplicador Graham BR:** 1/SELIC")
    st.write("**Threshold Score CS:** 8=Excelente, 6=Bom, 4=Regular, 2=Fraco, 0=Pessimo")


# ==================== MAIN ====================
def main():
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/stocks.png", width=60)
        st.title("SOBRAL Invest")
        st.markdown("---")

        menu = st.radio(
            "Navegacao",
            ["🏠 Dashboard", "🔍 Analise de Ativo", "📊 Rankings", "📈 Comparativo", "⚙️ Configuracoes"]
        )

        st.markdown("---")
        st.markdown("**Dados:** `ativos.xlsx`")
        st.markdown("**Fonte:** MFinance + BRAPI")

        selic = get_selic()
        st.markdown(f"**SELIC:** {selic}% a.a.")

    if menu == "🏠 Dashboard":
        pagina_inicial()
    elif menu == "🔍 Analise de Ativo":
        pagina_analise()
    elif menu == "📊 Rankings":
        pagina_rankings()
    elif menu == "📈 Comparativo":
        pagina_comparativo()
    elif menu == "⚙️ Configuracoes":
        pagina_configuracoes()


if __name__ == "__main__":
    main()
