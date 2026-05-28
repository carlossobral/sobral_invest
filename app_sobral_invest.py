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
    # Sidebar com navegação ORIGINAL (radio) + ordem correta
    with st.sidebar:
        st.title("Navegação")
        
        opcoes = ["home", "analise", "rankings", "comparativo", "configuracoes"]
        labels = ["🏠 Home", "🔍 Análise", "🏆 Rankings", "📊 Comparativo", "⚙️ Configurações"]
        
        # Mapeia o índice atual para o radio
        indice_atual = opcoes.index(st.session_state["pagina_atual"]) if st.session_state["pagina_atual"] in opcoes else 0
        
        pagina_escolhida = st.radio(
            "Selecione a página",
            labels,
            index=indice_atual,
            key="nav_radio",
            label_visibility="collapsed"
        )
        
        # Converte label de volta para chave interna
        pagina_key = opcoes[labels.index(pagina_escolhida)]
        
        # Atualiza estado se mudou via radio
        if pagina_key != st.session_state["pagina_atual"]:
            st.session_state["pagina_atual"] = pagina_key
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
