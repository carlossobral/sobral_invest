import streamlit as st
from home import pagina_inicial
from analise import pagina_analise
from rankings import pagina_rankings
from comparativo import pagina_comparativo
from configs import pagina_configuracoes

# Configuração da página
st.set_page_config(page_title="Sobral Invest", page_icon="📊", layout="wide")

# Inicialização do estado
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "home"
if "ticker_destino" not in st.session_state:
    st.session_state["ticker_destino"] = None

def main():
    with st.sidebar:
        # ✅ CSS para replicar EXATAMENTE o estilo da FOTO 2 (cards na sidebar)
        st.markdown("""
        <style>
        div[data-testid="stSidebar"] div.stButton > button {
            background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%) !important;
            border: 1px solid #334155 !important;
            border-radius: 10px !important;
            padding: 12px 16px !important;
            margin: 6px 0 !important;
            color: #e2e8f0 !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            transition: all 0.2s ease !important;
            width: 100% !important;
            box-shadow: none !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }
        div[data-testid="stSidebar"] div.stButton > button:hover {
            border-color: #60a5fa !important;
            transform: translateX(4px) !important;
        }
        /* Destaque do botão ativo (igual FOTO 2) */
        div[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
            background: linear-gradient(145deg, #1e3a8a 0%, #1e40af 100%) !important;
            border-color: #3b82f6 !important;
            color: #ffffff !important;
            box-shadow: 0 0 0 1px #3b82f6 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        st.title("Navegação")

        # Ordem correta conforme solicitado
        pages = [
            ("home", "🏠 Home"),
            ("analise", "🔍 Análise"),
            ("rankings", " Rankings"),
            ("comparativo", " Comparativo"),
            ("configuracoes", "⚙️ Configurações")
        ]

        for key, label in pages:
            is_active = st.session_state["pagina_atual"] == key
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_{key}", use_container_width=True, type=btn_type):
                st.session_state["pagina_atual"] = key
                st.rerun()

        st.markdown("---")
        st.caption("Sobral Invest v1.0")

    # Roteador centralizado
    pagina = st.session_state.get("pagina_atual", "home")
    
    if pagina == "home":
        pagina_inicial()
    elif pagina == "analise":
        pagina_analise()
    elif pagina == "rankings":
        pagina_rankings()
    elif pagina == "comparativo":
        pagina_comparativo()
    elif pagina == "configuracoes":
        pagina_configuracoes()

if __name__ == "__main__":
    main()
