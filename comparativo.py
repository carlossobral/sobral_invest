import streamlit as st
import plotly.graph_objects as go
from data import load_data

def pagina_comparativo():
    """Pagina de comparativo de ativos."""
    st.markdown('<h1 class="main-header">📊 Comparativo</h1>', unsafe_allow_html=True)

    with st.spinner("Preparando comparação de ativos..."):
        df = load_data()
        
    if df.empty:
        st.warning("Dados nao disponiveis.")
        return

    tickers = st.multiselect("Selecione ate 5 ativos", sorted(df["Ticker"].tolist()), max_selections=5)
    if len(tickers) < 2:
        st.info("Selecione pelo menos 2 ativos para comparar.")
        return

    selecionados = df[df["Ticker"].isin(tickers)]

    # Radar comparativo
    categorias = ["ROE", "DY", "Margem Liquida", "ROIC", "CAGR Lucros"]
    fig = go.Figure()

    for _, row in selecionados.iterrows():
        valores = [
            min(row.get("ROE", 0) / 30 * 100, 100),
            min(row.get("DY", 0) / 10 * 100, 100),
            min(row.get("MargemLiquida", 0) / 20 * 100, 100),
            min(row.get("ROIC", 0) / 20 * 100, 100),
            min(row.get("CAGR_Lucros_5a", 0) / 15 * 100, 100),
        ]
        fig.add_trace(go.Scatterpolar(
            r=valores + [valores[0]],
            theta=categorias + [categorias[0]],
            fill='toself',
            name=row['Ticker']
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabela comparativa
    st.subheader("📋 Tabela Comparativa")
    cols_comp = ["Ticker", "Nome", "Cotacao", "DY", "PL", "PVP", "ROE", "ROIC", "MargemLiquida", "Score_CS"]
    st.dataframe(selecionados[[c for c in cols_comp if c in selecionados.columns]], hide_index=True, use_container_width=True)
