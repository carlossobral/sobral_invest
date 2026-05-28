import streamlit as st
from home import pagina_home
from rankings import pagina_rankings
from analise import pagina_analise
from comparativo import pagina_comparativo

# Configuração da página
st.set_page_config(page_title="Sobral Invest", page_icon="📊", layout="wide")

# Inicialização segura do estado
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "home"
if "ticker_destino" not in st.session_state:
    st.session_state["ticker_destino"] = None

def main():
    # Sidebar com navegação em estilo CARD (sempre)
    with st.sidebar:
        st.markdown("""
        <style>
        .nav-button {
            background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px 16px;
            margin: 6px 0;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: left;
            width: 100%;
        }
        .nav-button:hover {
            border-color: #3b82f6;
            transform: translateX(4px);
        }
        .nav-button.active {
            border-color: #3b82f6;
            background: linear-gradient(145deg, #1e3a8a 0%, #1e40af 100%);
        }
        .nav-button-text {
            font-size: 0.95rem;
            font-weight: 600;
            color: #f1f5f9;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.title("Navegação")
        
        # Botão Home
        home_active = st.session_state["pagina_atual"] == "home"
        if st.button("🏠 Home", key="btn_home", use_container_width=True, 
                     type="primary" if home_active else "secondary"):
            st.session_state["pagina_atual"] = "home"
            st.rerun()
        
        # Botão Rankings
        rankings_active = st.session_state["pagina_atual"] == "rankings"
        if st.button("🏆 Rankings", key="btn_rankings", use_container_width=True,
                     type="primary" if rankings_active else "secondary"):
            st.session_state["pagina_atual"] = "rankings"
            st.rerun()
        
        # Botão Comparativo
        comparativo_active = st.session_state["pagina_atual"] == "comparativo"
        if st.button("📊 Comparativo", key="btn_comparativo", use_container_width=True,
                     type="primary" if comparativo_active else "secondary"):
            st.session_state["pagina_atual"] = "comparativo"
            st.rerun()
        
        # Botão Análise
        analise_active = st.session_state["pagina_atual"] == "analise"
        if st.button("🔍 Análise", key="btn_analise", use_container_width=True,
                     type="primary" if analise_active else "secondary"):
            st.session_state["pagina_atual"] = "analise"
            st.rerun()
        
        st.markdown("---")
        st.caption("Sobral Invest v1.0")

    # Roteador centralizado
    pagina = st.session_state.get("pagina_atual", "home")
    
    if pagina == "home":
        pagina_home()
    elif pagina == "rankings":
        pagina_rankings()
    elif pagina == "comparativo":
        pagina_comparativo()
    elif pagina == "analise":
        pagina_analise()

if __name__ == "__main__":
    main()
