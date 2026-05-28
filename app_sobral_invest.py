import streamlit as st
from rankings import pagina_rankings
from analise import pagina_analise

# Configuração da página (deve ser a primeira chamada do Streamlit)
st.set_page_config(page_title="Sobral Invest", page_icon="📊", layout="wide")

# Inicialização segura do estado
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "rankings"
if "ticker_destino" not in st.session_state:
    st.session_state["ticker_destino"] = None

def main():
    # Menu lateral para navegação manual (opcional, mas recomendado)
    with st.sidebar:
        st.title("Navegação")
        if st.button("🏆 Rankings", use_container_width=True):
            st.session_state["pagina_atual"] = "rankings"
            st.rerun()
        if st.button("🔍 Análise", use_container_width=True):
            st.session_state["pagina_atual"] = "analise"
            st.rerun()
        st.markdown("---")
        st.caption("Sobral Invest v1.0")

    # Roteador centralizado
    pagina = st.session_state.get("pagina_atual", "rankings")
    
    if pagina == "analise":
        pagina_analise()
    else:
        pagina_rankings()

if __name__ == "__main__":
    main()
