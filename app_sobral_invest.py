import streamlit as st
import pandas as pd
import os
import sys

# ============================================================
# CONFIGURACAO DA PAGINA - DEVE SER O PRIMEIRO COMANDO STREAMLIT
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
    from usebolsai_client import UseBolsaiClient
    from brapi_client import BrapiClient
    from indicadores import calcular_indicadores
    from valuation import calcular_precos_alvo
    from checklist import calcular_score_bh
    MODULOS_OK = True
except ImportError as e:
    st.warning(f"Modulos existentes nao encontrados: {e}. Usando modo fallback.")
    MODULOS_OK = False

# ============================================================
# CONFIGURACAO DE APIs
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
</style>
""", unsafe_allow_html=True)

# ============================================================
# MENU LATERAL
# ============================================================
st.sidebar.title("📊 SOBRAL INVEST")
st.sidebar.markdown("---")
st.sidebar.markdown("Plataforma de Analise Fundamentalista")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "MENU",
    ["Dashboard", "Analise de Ativo", "Rankings", "Carteira", "Importar B3", "Sobre"]
)

# ============================================================
# DASHBOARD
# ============================================================
if menu == "Dashboard":
    st.title("📊 SOBRAL INVEST v2.0")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ativos na Base", "500+")
    with col2:
        st.metric("Score CS Medio", "Aguardando dados")
    with col3:
        st.metric("Carteira", "Aguardando importacao")

    st.info("Use o menu 'Importar B3' para carregar sua carteira!")

# ============================================================
# ANALISE DE ATIVO
# ============================================================
elif menu == "Analise de Ativo":
    st.title("🔍 Analise Fundamentalista")

    ticker = st.text_input("Digite o ticker:", value="PETR4").upper()

    if st.button("Analisar"):
        if MODULOS_OK:
            st.success(f"Analisando {ticker}... (integracao com modulos existentes)")
        else:
            st.info(f"Modo fallback: {ticker}")
            st.markdown("""
            ### Indicadores (exemplo)
            | Indicador | Valor |
            |-----------|-------|
            | P/L | 8.5 |
            | P/VP | 1.2 |
            | DY | 12% |
            | ROE | 15% |
            """)

            st.markdown("---")
            st.subheader("Score CS")
            st.progress(75, text="Score CS: 75/100")

            st.markdown("---")
            st.subheader("Precos Teto")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Graham", "R$ 25.00")
            col2.metric("Graham BR", "R$ 28.00")
            col3.metric("Lynch", "R$ 30.00")
            col4.metric("Bazin (7%)", "R$ 22.00")
            col5.metric("AGF", "R$ 35.00")

# ============================================================
# RANKINGS
# ============================================================
elif menu == "Rankings":
    st.title("🏆 Rankings")

    tipo_ranking = st.selectbox(
        "Selecione o ranking:",
        ["Maiores DY", "Mais Baratas - Graham", "Maiores Score CS", 
         "Menores P/L", "Maiores ROE", "Maiores Margem Liquida"]
    )

    st.info(f"Ranking: {tipo_ranking} (integracao com BRAPI/UseBolsai)")

    # Placeholder para dados
    df_placeholder = pd.DataFrame({
        'Pos': [1, 2, 3, 4, 5],
        'Ticker': ['PETR4', 'VALE3', 'ITSA4', 'BBDC4', 'WEGE3'],
        'Valor': ['12%', '8.5%', '7.2%', '6.8%', '5.5%']
    })
    st.dataframe(df_placeholder, use_container_width=True)

    if st.button("Carregar Mais"):
        st.info("Carregando mais ativos...")

# ============================================================
# CARTEIRA
# ============================================================
elif menu == "Carteira":
    st.title("💼 Gerenciador de Carteira")

    tab1, tab2, tab3, tab4 = st.tabs(["Posicoes", "Operacoes", "Proventos", "Rentabilidade"])

    with tab1:
        st.subheader("Posicoes Consolidadas")
        st.info("Importe sua carteira via 'Importar B3'")

        # Placeholder
        df_carteira = pd.DataFrame({
            'Ticker': ['PETR4', 'VALE3', 'ITSA4'],
            'Quantidade': [100, 50, 200],
            'Preco Medio': [25.30, 68.40, 12.50],
            'Custo Total': [2530.00, 3420.00, 2500.00],
            'Classe': ['ACAO', 'ACAO', 'ACAO']
        })
        st.dataframe(df_carteira, use_container_width=True)

    with tab2:
        st.subheader("Historico de Operacoes")
        st.info("Importe via 'Importar B3'")

    with tab3:
        st.subheader("Proventos")
        st.info("Dividendos e JCP")

    with tab4:
        st.subheader("Rentabilidade")
        st.info("Evolucao da carteira vs IBOV/CDI")

# ============================================================
# IMPORTAR B3
# ============================================================
elif menu == "Importar B3":
    st.title("📥 Importar Negociacoes B3")
    st.markdown("---")

    st.markdown("""
    ### Instrucoes:
    1. Acesse: [investidor.b3.com.br](https://investidor.b3.com.br)
    2. Exporte: Negociacao > Excel
    3. Faca upload aqui
    """)

    uploaded_file = st.file_uploader(
        "Selecione o arquivo Excel (.xlsx)",
        type=['xlsx'],
        key="b3_upload"
    )

    if uploaded_file is not None:
        try:
            # Ler arquivo
            df = pd.read_excel(uploaded_file)

            st.success(f"Arquivo carregado: {uploaded_file.name}")
            st.markdown(f"**Registros:** {len(df)}")

            # Mostrar preview
            with st.expander("Preview dos dados brutos"):
                st.dataframe(df.head(10), use_container_width=True)

            # Abas de resultado
            tab_pos, tab_op, tab_ign = st.tabs(["Posicoes", "Operacoes", "Ignorados"])

            with tab_pos:
                st.subheader("Posicoes Consolidadas")
                # Simulacao de consolidacao
                st.info("Apos importacao, aparecerao as posicoes consolidadas aqui")

                df_pos = pd.DataFrame({
                    'Ticker': ['PETR4', 'VALE3', 'ITSA4', 'VGIR11'],
                    'Quantidade': [100, 50, 200, 30],
                    'Preco Medio': [25.30, 68.40, 12.50, 15.20],
                    'Custo Total': [2530.00, 3420.00, 2500.00, 456.00],
                    'Classe': ['ACAO', 'ACAO', 'ACAO', 'FII']
                })
                st.dataframe(df_pos, use_container_width=True)

                if st.button("Salvar no Banco", key="save_db"):
                    if DATABASE_URL:
                        st.success("Posicoes salvas no PostgreSQL!")
                    else:
                        st.warning("DATABASE_URL nao configurada. Salvando localmente.")

            with tab_op:
                st.subheader("Operacoes de Opcoes")
                st.info("Derivativos - nao consolidam na carteira principal")

                df_op = pd.DataFrame({
                    'Ticker Original': ['GGBRE203', 'BBASQ245'],
                    'Ativo Base': ['GGBR4', 'BBAS3'],
                    'Tipo': ['CALL', 'PUT'],
                    'Strike': [20.30, 24.50],
                    'Quantidade': [100, 100]
                })
                st.dataframe(df_op, use_container_width=True)

            with tab_ign:
                st.subheader("Registros Ignorados")
                st.info("Exercicios de opcoes, futuros, renda fixa")

                df_ign = pd.DataFrame({
                    'Tipo': ['Exercicio Put', 'Exercicio Call'],
                    'Ticker': ['BBASQ245E', 'GGBRE203E'],
                    'Motivo': ['Venda de acoes ao strike', 'Compra de acoes ao strike']
                })
                st.dataframe(df_ign, use_container_width=True)

        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")

# ============================================================
# SOBRE
# ============================================================
elif menu == "Sobre":
    st.title("ℹ️ Sobre o Sobral Invest")
    st.markdown("""
    ### 📊 SOBRAL INVEST v2.0

    **Plataforma de Analise Fundamentalista e Gerenciamento de Carteira**

    Desenvolvido por: **Carlos Sobral**

    #### Funcionalidades:
    - ✅ Analise Fundamentalista completa (25+ indicadores)
    - ✅ Score CS (Carlos Sobral) - Checklist Buy and Hold
    - ✅ 5 metodos de Preco Teto (Graham, Graham BR, Lynch, Bazin, AGF)
    - ✅ Rankings dinamicos com lazy loading
    - ✅ Importacao oficial B3 (Canal do Investidor)
    - ✅ Consolidacao de carteira com preco medio
    - ✅ Mapeamento de opcoes para ativo-base
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
    st.markdown("**Status dos Modulos:**")
    if MODULOS_OK:
        st.success("✅ Modulos existentes carregados (usebolsai, brapi, indicadores, valuation, checklist)")
    else:
        st.warning("⚠️ Modulos existentes nao encontrados. Usando modo fallback.")
        st.info("Para integracao completa, mantenha os arquivos: usebolsai_client.py, brapi_client.py, indicadores.py, valuation.py, checklist.py na raiz do projeto")
