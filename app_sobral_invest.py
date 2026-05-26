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


# CSS GLOBAL para alinhamento de cards
st.markdown("""
<style>
/* Forçar gap entre colunas do Streamlit */
div[data-testid="stHorizontalBlock"] {
    gap: 0.75rem !important;
}

/* Forçar padding zero nas colunas */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    padding-left: 0.375rem !important;
    padding-right: 0.375rem !important;
}

/* Garantir que cards tenham margin-bottom */
.bh-card-v2 {
    margin-bottom: 0.75rem !important;
}

.metric-card-v2 {
    margin-bottom: 0.75rem !important;
}
</style>
""", unsafe_allow_html=True)

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
    # Dicionário de descrições para tooltips
    TOOLTIP_DESC = {
        "P/L (PL)": "Preço / Lucro. Indica quantos anos de lucro seriam necessários para pagar o preço da ação. Quanto menor, mais barata.",
        "P/VP (PVP)": "Preço / Valor Patrimonial. Mostra se a ação está negociando acima ou abaixo do valor contábil. < 1 = abaixo do patrimônio.",
        "P/E (PE)": "Price / Earnings Ratio. Versão americana do P/L. Mesma interpretação: quanto menor, mais barata.",
        "EPS": "Earnings Per Share. Lucro líquido dividido pelo número de ações. Quanto maior, mais lucrativa a empresa por ação.",
        "PSR (P/Receita)": "Preço / Receita. Útil para empresas que ainda não têm lucro. < 1 é considerado atraente.",
        "P/Ativo": "Preço / Ativo Total. Indica quanto o mercado paga pelos ativos da empresa. Útil para holdings.",
        "P/Cap.Giro": "Preço / Capital de Giro. Mede a relação entre preço e o capital de giro da empresa.",
        "P/Ativo Circ. Líq.": "Preço / Ativo Circulante Líquido. Negativo pode indicar empresa com mais caixa que dívidas de curto prazo.",
        "P/EBIT": "Preço / EBIT. Valuation baseado no lucro operacional antes de juros e impostos.",
        "P/EBITDA": "Preço / EBITDA. Elimina efeitos de depreciação. Útil para comparar empresas de setores diferentes.",
        "EV/EBIT": "Enterprise Value / EBIT. Considera dívida líquida. Melhor que P/EBIT para comparar empresas alavancadas.",
        "EV/EBITDA": "EV / EBITDA. O valuation mais completo: considera dívida, depreciação e lucro operacional.",
        "ROE": "Return on Equity. Retorno sobre o Patrimônio Líquido. > 15% é excelente. Mede eficiência na geração de lucro.",
        "ROA": "Return on Assets. Retorno sobre Ativos. Mede eficiência total da empresa em gerar lucro com todos os recursos.",
        "ROIC": "Return on Invested Capital. Retorno sobre Capital Investido. > 10% é bom. Considera dívida + patrimônio.",
        "Giro Ativos": "Receita / Ativos Totais. Mede quantas vezes a empresa 'gira' seus ativos em receita no ano.",
        "Margem Bruta": "(Receita - CMV) / Receita. Lucro antes de despesas operacionais. > 30% é bom para maioria dos setores.",
        "Margem EBITDA": "EBITDA / Receita. Lucro operacional antes de depreciação. Mostra eficiência operacional pura.",
        "Margem EBIT": "EBIT / Receita. Lucro operacional. > 10% indica empresa com bom controle de custos.",
        "Margem Líquida": "Lucro Líquido / Receita. Lucro final após todas as despesas e impostos. > 5% é saudável.",
        "Dív.Líq / Ativos": "Dívida Líquida / Ativos. < 0.5 indica empresa com pouca alavancagem financeira.",
        "Dív.Líq / PL": "Dívida Líquida / Patrimônio. < 1 é ideal: patrimônio maior que dívida.",
        "Dív.Líq / EBIT": "Dívida Líquida / EBIT. Indica quantos anos de lucro operacional levaria para quitar dívidas. < 3 é bom.",
        "Dív.Líq / EBITDA": "Dívida Líquida / EBITDA. < 2.5 é considerado saudável pelo Score CS. Principal indicador de endividamento.",
        "Liquidez Corrente": "Ativo Circulante / Passivo Circulante. > 1 indica capacidade de pagar dívidas de curto prazo.",
        "Passivos / Ativos": "Passivo Total / Ativo Total. < 0.7 indica estrutura de capital conservadora.",
        "PL / Ativos": "Patrimônio / Ativos. Quanto maior, mais capital próprio a empresa tem vs. capital de terceiros.",
        "LPA": "Lucro Por Ação. Lucro líquido dividido por número de ações. Base para cálculo do P/L.",
        "VPA": "Valor Patrimonial Por Ação. Patrimônio líquido dividido por ações. Base para cálculo do P/VP.",
        "Patrimônio Líq.": "Patrimônio Líquido total da empresa. Ativos - Passivos. Representa o valor contábil.",
        "Lucro Líquido": "Lucro após todas as despesas, impostos e juros. O resultado final para acionistas.",
        "EBIT": "Earnings Before Interest and Taxes. Lucro operacional antes de juros e impostos. Mede eficiência do negócio.",
        "Receita Líq.": "Receita Líquida total. Faturamento bruto menos impostos, devoluções e descontos.",
        "CAGR Receitas 5a": "Compound Annual Growth Rate de Receitas. Taxa média anual de crescimento nos últimos 5 anos.",
        "CAGR Lucros 5a": "CAGR de Lucros. Taxa média anual de crescimento do lucro nos últimos 5 anos. > 5% é positivo.",
        "Qtd. de Ações": "Número total de ações emitidas pela empresa. Usado para calcular LPA, VPA e EPS.",
        "DY Atual": "Dividend Yield dos últimos 12 meses. Dividendos pagos / Preço atual. > 6% é atrativo para renda.",
        "DY 12 meses": "Dividend Yield médio dos últimos 12 meses. Média histórica mais estável que o DY atual.",
        "Div. Médio 12m": "Média dos dividendos pagos nos últimos 12 meses. Indica previsibilidade de renda.",
        "Div. Total 12m": "Soma total dos dividendos pagos nos últimos 12 meses. Útil para projeção anual.",
        "Div. Último": "Valor do último dividendo pago. Útil para identificar tendência de aumento ou redução.",
        "Qtd. Div. 12m": "Quantidade de pagamentos de dividendos no ano. Mensal = 12, trimestral = 4, semestral = 2.",
        "Div. Médio 6a": "Média dos dividendos dos últimos 6 anos. Indica consistência histórica de pagamentos.",
        "Graham": "Preço Justo por Graham: √(22.5 × VPA × LPA). Fórmula clássica de Benjamin Graham para valor intrínseco.",
        "Graham BR": "Preço Justo Graham ajustado para Brasil. Considera peculiaridades do mercado brasileiro.",
        "Bazin": "Preço Justo por Bazin: Dividendo Médio / 0.06. Baseado em DY de 6% (teto de Bazin para compra).",
        "Lynch": "Preço Justo por Lynch: PEG Ratio. Relaciona crescimento com valuation. < 1 indica subvalorizada.",
        "AGF Médio": "Preço Justo Médio das 4 fórmulas (Graham, Graham_BR, Bazin, Lynch). Consenso de valuation.",
    }

    def tooltip_html(label_text):
        desc = TOOLTIP_DESC.get(label_text, "")
        if desc:
            return f'<span class="tooltip-container"><span class="tooltip-icon">?</span><span class="tooltip-text">{desc}</span></span>'
        return ""

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

    /* Tooltip customizado */
    .tooltip-container {
        position: relative;
        display: inline-block;
    }

    .tooltip-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #475569;
        color: #f1f5f9;
        font-size: 11px;
        font-weight: 700;
        cursor: help;
        margin-left: 6px;
        transition: all 0.2s ease;
    }

    .tooltip-icon:hover {
        background: #3b82f6;
    }

    .tooltip-text {
        visibility: hidden;
        width: 280px;
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #475569;
        color: #e2e8f0;
        text-align: left;
        border-radius: 10px;
        padding: 12px 14px;
        position: absolute;
        z-index: 1000;
        bottom: 125%;
        left: 50%;
        margin-left: -140px;
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.8rem;
        line-height: 1.4;
        box-shadow: 0 10px 15px rgba(0,0,0,0.3);
    }

    .tooltip-text::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #475569 transparent transparent transparent;
    }

    .tooltip-container:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
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
    # INFO DO ATIVO - SETOR/SUBSETOR/SEGMENTO
    # ============================================================
    st.markdown(f"""
    <div style="display: flex; gap: 24px; margin: 8px 0 16px 0; padding: 0;">
        <div>
            <span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Setor</span>
            <span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('Setor', 'N/A')}</span>
        </div>
        <div style="color: #475569;">›</div>
        <div>
            <span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">SubSetor</span>
            <span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('SubSetor', 'N/A')}</span>
        </div>
        <div style="color: #475569;">›</div>
        <div>
            <span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Segmento</span>
            <span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('Segmento', 'N/A')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 16px 0;'></div>", unsafe_allow_html=True)
    # ============================================================
    # WIDGET TRADINGVIEW DO ATIVO
    # ============================================================
    
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
        "height": "350",
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
      }}
      </script>
    </div>
    """
    components.html(tv_chart, height=360)

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
                    <div class="metric-label-v2">{label}{tooltip_html(label)}</div>
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
                    <div class="metric-label-v2">{label}{tooltip_html(label)}</div>
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
                    <div class="metric-label-v2">{label}{tooltip_html(label)}</div>
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
            <div class="metric-label-v2">{label}{tooltip_html(label)}</div>
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
            <div class="metric-label-v2">{label}{tooltip_html(label)}</div>
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
            <div class="metric-label-v2">{label}{tooltip_html(label)}</div>
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
    # 10. SCORE CS
    # ============================================================
    st.markdown('<div class="section-title-v2">🎯 SCORE CS</div>', unsafe_allow_html=True)
    
    # Critérios do Score CS
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


    score = int(ativo.get('Score_CS', 0))
    if score >= 9:
        score_color, score_bg, score_label = "#10b981", "#065f46", "Excelente"
    elif score >= 7:
        score_color, score_bg, score_label = "#84cc16", "#3f6212", "Bom"
    elif score >= 5:
        score_color, score_bg, score_label = "#f59e0b", "#92400e", "Regular"
    elif score >= 3:
        score_color, score_bg, score_label = "#f97316", "#7c2d12", "Fraco"
    else:
        score_color, score_bg, score_label = "#dc2626", "#7f1d1d", "Pessimo"

    # Card do Score
    # Card do Score centralizado
    score_cols = st.columns([2, 3, 2])
    with score_cols[1]:
        st.markdown(f"""
        <div class="score-card-v2" style="background: linear-gradient(135deg, {score_bg} 0%, {score_color}20 100%); border: 2px solid {score_color};">
            <div class="score-number-v2" style="color: {score_color};">{score}</div>
            <div class="score-label-v2" style="color: {score_color};">{score_label}</div>
            <div class="score-desc-v2">de 10 pontos</div>
        </div>
        """, unsafe_allow_html=True)



    # Cards dos critérios
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

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
    st.markdown('</div>', unsafe_allow_html=True)


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




def pagina_rankings():
    """Pagina de rankings completos - 5 abas, 50 ativos, cards estilizados."""
    st.markdown('<h1 class="main-header">🏆 Rankings</h1>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Dados nao disponiveis.")
        return

    # CSS dos cards de ranking
    st.markdown("""
    <style>
    .ranking-card {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 14px 10px;
        margin-bottom: 0.75rem;
        transition: all 0.3s ease;
        text-align: center;
        height: 100%;
    }
    .ranking-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        border-color: #3b82f6;
    }
    .ranking-ticker {
        font-size: 1.1rem;
        font-weight: 800;
        color: #f1f5f9;
        letter-spacing: 0.02em;
    }
    .ranking-nome {
        font-size: 0.72rem;
        color: #94a3b8;
        margin: 4px 0 8px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
    }
    .ranking-valor {
        font-size: 1.35rem;
        font-weight: 800;
        color: #38bdf8;
        margin: 6px 0;
        line-height: 1.1;
    }
    .ranking-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.68rem;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #334155;
    }
    .ranking-score {
        font-weight: 700;
    }
    .ranking-setor {
        color: #64748b;
        font-weight: 500;
    }
    .ranking-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    </style>
    """, unsafe_allow_html=True)

    # ============================================================
    # FILTROS
    # ============================================================
    setores = ["Todos"] + sorted([str(x) for x in df['Setor'].dropna().unique().tolist() if str(x) != 'nan'])
    subsetores = ["Todos"] + sorted([str(x) for x in df['SubSetor'].dropna().unique().tolist() if str(x) != 'nan'])

    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
    with col_f1:
        setor_sel = st.selectbox("📂 Setor", setores, key="rank_setor")
    with col_f2:
        subsetor_sel = st.selectbox("📁 SubSetor", subsetores, key="rank_subsetor")
    with col_f3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        ativos_count = len(df)
        st.markdown(f'<p style="color:#94a3b8; font-size:0.85rem; margin:0;">📊 {ativos_count} ativos carregados</p>', unsafe_allow_html=True)

    # Aplicar filtros
    df_filt = df.copy()
    if setor_sel != "Todos":
        df_filt = df_filt[df_filt['Setor'] == setor_sel]
    if subsetor_sel != "Todos":
        df_filt = df_filt[df_filt['SubSetor'] == subsetor_sel]

    if df_filt.empty:
        st.warning("Nenhum ativo encontrado com os filtros selecionados.")
        return

    # ============================================================
    # FUNCAO AUXILIAR PARA RENDERIZAR RANKING
    # ============================================================
    def render_ranking(df_rank, col_indicador, titulo, fmt_func, is_ascending=False, cor_valor="#38bdf8"):
        df_work = df_rank.copy()
        # Remover zeros/negativos para indicadores onde nao faz sentido
        if col_indicador in ['PL', 'PVP', 'EV_EBITDA', 'DivLiquida_EBITDA']:
            df_work = df_work[df_work[col_indicador] > 0]
        if col_indicador in ['DY', 'ROE', 'ROIC', 'MargemLiquida', 'CAGR_Lucros_5a', 'CAGR_Receitas_5a', 'Score_CS']:
            df_work = df_work[df_work[col_indicador].notna()]

        if df_work.empty:
            st.info(f"Dados insuficientes para {titulo}.")
            return

        if is_ascending:
            top = df_work.nsmallest(50, col_indicador)
        else:
            top = df_work.nlargest(50, col_indicador)

        st.markdown(f'<div class="section-title-v2">{titulo}</div>', unsafe_allow_html=True)

        items = []
        for _, row in top.iterrows():
            ticker = row['Ticker']
            nome = str(row.get('Nome', ticker))
            valor_raw = row.get(col_indicador, 0)
            valor = fmt_func(valor_raw)
            score = int(row.get('Score_CS', 0))
            setor = str(row.get('Setor', 'N/A'))

            # Cor do score
            if score >= 9: sc_color = "#10b981"
            elif score >= 7: sc_color = "#84cc16"
            elif score >= 5: sc_color = "#f59e0b"
            elif score >= 3: sc_color = "#f97316"
            else: sc_color = "#dc2626"

            # Badge do score
            if score >= 9: badge_bg, badge_text, badge_label = "#065f46", "#10b981", "Excelente"
            elif score >= 7: badge_bg, badge_text, badge_label = "#3f6212", "#84cc16", "Bom"
            elif score >= 5: badge_bg, badge_text, badge_label = "#92400e", "#f59e0b", "Regular"
            elif score >= 3: badge_bg, badge_text, badge_label = "#7c2d12", "#f97316", "Fraco"
            else: badge_bg, badge_text, badge_label = "#7f1d1d", "#dc2626", "Pessimo"

            items.append((ticker, nome, valor, score, sc_color, setor, badge_bg, badge_text, badge_label))

        # Renderizar 5 cards por linha (max 10 linhas = 50)
        total_items = len(items)
        for row_idx in range(10):
            cols = st.columns(5)
            for col_idx in range(5):
                idx = row_idx * 5 + col_idx
                if idx < total_items:
                    ticker, nome, valor, score, sc_color, setor, badge_bg, badge_text, badge_label = items[idx]
                    # Truncar nome
                    nome_curto = nome[:22] + "..." if len(nome) > 22 else nome
                    setor_curto = setor[:15] + "..." if len(setor) > 15 else setor

                    cols[col_idx].markdown(f"""
                    <div class="ranking-card">
                        <div class="ranking-ticker">{ticker}</div>
                        <div class="ranking-nome">{nome_curto}</div>
                        <div class="ranking-valor" style="color: {cor_valor};">{valor}</div>
                        <div style="margin-top:6px;">
                            <span class="ranking-badge" style="background:{badge_bg}40; color:{badge_text};">{badge_label}</span>
                        </div>
                        <div class="ranking-footer">
                            <span class="ranking-score" style="color:{sc_color};">● CS {score}</span>
                            <span class="ranking-setor">{setor_curto}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # ============================================================
    # ABAS
    # ============================================================
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏆 Destaque", "💰 Valuation", "📈 Crescimento", "🏛️ Tamanho", "🎖️ Score CS"])

    # ---------- ABA 1 - DESTAQUE ----------
    with tab1:
        render_ranking(df_filt, 'DY', '💰 Maiores Dividend Yield', lambda x: f"{x:.2f}%", cor_valor="#f59e0b")
        render_ranking(df_filt, 'PL', '📉 Menores P/L', lambda x: f"{x:.2f}x", is_ascending=True, cor_valor="#38bdf8")
        render_ranking(df_filt, 'ROE', '📈 Maiores ROE', lambda x: f"{x:.2f}%", cor_valor="#10b981")
        render_ranking(df_filt, 'Upside_AGF_Medio', '🎯 Maior Upside Medio', lambda x: f"{x:+.1f}%", cor_valor="#a78bfa")

    # ---------- ABA 2 - VALUATION ----------
    with tab2:
        render_ranking(df_filt, 'Upside_Graham', '📊 Mais Baratas — Graham', lambda x: f"{x:+.1f}%", cor_valor="#34d399")
        render_ranking(df_filt, 'Upside_Bazin', '💵 Mais Baratas — Bazin', lambda x: f"{x:+.1f}%", cor_valor="#fbbf24")
        render_ranking(df_filt, 'PVP', '📉 Menores P/VP', lambda x: f"{x:.2f}x", is_ascending=True, cor_valor="#38bdf8")
        render_ranking(df_filt, 'EV_EBITDA', '⚡ Menor EV/EBITDA', lambda x: f"{x:.2f}x", is_ascending=True, cor_valor="#60a5fa")

    # ---------- ABA 3 - CRESCIMENTO ----------
    with tab3:
        render_ranking(df_filt, 'CAGR_Lucros_5a', '🚀 Maior CAGR Lucros 5a', lambda x: f"{x:.2f}%", cor_valor="#10b981")
        render_ranking(df_filt, 'CAGR_Receitas_5a', '📊 Maior CAGR Receitas 5a', lambda x: f"{x:.2f}%", cor_valor="#34d399")
        render_ranking(df_filt, 'MargemLiquida', '💎 Maior Margem Liquida', lambda x: f"{x:.2f}%", cor_valor="#a78bfa")
        render_ranking(df_filt, 'DivLiquida_EBITDA', '🛡️ Menor Divida Liq/EBITDA', lambda x: f"{x:.2f}x", is_ascending=True, cor_valor="#f87171")

    # ---------- ABA 4 - TAMANHO ----------
    with tab4:
        render_ranking(df_filt, 'Market_Cap', '🏢 Maior Valor de Mercado', lambda x: f"R$ {x/1e9:.2f}B" if x >= 1e9 else f"R$ {x/1e6:.2f}M", cor_valor="#fbbf24")
        render_ranking(df_filt, 'Lucro_Liquido', '💰 Maiores Lucros', lambda x: f"R$ {x/1e9:.2f}B" if abs(x) >= 1e9 else f"R$ {x/1e6:.2f}M", cor_valor="#10b981")
        render_ranking(df_filt, 'Receita_Liquida', '📈 Maiores Receitas', lambda x: f"R$ {x/1e9:.2f}B" if x >= 1e9 else f"R$ {x/1e6:.2f}M", cor_valor="#38bdf8")

    # ---------- ABA 5 - SCORE CS ----------
    with tab5:
        df_score = df_filt[df_filt['Score_CS'].notna()]
        if not df_score.empty:
            top_score = df_score.nlargest(50, 'Score_CS')
            st.markdown('<div class="section-title-v2">🎖️ Top Score CS</div>', unsafe_allow_html=True)

            items = []
            for _, row in top_score.iterrows():
                ticker = row['Ticker']
                nome = str(row.get('Nome', ticker))
                score = int(row.get('Score_CS', 0))
                setor = str(row.get('Setor', 'N/A'))

                if score >= 9:
                    card_border, score_color, score_bg, score_label = "#10b981", "#10b981", "#065f46", "Excelente"
                elif score >= 7:
                    card_border, score_color, score_bg, score_label = "#84cc16", "#84cc16", "#3f6212", "Bom"
                elif score >= 5:
                    card_border, score_color, score_bg, score_label = "#f59e0b", "#f59e0b", "#92400e", "Regular"
                elif score >= 3:
                    card_border, score_color, score_bg, score_label = "#f97316", "#f97316", "#7c2d12", "Fraco"
                else:
                    card_border, score_color, score_bg, score_label = "#dc2626", "#dc2626", "#7f1d1d", "Pessimo"

                nome_curto = nome[:22] + "..." if len(nome) > 22 else nome
                setor_curto = setor[:15] + "..." if len(setor) > 15 else setor

                items.append((ticker, nome_curto, score, score_color, score_bg, score_label, setor_curto, card_border))

            for row_idx in range(10):
                cols = st.columns(5)
                for col_idx in range(5):
                    idx = row_idx * 5 + col_idx
                    if idx < len(items):
                        ticker, nome_curto, score, score_color, score_bg, score_label, setor_curto, card_border = items[idx]
                        cols[col_idx].markdown(f"""
                        <div class="ranking-card" style="border: 2px solid {card_border};">
                            <div class="ranking-ticker">{ticker}</div>
                            <div class="ranking-nome">{nome_curto}</div>
                            <div style="margin: 10px 0;">
                                <div style="font-size: 2.2rem; font-weight: 800; color: {score_color}; line-height: 1;">{score}</div>
                                <div style="font-size: 0.75rem; font-weight: 700; color: {score_color}; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px;">{score_label}</div>
                            </div>
                            <div class="ranking-footer">
                                <span style="color:#64748b; font-size:0.7rem; font-weight:600;">de 10</span>
                                <span class="ranking-setor">{setor_curto}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("Dados de Score CS nao disponiveis.")


def main():
    """Funcao principal."""
    st.sidebar.markdown("## 📈 SOBRAL Invest")
    st.sidebar.markdown("---")

    pagina = st.sidebar.radio(
        "Navegacao",
        ["🏠 Dashboard", "🔍 Analise", "🏆 Rankings", "📊 Comparativo", "⚙️ Configuracoes"],
        key="nav_radio_main"
    )

    if pagina == "🏠 Dashboard":
        pagina_inicial()
    elif pagina == "🔍 Analise":
        pagina_analise()
    elif pagina == "🏆 Rankings":
        pagina_rankings()
    elif pagina == "📊 Comparativo":
        pagina_comparativo()
    elif pagina == "⚙️ Configuracoes":
        pagina_configuracoes()


if __name__ == "__main__":
    main()
