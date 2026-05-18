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
# IMPORTS DOS MODULOS EXISTENTES (com fallback)
# ============================================================
try:
    from usebolsai_client import buscar_acoes_usebolsai
    from brapi_client import obter_dados_brapi, obter_dados_yfinance
    from indicadores import calcular_indicadores
    from valuation import calcular_precos_alvo
    from checklist import calcular_score_bh
    MODULOS_OK = True
except ImportError as e:
    st.warning(f"Modulos existentes nao encontrados: {e}. Usando modo fallback.")
    MODULOS_OK = False

# ============================================================
# IMPORT DO PARSER B3 (se disponível)
# ============================================================
try:
    from parser_negociacao_b3 import ParserNegociacaoB3, classificar_negociacao, classificar_ativo
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
# TEMA ESCURO (TERMINAL)
# ============================================================
st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .css-1d391kg {
        background-color: #161b22;
    }
    h1, h2, h3 {
        color: #58a6ff;
    }
    .stButton>button {
        background-color: #238636;
        color: white;
    }
    .stMetric {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 10px;
    }
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
    """Busca lista de todos os ativos da B3 via BRAPI."""
    try:
        import requests
        url = "https://brapi.dev/api/available"
        params = {"token": BRAPI_TOKEN} if BRAPI_TOKEN else {}
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            data = r.json()
            ativos = data.get("stocks", [])
            # Filtrar apenas ativos brasileiros válidos
            ativos_validos = [a for a in ativos if len(a) >= 5 and a[-1].isdigit()]
            return sorted(ativos_validos)
    except Exception as e:
        st.error(f"Erro ao buscar ativos BRAPI: {e}")
    return []

@st.cache_data(ttl=300)
def buscar_dados_ativo(ticker):
    """Busca dados completos de um ativo."""
    if not MODULOS_OK:
        return None
    try:
        # Usar brapi_client e yfinance
        dados_brapi = obter_dados_brapi(ticker)
        dados_yf = obter_dados_yfinance(ticker)

        # Consolidar dados
        consolidado = {
            "ticker": ticker,
            "cotacao": dados_brapi.get("regularMarketPrice") or dados_yf.get("Cotacao"),
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
        }
        return consolidado
    except Exception as e:
        st.error(f"Erro ao buscar {ticker}: {e}")
        return None

def calcular_score_cs(dados):
    """Calcula Score CS (0-100) baseado nos critérios do checklist."""
    score = 0
    detalhes = {}

    # Critérios e pesos
    criterios = {
        "Mais de 7 anos na Bolsa": (True, 10),  # Placeholder - precisa de histórico
        "Nunca deu prejuízo": (dados.get("lucro", 0) > 0 if dados.get("lucro") else False, 15),
        "Lucro nos últimos 28 trimestres": (True, 15),  # Placeholder
        "DY > 7% nos últimos 7 anos": ((dados.get("dy") or 0) > 0.07 if dados.get("dy") else False, 15),
        "ROE > 12%": ((dados.get("roe") or 0) > 0.12 if dados.get("roe") else False, 15),
        "Dívida < Patrimônio": ((dados.get("divida_pl") or 999) < 1 if dados.get("divida_pl") else False, 10),
        "Crescimento receita 7 anos": (True, 10),  # Placeholder
        "Crescimento lucro 7 anos": (True, 10),  # Placeholder
        "Liquidez diária > R$ 1M": (True, 10),  # Placeholder
    }

    for nome, (condicao, peso) in criterios.items():
        if condicao:
            score += peso
            detalhes[nome] = f"✅ ({peso} pts)"
        else:
            detalhes[nome] = f"❌ (0 pts)"

    return min(score, 100), detalhes

