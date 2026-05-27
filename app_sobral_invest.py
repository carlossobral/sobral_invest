"""
app_sobral_invest.py - Streamlit Dashboard SOBRAL Invest v5.0
Entry point. Importa páginas separadas.
"""

import streamlit as st
from data import load_data
from home import pagina_inicial
from analise import pagina_analise
from rankings import pagina_rankings
from comparativo import pagina_comparativo
from configs import pagina_configuracoes

st.set_page_config(
    page_title="SOBRAL Invest",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS GLOBAL
st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] {
    gap: 0.75rem !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    padding-left: 0.375rem !important;
    padding-right: 0.375rem !important;
}
.bh-card-v2 {
    margin-bottom: 0.75rem !important;
}
.metric-card-v2 {
    margin-bottom: 0.75rem !important;
}
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

def main():
    """Funcao principal."""
    st.sidebar.markdown("## 📈 SOBRAL Invest")
    st.sidebar.markdown("---")

    # Capturar query params para navegação do Ranking -> Análise
    query_params = st.query_params
    ticker_from_ranking = query_params.get("ticker", None)
    page_from_ranking = query_params.get("page", None)

    if ticker_from_ranking and page_from_ranking == "Analise":
        st.session_state["nav_radio_main"] = "🔍 Analise"
        st.session_state["ticker_from_ranking"] = ticker_from_ranking

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
