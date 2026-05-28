import streamlit as st
from data import load_data

def pagina_rankings():
    st.markdown('<h1 class="main-header">🏆 Rankings</h1>', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Dados nao disponiveis.")
        return

    # Filtro de nomes válidos
    df = df[df['Nome'] != '#N/A']
    df = df[df['Nome'].notna()]
    df = df[df['Nome'].str.strip() != '']
    df = df[df['Nome'].str.strip() != 'nan']

    if df.empty:
        st.warning("Nenhum ativo valido encontrado apos filtro de Nome.")
        return

    # CSS: Botão estilizado como link + cards
    st.markdown("""
    <style>
    /* Botão Streamlit transformado em link */
    div[data-testid="stButton"] > button[kind="secondary"] {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        color: #38bdf8 !important;
        text-decoration: underline !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        cursor: pointer !important;
        width: auto !important;
        min-width: 0 !important;
        box-shadow: none !important;
        margin: 0 auto 4px auto !important;
        display: block !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        color: #60a5fa !important;
        text-decoration: none !important;
    }
    
    .ranking-card {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 4px 10px 14px 10px;
        margin-bottom: 0.75rem;
        transition: all 0.3s ease;
        text-align: center;
        height: 100%;
    }
    .ranking-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        border-color: #3b82f6;
    }
    .ranking-nome {
        font-size: 0.72rem;
        color: #94a3b8;
        margin: 0 0 8px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
    }
    .ranking-valor {
        font-size: 1.35rem;
        font-weight: 800;
        color: #38bdf8;
        margin: 6px 0;
        line-height: 1.1;
    }
    .ranking-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.68rem;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #334155;
    }
    .ranking-score { font-weight: 700; }
    .ranking-setor { color: #64748b; font-weight: 500; }
    .ranking-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    </style>
    """, unsafe_allow_html=True)

    # Filtros
    setores = ["Todos"] + sorted([str(x) for x in df['Setor'].dropna().unique().tolist() if str(x) not in ['nan', 'N/A', '#N/A', '']])
    subsetores = ["Todos"] + sorted([str(x) for x in df['SubSetor'].dropna().unique().tolist() if str(x) not in ['nan', 'N/A', '#N/A', '']])

    rankings = [
        "Selecione um Ranking...",
        "Maior Valor de Mercado",
        "Maiores Lucros",
        "Maiores Receitas",
        "Maiores Dividend Yield",
        "Menores P/L",
        "Maiores ROE",
        "Maior Upside AGF Medio",
        "Mais Baratas — Graham",
        "Mais Baratas — Bazin",
        "Menores P/VP",
        "Menor EV/EBIT
