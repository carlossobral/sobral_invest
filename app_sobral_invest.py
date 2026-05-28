"""
app_sobral_invest.py - Entry point.
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
div[data-testid="stHorizontalBlock"] { gap: 0.75rem !important; }
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] { padding-left: 0.375rem !important; padding-right: 0.375rem !important; }
.main-header { font-size: 2.5rem; font-weight: bold; color: #1f77b4; text-align: center; margin-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

def main():
    st.sidebar.markdown("## 📈 SOBRAL Invest")
    st.sidebar.markdown("---")

    # 1. LEITURA DE NAVEGAÇÃO (DEEP LINKING)
    # Fazemos isso ANTES de desenhar o menu para garantir que a mudança seja instantânea
    query_params = st.query_params
    target_page = query_params.get("page")
    target_ticker = query_params.get("ticker")

    # Se veio um link externo ou do ranking...
    if target_page == "Analise" and target_ticker:
        # 1. Prepara o estado interno
        st.session_state["ticker_from_ranking"] = target_ticker
        
        # 2. Força o menu lateral a ir para Análise
        # Usamos o valor exato que está na lista do radio
        st.session_state["nav_radio_main"] = "🔍 Analise"
        
        # 3. Limpa a URL para não ficar "suja" e causar loops
        st.query_params.clear()
        
        # 4. Recarrega a página com as novas configurações
        st.rerun()

    # 2. MENU LATERAL
    # Se o estado já foi atualizado acima, ele já vai aparecer selecionado em "Analise"
    menu_options = ["🏠 Home", "🔍 Analise", "🏆 Rankings", "📊 Comparativo", "⚙️ Configuracoes"]
    
    pagina = st.sidebar.radio(
        "Navegacao",
        menu_options,
        key="nav_radio_main"
    )

    # 3. LIMPEZA DE ESTADO (Segurança)
    # Se o usuário mudou de página manualmente (clicando no menu), limpamos o ticker salvo
    # para que, se ele voltar para a home e depois para análise, não carregue o ticker antigo.
    if pagina != " Analise" and "ticker_from_ranking" in st.session_state:
        del st.session_state["ticker_from_ranking"]

    # 4. RENDERIZAÇÃO
    if pagina == "🏠 Home":
        pagina_inicial()
    elif pagina == "🔍 Analise":
        pagina_analise()
    elif pagina == "🏆 Rankings":
        pagina_rankings()
    elif pagina == "📊 Comparativo":
        pagina_comparativo()
    elif pagina == "️ Configuracoes":
        pagina_configuracoes()

if __name__ == "__main__":
    main()
