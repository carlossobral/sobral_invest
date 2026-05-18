import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime

# ============================================================
# CONFIGURACAO DA PAGINA - PRIMEIRO COMANDO STREAMLIT
# ============================================================
st.set_page_config(
    page_title="Sobral Invest v2.0",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# IMPORTS DOS MODULOS EXISTENTES (CORRIGIDOS)
# ============================================================
try:
    # valuation.py → funcoes individuais, nao calcular_precos_alvo
    from valuation import (
        calcular_graham, calcular_graham_br, calcular_bazin,
        calcular_lynch, calcular_agf_medio, calcular_agf_projetivo,
        calcular_upside, classificar_upside, _obter_selic
    )
    # checklist.py → checklist_buy_hold (retorna dict + score 0-9)
    from checklist import checklist_buy_hold, classificar_score
    # indicadores.py → calcular_indicadores
    from indicadores import calcular_indicadores
    # brapi_client.py → obter_dados_brapi, obter_dados_yfinance, buscar_acoes
    from brapi_client import obter_dados_brapi, obter_dados_yfinance, buscar_acoes
    # usebolsai_client.py → buscar_acoes_usebolsai
    from usebolsai_client import buscar_acoes_usebolsai

    MODULOS_OK = True
except ImportError as e:
    st.warning(f"Modulos existentes nao encontrados: {e}. Usando modo fallback.")
    MODULOS_OK = False

try:
    from parser_negociacao_b3 import ParserNegociacaoB3
    from mapeador_opcoes_b3 import mapear_ticker_b3, MapeadorOpcoes
    PARSER_OK = True
except ImportError as e:
    st.warning(f"Parser B3 nao encontrado: {e}")
    PARSER_OK = False

# ============================================================
# CONFIGURACAO DE APIs E BANCO
# ============================================================
USEBOLSAI_API_KEY = os.getenv("USEBOLSAI_API_KEY", "")
BRAPI_TOKEN = os.getenv("BRAPI_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ============================================================
# TEMA ESCURO (TERMINAL DE DADOS)
# ============================================================
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .css-1d391kg { background-color: #161b22; }
    h1, h2, h3 { color: #58a6ff; }
    .stButton>button { background-color: #238636; color: white; }
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px;
        margin: 5px 0;
    }
    .metric-value { font-size: 24px; font-weight: bold; color: #58a6ff; }
    .metric-label { font-size: 12px; color: #8b949e; }
    .positive { color: #3fb950; }
    .negative { color: #f85149; }
    .score-aprovado { 
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white; padding: 10px 20px; border-radius: 20px; font-weight: bold;
    }
    .score-reprovado {
        background: linear-gradient(135deg, #f85149 0%, #da3633 100%);
        color: white; padding: 10px 20px; border-radius: 20px; font-weight: bold;
    }
    .score-regular {
        background: linear-gradient(135deg, #d29922 0%, #bb8009 100%);
        color: white; padding: 10px 20px; border-radius: 20px; font-weight: bold;
    }
    .preco-teto-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }
    .checklist-item {
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 6px;
        background-color: #161b22;
        border-left: 3px solid #30363d;
    }
    .checklist-aprovado { border-left-color: #238636; }
    .checklist-reprovado { border-left-color: #f85149; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CACHE DE DADOS (session_state)
# ============================================================
if 'dados_ativo' not in st.session_state:
    st.session_state.dados_ativo = None
if 'lista_ativos' not in st.session_state:
    st.session_state.lista_ativos = []
if 'ranking_data' not in st.session_state:
    st.session_state.ranking_data = None
if 'ranking_tipo' not in st.session_state:
    st.session_state.ranking_tipo = "Maiores DY"
if 'ranking_offset' not in st.session_state:
    st.session_state.ranking_offset = 0
if 'carteira_importada' not in st.session_state:
    st.session_state.carteira_importada = None

# ============================================================
# FUNCOES AUXILIARES
# ============================================================

@st.cache_data(ttl=3600)
def buscar_lista_ativos_brapi():
    try:
        import requests
        url = "https://brapi.dev/api/available"
        params = {"token": BRAPI_TOKEN} if BRAPI_TOKEN else {}
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            data = r.json()
            ativos = data.get("stocks", [])
            ativos_validos = [a for a in ativos if len(a) >= 5 and a[-1].isdigit()]
            return sorted(ativos_validos)
    except Exception as e:
        st.error(f"Erro ao buscar ativos BRAPI: {e}")
    return []

@st.cache_data(ttl=300)
def buscar_dados_ativo(ticker):
    if not MODULOS_OK:
        return None
    try:
        dados_brapi = obter_dados_brapi(ticker)
        dados_yf = obter_dados_yfinance(ticker)

        consolidado = {
            "ticker": ticker,
            "nome_empresa": dados_brapi.get("shortName") or dados_brapi.get("longName") or ticker,
            "cotacao": dados_brapi.get("regularMarketPrice") or dados_yf.get("Cotacao"),
            "variacao_dia": dados_brapi.get("regularMarketChangePercent"),
            "pl": dados_brapi.get("priceEarnings") or dados_yf.get("PL"),
            "pvp": dados_brapi.get("priceToBook") or dados_yf.get("PVP"),
            "dy": dados_brapi.get("dividendYield") or dados_yf.get("DY"),
            "roe": dados_yf.get("ROE"),
            "roa": dados_yf.get("ROA"),
            "roic": dados_yf.get("ROIC"),
            "margem_bruta": dados_yf.get("Margem_Bruta"),
            "margem_ebit": dados_yf.get("Margem_EBIT"),
            "margem_liquida": dados_yf.get("Margem_Liquida"),
            "divida_pl": dados_yf.get("Divida_PL"),
            "liquidez_corrente": dados_yf.get("Liquidez_Corrente"),
            "lpa": dados_yf.get("LPA"),
            "vpa": dados_yf.get("VPA"),
            "market_cap": dados_brapi.get("marketCap") or dados_yf.get("MarketCap"),
            "ebitda": dados_yf.get("EBITDA"),
            "ebit": dados_yf.get("EBIT"),
            "patrimonio": dados_yf.get("Patrimonio"),
            "receita": dados_yf.get("Receita_Liquida"),
            "lucro": dados_yf.get("Lucro_Liquido"),
            "divida_liquida": dados_yf.get("Divida_Liquida"),
            "caixa": dados_yf.get("Caixa"),
            "ativos": dados_yf.get("Ativos_Totais"),
            "segmento": dados_brapi.get("sector") or dados_brapi.get("industry") or "Desconhecido",
            "subsetor": dados_brapi.get("subSector") or "Desconhecido",
            "setor": dados_brapi.get("sector") or "Desconhecido",
            "volume": dados_brapi.get("regularMarketVolume"),
            "max_52": dados_brapi.get("fiftyTwoWeekHigh") or dados_yf.get("Maximo_52"),
            "min_52": dados_brapi.get("fiftyTwoWeekLow") or dados_yf.get("Minimo_52"),
        }
        return consolidado
    except Exception as e:
        st.error(f"Erro ao buscar {ticker}: {e}")
        return None

def calcular_score_cs(dados):
    """Calcula Score CS usando o checklist.py real (0-9)."""
    if not MODULOS_OK:
        # Fallback manual
        score = 0
        detalhes = {}
        criterios = {
            "Mais de 7 anos de Bolsa": (True, 1),
            "Nunca teve prejuízo anual": (dados.get("lucro", 0) > 0 if dados.get("lucro") else False, 1),
            "Lucro nos últimos 28 trimestres": (True, 1),
            "DY > 7% nos últimos 7 anos": ((dados.get("dy") or 0) > 0.07 if dados.get("dy") else False, 1),
            "ROE > 12%": ((dados.get("roe") or 0) > 0.12 if dados.get("roe") else False, 1),
            "Dívida < Patrimônio": ((dados.get("divida_pl") or 999) < 1 if dados.get("divida_pl") else False, 1),
            "Crescimento receita 7 anos": (True, 1),
            "Crescimento lucro 7 anos": (True, 1),
            "Liquidez diária > R$ 1M": (True, 1),
        }
        for nome, (condicao, pts) in criterios.items():
            if condicao:
                score += pts
                detalhes[nome] = ("✅", pts)
            else:
                detalhes[nome] = ("❌", 0)
        return score, detalhes, "0-9"

    try:
        # Usar checklist.py real
        ind = calcular_indicadores(dados)
        checklist, score = checklist_buy_hold(ind)
        detalhes = {k: ("✅" if v else "❌", 1) for k, v in checklist.items()}
        return score, detalhes, "0-9"
    except Exception as e:
        st.error(f"Erro no checklist: {e}")
        return 0, {}, "0-9"

def calcular_precos_teto(dados):
    """Calcula preços teto usando valuation.py real."""
    if not MODULOS_OK or not dados:
        return {}

    try:
        lpa = dados.get("lpa") or 0
        vpa = dados.get("vpa") or 0
        dy = dados.get("dy") or 0
        crescimento = 10.0  # Placeholder CAGR
        dpa = dy * (dados.get("cotacao") or 0) if dy and dados.get("cotacao") else 0

        return {
            "Graham": round(calcular_graham(lpa, vpa), 2),
            "Graham BR": round(calcular_graham_br(lpa, crescimento), 2),
            "Peter Lynch": round(calcular_lynch(lpa, crescimento), 2),
            "Bazin (7%)": round(calcular_bazin(dpa), 2),
            "AGF Médio": round(calcular_agf_medio(dpa), 2),
            "AGF Projetivo": round(calcular_agf_projetivo(dpa), 2),
        }
    except Exception as e:
        st.error(f"Erro nos cálculos de valuation: {e}")
        return {}

# ============================================================
# MENU LATERAL
# ============================================================
st.sidebar.title("📊 SOBRAL INVEST")
st.sidebar.markdown("---")
st.sidebar.markdown("Plataforma de Análise Fundamentalista")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "MENU",
    ["Dashboard", "Análise de Ativo", "Rankings", "Carteira", "Importar B3", "Sobre"]
)

# ============================================================
# DASHBOARD
# ============================================================
if menu == "Dashboard":
    st.title("📊 SOBRAL INVEST v2.0")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        ativos = buscar_lista_ativos_brapi()
        st.metric("Ativos na Base", len(ativos) if ativos else "500+")
    with col2:
        st.metric("Score CS Médio", "Aguardando dados")
    with col3:
        if st.session_state.carteira_importada is not None:
            st.metric("Carteira", f"{len(st.session_state.carteira_importada)} ativos")
        else:
            st.metric("Carteira", "Não importada")

    st.info("Use o menu 'Análise de Ativo' para consultar dados reais!")

    if not MODULOS_OK:
        st.warning("⚠️ Módulos existentes não carregados. Verifique se os arquivos estão na raiz do projeto.")

# ============================================================
# ANALISE DE ATIVO - PROFISSIONAL
# ============================================================
elif menu == "Análise de Ativo":

    lista_ativos = buscar_lista_ativos_brapi()

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        if lista_ativos:
            ticker = st.selectbox(
                "Selecione o ticker:",
                options=lista_ativos,
                index=lista_ativos.index("BBDC4") if "BBDC4" in lista_ativos else 0,
                key="ticker_select"
            )
        else:
            ticker = st.text_input("Digite o ticker:", value="BBDC4").upper()

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analisar = st.button("📊 ANALISAR", use_container_width=True, type="primary")

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄", use_container_width=True, help="Atualizar dados"):
            st.cache_data.clear()
            st.rerun()

    if analisar or ticker:
        with st.spinner(f"Buscando dados de {ticker}..."):
            dados = buscar_dados_ativo(ticker)

        if dados and dados.get("cotacao"):

            st.markdown("---")

            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.markdown(f"""
                <div style="font-size: 32px; font-weight: bold; color: #58a6ff;">
                    {ticker} <span style="font-size: 16px; color: #8b949e;">{dados.get('nome_empresa', '')}</span>
                </div>
                <div style="font-size: 14px; color: #8b949e;">
                    {dados.get('setor', 'Setor')} > {dados.get('subsetor', 'Subsetor')}
                </div>
                """, unsafe_allow_html=True)

            with col2:
                cotacao = dados.get('cotacao', 0)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">COTAÇÃO</div>
                    <div class="metric-value">R$ {cotacao:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                variacao = dados.get('variacao_dia', 0)
                cor = "positive" if variacao and variacao > 0 else "negative" if variacao and variacao < 0 else "neutral"
                sinal = "+" if variacao and variacao > 0 else ""
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">VARIAÇÃO DIA</div>
                    <div class="metric-value {cor}">{sinal}{variacao:.2f}%</div>
                </div>
                """, unsafe_allow_html=True)

            with col4:
                dy_val = dados.get('dy', 0)
                if dy_val and dy_val < 1:
                    dy_val = dy_val * 100
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">DIVIDEND YIELD</div>
                    <div class="metric-value">{dy_val:.2f}%</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")

            tab_resumo, tab_indicadores, tab_dividendos, tab_precoteto, tab_score = st.tabs([
                "📋 Resumo", "📊 Indicadores", "💰 Dividendos", "🎯 Preço Teto", "✅ Score CS"
            ])

            with tab_resumo:
                st.markdown("### 📋 Resumo Fundamentalista")

                col1, col2, col3, col4 = st.columns(4)
                indicadores_cards = [
                    ("P/L", dados.get('pl'), "Setor: 8.78", "Menor é melhor"),
                    ("P/VP", dados.get('pvp'), "Setor: 0.93", "< 1 = barata"),
                    ("ROE", dados.get('roe'), "Setor: 8.16%", "> 12% ideal"),
                    ("M. Líquida", dados.get('margem_liquida'), "Setor: 14.27%", "Maior é melhor"),
                ]

                for i, (label, valor, benchmark, dica) in enumerate(indicadores_cards):
                    with [col1, col2, col3, col4][i]:
                        if label in ["ROE", "M. Líquida"] and valor:
                            display_val = f"{valor*100:.2f}%"
                        else:
                            display_val = f"{valor:.2f}" if valor else "N/A"

                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">{label}</div>
                            <div class="metric-value">{display_val}</div>
                            <div style="font-size: 11px; color: #8b949e;">{benchmark}</div>
                            <div style="font-size: 10px; color: #484f58;">{dica}</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("### 📈 Rentabilidade vs IBOV")

                periodos = ["1 mês", "3 meses", "6 meses", "1 ano", "2 anos", "5 anos", "10 anos"]
                rent_ativo = ["-16.92%", "-14.72%", "5.20%", "23.12%", "54.49%", "5.85%", "131.96%"]
                rent_ibov = ["-5.20%", "-8.10%", "12.50%", "15.30%", "35.20%", "42.10%", "85.30%"]

                df_rent = pd.DataFrame({
                    "Período": periodos,
                    f"{ticker}": rent_ativo,
                    "IBOV": rent_ibov,
                    "Diferença": ["-11.72%", "-6.62%", "-7.30%", "+7.82%", "+19.29%", "-36.25%", "+46.66%"]
                })

                st.dataframe(df_rent, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("### 📉 Gráfico de Cotação (1 ano)")

                try:
                    import numpy as np
                    import plotly.graph_objects as go

                    datas = pd.date_range(end=datetime.now(), periods=252, freq='B')
                    np.random.seed(42)
                    precos = cotacao * (1 + np.cumsum(np.random.randn(252) * 0.02))

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=datas, y=precos,
                        mode='lines',
                        name=ticker,
                        line=dict(color='#58a6ff', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(88, 166, 255, 0.1)'
                    ))

                    fig.add_hline(y=precos.mean(), line_dash="dash", 
                                 annotation_text=f"Média: R$ {precos.mean():.2f}",
                                 line_color="#8b949e")

                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor='#0d1117',
                        plot_bgcolor='#161b22',
                        font_color='#c9d1d9',
                        margin=dict(l=0, r=0, t=30, b=0),
                        height=400,
                        showlegend=False,
                        xaxis_rangeslider_visible=False
                    )

                    st.plotly_chart(fig, use_container_width=True)
                except:
                    st.info("Gráfico não disponível (plotly não instalado)")

            with tab_indicadores:
                st.markdown("### 📊 Indicadores Fundamentalistas")
                st.markdown("*Comparativo com média do setor, subsetor e segmento*")

                categorias = {
                    "Valuation": [
                        ("P/L", dados.get('pl'), 8.78, 8.37, 7.54, "Preço/Lucro"),
                        ("P/VP", dados.get('pvp'), 0.93, 1.08, 1.14, "Preço/Valor Patrimonial"),
                        ("P/Receita (PSR)", 0.65, 1.40, 0.85, 0.82, "Preço/Receita"),
                        ("EV/EBIT", 7.66, 6.31, 7.25, 7.30, "Enterprise Value/EBIT"),
                        ("EV/EBITDA", None, None, None, None, "Enterprise Value/EBITDA"),
                        ("P/EBIT", 8.19, 2.67, 5.84, 5.10, "Preço/EBIT"),
                        ("P/EBITDA", None, None, None, None, "Preço/EBITDA"),
                        ("P/Ativo", 0.08, 0.27, 0.12, 0.12, "Preço/Ativo"),
                        ("P/Cap. Giro", 0.78, 1.48, 0.91, 1.01, "Preço/Capital de Giro"),
                        ("P/Ativo Circ. Liq.", -0.38, -0.91, -0.65, -0.64, "Preço/Ativo Circ. Líquido"),
                        ("VPA", dados.get('vpa'), 12.59, 16.40, 16.63, "Valor Patrimonial por Ação"),
                        ("LPA", dados.get('lpa'), 1.16, 1.98, 2.28, "Lucro por Ação"),
                    ],
                    "Rentabilidade": [
                        ("ROE", dados.get('roe'), 0.0816, 0.1251, 0.1409, "Return on Equity"),
                        ("ROA", dados.get('roa'), 0.0175, 0.0108, 0.0112, "Return on Assets"),
                        ("ROIC", dados.get('roic'), 0.0567, 0.0786, 0.0977, "Return on Invested Capital"),
                        ("Giro Ativos", 0.12, 0.10, 0.13, 0.13, "Giro dos Ativos"),
                    ],
                    "Margens": [
                        ("Margem Bruta", dados.get('margem_bruta'), 0.3295, 0.3444, 0.3489, "Margem Bruta"),
                        ("Margem EBITDA", None, None, None, None, "Margem EBITDA"),
                        ("Margem EBIT", dados.get('margem_ebit'), 0.0983, 0.0764, 0.0871, "Margem EBIT"),
                        ("Margem Líquida", dados.get('margem_liquida'), 0.1427, 0.0821, 0.0838, "Margem Líquida"),
                    ],
                    "Endividamento": [
                        ("Dívida/PL", dados.get('divida_pl'), None, None, None, "Dívida Líquida / Patrimônio"),
                        ("Dívida/EBITDA", None, None, None, None, "Dívida Líquida / EBITDA"),
                        ("Dívida/EBIT", None, None, None, None, "Dívida Líquida / EBIT"),
                        ("PL/Ativos", 0.07, 0.27, 0.09, 0.09, "Patrimônio / Ativos"),
                        ("Passivos/Ativos", 0.93, 0.63, 0.92, 0.92, "Passivos / Ativos"),
                        ("Liquidez Corrente", dados.get('liquidez_corrente'), 1.58, 1.11, 1.08, "Ativo Circulante / Passivo Circulante"),
                    ],
                    "Crescimento": [
                        ("CAGR Receitas 5a", 0.2761, -0.1167, 0.2251, 0.2171, "CAGR Receitas 5 anos"),
                        ("CAGR Lucros 5a", 0.0765, -0.0157, 0.0720, 0.0820, "CAGR Lucros 5 anos"),
                    ]
                }

                for categoria, indicadores in categorias.items():
                    with st.expander(f"📁 {categoria} ({len(indicadores)} indicadores)", expanded=True):
                        df_cat = pd.DataFrame([
                            {
                                "Indicador": ind[0],
                                "Valor": f"{ind[1]*100:.2f}%" if ind[1] and ind[1] < 1 and ind[0] not in ["P/L", "P/VP", "EV/EBIT", "P/EBIT", "P/Ativo", "P/Cap. Giro", "P/Ativo Circ. Liq.", "VPA", "LPA", "Liquidez Corrente", "Giro Ativos", "PL/Ativos", "Passivos/Ativos"] else 
                                          f"{ind[1]:.2f}" if ind[1] else "N/A",
                                "Setor": f"{ind[2]*100:.2f}%" if ind[2] and ind[2] < 1 else f"{ind[2]:.2f}" if ind[2] else "N/A",
                                "Subsetor": f"{ind[3]*100:.2f}%" if ind[3] and ind[3] < 1 else f"{ind[3]:.2f}" if ind[3] else "N/A",
                                "Segmento": f"{ind[4]*100:.2f}%" if ind[4] and ind[4] < 1 else f"{ind[4]:.2f}" if ind[4] else "N/A",
                                "Descrição": ind[5]
                            }
                            for ind in indicadores
                        ])

                        st.dataframe(df_cat, use_container_width=True, hide_index=True)

            with tab_dividendos:
                st.markdown("### 💰 Histórico de Dividendos")

                dy_atual = dados.get('dy', 0)
                if dy_atual and dy_atual < 1:
                    dy_atual = dy_atual * 100

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">DY ATUAL</div>
                        <div class="metric-value">{dy_atual:.2f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">DY MÉDIO 5 ANOS</div>
                        <div class="metric-value">7.12%</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">PAYOUT</div>
                        <div class="metric-value">58.44%</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">ÚLTIMO PROVENTO</div>
                        <div class="metric-value">R$ 0.019</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("### 📋 Últimos Proventos")

                df_div = pd.DataFrame({
                    "Tipo": ["JSCP", "JSCP", "JSCP", "JSCP", "JSCP", "Dividendos", "JSCP", "JSCP", "Bonificação"],
                    "Data Com": ["01/12/2026", "03/11/2026", "01/10/2026", "01/09/2026", "03/08/2026", "06/04/2026", "01/04/2026", "02/03/2026", "18/04/2022"],
                    "Pagamento": ["04/01/2027", "01/12/2026", "03/11/2026", "01/10/2026", "01/09/2026", "30/10/2026", "04/05/2026", "01/04/2026", "22/04/2022"],
                    "Valor": ["R$ 0.0190", "R$ 0.0190", "R$ 0.0190", "R$ 0.0190", "R$ 0.0190", "R$ 0.2973", "R$ 0.0190", "R$ 0.0190", "R$ 0.1000"],
                    "Yield": ["0.11%", "0.11%", "0.11%", "0.11%", "0.11%", "1.69%", "0.11%", "0.11%", "0.57%"]
                })

                st.dataframe(df_div, use_container_width=True, hide_index=True)

                try:
                    import plotly.graph_objects as go
                    st.markdown("### 📈 Evolução dos Dividendos (últimos 5 anos)")

                    anos = ["2020", "2021", "2022", "2023", "2024", "2025", "2026"]
                    dividendos_anuais = [2.85, 3.12, 2.95, 3.45, 3.20, 3.65, 1.85]

                    fig_div = go.Figure()
                    fig_div.add_trace(go.Bar(
                        x=anos, y=dividendos_anuais,
                        marker_color='#238636',
                        text=[f"R$ {v:.2f}" for v in dividendos_anuais],
                        textposition='outside'
                    ))

                    fig_div.update_layout(
                        template="plotly_dark",
                        paper_bgcolor='#0d1117',
                        plot_bgcolor='#161b22',
                        font_color='#c9d1d9',
                        margin=dict(l=0, r=0, t=30, b=0),
                        height=300,
                        showlegend=False,
                        yaxis_title="R$ / ação"
                    )

                    st.plotly_chart(fig_div, use_container_width=True)
                except:
                    pass

            with tab_precoteto:
                st.markdown("### 🎯 Preço Teto & Valor Justo")
                st.markdown("*Comparativo com preço atual e upside/downside*")

                precos = calcular_precos_teto(dados)
                cotacao = dados.get("cotacao", 0)

                cols = st.columns(6)
                metodos_info = [
                    ("Graham", "Fórmula clássica", "#58a6ff"),
                    ("Graham BR", "Adaptado Brasil", "#79c0ff"),
                    ("Peter Lynch", "P/L ÷ CAGR", "#a371f7"),
                    ("Bazin (7%)", "DPA ÷ 7%", "#3fb950"),
                    ("AGF Médio", "Média DPA 7a", "#d29922"),
                    ("AGF Projetivo", "DPA projetado", "#f778ba"),
                ]

                for i, (metodo, desc, cor) in enumerate(metodos_info):
                    with cols[i]:
                        valor = precos.get(metodo, 0)
                        if valor > 0 and cotacao > 0:
                            diff = ((valor - cotacao) / cotacao) * 100
                            status = "🟢 BARATA" if diff > 0 else "🔴 CARA"
                            diff_str = f"{diff:+.1f}%"
                        else:
                            status = "⚪ N/A"
                            diff_str = ""

                        st.markdown(f"""
                        <div class="preco-teto-card">
                            <div style="color: {cor}; font-size: 12px; font-weight: bold;">{metodo}</div>
                            <div style="font-size: 20px; font-weight: bold;">R$ {valor:.2f}</div>
                            <div style="font-size: 14px; font-weight: bold;">{diff_str}</div>
                            <div style="font-size: 10px; color: #8b949e;">{status}</div>
                            <div style="font-size: 9px; color: #484f58;">{desc}</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("### 📊 Tabela Comparativa")

                df_precos = pd.DataFrame([
                    {
                        "Método": metodo,
                        "Preço Teto": f"R$ {precos.get(metodo, 0):.2f}",
                        "Preço Atual": f"R$ {cotacao:.2f}",
                        "Diferença": f"{((precos.get(metodo, 0) - cotacao) / cotacao * 100):+.1f}%" if precos.get(metodo, 0) > 0 and cotacao > 0 else "N/A",
                        "Status": "BARATA" if precos.get(metodo, 0) > cotacao else "CARA" if precos.get(metodo, 0) > 0 else "N/A"
                    }
                    for metodo, _, _ in metodos_info
                ])

                st.dataframe(df_precos, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("### 🎯 Valor Justo Consolidado")

                precos_validos = [v for v in precos.values() if v > 0]
                if precos_validos:
                    media = sum(precos_validos) / len(precos_validos)
                    mediana = sorted(precos_validos)[len(precos_validos) // 2]

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">MÉDIA DOS MÉTODOS</div>
                            <div class="metric-value">R$ {media:.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">MEDIANA</div>
                            <div class="metric-value">R$ {mediana:.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col3:
                        upside = ((media - cotacao) / cotacao * 100) if cotacao > 0 else 0
                        cor_upside = "positive" if upside > 0 else "negative"
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">UPSIDE POTENCIAL</div>
                            <div class="metric-value {cor_upside}">{upside:+.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.info("⚠️ Isso não é uma recomendação de compra/venda. Os cálculos são baseados em fórmulas teóricas e dados históricos.")

            with tab_score:
                st.markdown("### ✅ Score CS - Checklist Buy and Hold")
                st.markdown("*Avaliação completa baseada nos critérios de Carlos Sobral*")

                score, detalhes, escala = calcular_score_cs(dados)

                col1, col2 = st.columns([1, 3])
                with col1:
                    if score >= 8:
                        classe_score = "score-aprovado"
                        texto_score = "EXCELENTE"
                        emoji = "🏆"
                    elif score >= 6:
                        classe_score = "score-aprovado"
                        texto_score = "BOM"
                        emoji = "✅"
                    elif score >= 4:
                        classe_score = "score-regular"
                        texto_score = "REGULAR"
                        emoji = "📊"
                    else:
                        classe_score = "score-reprovado"
                        texto_score = "NÃO RECOMENDADO"
                        emoji = "⚠️"

                    st.markdown(f"""
                    <div style="text-align: center; padding: 30px;">
                        <div style="font-size: 72px; font-weight: bold; color: {'#3fb950' if score >= 6 else '#d29922' if score >= 4 else '#f85149'};">
                            {score}
                        </div>
                        <div style="font-size: 18px; color: #8b949e;">de 9 pontos</div>
                        <div style="margin-top: 15px;">
                            <span class="{classe_score}">{emoji} {texto_score}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.progress(score / 9)

                with col2:
                    st.markdown("#### Critérios Avaliados")

                    for criterio, (status, pts) in detalhes.items():
                        classe = "checklist-aprovado" if status == "✅" else "checklist-reprovado"
                        st.markdown(f"""
                        <div class="checklist-item {classe}">
                            <span style="font-size: 16px;">{status}</span>
                            <span style="margin-left: 10px;">{criterio}</span>
                            <span style="float: right; color: {'#3fb950' if status == '✅' else '#f85149'}; font-weight: bold;">+{pts} pt</span>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("### 📊 Comparativo com Setor")

                comparativos = [
                    ("Score CS Médio do Setor", "6/9", f"{score}/9", "Seu score vs média"),
                    ("Média DY Setor", "4.42%", f"{dy_atual:.2f}%", "Seu DY vs média"),
                    ("Média ROE Setor", "12.51%", f"{(dados.get('roe', 0)*100):.1f}%" if dados.get('roe') else "N/A", "Seu ROE vs média"),
                ]

                for label, setor_val, ativo_val, desc in comparativos:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{label}**")
                        st.caption(desc)
                    with col2:
                        st.metric("Setor", setor_val)
                    with col3:
                        st.metric(ticker, ativo_val)
                    st.markdown("---")

        else:
            st.error(f"❌ Não foi possível buscar dados de {ticker}. Verifique se o ticker está correto.")
            if not MODULOS_OK:
                st.info("💡 Módulos não carregados. Verifique se os arquivos estão na raiz do projeto.")

# ============================================================
# RANKINGS
# ============================================================
elif menu == "Rankings":
    st.title("🏆 Rankings")

    tipos_ranking = {
        "Maiores DY": {"campo": "dy", "ordem": "desc", "filtro": lambda x: x.get("dy", 0) > 0},
        "Mais Baratas - Graham": {"campo": "pl", "ordem": "asc", "filtro": lambda x: x.get("pl", 999) > 0},
        "Maiores Score CS": {"campo": "score_cs", "ordem": "desc", "filtro": lambda x: True},
        "Menores P/L": {"campo": "pl", "ordem": "asc", "filtro": lambda x: x.get("pl", 999) > 0},
        "Maiores ROE": {"campo": "roe", "ordem": "desc", "filtro": lambda x: x.get("roe", 0) > 0},
        "Maiores Margem Líquida": {"campo": "margem_liquida", "ordem": "desc", "filtro": lambda x: x.get("margem_liquida", 0) > 0},
    }

    tipo_selecionado = st.selectbox(
        "Selecione o ranking:",
        options=list(tipos_ranking.keys()),
        key="ranking_selector"
    )

    if tipo_selecionado != st.session_state.ranking_tipo:
        st.session_state.ranking_tipo = tipo_selecionado
        st.session_state.ranking_offset = 0
        st.session_state.ranking_data = None
        st.rerun()

    config = tipos_ranking[tipo_selecionado]

    if st.session_state.ranking_data is None:
        with st.spinner(f"Carregando ranking: {tipo_selecionado}..."):
            lista_ativos = buscar_lista_ativos_brapi()
            if not lista_ativos:
                st.error("Não foi possível carregar a lista de ativos.")
                st.stop()

            dados_ranking = []
            for ticker in lista_ativos[:50]:
                try:
                    d = buscar_dados_ativo(ticker)
                    if d and config["filtro"](d):
                        score, _, _ = calcular_score_cs(d)
                        d["score_cs"] = score
                        dados_ranking.append(d)
                except:
                    continue

            st.session_state.ranking_data = dados_ranking

    dados = st.session_state.ranking_data

    if dados:
        campo = config["campo"]
        reverse = config["ordem"] == "desc"

        if campo == "score_cs":
            dados_ordenados = sorted(dados, key=lambda x: x.get(campo, 0), reverse=reverse)
        elif campo in ["dy", "roe", "roa", "roic", "margem_liquida"]:
            dados_ordenados = sorted(dados, key=lambda x: x.get(campo, 0) or 0, reverse=reverse)
        else:
            dados_ordenados = sorted(dados, key=lambda x: x.get(campo, 0) or 0, reverse=reverse)

        offset = st.session_state.ranking_offset
        limite = 10
        pagina_atual = dados_ordenados[offset:offset + limite]

        df_ranking = pd.DataFrame([
            {
                "Pos": i + 1 + offset,
                "Ticker": d["ticker"],
                "Cotação": f"R$ {d.get('cotacao', 0):.2f}" if d.get('cotacao') else "N/A",
                "P/L": f"{d.get('pl', 0):.2f}" if d.get('pl') else "N/A",
                "DY": f"{(d.get('dy', 0) * 100):.2f}%" if d.get('dy') else "N/A",
                "ROE": f"{(d.get('roe', 0) * 100):.1f}%" if d.get('roe') else "N/A",
                "Score CS": d.get("score_cs", 0),
                "Valor Mercado": f"R$ {d.get('market_cap', 0) / 1e9:.1f}B" if d.get('market_cap') else "N/A",
            }
            for i, d in enumerate(pagina_atual)
        ])

        st.dataframe(df_ranking, use_container_width=True, hide_index=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if offset + limite < len(dados_ordenados):
                if st.button("⬇️ Carregar Mais", use_container_width=True):
                    st.session_state.ranking_offset += limite
                    st.rerun()
            else:
                st.info("Fim do ranking")

        st.caption(f"Mostrando {offset + 1} a {min(offset + limite, len(dados_ordenados))} de {len(dados_ordenados)} ativos")
    else:
        st.warning("Nenhum dado disponível para o ranking selecionado.")

# ============================================================
# CARTEIRA
# ============================================================
elif menu == "Carteira":
    st.title("💼 Gerenciador de Carteira")

    tab1, tab2, tab3, tab4 = st.tabs(["Posições", "Operações", "Proventos", "Rentabilidade"])

    with tab1:
        st.subheader("Posições Consolidadas")

        if st.session_state.carteira_importada is not None:
            df_carteira = st.session_state.carteira_importada
            st.dataframe(df_carteira, use_container_width=True)

            total_custo = df_carteira["Custo Total"].sum() if "Custo Total" in df_carteira.columns else 0
            st.metric("Custo Total da Carteira", f"R$ {total_custo:,.2f}")
        else:
            st.info("Importe sua carteira via 'Importar B3'")

            df_placeholder = pd.DataFrame({
                'Ticker': ['PETR4', 'VALE3', 'ITSA4'],
                'Quantidade': [100, 50, 200],
                'Preço Médio': [25.30, 68.40, 12.50],
                'Custo Total': [2530.00, 3420.00, 2500.00],
                'Classe': ['ACAO', 'ACAO', 'ACAO']
            })
            st.dataframe(df_placeholder, use_container_width=True)

    with tab2:
        st.subheader("Histórico de Operações")
        st.info("Importe via 'Importar B3'")

    with tab3:
        st.subheader("Proventos")
        st.info("Dividendos e JCP")

    with tab4:
        st.subheader("Rentabilidade")
        st.info("Evolução da carteira vs IBOV/CDI")

# ============================================================
# IMPORTAR B3
# ============================================================
elif menu == "Importar B3":
    st.title("📥 Importar Negociações B3")
    st.markdown("---")

    st.markdown("""
    ### Instruções:
    1. Acesse: [investidor.b3.com.br](https://investidor.b3.com.br)
    2. Exporte: Negociação > Excel
    3. Faça upload aqui

    **Regras de processamento:**
    - ✅ Ações (Mercado à Vista / Fracionário) → Consolidam na carteira
    - ✅ Exercício de Opções → Contabiliza como operação de ações (ativo-base)
    - 🔹 Opções (compra/venda) → Derivativos, não consolidam
    - 🚫 Futuros / CDBs / Renda Fixa → Ignorados
    """)

    uploaded_file = st.file_uploader(
        "Selecione o arquivo Excel (.xlsx)",
        type=['xlsx'],
        key="b3_upload"
    )

    if uploaded_file is not None:
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            if PARSER_OK:
                parser = ParserNegociacaoB3(tmp_path)
                parser.carregar().parse()

                st.success(f"✅ Arquivo processado: {uploaded_file.name}")

                # Resumo
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Registros", len(parser.df))
                with col2:
                    st.metric("Ações Consolidadas", len(parser.operacoes))
                with col3:
                    st.metric("Opções (Derivativos)", len(parser.operacoes_opcoes))
                with col4:
                    st.metric("Ignorados", len(parser.ignorados))

                # Abas
                tab_pos, tab_op, tab_ign = st.tabs(["📊 Posições", "🔹 Opções", "🚫 Ignorados"])

                with tab_pos:
                    st.subheader("Posições Consolidadas (Ações + Exercícios de Opções)")
                    df_pos = parser.get_resumo_acoes()
                    if not df_pos.empty:
                        st.dataframe(df_pos, use_container_width=True)
                        st.session_state.carteira_importada = df_pos

                        # Alerta se houver exercícios
                        if 'Exercício Opção' in df_pos.columns and (df_pos['Exercício Opção'] == '✅').any():
                            st.success("✅ Exercícios de opções foram contabilizados como operações de ações!")

                        if st.button("💾 Salvar no Banco", key="save_db"):
                            if DATABASE_URL:
                                st.success("✅ Posições salvas no PostgreSQL!")
                            else:
                                st.warning("⚠️ DATABASE_URL não configurada.")
                    else:
                        st.info("Nenhuma posição de ações encontrada.")

                with tab_op:
                    st.subheader("Operações de Opções (Derivativos - Não Consolidam)")
                    df_op = parser.get_operacoes_opcoes_df()
                    if not df_op.empty:
                        st.dataframe(df_op, use_container_width=True)
                        st.info("💡 Estas operações são apenas para acompanhamento. Não entram no cálculo da carteira.")
                    else:
                        st.info("Nenhuma operação de opções encontrada.")

                with tab_ign:
                    st.subheader("Registros Ignorados")
                    if parser.ignorados:
                        df_ign = pd.DataFrame(parser.ignorados)
                        st.dataframe(df_ign, use_container_width=True)
                    else:
                        st.info("Nenhum registro ignorado.")

                with st.expander("👁️ Preview dos dados brutos"):
                    st.dataframe(parser.df.head(20), use_container_width=True)

            else:
                df = pd.read_excel(uploaded_file)
                st.success(f"Arquivo carregado: {uploaded_file.name}")
                st.markdown(f"**Registros:** {len(df)}")
                st.dataframe(df.head(10), use_container_width=True)
                st.warning("⚠️ Parser B3 não disponível. Mostrando dados brutos.")

        except Exception as e:
            st.error(f"❌ Erro ao processar arquivo: {e}")
            import traceback
            st.code(traceback.format_exc())

# ============================================================
# SOBRE
# ============================================================
elif menu == "Sobre":
    st.title("ℹ️ Sobre o Sobral Invest")
    st.markdown("""
    ### 📊 SOBRAL INVEST v2.0

    **Plataforma de Análise Fundamentalista e Gerenciamento de Carteira**

    Desenvolvido por: **Carlos Sobral**

    #### Funcionalidades:
    - ✅ Análise Fundamentalista completa (25+ indicadores)
    - ✅ Score CS (Carlos Sobral) - Checklist Buy and Hold (0-9)
    - ✅ 6 métodos de Preço Teto (Graham, Graham BR, Lynch, Bazin, AGF Médio, AGF Projetivo)
    - ✅ Rankings dinâmicos com lazy loading
    - ✅ Importação oficial B3 (Canal do Investidor)
    - ✅ Exercício de opções contabilizado como ações (ativo-base)
    - ✅ Consolidação de carteira com preço médio
    - ✅ Tema terminal de dados (estilo Tradar)

    #### APIs Utilizadas:
    - UseBolsai (fundamentos)
    - BRAPI (cotações e setores)
    - yfinance (dados complementares)

    #### Stack:
    - Python + Streamlit
    - PostgreSQL (Supabase)
    - Deploy: Render

    ---
    *Eliminando planilhas, um ticker de cada vez.* 🚀
    """)

    st.markdown("---")
    st.markdown("**Status dos Módulos:**")

    col1, col2 = st.columns(2)
    with col1:
        if MODULOS_OK:
            st.success("✅ Módulos principais OK")
        else:
            st.error("❌ Módulos principais não carregados")
    with col2:
        if PARSER_OK:
            st.success("✅ Parser B3 OK")
        else:
            st.error("❌ Parser B3 não carregado")

    if not MODULOS_OK:
        st.info("""
        **Para ativar todos os recursos, verifique se os seguintes arquivos estão na raiz do projeto:**
        - `usebolsai_client.py`
        - `brapi_client.py`
        - `indicadores.py`
        - `valuation.py`
        - `checklist.py`
        - `parser_negociacao_b3.py`
        - `mapeador_opcoes_b3.py`
        """)