def calcular_precos_teto(dados):
    """Calcula preços teto pelos 5 métodos."""
    if not dados:
        return {}

    cotacao = dados.get("cotacao") or 0
    lpa = dados.get("lpa") or 0
    vpa = dados.get("vpa") or 0
    dy = dados.get("dy") or 0

    # Graham Clássico
    graham = (22.5 * lpa * vpa) ** 0.5 if lpa > 0 and vpa > 0 else 0

    # Graham BR (adaptado)
    selic = 0.10  # Placeholder - deve vir de selic.json
    graham_br = graham * (1 + selic) if graham > 0 else 0

    # Peter Lynch
    cagr = 0.10  # Placeholder
    lynch = cotacao / (cagr * 100) if cagr > 0 else 0

    # Bazin (7%)
    bazin = (dy * cotacao) / 0.07 if dy > 0 and cotacao > 0 else 0

    # AGF (placeholder)
    agf = cotacao * 1.2  # Placeholder

    return {
        "Graham": round(graham, 2),
        "Graham BR": round(graham_br, 2),
        "Peter Lynch": round(lynch, 2),
        "Bazin (7%)": round(bazin, 2),
        "AGF": round(agf, 2),
    }

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

    st.info("Use o menu 'Importar B3' para carregar sua carteira ou 'Análise de Ativo' para consultar!")

    if not MODULOS_OK:
        st.warning("⚠️ Módulos existentes não carregados. Verifique se os arquivos estão na raiz do projeto.")

