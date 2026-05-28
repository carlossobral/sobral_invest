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

    # 1. Ler parâmetros da URL (Deep Linking vindo do Ranking ou link externo)
    query_params = st.query_params
    target_page = query_params.get("page")
    target_ticker = query_params.get("ticker")

    # 2. Lógica de Redirecionamento ANTES de desenhar o widget
    # Se a URL pede uma página específica e temos um ticker, preparamos o estado
    if target_page == "Analise" and target_ticker:
        # Salva o ticker no session_state para a página de análise usar
        st.session_state["ticker_from_ranking"] = target_ticker
        
        # Limpa os parâmetros da URL para evitar loops ou estados presos
        st.query_params.clear()
        
        # Força o reload para que a página de análise carregue com o ticker correto
        st.rerun()

    # 3. Menu Lateral (Agora seguro, pois o redirecionamento já ocorreu se necessário)
    menu_options = ["🏠 Home", "🔍 Analise", "🏆 Rankings", "📊 Comparativo", "⚙️ Configuracoes"]
    
    pagina = st.sidebar.radio(
        "Navegacao",
        menu_options,
        key="nav_radio_main"
    )

    # 4. Limpeza de estado se o usuário mudou de página manualmente
    # Se estamos em outra página que não é Análise, limpamos o ticker salvo
    if pagina != "🔍 Analise" and "ticker_from_ranking" in st.session_state:
        del st.session_state["ticker_from_ranking"]

    # 5. Renderização das Páginas
    if pagina == "🏠 Home":
        pagina_inicial()
    elif pagina == " Analise":
        pagina_analise()
    elif pagina == "🏆 Rankings":
        pagina_rankings()
    elif pagina == "📊 Comparativo":
        pagina_comparativo()
    elif pagina == "⚙️ Configuracoes":
        pagina_configuracoes()

if __name__ == "__main__":
    main()
