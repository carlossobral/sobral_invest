import streamlit as st
from data import load_data

def pagina_configuracoes():
    """Pagina de configuracoes."""
    st.markdown('<h1 class="main-header">⚙️ Configuracoes</h1>', unsafe_allow_html=True)

    with st.spinner("Carregando estatísticas gerais..."):
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