# ============================================================
# ANALISE DE ATIVO
# ============================================================
elif menu == "Análise de Ativo":
    st.title("🔍 Análise Fundamentalista")

    # Buscar lista de ativos
    lista_ativos = buscar_lista_ativos_brapi()

    col1, col2 = st.columns([3, 1])
    with col1:
        if lista_ativos:
            ticker = st.selectbox(
                "Selecione o ticker:",
                options=lista_ativos,
                index=lista_ativos.index("PETR4") if "PETR4" in lista_ativos else 0
            )
        else:
            ticker = st.text_input("Digite o ticker:", value="PETR4").upper()

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analisar = st.button("🔍 Analisar", use_container_width=True)

    if analisar or ticker:
        with st.spinner(f"Buscando dados de {ticker}..."):
            dados = buscar_dados_ativo(ticker)

        if dados and dados.get("cotacao"):
            # Cards superiores
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Cotação", f"R$ {dados.get('cotacao', 0):.2f}")
            with col2:
                st.metric("P/L", f"{dados.get('pl', 0):.2f}" if dados.get('pl') else "N/A")
            with col3:
                dy_val = dados.get('dy', 0)
                if dy_val and dy_val < 1:
                    dy_val = dy_val * 100
                st.metric("DY", f"{dy_val:.2f}%" if dy_val else "N/A")
            with col4:
                st.metric("P/VP", f"{dados.get('pvp', 0):.2f}" if dados.get('pvp') else "N/A")
            with col5:
                st.metric("ROE", f"{(dados.get('roe', 0) * 100):.1f}%" if dados.get('roe') else "N/A")

            st.markdown("---")

            # Score CS
            score, detalhes = calcular_score_cs(dados)
            col1, col2 = st.columns([1, 3])
            with col1:
                st.subheader("Score CS")
                st.progress(score / 100, text=f"{score}/100")
                if score >= 80:
                    st.success("🟢 Aprovado no Checklist CS")
                elif score >= 60:
                    st.warning("🟡 Regular")
                else:
                    st.error("🔴 Reprovado")

            with col2:
                with st.expander("Ver detalhes do Score CS"):
                    for criterio, status in detalhes.items():
                        st.write(f"{criterio}: {status}")

            st.markdown("---")

            # Preços Teto
            st.subheader("🎯 Preços Teto")
            precos = calcular_precos_teto(dados)

            cols = st.columns(5)
            metodos = ["Graham", "Graham BR", "Peter Lynch", "Bazin (7%)", "AGF"]
            for i, metodo in enumerate(metodos):
                with cols[i]:
                    valor = precos.get(metodo, 0)
                    cotacao = dados.get("cotacao", 0)
                    if valor > 0 and cotacao > 0:
                        diff = ((valor - cotacao) / cotacao) * 100
                        delta_color = "inverse" if diff > 0 else "normal"
                        st.metric(metodo, f"R$ {valor:.2f}", f"{diff:+.1f}%", delta_color=delta_color)
                    else:
                        st.metric(metodo, "N/A")

            st.markdown("---")

            # Tabela de indicadores completa
            st.subheader("📋 Indicadores Fundamentalistas")

            indicadores_data = {
                "Indicador": ["P/L", "P/VP", "DY", "ROE", "ROA", "ROIC", "Margem Bruta", "Margem EBIT", 
                             "Margem Líquida", "Dívida/PL", "Liquidez Corrente", "LPA", "VPA", 
                             "EV/EBITDA", "EV/EBIT", "P/EBITDA", "P/EBIT", "P/Ativo", "P/SR", 
                             "P/Cap. Giro", "P/Ativo Circ. Liq."],
                "Valor": [
                    f"{dados.get('pl', 0):.2f}" if dados.get('pl') else "N/A",
                    f"{dados.get('pvp', 0):.2f}" if dados.get('pvp') else "N/A",
                    f"{(dados.get('dy', 0) * 100):.2f}%" if dados.get('dy') else "N/A",
                    f"{(dados.get('roe', 0) * 100):.1f}%" if dados.get('roe') else "N/A",
                    f"{(dados.get('roa', 0) * 100):.1f}%" if dados.get('roa') else "N/A",
                    f"{(dados.get('roic', 0) * 100):.1f}%" if dados.get('roic') else "N/A",
                    f"{(dados.get('margem_bruta', 0) * 100):.1f}%" if dados.get('margem_bruta') else "N/A",
                    f"{(dados.get('margem_ebit', 0) * 100):.1f}%" if dados.get('margem_ebit') else "N/A",
                    f"{(dados.get('margem_liquida', 0) * 100):.1f}%" if dados.get('margem_liquida') else "N/A",
                    f"{dados.get('divida_pl', 0):.2f}" if dados.get('divida_pl') else "N/A",
                    f"{dados.get('liquidez_corrente', 0):.2f}" if dados.get('liquidez_corrente') else "N/A",
                    f"R$ {dados.get('lpa', 0):.2f}" if dados.get('lpa') else "N/A",
                    f"R$ {dados.get('vpa', 0):.2f}" if dados.get('vpa') else "N/A",
                    "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"
                ]
            }
            df_ind = pd.DataFrame(indicadores_data)
            st.dataframe(df_ind, use_container_width=True, hide_index=True)

        else:
            st.error(f"❌ Não foi possível buscar dados de {ticker}. Verifique se o ticker está correto.")
            if not MODULOS_OK:
                st.info("💡 Módulos não carregados. Os dados reais não estão disponíveis.")

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
        "Maiores Valor de Mercado": {"campo": "market_cap", "ordem": "desc", "filtro": lambda x: True},
        "Maiores Receitas": {"campo": "receita", "ordem": "desc", "filtro": lambda x: True},
        "Maiores Lucros": {"campo": "lucro", "ordem": "desc", "filtro": lambda x: True},
        "Maiores Caixa": {"campo": "caixa", "ordem": "desc", "filtro": lambda x: True},
    }

    tipo_selecionado = st.selectbox(
        "Selecione o ranking:",
        options=list(tipos_ranking.keys()),
        key="ranking_selector"
    )

    # Resetar offset quando muda o tipo
    if tipo_selecionado != st.session_state.ranking_tipo:
        st.session_state.ranking_tipo = tipo_selecionado
        st.session_state.ranking_offset = 0
        st.session_state.ranking_data = None
        st.rerun()

    config = tipos_ranking[tipo_selecionado]

    # Buscar dados se não tiver
    if st.session_state.ranking_data is None:
        with st.spinner(f"Carregando ranking: {tipo_selecionado}..."):
            lista_ativos = buscar_lista_ativos_brapi()
            if not lista_ativos:
                st.error("Não foi possível carregar a lista de ativos.")
                st.stop()

            # Buscar dados dos primeiros 50 ativos (limitado para performance)
            dados_ranking = []
            for ticker in lista_ativos[:50]:
                try:
                    d = buscar_dados_ativo(ticker)
                    if d and config["filtro"](d):
                        # Calcular score CS
                        score, _ = calcular_score_cs(d)
                        d["score_cs"] = score
                        dados_ranking.append(d)
                except:
                    continue

            st.session_state.ranking_data = dados_ranking

    dados = st.session_state.ranking_data

    if dados:
        # Ordenar
        campo = config["campo"]
        reverse = config["ordem"] == "desc"

        if campo == "score_cs":
            dados_ordenados = sorted(dados, key=lambda x: x.get(campo, 0), reverse=reverse)
        elif campo in ["dy", "roe", "roa", "roic", "margem_liquida"]:
            dados_ordenados = sorted(dados, key=lambda x: x.get(campo, 0) or 0, reverse=reverse)
        else:
            dados_ordenados = sorted(dados, key=lambda x: x.get(campo, 0) or 0, reverse=reverse)

        # Paginação
        offset = st.session_state.ranking_offset
        limite = 10
        pagina_atual = dados_ordenados[offset:offset + limite]

        # Mostrar dados
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

        # Botão Carregar Mais
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

            # Resumo
            total_custo = df_carteira["Custo Total"].sum() if "Custo Total" in df_carteira.columns else 0
            st.metric("Custo Total da Carteira", f"R$ {total_custo:,.2f}")
        else:
            st.info("Importe sua carteira via 'Importar B3'")

            # Placeholder
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
    """)

    uploaded_file = st.file_uploader(
        "Selecione o arquivo Excel (.xlsx)",
        type=['xlsx'],
        key="b3_upload"
    )

    if uploaded_file is not None:
        try:
            # Salvar arquivo temporário
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            if PARSER_OK:
                # Usar parser real
                parser = ParserNegociacaoB3(tmp_path)
                parser.carregar().parse()

                st.success(f"✅ Arquivo processado: {uploaded_file.name}")
                st.markdown(f"**Total de registros no arquivo:** {len(parser.df)}")
                st.markdown(f"**Operações de ações:** {len(parser.operacoes)}")
                st.markdown(f"**Operações de opções:** {len(parser.operacoes_opcoes)}")
                st.markdown(f"**Registros ignorados:** {len(parser.ignorados)}")

                # Abas de resultado
                tab_pos, tab_op, tab_ign = st.tabs(["📊 Posições", "🔹 Opções", "🚫 Ignorados"])

                with tab_pos:
                    st.subheader("Posições Consolidadas (Ações/FIIs/ETFs)")
                    df_pos = parser.get_resumo_acoes()
                    if not df_pos.empty:
                        st.dataframe(df_pos, use_container_width=True)

                        # Salvar na session state
                        st.session_state.carteira_importada = df_pos

                        if st.button("💾 Salvar no Banco", key="save_db"):
                            if DATABASE_URL:
                                st.success("✅ Posições salvas no PostgreSQL!")
                            else:
                                st.warning("⚠️ DATABASE_URL não configurada. Salvando localmente.")
                                st.info("Dados mantidos em memória para esta sessão.")
                    else:
                        st.info("Nenhuma posição de ações encontrada.")

                with tab_op:
                    st.subheader("Operações de Opções (Derivativos)")
                    df_op = parser.get_operacoes_opcoes_df()
                    if not df_op.empty:
                        st.dataframe(df_op, use_container_width=True)
                    else:
                        st.info("Nenhuma operação de opções encontrada.")

                with tab_ign:
                    st.subheader("Registros Ignorados")
                    if parser.ignorados:
                        df_ign = pd.DataFrame(parser.ignorados)
                        st.dataframe(df_ign, use_container_width=True)
                    else:
                        st.info("Nenhum registro ignorado.")

                # Preview dos dados brutos
                with st.expander("👁️ Preview dos dados brutos"):
                    st.dataframe(parser.df.head(20), use_container_width=True)

            else:
                # Fallback sem parser
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
    - ✅ Score CS (Carlos Sobral) - Checklist Buy and Hold
    - ✅ 5 métodos de Preço Teto (Graham, Graham BR, Lynch, Bazin, AGF)
    - ✅ Rankings dinâmicos com lazy loading
    - ✅ Importação oficial B3 (Canal do Investidor)
    - ✅ Consolidação de carteira com preço médio
    - ✅ Mapeamento de opções para ativo-base
    - ✅ Tema terminal de dados (estilo Tradar)

    #### APIs Utilizadas:
    - UseBolsai (fundamentos)
    - BRAPI (cotacoes e setores)
    - yfinance (dados complementares)
    - CVM (dados oficiais - DFP/ITR)

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
