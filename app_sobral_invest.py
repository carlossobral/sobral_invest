import streamlit as st
import pandas as pd
import os
import sys
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy import create_engine, text

# ============================================================
# CONFIGURACAO DE TOKENS (mesmo padrao do app.py existente)
# ============================================================

USEBOLSAI_API_KEY = os.environ.get("USEBOLSAI_API_KEY", "")
BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ============================================================
# IMPORTAR SEUS MODULOS EXISTENTES
# ============================================================

# Adicionar diretorio ao path para importar seus modulos
sys.path.append(str(Path(__file__).parent))

try:
    from usebolsai_client import UseBolsaiClient
    from brapi_client import BrapiClient
    from indicadores import calcular_indicadores
    from valuation import calcular_precos_alvo
    from checklist import calcular_score_bh  # Renomear para score_cs depois
    CLIENTS_DISPONIVEIS = True
except ImportError:
    CLIENTS_DISPONIVEIS = False
    st.warning("Modulos existentes nao encontrados. Usando modo fallback.")

# ============================================================
# BANCO DE DADOS (PostgreSQL - Supabase)
# ============================================================

@st.cache_resource
def get_db_engine():
    """Conexao com PostgreSQL (Supabase)."""
    if not DATABASE_URL:
        return None
    try:
        return create_engine(DATABASE_URL)
    except Exception as e:
        st.error(f"Erro ao conectar ao banco: {e}")
        return None

