"""
app_sobral_invest.py - Streamlit Dashboard SOBRAL Invest v5.0
Correcoes:
- Score CS: 10 criterios (ROE>10%, DY>6%, DivLiq/EBITDA<2.5x, Volume>1M)
- 5 valuations: Graham, Graham_BR, Bazin, Lynch, AGF_Medio
- Remove Lynch_Preco_Teto, Lynch_Mod, AGF_Projetivo
- Dados corrigidos (PL, PVP via mfinance_client v2.1)
- Dashboard com TradingView widgets
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit.components.v1 as components
import numpy as np
import os

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
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .score-excelente { color: #00cc00; font-weight: bold; }
    .score-bom { color: #66cc00; font-weight: bold; }
    .score-regular { color: #ffcc00; font-weight: bold; }
    .score-fraco { color: #ff6600; font-weight: bold; }
    .score-pessimo { color: #ff0000; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


def load_data():
    """Carrega dados do ativos.xlsx com conversao correta."""
    try:
        df = pd.read_excel("ativos.xlsx", sheet_name="Dados")
    except:
        try:
            df = pd.read_csv("ativos.csv", encoding="utf-8-sig")
        except:
            st.error("Erro ao carregar dados. Verifique se ativos.xlsx ou ativos.csv existem.")
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


def pagina_inicial():
    """Dashboard principal com TradingView widgets."""
    st.markdown('<h1 class="main-header">📈 SOBRAL Invest</h1>', unsafe_allow_html=True)

    # Widget TradingView - Ibovespa Symbol Overview
    st.subheader("📊 Ibovespa")
    tv_ibov = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
      {
        "symbols": [
          ["BMFBOVESPA:IBOV|1D"]
        ],
        "chartOnly": false,
        "width": "960",
        "height": "400",
        "locale": "br",
        "colorTheme": "dark",
        "autosize": false,
        "showVolume": true,
        "showMA": false,
        "hideDateRanges": false,
        "hideMarketStatus": false,
        "hideSymbolLogo": false,
        "scalePosition": "right",
        "scaleMode": "Normal",
        "fontFamily": "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif",
        "fontSize": "10",
        "noTimeScale": false,
        "valuesTracking": "1",
        "changeMode": "price-and-percent",
        "chartType": "area",
        "maLineColor": "#2962FF",
        "maLineWidth": 1,
        "maLength": 9,
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
      }
      </script>
    </div>
    """
    components.html(tv_ibov, height=410)

    # Widget TradingView - Hotlists (Maiores Altas/Baixas)
    st.subheader("🔥 Maiores Altas e Baixas")
    tv_hotlists = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-hotlists.js" async>
      {
        "colorTheme": "dark",
        "dateRange": "1D",
        "exchange": "BMFBOVESPA",
        "showChart": true,
        "locale": "br",
        "largeChartUrl": "",
        "isTransparent": false,
        "showSymbolLogo": true,
        "showFloatingTooltip": true,
        "width": "960",
        "height": "550",
        "plotLineColorGrowing": "rgba(41, 98, 255, 1)",
        "plotLineColorFalling": "rgba(41, 98, 255, 1)",
        "plotLineColorGrowingBottom": "rgba(41, 98, 255, 0)",
        "plotLineColorFallingBottom": "rgba(41, 98, 255, 0)",
        "gridLineColor": "rgba(42, 46, 57, 0)",
        "scaleFontColor": "rgba(120, 123, 134, 1)",
        "belowLineFillColorGrowing": "rgba(41, 98, 255, 0.12)",
        "belowLineFillColorFalling": "rgba(41, 98, 255, 0.12)",
        "belowLineFillColorGrowingBottom": "rgba(41, 98, 255, 0)",
        "belowLineFillColorFallingBottom": "rgba(41, 98, 255, 0)",
        "symbolActiveColor": "rgba(41, 98, 255, 0.12)",
        "tabs": [
          {
            "title": "Mais Negociadas",
            "symbols": [
              { "s": "BMFBOVESPA:PETR4", "d": "Petrobras" },
              { "s": "BMFBOVESPA:VALE3", "d": "Vale" },
              { "s": "BMFBOVESPA:ITUB4", "d": "Itau Unibanco" },
              { "s": "BMFBOVESPA:BBDC4", "d": "Bradesco" },
              { "s": "BMFBOVESPA:ABEV3", "d": "Ambev" },
              { "s": "BMFBOVESPA:WEGE3", "d": "Weg" },
              { "s": "BMFBOVESPA:BBAS3", "d": "Banco do Brasil" }
            ],
            "originalTitle": "Equities"
          },
          {
            "title": "Maiores Altas",
            "symbols": [
              { "s": "BMFBOVESPA:IBOV", "d": "Ibovespa" }
            ]
          },
          {
            "title": "Maiores Baixas",
            "symbols": [
              { "s": "BMFBOVESPA:IBOV", "d": "Ibovespa" }
            ]
          }
        ]
      }
      </script>
    </div>
    """
    components.html(tv_hotlists, height=560)

    # Rankings rapidos
    st.subheader("🏆 Rankings")
    df = load_data()
    if not df.empty:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**📊 Score CS**")
            top_score = df.nlargest(5, "Score_CS")[["Ticker", "Nome", "Score_CS"]]
            st.dataframe(top_score, hide_index=True)

        with col2:
            st.markdown("**💰 Dividend Yield**")
            top_dy = df.nlargest(5, "DY")[["Ticker", "Nome", "DY"]]
            st.dataframe(top_dy, hide_index=True)

        with col3:
            st.markdown("**📈 Maiores Altas**")
            top_altas = df.nlargest(5, "Variacao")[["Ticker", "Nome", "Variacao"]]
            st.dataframe(top_altas, hide_index=True)



def pagina_analise():
    """Pagina de analise de ativo estilo Investidor10 - Layout v2.0 Cards."""

    # CSS customizado para esta pagina
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    .analise-container * {
        font-family: 'Inter', sans-serif;
    }

    /* Cards de metrica */
    .metric-card-v2 {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        height: 100%;
    }

    .metric-card-v2:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(0,0,0,0.2);
        border-color: #3b82f6;
    }

    .metric-label-v2 {
        font-size: 0.7rem;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
        line-height: 1.2;
    }

    .metric-value-v2 {
        font-size: 1.3rem;
        font-weight: 700;
        color: #f1f5f9;
        line-height: 1.2;
    }

    /* Score Card */
    .score-card-v2 {
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 10px 15px rgba(0,0,0,0.2);
    }

    .score-number-v2 {
        font-size: 3.5rem;
        font-weight: 800;
        line-height: 1;
        margin-bottom: 8px;
    }

    .score-label-v2 {
        font-size: 1.1rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    .score-desc-v2 {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 6px;
    }

    /* Checklist compacto */
    .checklist-item-v2 {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 8px 12px;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: all 0.2s ease;
        margin-bottom: 6px;
    }

    .checklist-item-v2:hover {
        border-color: #475569;
    }

    .checklist-icon-v2 {
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 700;
        flex-shrink: 0;
        color: white;
    }

    .checklist-text-v2 {
        font-size: 0.8rem;
        font-weight: 500;
        color: #e2e8f0;
        line-height: 1.2;
    }

    /* Section Title */
    .section-title-v2 {
        font-size: 1rem;
        font-weight: 700;
        color: #f1f5f9;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin: 28px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #334155;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Preco Justo Card */
    .pj-card-v2 {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        transition: all 0.3s ease;
    }

    .pj-card-v2:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(0,0,0,0.2);
    }

    .pj-title-v2 {
        font-size: 0.7rem;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 10px;
    }

    .pj-valor-v2 {
        font-size: 1.2rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 4px;
    }

    .pj-upside-v2 {
        font-size: 0.9rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 12px;
        display: inline-block;
    }

    /* Checklist B&H Cards */
    .bh-card-v2 {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid;
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        transition: all 0.3s ease;
    }

    .bh-card-v2:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 10px rgba(0,0,0,0.2);
    }

    .bh-icon-v2 {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 8px auto;
        font-size: 16px;
        font-weight: 700;
        color: white;
    }

    .bh-title-v2 {
        font-size: 0.75rem;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 2px;
        line-height: 1.2;
    }

    .bh-desc-v2 {
        font-size: 0.65rem;
        color: #94a3b8;
        line-height: 1.2;
    }

    /* Header do ativo */
    .ativo-header-v2 {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
    }

    .ativo-ticker-v2 {
        font-size: 1.8rem;
        font-weight: 800;
        color: #f1f5f9;
    }

    .ativo-nome-v2 {
        font-size: 1rem;
        color: #94a3b8;
        margin-top: 4px;
    }

    .ativo-setor-v2 {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 8px;
    }

    .ativo-cotacao-v2 {
        font-size: 2rem;
        font-weight: 700;
        color: #f1f5f9;
        text-align: right;
    }

    .ativo-var-v2 {
        font-size: 1rem;
        font-weight: 600;
        text-align: right;
        margin-top: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="analise-container">', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Dados nao disponiveis.")
        return

    # ============================================================
    # 1. SELETOR DE ATIVO
    # ============================================================
    df['Display'] = df['Ticker'] + ' — ' + df['Nome']
    ativo_selecionado = st.selectbox(
        "🔍 Selecione o ativo",
        options=sorted([str(x) for x in df['Display'].tolist()]),
        index=0,
        key="ativo_selector_v2"
    )

    ticker = ativo_selecionado.split(' — ')[0]
    ativo = df[df['Ticker'] == ticker].iloc[0] if len(df[df['Ticker'] == ticker]) > 0 else None

    if ativo is None:
        st.error("Ativo nao encontrado.")
        return

    # ============================================================
    # HEADER DO ATIVO
    # ============================================================
    cotacao = ativo.get("Cotacao", 0)
    variacao = ativo.get("Variacao", 0)
    var_color = "#10b981" if variacao >= 0 else "#ef4444"

    col_h1, col_h2 = st.columns([2, 1])
    with col_h1:
        st.markdown(f"""
        <div class="ativo-header-v2">
            <div class="ativo-ticker-v2">{ativo['Ticker']}</div>
            <div class="ativo-nome-v2">{ativo['Nome']}</div>
            <div class="ativo-setor-v2">{ativo.get('Setor', 'N/A')} › {ativo.get('SubSetor', 'N/A')} › {ativo.get('Segmento', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_h2:
        st.markdown(f"""
        <div class="ativo-header-v2">
            <div class="ativo-cotacao-v2">R$ {cotacao:.2f}</div>
            <div class="ativo-var-v2" style="color: {var_color};">{variacao:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # 2. SCORE CS + CHECKLIST COMPACTO
    # ============================================================
    st.markdown('<div class="section-title-v2">🎯 Score CS</div>', unsafe_allow_html=True)

    score = int(ativo.get('Score_CS', 0))
    if score >= 7:
        score_color, score_bg, score_label = "#10b981", "#065f46", "Excelente"
    elif score >= 4:
        score_color, score_bg, score_label = "#f59e0b", "#92400e", "Bom"
    else:
        score_color, score_bg, score_label = "#ef4444", "#991b1b", "Fraco"

    col_score, col_check = st.columns([1, 2])

    with col_score:
        st.markdown(f"""
        <div class="score-card-v2" style="background: linear-gradient(135deg, {score_bg} 0%, {score_color}20 100%); border: 2px solid {score_color};">
            <div class="score-number-v2" style="color: {score_color};">{score}</div>
            <div class="score-label-v2" style="color: {score_color};">{score_label}</div>
            <div class="score-desc-v2">de 10 pontos</div>
        </div>
        """, unsafe_allow_html=True)

    with col_check:
        checklist_items = [
            ("ROE > 10%", ativo.get('ROE_10pct', 0)),
            ("DY > 6%", ativo.get('DY_6pct', 0)),
            ("Dív.Liq/EBITDA < 2.5", ativo.get('DivLiq_EBITDA_2_5', 0)),
            ("PL < 15", ativo.get('PL_15', 0)),
            ("PVP < 2", ativo.get('PVP_2', 0)),
            ("Margem > 10%", ativo.get('Margem_10pct', 0)),
            ("Liq.Corrente > 1", ativo.get('LiqCorrente_1', 0)),
            ("CAGR > 5%", ativo.get('CAGR_5pct', 0)),
            ("ROIC > 10%", ativo.get('ROIC_10pct', 0)),
            ("Volume > 1M", ativo.get('Volume_1M', 0)),
        ]

        cols_check = st.columns(3)
        for i, (label, value) in enumerate(checklist_items):
            is_true = bool(value) if not pd.isna(value) else False
            icon = "✓" if is_true else "✗"
            bg_color = "#10b981" if is_true else "#ef4444"

            cols_check[i % 3].markdown(f"""
            <div class="checklist-item-v2">
                <div class="checklist-icon-v2" style="background: {bg_color};">{icon}</div>
                <div class="checklist-text-v2">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    # ============================================================
    # 3. VALUATION - 6 colunas x 2 linhas
    # ============================================================
    st.markdown('<div class="section-title-v2">📈 Valuation</div>', unsafe_allow_html=True)

    valuation_data = [
        ("P/L (PL)", f"{ativo.get('PL', 0):.2f}x"),
        ("P/VP (PVP)", f"{ativo.get('PVP', 0):.2f}x"),
        ("P/E (PE)", f"{ativo.get('PE', 0):.2f}x"),
        ("EPS", f"R$ {ativo.get('EPS', 0):.2f}"),
        ("PSR (P/Receita)", f"{ativo.get('PSR', 0):.2f}x"),
        ("P/Ativo", f"{ativo.get('PAtivo', 0):.2f}x"),
        ("P/Cap.Giro", f"{ativo.get('PCapGiro', 0):.2f}x"),
        ("P/Ativo Circ. Líq.", f"{ativo.get('PAtivoCircLiq', 0):.2f}x"),
        ("P/EBIT", f"{ativo.get('PEBIT', 0):.2f}x"),
        ("P/EBITDA", f"{ativo.get('PEBITDA', 0):.2f}x"),
        ("EV/EBIT", f"{ativo.get('EV_EBIT', 0):.2f}x"),
        ("EV/EBITDA", f"{ativo.get('EV_EBITDA', 0):.2f}x"),
    ]

    for row_idx in range(2):
        cols = st.columns(6)
        for col_idx in range(6):
            idx = row_idx * 6 + col_idx
            if idx < len(valuation_data):
                label, value = valuation_data[idx]
                cols[col_idx].markdown(f"""
                <div class="metric-card-v2">
                    <div class="metric-label-v2">{label}</div>
                    <div class="metric-value-v2">{value}</div>
                </div>
                """, unsafe_allow_html=True)

    # ============================================================
    # 4. RENTABILIDADE - 4 colunas x 2 linhas
    # ============================================================
    st.markdown('<div class="section-title-v2">💰 Rentabilidade</div>', unsafe_allow_html=True)

    rent_data = [
        ("ROE", f"{ativo.get('ROE', 0):.2f}%"),
        ("ROA", f"{ativo.get('ROA', 0):.2f}%"),
        ("ROIC", f"{ativo.get('ROIC', 0):.2f}%"),
        ("Giro Ativos", f"{ativo.get('GiroAtivos', 0):.2f}x"),
        ("Margem Bruta", f"{ativo.get('MargemBruta', 0):.2f}%"),
        ("Margem EBITDA", f"{ativo.get('MargemEBITDA', 0):.2f}%"),
        ("Margem EBIT", f"{ativo.get('MargemEBIT', 0):.2f}%"),
        ("Margem Líquida", f"{ativo.get('MargemLiquida', 0):.2f}%"),
    ]

    for row_idx in range(2):
        cols = st.columns(4)
        for col_idx in range(4):
            idx = row_idx * 4 + col_idx
            if idx < len(rent_data):
                label, value = rent_data[idx]
                cols[col_idx].markdown(f"""
                <div class="metric-card-v2">
                    <div class="metric-label-v2">{label}</div>
                    <div class="metric-value-v2">{value}</div>
                </div>
                """, unsafe_allow_html=True)

    # ============================================================
    # 5. ENDIVIDAMENTO - 4 colunas x 2 linhas
    # ============================================================
    st.markdown('<div class="section-title-v2">⚠️ Endividamento</div>', unsafe_allow_html=True)

    endiv_data = [
        ("Dív.Líq / Ativos", f"{ativo.get('DivLiquida_Ativos', 0):.2f}x"),
        ("Dív.Líq / PL", f"{ativo.get('DivLiquida_PL', 0):.2f}x"),
        ("Dív.Líq / EBIT", f"{ativo.get('DivLiquida_EBIT', 0):.2f}x"),
        ("Dív.Líq / EBITDA", f"{ativo.get('DivLiquida_EBITDA', 0):.2f}x"),
        ("Liquidez Corrente", f"{ativo.get('LiquidezCorrente', 0):.2f}x"),
        ("Passivos / Ativos", f"{ativo.get('Passivos_Ativos', 0):.2f}x"),
        ("PL / Ativos", f"{ativo.get('PL_Ativos', 0):.2f}x"),
    ]

    for row_idx in range(2):
        cols = st.columns(4)
        for col_idx in range(4):
            idx = row_idx * 4 + col_idx
            if idx < len(endiv_data):
                label, value = endiv_data[idx]
                cols[col_idx].markdown(f"""
                <div class="metric-card-v2">
                    <div class="metric-label-v2">{label}</div>
                    <div class="metric-value-v2">{value}</div>
                </div>
                """, unsafe_allow_html=True)

    # ============================================================
    # 6. RESULTADO - 6 colunas x 1 linha
    # ============================================================
    st.markdown('<div class="section-title-v2">📊 Resultado</div>', unsafe_allow_html=True)

    res_data = [
        ("LPA", f"R$ {ativo.get('LPA', 0):.2f}"),
        ("VPA", f"R$ {ativo.get('VPA', 0):.2f}"),
        ("Patrimônio Líq.", f"R$ {ativo.get('Patrimonio', 0)/1e9:.2f}B"),
        ("Lucro Líquido", f"R$ {ativo.get('Lucro_Liquido', 0)/1e9:.2f}B"),
        ("EBIT", f"R$ {ativo.get('EBIT', 0)/1e9:.2f}B"),
        ("Receita Líq.", f"R$ {ativo.get('Receita_Liquida', 0)/1e9:.2f}B"),
    ]

    cols_res = st.columns(6)
    for i, (label, value) in enumerate(res_data):
        cols_res[i].markdown(f"""
        <div class="metric-card-v2">
            <div class="metric-label-v2">{label}</div>
            <div class="metric-value-v2">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # 7. CRESCIMENTO - 1 linha
    # ============================================================
    st.markdown('<div class="section-title-v2">🚀 Crescimento</div>', unsafe_allow_html=True)

    cresc_data = [
        ("CAGR Receitas 5a", f"{ativo.get('CAGR_Receitas_5a', 0):.2f}%"),
        ("CAGR Lucros 5a", f"{ativo.get('CAGR_Lucros_5a', 0):.2f}%"),
        ("Qtd. de Ações", f"{ativo.get('Qtd_Acoes', 0)/1e9:.2f}B"),
    ]

    cols_cresc = st.columns(3)
    for i, (label, value) in enumerate(cresc_data):
        cols_cresc[i].markdown(f"""
        <div class="metric-card-v2">
            <div class="metric-label-v2">{label}</div>
            <div class="metric-value-v2">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # 8. DIVIDENDOS - 1 linha
    # ============================================================
    st.markdown('<div class="section-title-v2">💵 Dividendos</div>', unsafe_allow_html=True)

    div_data = [
        ("DY Atual", f"{ativo.get('DY', 0):.2f}%"),
        ("DY 12 meses", f"{ativo.get('DY_12m', 0):.2f}%"),
        ("Div. Médio 12m", f"R$ {ativo.get('Dividendo_Medio_12m', 0):.4f}"),
        ("Div. Total 12m", f"R$ {ativo.get('Dividendo_Total_12m', 0):.4f}"),
        ("Div. Último", f"R$ {ativo.get('Dividendo_Ultimo', 0):.4f}"),
        ("Qtd. Div. 12m", f"{int(ativo.get('Qtd_Dividendos_12m', 0))}"),
        ("Div. Médio 6a", f"R$ {ativo.get('Dividendo_Medio_6a', 0):.4f}"),
    ]

    cols_div = st.columns(7)
    for i, (label, value) in enumerate(div_data):
        cols_div[i].markdown(f"""
        <div class="metric-card-v2">
            <div class="metric-label-v2">{label}</div>
            <div class="metric-value-v2">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # 9. PREÇO JUSTO - lado a lado com upside
    # ============================================================
    st.markdown('<div class="section-title-v2">🎯 Preço Justo</div>', unsafe_allow_html=True)

    pj_data = [
        ("Graham", ativo.get('Graham', 0), ativo.get('Upside_Graham', 0)),
        ("Graham BR", ativo.get('Graham_BR', 0), ativo.get('Upside_Graham_BR', 0)),
        ("Bazin", ativo.get('Bazin', 0), ativo.get('Upside_Bazin', 0)),
        ("Lynch", ativo.get('Lynch', 0), ativo.get('Upside_Lynch', 0)),
        ("AGF Médio", ativo.get('AGF_Medio', 0), ativo.get('Upside_AGF_Medio', 0)),
    ]

    cols_pj = st.columns(5)
    for i, (title, preco, upside) in enumerate(pj_data):
        try:
            upside_val = float(upside)
            if upside_val > 0:
                up_color, up_bg = "#10b981", "#065f46"
            elif upside_val < 0:
                up_color, up_bg = "#ef4444", "#991b1b"
            else:
                up_color, up_bg = "#94a3b8", "#475569"
        except:
            up_color, up_bg = "#94a3b8", "#475569"
            upside_val = 0

        preco_str = f"R$ {preco:.2f}" if preco > 0 else "N/A"
        upside_str = f"{upside_val:+.1f}%" if preco > 0 else "—"

        cols_pj[i].markdown(f"""
        <div class="pj-card-v2" style="border-color: {up_color}40;">
            <div class="pj-title-v2">{title}</div>
            <div class="pj-valor-v2">{preco_str}</div>
            <div class="pj-upside-v2" style="background: {up_bg}40; color: {up_color};">{upside_str}</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # 10. CHECKLIST BUY & HOLD - Cards melhorados
    # ============================================================
    st.markdown('<div class="section-title-v2">✅ Checklist Buy & Hold</div>', unsafe_allow_html=True)

    bh_items = [
        ("ROE > 10%", ativo.get('ROE_10pct', 0), "Rentabilidade do patrimônio"),
        ("DY > 6%", ativo.get('DY_6pct', 0), "Dividend Yield atrativo"),
        ("Dív.Liq/EBITDA < 2.5", ativo.get('DivLiq_EBITDA_2_5', 0), "Endividamento controlado"),
        ("PL < 15", ativo.get('PL_15', 0), "Preço não está caro"),
        ("PVP < 2", ativo.get('PVP_2', 0), "Próximo do valor patrimonial"),
        ("Margem > 10%", ativo.get('Margem_10pct', 0), "Lucratividade saudável"),
        ("Liq.Corrente > 1", ativo.get('LiqCorrente_1', 0), "Capacidade de pagamento"),
        ("CAGR > 5%", ativo.get('CAGR_5pct', 0), "Crescimento consistente"),
        ("ROIC > 10%", ativo.get('ROIC_10pct', 0), "Retorno sobre capital"),
        ("Volume > 1M", ativo.get('Volume_1M', 0), "Liquidez diária"),
    ]

    cols_bh = st.columns(5)
    for i, (title, value, desc) in enumerate(bh_items):
        is_true = bool(value) if not pd.isna(value) else False
        icon = "✓" if is_true else "✗"
        border_color = "#10b981" if is_true else "#ef4444"
        bg_icon = "#10b981" if is_true else "#ef4444"

        cols_bh[i % 5].markdown(f"""
        <div class="bh-card-v2" style="border-color: {border_color}60;">
            <div class="bh-icon-v2" style="background: {bg_icon};">{icon}</div>
            <div class="bh-title-v2">{title}</div>
            <div class="bh-desc-v2">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def pagina_rankings():
    """Pagina de rankings."""
    st.markdown('<h1 class="main-header">🏆 Rankings</h1>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Dados nao disponiveis.")
        return

    categorias = {
        "Score CS": "Score_CS",
        "Dividend Yield": "DY",
        "P/L (menor)": "PL",
        "ROE": "ROE",
        "ROIC": "ROIC",
        "Margem Liquida": "MargemLiquida",
        "Graham Upside": "Upside_Graham",
        "Bazin Upside": "Upside_Bazin",
    }

    categoria = st.selectbox("Categoria", list(categorias.keys()))
    col = categorias[categoria]

    if categoria in ["P/L (menor)", "Score CS"]:
        top = df.nsmallest(20, col) if categoria == "P/L (menor)" else df.nlargest(20, col)
    else:
        top = df.nlargest(20, col)

    st.dataframe(top[["Ticker", "Nome", "Setor", col]], hide_index=True, use_container_width=True)


def pagina_comparativo():
    """Pagina de comparativo de ativos."""
    st.markdown('<h1 class="main-header">📊 Comparativo</h1>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Dados nao disponiveis.")
        return

    tickers = st.multiselect("Selecione ate 5 ativos", sorted(df["Ticker"].tolist()), max_selections=5)
    if len(tickers) < 2:
        st.info("Selecione pelo menos 2 ativos para comparar.")
        return

    selecionados = df[df["Ticker"].isin(tickers)]

    # Radar comparativo
    categorias = ["ROE", "DY", "Margem Liquida", "ROIC", "CAGR Lucros"]
    fig = go.Figure()

    for _, row in selecionados.iterrows():
        valores = [
            min(row.get("ROE", 0) / 30 * 100, 100),
            min(row.get("DY", 0) / 10 * 100, 100),
            min(row.get("MargemLiquida", 0) / 20 * 100, 100),
            min(row.get("ROIC", 0) / 20 * 100, 100),
            min(row.get("CAGR_Lucros_5a", 0) / 15 * 100, 100),
        ]
        fig.add_trace(go.Scatterpolar(
            r=valores + [valores[0]],
            theta=categorias + [categorias[0]],
            fill='toself',
            name=row['Ticker']
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabela comparativa
    st.subheader("📋 Tabela Comparativa")
    cols_comp = ["Ticker", "Nome", "Cotacao", "DY", "PL", "PVP", "ROE", "ROIC", "MargemLiquida", "Score_CS"]
    st.dataframe(selecionados[[c for c in cols_comp if c in selecionados.columns]], hide_index=True, use_container_width=True)


def pagina_configuracoes():
    """Pagina de configuracoes."""
    st.markdown('<h1 class="main-header">⚙️ Configuracoes</h1>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Dados nao disponiveis.")
        return

    st.subheader("📊 Estatisticas Gerais")
    st.metric("Total de Ativos", len(df))
    st.metric("Score CS Medio", round(df["Score_CS"].mean(), 1))
    st.metric("Score CS Maximo", int(df["Score_CS"].max()))
    st.metric("Score CS Minimo", int(df["Score_CS"].min()))

    st.subheader("📅 Informacoes dos Dados")
    st.info("Dados atualizados diariamente via GitHub Actions.")
    st.info("Fonte: MFinance API + BRAPI (complementar)")

    st.subheader("📋 Colunas Disponiveis")
    st.write(f"Total de colunas: {len(df.columns)}")
    st.write(list(df.columns))


def main():
    """Funcao principal."""
    st.sidebar.markdown("## 📈 SOBRAL Invest")
    st.sidebar.markdown("---")

    pagina = st.sidebar.radio(
        "Navegacao",
        ["🏠 Dashboard", "🔍 Analise de Ativo", "🏆 Rankings", "📊 Comparativo", "⚙️ Configuracoes"]
    )

    if pagina == "🏠 Dashboard":
        pagina_inicial()
    elif pagina == "🔍 Analise de Ativo":
        pagina_analise()
    elif pagina == "🏆 Rankings":
        pagina_rankings()
    elif pagina == "📊 Comparativo":
        pagina_comparativo()
    elif pagina == "⚙️ Configuracoes":
        pagina_configuracoes()


if __name__ == "__main__":
    main()
