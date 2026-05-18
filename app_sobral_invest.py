import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Adicionar diretorio do projeto ao path
sys.path.append(str(Path(__file__).parent))

from parser_negociacao_b3 import ParserNegociacaoB3, TipoOperacao, ClasseAtivo

# ============================================================
# CONFIGURACAO DA PAGINA
# ============================================================

st.set_page_config(
    page_title="Sobral Invest - Importacao B3",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS custom - tema escuro (estilo terminal)
st.markdown("""
<style>
    .main {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .stApp {
        background-color: #0d1117;
    }
    h1, h2, h3 {
        color: #58a6ff !important;
        font-family: 'Courier New', monospace;
    }
    .stDataFrame {
        background-color: #161b22;
        border: 1px solid #30363d;
    }
    .stMetric {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 10px;
    }
    .stMetric label {
        color: #8b949e !important;
    }
    .stMetric div {
        color: #c9d1d9 !important;
        font-family: 'Courier New', monospace;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .css-1d391kg {
        background-color: #161b22;
    }
    .stButton>button {
        background-color: #238636;
        color: white;
        border: 1px solid #2ea043;
        font-family: 'Courier New', monospace;
    }
    .stButton>button:hover {
        background-color: #2ea043;
    }
    .stFileUploader {
        background-color: #161b22;
        border: 2px dashed #30363d;
        border-radius: 6px;
        padding: 20px;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #161b22;
        border-bottom: 1px solid #30363d;
    }
    .stTabs [data-baseweb="tab"] {
        color: #8b949e;
        font-family: 'Courier New', monospace;
    }
    .stTabs [aria-selected="true"] {
        color: #58a6ff !important;
        border-bottom: 2px solid #58a6ff;
    }
    div[data-testid="stMarkdownContainer"] {
        font-family: 'Courier New', monospace;
    }
    .success-box {
        background-color: #23863620;
        border: 1px solid #2ea043;
        border-radius: 6px;
        padding: 15px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #d2992220;
        border: 1px solid #d29922;
        border-radius: 6px;
        padding: 15px;
        margin: 10px 0;
    }
    .error-box {
        background-color: #da363320;
        border: 1px solid #f85149;
        border-radius: 6px;
        padding: 15px;
        margin: 10px 0;
    }
    .info-box {
        background-color: #1f6feb20;
        border: 1px solid #58a6ff;
        border-radius: 6px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================

st.title("📊 SOBRAL INVEST")
st.markdown("### `Importacao Canal do Investidor B3`")
st.markdown("---")

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown("## `MENU`")
st.sidebar.markdown("---")

modo = st.sidebar.radio(
    "Modo:",
    ["Importar Arquivo", "Sobre"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### `Status`")

# ============================================================
# ABA: IMPORTAR ARQUIVO
# ============================================================

if modo == "Importar Arquivo":

    st.markdown("## `Upload do Arquivo B3`")
    st.markdown("""
    <div class="info-box">
    <b>Instrucoes:</b><br>
    1. Acesse o <b>Canal do Investidor B3</b><br>
    2. Exporte a aba <b>"Negociacao"</b> em Excel<br>
    3. Faca o upload aqui<br>
    <br>
    <b>Regras de parse:</b><br>
    • Acoes: Compra/Venda (mercado a vista / fracionario)<br>
    • Opcoes: Apenas negociacoes (derivativos)<br>
    • Ignorar: Exercicio de opcoes, futuros, CDBs<br>
    • Fracionario: sufixo F removido automaticamente
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Selecione o arquivo Excel (.xlsx)",
        type=['xlsx'],
        help="Arquivo exportado do Canal do Investidor B3 - aba Negociacao"
    )

    if uploaded_file is not None:

        # Salvar temporariamente
        temp_path = Path("temp_upload.xlsx")
        temp_path.write_bytes(uploaded_file.getvalue())

        try:
            # Parse
            with st.spinner("Processando arquivo..."):
                parser = ParserNegociacaoB3(str(temp_path))
                parser.carregar().parse()

            # Metricas
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Acoes Parseadas",
                    len(parser.operacoes),
                    delta=None
                )

            with col2:
                st.metric(
                    "Opcoes (Derivativos)",
                    len(parser.operacoes_opcoes),
                    delta=None
                )

            with col3:
                st.metric(
                    "Posicoes Consolidadas",
                    len(parser.posicoes_acoes),
                    delta=None
                )

            with col4:
                st.metric(
                    "Ignorados",
                    len(parser.ignorados),
                    delta=None
                )

            st.markdown("---")

            # Tabs
            tab1, tab2, tab3, tab4 = st.tabs([
                "📈 Posicoes Consolidadas",
                "📋 Operacoes Acoes",
                "🎯 Operacoes Opcoes",
                "⚠️ Ignorados"
            ])

            # TAB 1: Posicoes Consolidadas
            with tab1:
                st.markdown("## `Posicoes Consolidadas de Acoes`")

                df_posicoes = parser.get_resumo_acoes()

                if not df_posicoes.empty:
                    # Colorir por classe
                    def color_classe(val):
                        colors = {
                            'ACAO': '#58a6ff',
                            'FII': '#a371f7',
                            'FIAGRO': '#3fb950',
                            'ETF': '#d29922',
                            'BDR': '#f85149'
                        }
                        return f'color: {colors.get(val, "#c9d1d9")}'

                    st.dataframe(
                        df_posicoes.style.applymap(color_classe, subset=['Classe']),
                        use_container_width=True,
                        height=400
                    )

                    # Grafico de pizza - composicao
                    st.markdown("### `Composicao da Carteira`")

                    col_pizza1, col_pizza2 = st.columns(2)

                    with col_pizza1:
                        # Por classe
                        df_classe = df_posicoes.groupby('Classe')['Custo Total'].sum().reset_index()
                        st.bar_chart(
                            df_classe.set_index('Classe'),
                            use_container_width=True
                        )

                    with col_pizza2:
                        # Top 10 por valor
                        df_top10 = df_posicoes.nlargest(10, 'Custo Total')[['Ticker', 'Custo Total']]
                        st.bar_chart(
                            df_top10.set_index('Ticker'),
                            use_container_width=True
                        )

                else:
                    st.warning("Nenhuma posicao de acao encontrada.")

            # TAB 2: Operacoes Acoes
            with tab2:
                st.markdown("## `Historico de Operacoes - Acoes`")

                df_acoes = parser.get_operacoes_acoes_df()

                if not df_acoes.empty:
                    # Filtros
                    col_filtro1, col_filtro2 = st.columns(2)

                    with col_filtro1:
                        ticker_filtro = st.multiselect(
                            "Filtrar por Ticker:",
                            options=sorted(df_acoes['Ticker'].unique()),
                            default=[]
                        )

                    with col_filtro2:
                        tipo_filtro = st.multiselect(
                            "Filtrar por Tipo:",
                            options=sorted(df_acoes['Tipo'].unique()),
                            default=[]
                        )

                    # Aplicar filtros
                    df_filtrado = df_acoes.copy()
                    if ticker_filtro:
                        df_filtrado = df_filtrado[df_filtrado['Ticker'].isin(ticker_filtro)]
                    if tipo_filtro:
                        df_filtrado = df_filtrado[df_filtrado['Tipo'].isin(tipo_filtro)]

                    st.dataframe(
                        df_filtrado.sort_values('Data', ascending=False),
                        use_container_width=True,
                        height=500
                    )

                    # Download CSV
                    csv = df_filtrado.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name="operacoes_acoes.csv",
                        mime="text/csv"
                    )

                else:
                    st.warning("Nenhuma operacao de acao encontrada.")

            # TAB 3: Operacoes Opcoes
            with tab3:
                st.markdown("## `Operacoes de Opcoes (Derivativos)`")
                st.markdown("""
                <div class="warning-box">
                <b>Aviso:</b> Opcoes sao <b>derivativos</b> e NAO consolidam na carteira de acoes.<br>
                Sao registradas separadamente para acompanhamento.
                </div>
                """, unsafe_allow_html=True)

                df_opcoes = parser.get_operacoes_opcoes_df()

                if not df_opcoes.empty:
                    st.dataframe(
                        df_opcoes.sort_values('Data', ascending=False),
                        use_container_width=True,
                        height=500
                    )

                    # Resumo por ativo-base
                    st.markdown("### `Resumo por Ativo-Base`")
                    df_op_resumo = df_opcoes.groupby('Ativo Base').agg({
                        'Quantidade': 'sum',
                        'Valor Total': 'sum',
                        'Tipo Opcao': 'count'
                    }).reset_index()
                    df_op_resumo.columns = ['Ativo Base', 'Quantidade Total', 'Valor Total', 'Operacoes']
                    st.dataframe(df_op_resumo, use_container_width=True)

                else:
                    st.info("Nenhuma operacao de opcoes encontrada.")

            # TAB 4: Ignorados
            with tab4:
                st.markdown("## `Registros Ignorados`")
                st.markdown("""
                <div class="info-box">
                <b>Motivos de ignorar:</b><br>
                • Exercicio de opcao (eh operacao de acao, nao de opcao)<br>
                • Futuros (WIN, WDO) - day trade<br>
                • CDBs / Renda fixa<br>
                • Outros nao identificados
                </div>
                """, unsafe_allow_html=True)

                if parser.ignorados:
                    df_ignorados = pd.DataFrame(parser.ignorados)
                    st.dataframe(df_ignorados, use_container_width=True, height=400)

                    st.metric("Total Ignorados", len(parser.ignorados))
                else:
                    st.success("Nenhum registro ignorado!")

            # Botao para exportar tudo
            st.markdown("---")

            col_exp1, col_exp2 = st.columns(2)

            with col_exp1:
                # Exportar posicoes para SQL
                acoes_sql, opcoes_sql = parser.exportar_para_sql()

                if acoes_sql:
                    df_sql = pd.DataFrame(acoes_sql)
                    csv_sql = df_sql.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Exportar Posicoes (SQL-ready CSV)",
                        data=csv_sql,
                        file_name="posicoes_para_sql.csv",
                        mime="text/csv"
                    )

            with col_exp2:
                # Exportar opcoes
                if opcoes_sql:
                    df_op_sql = pd.DataFrame(opcoes_sql)
                    csv_op_sql = df_op_sql.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Exportar Opcoes (SQL-ready CSV)",
                        data=csv_op_sql,
                        file_name="opcoes_para_sql.csv",
                        mime="text/csv"
                    )

            # Limpar arquivo temporario
            temp_path.unlink(missing_ok=True)

        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# ============================================================