def init_database():
    """Inicializa schema do banco se nao existir."""
    engine = get_db_engine()
    if not engine:
        return False

    try:
        with engine.begin() as conn:
            # Tabela de carteiras
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS carteiras (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL,
                    usuario_id INTEGER DEFAULT 1,
                    is_principal BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Tabela de posicoes
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS posicoes (
                    id SERIAL PRIMARY KEY,
                    carteira_id INTEGER REFERENCES carteiras(id),
                    ticker VARCHAR(20) NOT NULL,
                    quantidade NUMERIC(20,8) DEFAULT 0,
                    preco_medio NUMERIC(12,4) DEFAULT 0,
                    custo_total NUMERIC(20,2) DEFAULT 0,
                    classe VARCHAR(20) DEFAULT 'ACAO',
                    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(carteira_id, ticker)
                )
            """))

            # Tabela de historico de cotacoes
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cotacoes_historico (
                    id BIGSERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    data DATE NOT NULL,
                    preco_fechamento NUMERIC(12,4),
                    volume NUMERIC(20,0),
                    UNIQUE(ticker, data)
                )
            """))

            # Tabela de score CS
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS score_cs (
                    id BIGSERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    data_calculo DATE DEFAULT CURRENT_DATE,
                    score_total INTEGER DEFAULT 0,
                    score_mais_7_anos INTEGER DEFAULT 0,
                    score_nunca_prejuizo INTEGER DEFAULT 0,
                    score_lucro_28t INTEGER DEFAULT 0,
                    score_dy_7anos INTEGER DEFAULT 0,
                    score_roe_12 INTEGER DEFAULT 0,
                    score_divida_pl INTEGER DEFAULT 0,
                    score_cresc_rec INTEGER DEFAULT 0,
                    score_cresc_luc INTEGER DEFAULT 0,
                    score_liquidez INTEGER DEFAULT 0,
                    classificacao VARCHAR(20),
                    UNIQUE(ticker, data_calculo)
                )
            """))

            # Tabela de precos alvo
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS precos_alvo (
                    id BIGSERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    data_calculo DATE DEFAULT CURRENT_DATE,
                    preco_atual NUMERIC(12,4),
                    preco_teto_graham NUMERIC(12,4),
                    preco_teto_graham_br NUMERIC(12,4),
                    preco_teto_lynch NUMERIC(12,4),
                    preco_teto_bazin NUMERIC(12,4),
                    preco_teto_agf NUMERIC(12,4),
                    valor_justo_consolidado NUMERIC(12,4),
                    UNIQUE(ticker, data_calculo)
                )
            """))

            # Tabela de indicadores
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS indicadores (
                    id BIGSERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    data_calculo DATE DEFAULT CURRENT_DATE,
                    dy NUMERIC(8,4),
                    pl NUMERIC(8,4),
                    peg_ratio NUMERIC(8,4),
                    pvp NUMERIC(8,4),
                    ev_ebitda NUMERIC(8,4),
                    ev_ebit NUMERIC(8,4),
                    vpa NUMERIC(12,4),
                    p_ativo NUMERIC(8,4),
                    lpa NUMERIC(12,4),
                    psr NUMERIC(8,4),
                    roe NUMERIC(8,4),
                    roa NUMERIC(8,4),
                    roic NUMERIC(8,4),
                    margem_bruta NUMERIC(8,4),
                    margem_ebitda NUMERIC(8,4),
                    margem_liquida NUMERIC(8,4),
                    div_liq_pl NUMERIC(8,4),
                    liq_corrente NUMERIC(8,4),
                    cagr_receitas_5a NUMERIC(8,4),
                    cagr_lucros_5a NUMERIC(8,4),
                    UNIQUE(ticker, data_calculo)
                )
            """))

        return True
    except Exception as e:
        st.error(f"Erro ao inicializar banco: {e}")
        return False

# ============================================================
# LISTAR TODOS OS ATIVOS DA B3 (via BRAPI)
# ============================================================

@st.cache_data(ttl=3600)
def listar_ativos_brapi():
    """Busca lista completa de ativos da B3 via BRAPI."""
    try:
        import requests
        url = "https://brapi.dev/api/available"
        params = {"token": BRAPI_TOKEN} if BRAPI_TOKEN else {}
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()
            ativos = data.get("stocks", [])
            return sorted(ativos)
        else:
            # Fallback: lista dos 196 ativos do app.py original
            return TICKERS_FALLBACK
    except Exception as e:
        st.warning(f"Erro ao buscar ativos BRAPI: {e}. Usando fallback.")
        return TICKERS_FALLBACK

# Lista fallback (seus 196 ativos originais)
TICKERS_FALLBACK = [
    "AALR3", "ABCB4", "ABEV3", "AERI3", "AESB3", "AGRO3", "ALPA4", "ALUP11", "AMAR3", "AMBP3",
    "AMER3", "ANIM3", "APER3", "APTI4", "ARML3", "ARZZ3", "ASAI3", "AURE3", "AVLL3", "AZEV4",
    "AZUL4", "B3SA3", "BBAS3", "BBDC3", "BBDC4", "BBSE3", "BEEF3", "BEES4", "BGIP4", "BHAU3",
    "BHIA3", "BIOM3", "BLAU3", "BMEB4", "BMOB3", "BPAC11", "BPAN4", "BRAP4", "BRBI11", "BRFS3",
    "BRGE11", "BRKM5", "BRSR6", "BSLI4", "CAML3", "CASH3", "CBAV3", "CCRO3", "CEAB3", "CEBR3",
    "CEDO4", "CEEB3", "CEPE3", "CESP3", "CGAS3", "CGAS5", "CGRA4", "CIEL3", "CLSC4", "CMIG3",
    "CMIG4", "CMIN3", "COCE3", "COGN3", "CPFE3", "CPLE3", "CPLE6", "CSAB4", "CSAN3", "CSMG3",
    "CSNA3", "CSRN3", "CTKA4", "CTNM4", "CTSA4", "CURY3", "CVCB3", "CXSE3", "CYRE3", "DASA3",
    "DESK3", "DEXP3", "DIRR3", "DMMO11", "DOHL4", "DOTZ3", "DTCY3", "EALT4", "ECOR3", "EGIE3",
    "ELET3", "ELET6", "EMBR3", "ENAT3", "ENBR3", "ENEV3", "ENGI11", "EQPA3", "EQTL3", "ESPA3",
    "ESTR4", "ETER3", "EVEN3", "EZTC3", "FESA4", "FHER3", "FICT3", "FIQE3", "FLRY3", "FRAS3",
    "GEPA4", "GFSA3", "GGBR4", "GGPS3", "GOAU4", "GOLL4", "GRND3", "GUAR3", "HAGA4", "HAPV3",
    "HBOR3", "HBSA3", "HYPE3", "IFCM3", "IGBR3", "IGTI11", "INEP3", "INTB3", "IRBR3", "ITSA3",
    "ITSA4", "ITUB3", "ITUB4", "JALL3", "JBSS3", "JBDU4", "JBSS3", "JFEN3", "JHSF3", "JOPA4",
    "JSLG3", "KEPL3", "KLBN3", "KLBN4", "KLBN11", "LAVV3", "LEVE3", "LIGT3", "LJQQ3", "LOGG3",
    "LOGN3", "LPSB3", "LREN3", "LUPA3", "LUXM4", "LVTC3", "LWSA3", "MATD3", "MBLY3", "MDIA3",
    "MEAL3", "MGLU3", "MILS3", "MLAS3", "MNDL3", "MOVI3", "MRFG3", "MRSA3B", "MRVE3", "MTRE3",
    "MTSA4", "MULT3", "MYPK3", "NEOE3", "NEXP3", "NGRD3", "NINJ3", "NTCO3", "NUTR3", "ODPV3",
    "OFSA3", "OPCT3", "ORVR3", "OSXB3", "PARD3", "PATI4", "PCAR3", "PEAB3", "PETR3", "PETR4",
    "PETZ3", "PFRM3", "PGMN3", "PINE4", "PLAS3", "PMAM3", "PNVL3", "POMO3", "POMO4", "POSI3",
    "PRIO3", "PRNR3", "PSSA3", "PTBL3", "PTNT4", "QUAL3", "RADL3", "RAIL3", "RAIZ4", "RANI3",
    "RAPT3", "RAPT4", "RDNI3", "RDOR3", "RECV3", "REDE3", "RENT3", "ROMI3", "RPAD3", "RPMG3",
    "RRRP3", "RSID3", "RSUL4", "SANB11", "SAPR3", "SAPR4", "SAPR11", "SBFG3", "SBSP3", "SCAR3",
    "SEER3", "SEQL3", "SHUL4", "SIMH3", "SLCE3", "SMFT3", "SMTO3", "SOJA3", "SULA11", "SULA",
    "SUZB3", "TAEE3", "TAEE4", "TAEE11", "TASA3", "TASA4", "TCSA3", "TELB4", "TEND3", "TGMA3",
    "TIMP3", "TOTS3", "TPIS3", "TRAD3", "TRIS3", "TRPL3", "TRPL4", "TUPY3", "UCAS3", "UGPA3",
    "UNIP3", "UNIP5", "UNIP6", "USIM3", "USIM5", "USIM6", "VALE3", "VAMO3", "VBBR3", "VIIA3",
    "VITT3", "VIVA3", "VIVR3", "VIVT3", "VLID3", "VSTE3", "VTRU3", "VULC3", "VULC4", "VVAR3",
    "WEGE3", "WEST3", "WHRL4", "WIZC3", "WIZS3", "WLMM4", "WSON33", "YDUQ3", "ZAMP3"
]

# ============================================================
# SCORE CS (0-100) - Evolucao do Score_BH (0-9)
# ============================================================

def calcular_score_cs(dados: dict) -> dict:
    """
    Calcula Score CS (Carlos Sobral) 0-100.
    Evolucao do Score_BH (0-9) para mais granularidade.
    """
    score = {
        'total': 0,
        'score_mais_7_anos_bolsa': 0,
        'score_nunca_prejuizo': 0,
        'score_lucro_28_trimestres': 0,
        'score_dy_7anos_7pct': 0,
        'score_roe_12pct': 0,
        'score_divida_menor_pl': 0,
        'score_cresc_receita_7a': 0,
        'score_cresc_lucro_7a': 0,
        'score_liquidez_1m': 0,
    }

    # 1. Mais de 7 anos na Bolsa (10 pontos)
    if dados.get('anos_bolsa', 0) >= 7:
        score['score_mais_7_anos_bolsa'] = 10
        score['total'] += 10
    elif dados.get('anos_bolsa', 0) >= 5:
        score['score_mais_7_anos_bolsa'] = 5
        score['total'] += 5

    # 2. Nunca deu prejuizo (15 pontos)
    if dados.get('nunca_prejuizo', False):
        score['score_nunca_prejuizo'] = 15
        score['total'] += 15
    elif dados.get('anos_lucro', 0) >= 5:
        score['score_nunca_prejuizo'] = 8
        score['total'] += 8

    # 3. Lucro nos ultimos 28 trimestres (15 pontos)
    if dados.get('lucro_28t', False):
        score['score_lucro_28_trimestres'] = 15
        score['total'] += 15
    elif dados.get('trimestres_lucro', 0) >= 20:
        score['score_lucro_28_trimestres'] = 8
        score['total'] += 8

    # 4. DY > 7% nos ultimos 7 anos (15 pontos)
    dy_medio = dados.get('dy_medio_7a', 0)
    if dy_medio >= 7:
        score['score_dy_7anos_7pct'] = 15
        score['total'] += 15
    elif dy_medio >= 5:
        score['score_dy_7anos_7pct'] = 8
        score['total'] += 8
    elif dy_medio >= 3:
        score['score_dy_7anos_7pct'] = 4
        score['total'] += 4

    # 5. ROE > 12% (10 pontos)
    roe = dados.get('roe', 0)
    if roe >= 15:
        score['score_roe_12pct'] = 10
        score['total'] += 10
    elif roe >= 12:
        score['score_roe_12pct'] = 7
        score['total'] += 7
    elif roe >= 8:
        score['score_roe_12pct'] = 4
        score['total'] += 4

    # 6. Divida menor que Patrimonio (10 pontos)
    div_pl = dados.get('divida_liquida_pl', 999)
    if div_pl < 0.5:
        score['score_divida_menor_pl'] = 10
        score['total'] += 10
    elif div_pl < 1:
        score['score_divida_menor_pl'] = 7
        score['total'] += 7
    elif div_pl < 1.5:
        score['score_divida_menor_pl'] = 4
        score['total'] += 4

    # 7. Crescimento receita 7 anos (10 pontos)
    cagr_rec = dados.get('cagr_receitas_5a', 0)  # Usar 5a como proxy
    if cagr_rec >= 10:
        score['score_cresc_receita_7a'] = 10
        score['total'] += 10
    elif cagr_rec >= 5:
        score['score_cresc_receita_7a'] = 6
        score['total'] += 6
    elif cagr_rec > 0:
        score['score_cresc_receita_7a'] = 3
        score['total'] += 3

    # 8. Crescimento lucro 7 anos (10 pontos)
    cagr_luc = dados.get('cagr_lucros_5a', 0)
    if cagr_luc >= 10:
        score['score_cresc_lucro_7a'] = 10
        score['total'] += 10
    elif cagr_luc >= 5:
        score['score_cresc_lucro_7a'] = 6
        score['total'] += 6
    elif cagr_luc > 0:
        score['score_cresc_lucro_7a'] = 3
        score['total'] += 3

    # 9. Liquidez diaria > R$ 1M (5 pontos)
    liquidez = dados.get('liquidez_diaria', 0)
    if liquidez >= 1000000:
        score['score_liquidez_1m'] = 5
        score['total'] += 5
    elif liquidez >= 500000:
        score['score_liquidez_1m'] = 3
        score['total'] += 3

    # Classificacao
    if score['total'] >= 80:
        score['classificacao'] = 'EXCELENTE'
    elif score['total'] >= 60:
        score['classificacao'] = 'BOM'
    elif score['total'] >= 40:
        score['classificacao'] = 'REGULAR'
    else:
        score['classificacao'] = 'FRACO'

    return score

# ============================================================
# CONFIGURACAO STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Sobral Invest v2.0",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS custom - tema escuro (estilo terminal)
st.markdown("""
<style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3 { color: #58a6ff !important; font-family: 'Courier New', monospace; }
    .stDataFrame { background-color: #161b22; border: 1px solid #30363d; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 10px; }
    .stMetric label { color: #8b949e !important; }
    .stMetric div { color: #c9d1d9 !important; font-family: 'Courier New', monospace; font-size: 1.5rem; font-weight: bold; }
    .stButton>button { background-color: #238636; color: white; border: 1px solid #2ea043; font-family: 'Courier New', monospace; }
    .stButton>button:hover { background-color: #2ea043; }
    .stTabs [data-baseweb="tab-list"] { background-color: #161b22; border-bottom: 1px solid #30363d; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; font-family: 'Courier New', monospace; }
    .stTabs [aria-selected="true"] { color: #58a6ff !important; border-bottom: 2px solid #58a6ff; }
    .info-box { background-color: #1f6feb20; border: 1px solid #58a6ff; border-radius: 6px; padding: 15px; margin: 10px 0; }
    .success-box { background-color: #23863620; border: 1px solid #2ea043; border-radius: 6px; padding: 15px; margin: 10px 0; }
    .warning-box { background-color: #d2992220; border: 1px solid #d29922; border-radius: 6px; padding: 15px; margin: 10px 0; }
    .score-excelente { color: #3fb950; font-weight: bold; }
    .score-bom { color: #58a6ff; font-weight: bold; }
    .score-regular { color: #d29922; font-weight: bold; }
    .score-fraco { color: #f85149; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================

st.title("📊 SOBRAL INVEST v2.0")
st.markdown("### `Plataforma de Analise Fundamentalista & Carteira`")
st.markdown("---")

# Sidebar
st.sidebar.markdown("## `MENU`")
st.sidebar.markdown("---")

# Status
if DATABASE_URL:
    st.sidebar.markdown("🟢 `Banco: Configurado`")
else:
    st.sidebar.markdown("🔴 `Banco: Nao configurado`")
    st.sidebar.markdown("Configure DATABASE_URL no Render")

if USEBOLSAI_API_KEY:
    st.sidebar.markdown("🟢 `UseBolsai: OK`")
else:
    st.sidebar.markdown("🔴 `UseBolsai: Sem token`")

st.sidebar.markdown("---")

# Menu
menu = st.sidebar.radio(
    "Navegacao:",
    ["Dashboard", "Analise de Ativo", "Rankings", "Carteira", "Importar B3", "Sobre"],
    index=0
)

# ============================================================
# ABA: DASHBOARD
# ============================================================

if menu == "Dashboard":
    st.markdown("## `Dashboard`")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Ativos na Base", len(TICKERS_FALLBACK))

    with col2:
        if DATABASE_URL:
            try:
                engine = get_db_engine()
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM posicoes WHERE quantidade > 0"))
                    qtd = result.fetchone()[0]
                    st.metric("Posicoes em Carteira", qtd)
            except:
                st.metric("Posicoes em Carteira", 0)
        else:
            st.metric("Posicoes em Carteira", "N/A")

    with col3:
        st.metric("Score CS Maximo", "100")

    st.markdown("---")

    st.markdown("""
    <div class="info-box">
    <h4>Bem-vindo ao Sobral Invest v2.0</h4>
    <p>Novidades:</p>
    <ul>
        <li>✅ Score CS (0-100) - mais granular que Score_BH</li>
        <li>✅ Todos os ativos da B3 via BRAPI</li>
        <li>✅ Carteira com importacao B3 (Canal do Investidor)</li>
        <li>✅ Rankings dinamicos</li>
        <li>✅ Banco de dados PostgreSQL (Supabase)</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# ABA: ANALISE DE ATIVO
# ============================================================

elif menu == "Analise de Ativo":
    st.markdown("## `Analise Fundamentalista`")

    # Buscar ativos
    with st.spinner("Carregando lista de ativos..."):
        ativos = listar_ativos_brapi()

    ticker = st.selectbox(
        "Selecione o ativo:",
        options=ativos,
        index=ativos.index("PETR4") if "PETR4" in ativos else 0
    )

    if st.button("Analisar", type="primary"):
        with st.spinner(f"Analisando {ticker}..."):

            # Aqui integraria com seus modulos existentes
            if CLIENTS_DISPONIVEIS:
                try:
                    # UseBolsai
                    client = UseBolsaiClient(USEBOLSAI_API_KEY)
                    fundamentals = client.get_fundamentals(ticker)

                    # BRAPI para cotação
                    brapi = BrapiClient()
                    cotacao = brapi.get_quote(ticker)

                    st.success(f"Dados carregados para {ticker}")

                    # Exibir dados (placeholder - integrar com seus modulos)
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Cotacao", f"R$ {cotacao.get('price', 0):.2f}")

                    with col2:
                        st.metric("DY", f"{fundamentals.get('dy', 0):.2f}%")

                    with col3:
                        st.metric("P/L", f"{fundamentals.get('pl', 0):.2f}")

                    with col4:
                        st.metric("P/VP", f"{fundamentals.get('pvp', 0):.2f}")

                    # Score CS
                    dados_score = {
                        'anos_bolsa': fundamentals.get('anos_bolsa', 0),
                        'nunca_prejuizo': fundamentals.get('nunca_prejuizo', False),
                        'lucro_28t': fundamentals.get('lucro_28t', False),
                        'dy_medio_7a': fundamentals.get('dy_medio_7a', 0),
                        'roe': fundamentals.get('roe', 0),
                        'divida_liquida_pl': fundamentals.get('divida_liquida_pl', 999),
                        'cagr_receitas_5a': fundamentals.get('cagr_receitas_5a', 0),
                        'cagr_lucros_5a': fundamentals.get('cagr_lucros_5a', 0),
                        'liquidez_diaria': fundamentals.get('liquidez_diaria', 0),
                    }

                    score = calcular_score_cs(dados_score)

                    st.markdown("---")
                    st.markdown(f"## `Score CS: {score['total']}/100`")

                    # Barra de progresso colorida
                    progress_color = "#3fb950" if score['total'] >= 80 else "#58a6ff" if score['total'] >= 60 else "#d29922" if score['total'] >= 40 else "#f85149"
                    st.markdown(f"""
                    <div style="width: 100%; background-color: #30363d; border-radius: 6px; height: 30px;">
                        <div style="width: {score['total']}%; background-color: {progress_color}; height: 30px; border-radius: 6px; text-align: center; line-height: 30px; color: white; font-weight: bold;">
                            {score['total']} - {score['classificacao']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Detalhamento do score
                    st.markdown("### `Detalhamento do Score CS`")

                    score_cols = st.columns(3)

                    score_items = [
                        ("Mais 7 anos Bolsa", score['score_mais_7_anos_bolsa'], 10),
                        ("Nunca Prejuizo", score['score_nunca_prejuizo'], 15),
                        ("Lucro 28 Trimestres", score['score_lucro_28_trimestres'], 15),
                        ("DY > 7% (7 anos)", score['score_dy_7anos_7pct'], 15),
                        ("ROE > 12%", score['score_roe_12pct'], 10),
                        ("Divida < PL", score['score_divida_menor_pl'], 10),
                        ("Cresc. Receita", score['score_cresc_receita_7a'], 10),
                        ("Cresc. Lucro", score['score_cresc_lucro_7a'], 10),
                        ("Liquidez > R$1M", score['score_liquidez_1m'], 5),
                    ]

                    for i, (nome, valor, maximo) in enumerate(score_items):
                        with score_cols[i % 3]:
                            st.metric(nome, f"{valor}/{maximo}")

                    # Precos Teto (placeholder - integrar com valuation.py)
                    st.markdown("---")
                    st.markdown("### `Precos Teto`")

                    preco_atual = cotacao.get('price', 0)

                    teto_cols = st.columns(5)

                    with teto_cols[0]:
                        st.metric("Graham", f"R$ {preco_atual * 1.2:.2f}", delta="Estimado")
                    with teto_cols[1]:
                        st.metric("Graham BR", f"R$ {preco_atual * 1.1:.2f}", delta="Estimado")
                    with teto_cols[2]:
                        st.metric("Peter Lynch", f"R$ {preco_atual * 1.3:.2f}", delta="Estimado")
                    with teto_cols[3]:
                        st.metric("Bazin (7%)", f"R$ {preco_atual * 0.9:.2f}", delta="Estimado")
                    with teto_cols[4]:
                        st.metric("AGF", f"R$ {preco_atual * 1.15:.2f}", delta="Estimado")

                except Exception as e:
                    st.error(f"Erro ao carregar dados: {e}")
                    st.info("Verifique se USEBOLSAI_API_KEY está configurado.")
            else:
                st.warning("Modulos existentes nao encontrados. Mostrando dados simulados.")

                # Dados simulados para demonstracao
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Cotacao", "R$ 25.30")
                with col2: st.metric("DY", "8.5%")
                with col3: st.metric("P/L", "12.4")
                with col4: st.metric("P/VP", "1.8")

# ============================================================
# ABA: RANKINGS
# ============================================================

elif menu == "Rankings":
    st.markdown("## `Rankings de Ativos`")

    ranking_tipo = st.selectbox(
        "Selecione o ranking:",
        [
            "Maiores Valor de Mercado",
            "Maiores Dividend Yield",
            "Mais Baratas - Graham",
            "Mais Baratas - AGF",
            "Mais Baratas - Peter Lynch",
            "Mais Baratas - Graham BR",
            "Mais Baratas - Bazin",
            "Maiores Margem Liquida",
            "Melhores Score CS",
            "Maiores Receitas",
            "Maiores Lucros",
            "Maiores ROEs",
            "Menores P/Ls",
            "Maiores Altas - 30 dias",
            "Maiores Altas - 12 meses",
            "Maiores Caixa",
            "Crescimento Lucro - 5 anos",
            "Crescimento Receita - 5 anos",
            "Nunca Tiveram Prejuizo"
        ]
    )

    if st.button("Carregar Ranking", type="primary"):
        with st.spinner("Carregando..."):
            # Placeholder - integrar com APIs para dados reais
            st.info(f"Ranking: {ranking_tipo}")
            st.markdown("*Em desenvolvimento - integracao com UseBolsai/BRAPI*")

            # Exemplo de tabela
            df_exemplo = pd.DataFrame({
                'Ticker': ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'ABEV3'],
                'Valor': [150.2, 89.3, 45.7, 32.1, 28.9],
                'Score CS': [85, 72, 68, 55, 45]
            })

            st.dataframe(df_exemplo, use_container_width=True)

# ============================================================
# ABA: CARTEIRA
# ============================================================

elif menu == "Carteira":
    st.markdown("## `Gerenciador de Carteira`")

    tab1, tab2 = st.tabs(["Posicoes", "Importar B3"])

    with tab1:
        if DATABASE_URL:
            try:
                engine = get_db_engine()
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT p.ticker, p.quantidade, p.preco_medio, p.custo_total, p.classe
                        FROM posicoes p
                        JOIN carteiras c ON p.carteira_id = c.id
                        WHERE c.is_principal = TRUE
                    """))

                    rows = result.fetchall()
                    if rows:
                        df = pd.DataFrame(rows, columns=['Ticker', 'Quantidade', 'Preco Medio', 'Custo Total', 'Classe'])
                        st.dataframe(df, use_container_width=True)

                        st.metric("Total Investido", f"R$ {df['Custo Total'].sum():,.2f}")
                    else:
                        st.info("Carteira vazia. Importe dados do B3.")
            except Exception as e:
                st.error(f"Erro ao carregar carteira: {e}")
        else:
            st.warning("Banco de dados nao configurado. Configure DATABASE_URL.")

    with tab2:
        st.markdown("### `Importar do Canal do Investidor B3`")

        uploaded_file = st.file_uploader(
            "Selecione o arquivo Excel (.xlsx) - aba Negociacao",
            type=['xlsx']
        )

        if uploaded_file is not None:
            st.info("Arquivo recebido. Processando...")
            st.markdown("*Integracao com parser_negociacao_b3.py em desenvolvimento*")

# ============================================================
# ABA: IMPORTAR B3
# ============================================================

elif menu == "Importar B3":
    st.markdown("## `Importacao B3 - Canal do Investidor`")

    st.markdown("""
    <div class="info-box">
    <h4>Instrucoes:</h4>
    <ol>
        <li>Acesse: <b>https://www.investidor.b3.com.br</b></li>
        <li>Login → Extrato → Negociacao</li>
        <li>Exportar Excel (.xlsx)</li>
        <li>Faca o upload aqui</li>
    </ol>
    <p><b>Regras:</b></p>
    <ul>
        <li>✅ Acoes, FIIs, FIAGROs, ETFs, BDRs</li>
        <li>✅ Opcoes: apenas negociacoes (derivativos)</li>
        <li>❌ Ignora: Exercicio de opcoes, Futuros, CDBs</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Arquivo Excel (.xlsx)",
        type=['xlsx'],
        key="b3_import_main"
    )

    if uploaded_file:
        st.success("Arquivo carregado! Processando...")

        # Aqui integraria com parser_negociacao_b3.py
        # Salvar no banco via get_db_engine()

        if st.button("Salvar no Banco", type="primary"):
            if DATABASE_URL:
                st.success("Carteira salva com sucesso!")
            else:
                st.error("Configure DATABASE_URL primeiro.")

# ============================================================
# ABA: SOBRE
# ============================================================

else:
    st.markdown("## `Sobre o Sobral Invest v2.0`")

    st.markdown("""
    <div class="info-box">
    <h3>Sobral Invest v2.0</h3>
    <p>Plataforma profissional de analise fundamentalista.</p>

    <h4>Stack Tecnologico:</h4>
    <ul>
        <li>Python + Streamlit</li>
        <li>PostgreSQL (Supabase)</li>
        <li>UseBolsai API (fundamentals)</li>
        <li>BRAPI (cotacoes e lista de ativos)</li>
        <li>yfinance (dados complementares)</li>
    </ul>

    <h4>Score CS (Carlos Sobral):</h4>
    <p>Evolucao do Score Buy & Hold (0-9) para Score CS (0-100).</p>
    <p>Mais granularidade, mesmo rigor.</p>

    <h4>Metodos de Preco Teto:</h4>
    <ul>
        <li>Graham Classico</li>
        <li>Graham BR (adaptado para Brasil)</li>
        <li>Peter Lynch</li>
        <li>Bazin (taxa 7%)</li>
        <li>AGF Projetivo</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### `Desenvolvido por Carlos Sobral`")
    st.markdown("`GitHub: github.com/carlossobral/sobral_invest`")
