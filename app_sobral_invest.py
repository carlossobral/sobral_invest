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
    """Pagina de analise de ativo estilo Investidor10."""
    st.markdown('<h1 class="main-header">🔍 Analise de Ativo</h1>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Dados nao disponiveis.")
        return

    # Selecao de ativo
    ticker = st.selectbox("Selecione o ativo", sorted(df["Ticker"].tolist()))
    ativo = df[df["Ticker"] == ticker].iloc[0] if len(df[df["Ticker"] == ticker]) > 0 else None

    if ativo is None:
        st.error("Ativo nao encontrado.")
        return

    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"### {ativo['Ticker']} - {ativo['Nome']}")
        st.markdown(f"**Setor:** {ativo.get('Setor', 'N/A')} | **Subsetor:** {ativo.get('SubSetor', 'N/A')}")
    with col2:
        cotacao = ativo.get("Cotacao", 0)
        variacao = ativo.get("Variacao", 0)
        color = "green" if variacao >= 0 else "red"
        st.markdown(f"### R$ {cotacao:.2f}")
        st.markdown(f"<span style='color:{color}'>{variacao:+.2f}%</span>", unsafe_allow_html=True)
    with col3:
        score = int(ativo.get("Score_CS", 0))
        score_class = ativo.get("Score_CS_Classificacao", "N/A")
        score_color = {
            "Excelente": "score-excelente",
            "Bom": "score-bom",
            "Regular": "score-regular",
            "Fraco": "score-fraco",
            "Pessimo": "score-pessimo"
        }.get(score_class, "")
        st.markdown(f"### Score CS: {score}/10")
        st.markdown(f"<span class='{score_color}'>{score_class}</span>", unsafe_allow_html=True)

    # Widget TradingView para o ativo
    st.subheader("📈 Grafico")
    tv_symbol = f"BMFBOVESPA:{ticker}"
    tv_chart = f"""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
      {{
        "symbols": [
          ["{tv_symbol}|1D"]
        ],
        "chartOnly": false,
        "width": "100%",
        "height": "300",
        "locale": "br",
        "colorTheme": "dark",
        "autosize": true,
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
      }}
      </script>
    </div>
    """
    components.html(tv_chart, height=310)

    # Precos Justos
    st.subheader("🎯 Precos Justos")
    col1, col2, col3, col4, col5 = st.columns(5)

    valuations = [
        ("Graham", "Graham", "Upside_Graham"),
        ("Graham BR", "Graham_BR", "Upside_Graham_BR"),
        ("Bazin (6%)", "Bazin", "Upside_Bazin"),
        ("Lynch", "Lynch", "Upside_Lynch"),
        ("AGF Medio", "AGF_Medio", "Upside_AGF_Medio"),
    ]

    for i, (nome, col_val, col_up) in enumerate(valuations):
        with [col1, col2, col3, col4, col5][i]:
            preco = ativo.get(col_val, 0)
            upside = ativo.get(col_up, 0)
            if preco > 0:
                color = "green" if upside >= 0 else "red"
                st.metric(nome, f"R$ {preco:.2f}", f"{upside:+.1f}%", delta_color="inverse")
            else:
                st.metric(nome, "N/A", "—")

    # Indicadores
    st.subheader("📊 Indicadores Fundamentalistas")
    cols = st.columns(5)
    indicadores = [
        ("P/L", "PL", "x"),
        ("P/VP", "PVP", "x"),
        ("DY", "DY", "%"),
        ("ROE", "ROE", "%"),
        ("ROIC", "ROIC", "%"),
        ("Margem Liquida", "MargemLiquida", "%"),
        ("Margem Bruta", "MargemBruta", "%"),
        ("Margem EBITDA", "MargemEBITDA", "%"),
        ("EV/EBIT", "EV_EBIT", "x"),
        ("EV/EBITDA", "EV_EBITDA", "x"),
        ("LPA", "LPA", "R$"),
        ("VPA", "VPA", "R$"),
        ("CAGR Receitas 5a", "CAGR_Receitas_5a", "%"),
        ("CAGR Lucros 5a", "CAGR_Lucros_5a", "%"),
        ("Liquidez Corrente", "LiquidezCorrente", "x"),
        ("Div.Liq/EBITDA", "DivLiquida_EBITDA", "x"),
        ("Div.Liq/PL", "DivLiquida_PL", "x"),
        ("Passivos/Ativos", "Passivos_Ativos", "x"),
        ("PL/Ativos", "PL_Ativos", "x"),
        ("Giro Ativos", "GiroAtivos", "x"),
    ]

    for i, (nome, col, unit) in enumerate(indicadores):
        with cols[i % 5]:
            val = ativo.get(col, 0)
            if unit == "%":
                st.metric(nome, f"{val:.2f}%")
            elif unit == "x":
                st.metric(nome, f"{val:.2f}x")
            elif unit == "R$":
                st.metric(nome, f"R$ {val:.2f}")
            else:
                st.metric(nome, f"{val:.2f}")

    # Checklist Score CS
    st.subheader("✅ Checklist Score CS (Carlos Sobral)")

    checklist = [
        ("ROE > 10%", "ROE_10pct", "ROE", "%", 10),
        ("DY > 6%", "DY_6pct", "DY", "%", 6),
        ("Div.Liq/EBITDA < 2.5x", "DivLiq_EBITDA_2_5", "DivLiquida_EBITDA", "x", 2.5),
        ("P/L < 15", "PL_15", "PL", "x", 15),
        ("P/VP < 2", "PVP_2", "PVP", "x", 2),
        ("Margem Liquida > 10%", "Margem_10pct", "MargemLiquida", "%", 10),
        ("Liquidez Corrente > 1", "LiqCorrente_1", "LiquidezCorrente", "x", 1),
        ("CAGR Lucros 5a > 5%", "CAGR_5pct", "CAGR_Lucros_5a", "%", 5),
        ("ROIC > 10%", "ROIC_10pct", "ROIC", "%", 10),
        ("Volume Medio > R$ 1M", "Volume_1M", "Volume_Medio", "R$", 1000000),
    ]

    cols_check = st.columns(2)
    for i, (nome, check_col, val_col, unit, limite) in enumerate(checklist):
        with cols_check[i % 2]:
            passou = ativo.get(check_col, 0) == 1
            valor = ativo.get(val_col, 0)
            icon = "✅" if passou else "❌"
            status = "PASSOU" if passou else "NAO PASSOU"
            color = "green" if passou else "red"

            if unit == "%":
                val_str = f"{valor:.2f}%"
            elif unit == "x":
                val_str = f"{valor:.2f}x"
            elif unit == "R$":
                val_str = f"R$ {valor:,.0f}"
            else:
                val_str = f"{valor:.2f}"

            st.markdown(f"{icon} **{nome}** — Valor atual: {val_str} (limite: {limite}{unit})")
            st.markdown(f"<span style='color:{color}'>{status}</span>", unsafe_allow_html=True)
            st.markdown("---")

    # Radar de Indicadores
    st.subheader("🎯 Radar de Indicadores")
    categorias = ["ROE", "DY", "Margem Liquida", "ROIC", "CAGR Lucros"]
    valores = [
        min(ativo.get("ROE", 0) / 30 * 100, 100),
        min(ativo.get("DY", 0) / 10 * 100, 100),
        min(ativo.get("MargemLiquida", 0) / 20 * 100, 100),
        min(ativo.get("ROIC", 0) / 20 * 100, 100),
        min(ativo.get("CAGR_Lucros_5a", 0) / 15 * 100, 100),
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores + [valores[0]],
        theta=categorias + [categorias[0]],
        fill='toself',
        name=ativo['Ticker']
    ))
    fig.add_trace(go.Scatterpolar(
        r=[100, 100, 100, 100, 100, 100],
        theta=categorias + [categorias[0]],
        mode='lines',
        line=dict(color='gray', dash='dash'),
        name='Referencia'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

    # Valuation Completo
    st.subheader("📋 Valuation Completo")
    valuation_data = []
    for nome, col_val, col_up in valuations:
        preco = ativo.get(col_val, 0)
        upside = ativo.get(col_up, 0)
        valuation_data.append({
            "Metodo": nome,
            "Preco Justo": f"R$ {preco:.2f}" if preco > 0 else "N/A",
            "Upside": f"{upside:+.1f}%" if preco > 0 else "N/A",
            "Sinal": "🟢 Compra" if upside >= 20 else ("🟡 Atencao" if upside >= 0 else "🔴 Acima do teto") if preco > 0 else "—"
        })

    st.dataframe(pd.DataFrame(valuation_data), hide_index=True, use_container_width=True)


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