# ABA: SOBRE
# ============================================================

else:
    st.markdown("## `Sobre o Sobral Invest`")

    st.markdown("""
    <div class="info-box">
    <h3>Sobral Invest v0.1</h3>
    <p>Plataforma de analise fundamentalista e gerenciamento de carteira.</p>

    <h4>Funcionalidades:</h4>
    <ul>
        <li>Importacao de negociacoes do Canal do Investidor B3</li>
        <li>Consolidacao de posicoes de acoes, FIIs, FIAGROs, ETFs, BDRs</li>
        <li>Registro separado de opcoes (derivativos)</li>
        <li>Calculo automatico de preco medio</li>
        <li>Exportacao para banco de dados</li>
    </ul>

    <h4>Regras de Importacao:</h4>
    <ul>
        <li><b>Acoes:</b> Mercado a vista e fracionario (consolidados)</li>
        <li><b>Opcoes:</b> Apenas negociacoes (compra/venda no mercado)</li>
        <li><b>Ignorar:</b> Exercicio de opcoes, futuros, CDBs</li>
        <li><b>Fracionario:</b> Sufixo F removido automaticamente</li>
    </ul>

    <h4>Stack Tecnologico:</h4>
    <ul>
        <li>Python + Streamlit</li>
        <li>PostgreSQL (banco de dados)</li>
        <li>CVM Dados Abertos (demonstracoes financeiras)</li>
        <li>BRAPI/UseBolsai (cotacoes e indicadores)</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### `Desenvolvido por Carlos Sobral`")
    st.markdown("`GitHub: github.com/carlossobral/sobral_invest`")
