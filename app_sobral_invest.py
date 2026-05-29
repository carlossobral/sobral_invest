import streamlit as st
from home import pagina_inicial
from analise import pagina_analise
from rankings import pagina_rankings
from comparativo import pagina_comparativo
from configs import pagina_configuracoes

import os
from datetime import datetime

def debug_log(message):
    with open(os.path.join(os.path.dirname(__file__), "data", "debug_indic.log"), "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} - {message}\n")

# Configuração da página
st.set_page_config(page_title="Sobral Invest", page_icon="📊", layout="wide")

# Inicialização do estado
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "home"
if "ticker_destino" not in st.session_state:
    st.session_state["ticker_destino"] = None

def render_header(pagina):
    """Renderiza o Header Unificado (Marca + Breadcrumb Contextual)."""
    
    # Lógica de Breadcrumb Dinâmico
    titulo_pagina = ""
    subtitulo = ""
    
    if pagina == "home":
        titulo_pagina = "🏠 Home"
        subtitulo = "Dashboard & Mercado"
    elif pagina == "analise":
        titulo_pagina = "🔍 Análise"
        ticker = st.session_state.get("ticker_destino")
        if ticker:
            subtitulo = f"Ativo: {ticker}"
        else:
            subtitulo = "Selecione um ativo"
    elif pagina == "rankings":
        titulo_pagina = "🏆 Rankings"
        subtitulo = "Top 50 Ativos & Valuation"
    elif pagina == "comparativo":
        titulo_pagina = "📊 Comparativo"
        subtitulo = "Análise Relativa"
    elif pagina == "configuracoes":
        titulo_pagina = "️ Configurações"
        subtitulo = "Estatísticas & Info"

    st.markdown(f"""
    <style>
    .header-container {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #334155;
        padding-bottom: 16px;
        margin-bottom: 24px;
        margin-top: -10px; /* Compensa margem padrão do streamlit */
    }}
    .header-brand {{
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    .header-brand-icon {{ font-size: 1.8rem; }}
    .header-brand-name {{
        font-size: 1.4rem;
        font-weight: 800;
        color: #f1f5f9;
        letter-spacing: -0.03em;
        line-height: 1.2;
    }}
    .header-brand-tag {{
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 500;
    }}
    .header-context {{
        text-align: right;
    }}
    .header-page-title {{
        font-size: 1.1rem;
        font-weight: 600;
        color: #38bdf8; /* Azul destaque */
        margin-bottom: 2px;
    }}
    .header-subtitle {{
        font-size: 0.8rem;
        color: #94a3b8;
    }}
    </style>
    
    <div class="header-container">
        <div class="header-brand">
            <div class="header-brand-icon"></div>
            <div>
                <div class="header-brand-name">SOBRAL Invest</div>
                <div class="header-brand-tag">Análise Fundamentalista & Valuation</div>
            </div>
        </div>
        <div class="header-context">
            <div class="header-page-title">{titulo_pagina}</div>
            <div class="header-subtitle">{subtitulo}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def main():
    # 1. Renderiza o Header Unificado no topo
    render_header(st.session_state["pagina_atual"])
    debug_log(f"Rendered header for page: {st.session_state.get('pagina_atual', 'unknown')}")

    # 2. Sidebar com navegação estilo Card (Foto 2)
    with st.sidebar:
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
        div[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
            background: linear-gradient(145deg, #1e3a8a 0%, #1e40af 100%) !important;
            border-color: #3b82f6 !important;
            color: #ffffff !important;
            box-shadow: 0 0 0 1px #3b82f6 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("<div style='font-size: 1.1rem; font-weight: 700; color: #f1f5f9; margin-bottom: 12px;'>Navegação</div>", unsafe_allow_html=True)

        # Ordem correta conforme solicitado
        pages = [
            ("home", "🏠 Home"),
            ("analise", "🔍 Análise"),
            ("rankings", "🏆 Rankings"),
            ("comparativo", "📊 Comparativo"),
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

    # 3. Roteador centralizado
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
# Updated for deployment
