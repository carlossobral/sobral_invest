"""
app_sobral_invest.py - SOBRAL Invest v4.0
Dashboard com TradingView Widgets
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

        # Converter TODAS as colunas numéricas
        numeric_cols = [
            "Cotacao", "Variacao", "Score_CS", "PL", "PVP", "DY", "ROE", "ROIC",
            "MargemLiquida", "MargemBruta", "MargemEBIT", "EV_EBIT", "EV_EBITDA",
            "DividaLiquida_PL", "DividaLiquida_EBITDA", "LiquidezCorrente",
            "VPA", "LPA", "P_Ativo", "P_EBIT", "P_Ativo_Circ", "PSR",
            "GiroAtivos", "CAGR_Receitas_5a", "CAGR_Lucros_5a",
            "Graham", "Graham_BR", "Bazin", "Lynch_Preco_Teto", "AGF",
            "Upside_Graham", "Upside_Graham_BR", "Upside_Bazin",
            "Upside_Lynch_Preco_Teto", "Upside_AGF",
            "ROE_15pct", "DY_3pct", "DivPL_0_5", "PL_15", "PVP_2",
            "Margem_10pct", "LiqCorrente_1", "CAGR_5pct", "ROIC_10pct"
        ]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Converter Ticker para string
        if "Ticker" in df.columns:
            df["Ticker"] = df["Ticker"].astype(str)

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


# ==================== PAGINA INICIAL - DASHBOARD ====================
def pagina_inicial():
    st.markdown('<div class="main-header">📈 SOBRAL Invest</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Acompanhe em tempo real o mercado da B3</div>', unsafe_allow_html=True)

    # IBOVESPA - TradingView Symbol Overview Widget
    st.markdown("---")

    tv_ibov = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <div class="tradingview-widget-copyright"><a href="https://br.tradingview.com/" rel="noopener nofollow" target="_blank"><span class="blue-text">Track all markets on TradingView</span></a></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
      {
        "lineWidth": 2,
        "lineType": 0,
        "chartType": "area",
        "fontColor": "rgb(106, 109, 120)",
        "gridLineColor": "rgba(242, 242, 242, 0.06)",
        "volumeUpColor": "rgba(34, 171, 148, 0.5)",
        "volumeDownColor": "rgba(247, 82, 95, 0.5)",
        "backgroundColor": "#0F0F0F",
        "widgetFontColor": "#DBDBDB",
        "upColor": "#22ab94",
        "downColor": "#f7525f",
        "borderUpColor": "#22ab94",
        "borderDownColor": "#f7525f",
        "wickUpColor": "#22ab94",
        "wickDownColor": "#f7525f",
        "colorTheme": "dark",
        "isTransparent": true,
        "locale": "br",
        "chartOnly": false,
        "scalePosition": "right",
        "scaleMode": "Normal",
        "fontFamily": "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif",
        "valuesTracking": "1",
        "changeMode": "price-and-percent",
        "symbols": [
          [
            "BMFBOVESPA:IBOV|1D"
          ]
        ],
        "dateRanges": [
          "1d|1",
          "1m|30",
          "3m|60",
          "12m|1D",
          "60m|1W",
          "all|1M"
        ],
        "fontSize": "10",
        "headerFontSize": "medium",
        "autosize": true,
        "dateFormat": "dd/MM/yyyy",
        "width": "960",
        "height": "400",
        "noTimeScale": false,
        "hideDateRanges": false,
        "hideMarketStatus": false,
        "hideSymbolLogo": false
      }
      </script>
    </div>
    """
    import streamlit.components.v1 as components
    components.html(tv_ibov, height=410)

    st.markdown("---")

    # MAIORES ALTAS E BAIXAS - TradingView Hotlists Widget
    st.markdown("## 📊 Mais Negociadas / Maiores Altas / Maiores Baixas")

    tv_hotlists = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-hotlists.js" async>
      {
        "exchange": "BMFBOVESPA",
        "colorTheme": "dark",
        "dateRange": "1D",
        "showChart": true,
        "locale": "br",
        "largeChartUrl": "",
        "isTransparent": false,
        "showSymbolLogo": true,
        "showFloatingTooltip": true,
        "plotLineColorGrowing": "rgba(41, 98, 255, 1)",
        "plotLineColorFalling": "rgba(41, 98, 255, 1)",
        "gridLineColor": "rgba(240, 243, 250, 0)",
        "scaleFontColor": "#DBDBDB",
        "belowLineFillColorGrowing": "rgba(41, 98, 255, 0.12)",
        "belowLineFillColorFalling": "rgba(41, 98, 255, 0.12)",
        "belowLineFillColorGrowingBottom": "rgba(41, 98, 255, 0)",
        "belowLineFillColorFallingBottom": "rgba(41, 98, 255, 0)",
        "symbolActiveColor": "rgba(41, 98, 255, 0.12)",
        "width": "960",
        "height": "550"
      }
      </script>
    </div>
    """
    components.html(tv_hotlists, height=560)

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
    st.markdown('<div class="main-header">🔍 Análise de Ativo</div>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Nenhum dado disponivel.")
        return

    ticker = st.selectbox("Selecione o ativo", sorted(df["Ticker"].tolist()))

    if not ticker:
        return

    ativo = df[df["Ticker"] == ticker].iloc[0]

    # ─── HEADER DO ATIVO ──────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:15px;">
            <div style="width:60px; height:60px; background:linear-gradient(135deg, #667eea, #764ba2); 
                        border-radius:12px; display:flex; align-items:center; justify-content:center; 
                        color:white; font-size:1.5rem; font-weight:700;">
                {ticker[:2]}
            </div>
            <div>
                <div style="font-size:1.5rem; font-weight:700;">{ticker}</div>
                <div style="font-size:0.9rem; color:#666;">{ativo.get('Nome', '')}</div>
                <div style="font-size:0.8rem; color:#888;">{ativo.get('Setor', '')} › {ativo.get('SubSetor', '')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.metric("Cotação", f"R$ {ativo.get('Cotacao', 0):.2f}")

    with col3:
        var = ativo.get("Variacao", 0)
        delta_color = "normal" if var == 0 else ("inverse" if var < 0 else "normal")
        st.metric("Variação", f"{var:+.2f}%", delta_color=delta_color)

    with col4:
        score = int(ativo.get("Score_CS", 0))
        score_colors = {8: "🟢", 6: "🟡", 4: "🟠", 0: "🔴"}
        score_emoji = next((v for k, v in sorted(score_colors.items(), reverse=True) if score >= k), "🔴")
        st.metric("Score CS", f"{score_emoji} {score}/9")

    st.markdown("---")

    # ─── GRÁFICO DO ATIVO (TradingView) ───────────────────────────────────────
    tv_ativo = f"""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <div class="tradingview-widget-copyright"><a href="https://br.tradingview.com/" rel="noopener nofollow" target="_blank"><span class="blue-text">Track all markets on TradingView</span></a></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
      {{
        "symbols": [
          ["BMFBOVESPA:{ticker}|1D"]
        ],
        "chartOnly": false,
        "width": "100%",
        "height": "300",
        "locale": "br",
        "colorTheme": "dark",
        "isTransparent": true,
        "autosize": true,
        "showVolume": false,
        "scalePosition": "right",
        "scaleMode": "Normal",
        "fontFamily": "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif",
        "fontSize": "10",
        "noTimeScale": false,
        "valuesTracking": "1",
        "changeMode": "price-and-percent",
        "chartType": "area",
        "lineWidth": 2,
        "lineType": 0,
        "dateRanges": [
          "1d|1",
          "1m|30",
          "3m|60",
          "12m|1D",
          "60m|1W",
          "all|1M"
        ]
      }}
      </script>
    </div>
    """
    import streamlit.components.v1 as components
    components.html(tv_ativo, height=310)

    st.markdown("---")

    # ─── PREÇO JUSTO (Graham) ────────────────────────────────────────────────
    st.subheader("💰 Preço Justo")

    col_g1, col_g2, col_g3 = st.columns(3)

    with col_g1:
        graham = ativo.get("Graham", 0)
        upside_g = ativo.get("Upside_Graham", 0)
        color_g = "#00c853" if upside_g > 0 else "#ff1744" if upside_g < 0 else "#ffab00"
        st.markdown(f"""
        <div style="background:#f8f9fa; border-radius:12px; padding:20px; text-align:center;">
            <div style="font-size:0.9rem; color:#666; margin-bottom:5px;">Graham</div>
            <div style="font-size:1.8rem; font-weight:700; color:#667eea;">R$ {graham:.2f}</div>
            <div style="font-size:0.9rem; color:{color_g}; margin-top:5px; font-weight:600;">
                {f"Upside: {upside_g:+.1f}%" if graham > 0 else "N/A"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_g2:
        bazin = ativo.get("Bazin", 0)
        upside_b = ativo.get("Upside_Bazin", 0)
        color_b = "#00c853" if upside_b > 0 else "#ff1744" if upside_b < 0 else "#ffab00"
        st.markdown(f"""
        <div style="background:#f8f9fa; border-radius:12px; padding:20px; text-align:center;">
            <div style="font-size:0.9rem; color:#666; margin-bottom:5px;">Bazin (6% DY)</div>
            <div style="font-size:1.8rem; font-weight:700; color:#667eea;">R$ {bazin:.2f}</div>
            <div style="font-size:0.9rem; color:{color_b}; margin-top:5px; font-weight:600;">
                {f"Upside: {upside_b:+.1f}%" if bazin > 0 else "N/A"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_g3:
        lynch = ativo.get("Lynch_Preco_Teto", 0)
        upside_l = ativo.get("Upside_Lynch_Preco_Teto", 0)
        color_l = "#00c853" if upside_l > 0 else "#ff1744" if upside_l < 0 else "#ffab00"
        st.markdown(f"""
        <div style="background:#f8f9fa; border-radius:12px; padding:20px; text-align:center;">
            <div style="font-size:0.9rem; color:#666; margin-bottom:5px;">Lynch</div>
            <div style="font-size:1.8rem; font-weight:700; color:#667eea;">R$ {lynch:.2f}</div>
            <div style="font-size:0.9rem; color:{color_l}; margin-top:5px; font-weight:600;">
                {f"Upside: {upside_l:+.1f}%" if lynch > 0 else "N/A"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ─── INDICADORES PRINCIPAIS ────────────────────────────────────────────────
    st.subheader("📊 Indicadores Fundamentalistas")

    indicadores = {
        "P/L": (ativo.get("PL", 0), "x"),
        "P/VP": (ativo.get("PVP", 0), "x"),
        "DY": (ativo.get("DY", 0), "%"),
        "ROE": (ativo.get("ROE", 0), "%"),
        "ROIC": (ativo.get("ROIC", 0), "%"),
        "Margem Líquida": (ativo.get("MargemLiquida", 0), "%"),
        "Margem Bruta": (ativo.get("MargemBruta", 0), "%"),
        "Margem EBIT": (ativo.get("MargemEBIT", 0), "%"),
        "EV/EBIT": (ativo.get("EV_EBIT", 0), "x"),
        "EV/EBITDA": (ativo.get("EV_EBITDA", 0), "x"),
        "Dívida/PL": (ativo.get("DividaLiquida_PL", 0), "x"),
        "Dívida/EBITDA": (ativo.get("DividaLiquida_EBITDA", 0), "x"),
        "Liquidez Corrente": (ativo.get("LiquidezCorrente", 0), "x"),
        "VPA": (ativo.get("VPA", 0), "R$"),
        "LPA": (ativo.get("LPA", 0), "R$"),
        "P/Ativo": (ativo.get("P_Ativo", 0), "x"),
        "P/EBIT": (ativo.get("P_EBIT", 0), "x"),
        "Giro Ativos": (ativo.get("GiroAtivos", 0), "x"),
        "CAGR Receitas": (ativo.get("CAGR_Receitas_5a", 0), "%"),
        "CAGR Lucros": (ativo.get("CAGR_Lucros_5a", 0), "%"),
    }

    cols = st.columns(5)
    idx = 0
    for nome, (valor, unidade) in indicadores.items():
        if valor != 0 or nome in ["P/L", "P/VP", "DY", "ROE"]:
            with cols[idx % 5]:
                suffix = f"{unidade}" if unidade != "R$" else ""
                prefix = "R$ " if unidade == "R$" else ""
                st.markdown(f"""
                <div style="background:#f8f9fa; border-radius:10px; padding:12px; text-align:center; margin:3px 0;">
                    <div style="font-size:0.75rem; color:#888;">{nome}</div>
                    <div style="font-size:1.1rem; font-weight:700; color:#1a1a2e;">
                        {prefix}{valor:.2f}{suffix}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            idx += 1

    st.markdown("---")

    # ─── CHECKLIST SCORE CS ──────────────────────────────────────────────────
    st.subheader("✅ Checklist Score CS (Carlos Sobral)")

    criterios = [
        ("ROE > 15%", ativo.get("ROE_15pct", 0) == 1, f"{ativo.get('ROE', 0):.2f}%"),
        ("DY > 3%", ativo.get("DY_3pct", 0) == 1, f"{ativo.get('DY', 0):.2f}%"),
        ("Dívida/PL < 0.5", ativo.get("DivPL_0_5", 0) == 1, f"{ativo.get('DividaLiquida_PL', 0):.2f}"),
        ("P/L < 15", ativo.get("PL_15", 0) == 1, f"{ativo.get('PL', 0):.2f}"),
        ("P/VP < 2", ativo.get("PVP_2", 0) == 1, f"{ativo.get('PVP', 0):.2f}"),
        ("Margem Líquida > 10%", ativo.get("Margem_10pct", 0) == 1, f"{ativo.get('MargemLiquida', 0):.2f}%"),
        ("Liquidez Corrente > 1", ativo.get("LiqCorrente_1", 0) == 1, f"{ativo.get('LiquidezCorrente', 0):.2f}"),
        ("CAGR Lucros > 5%", ativo.get("CAGR_5pct", 0) == 1, f"{ativo.get('CAGR_Lucros_5a', 0):.2f}%"),
        ("ROIC > 10%", ativo.get("ROIC_10pct", 0) == 1, f"{ativo.get('ROIC', 0):.2f}%"),
    ]

    col1, col2 = st.columns(2)
    for i, (criterio, passou, valor) in enumerate(criterios):
        with col1 if i < 5 else col2:
            status = "✅ PASSOU" if passou else "❌ NÃO PASSOU"
            cor = "#e8f5e9" if passou else "#ffebee"
            cor_borda = "#00c853" if passou else "#ff1744"
            st.markdown(f"""
            <div style="background:{cor}; border-left:4px solid {cor_borda}; border-radius:8px; 
                        padding:10px 15px; margin:5px 0; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-weight:600; font-size:0.9rem;">{criterio}</div>
                    <div style="font-size:0.8rem; color:#666;">Valor atual: {valor}</div>
                </div>
                <div style="font-weight:700; font-size:0.85rem; color:{cor_borda};">{status}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ─── RADAR DE INDICADORES ────────────────────────────────────────────────
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
        fill="toself",
        fillcolor="rgba(102, 126, 234, 0.3)",
        line=dict(color="#667eea", width=2),
        name=ticker
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=[100, 100, 100, 100, 100, 100],
        theta=list(radar_metrics.keys()) + [list(radar_metrics.keys())[0]],
        line=dict(color="#ccc", width=1, dash="dash"),
        name="Referência"
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=400
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("---")

    # ─── TABELA COMPLETA DE VALUATION ────────────────────────────────────────
    st.subheader("📋 Valuation Completo")

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
    df_val["Upside"] = df_val["Upside"].apply(lambda x: f"{x:+.1f}%" if x != 0 else "N/A")
    st.dataframe(df_val, use_container_width=True, hide_index=True)


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
