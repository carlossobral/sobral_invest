import streamlit as st
import pandas as pd
from data import load_data

def pagina_comparativo():
    st.markdown('<h1 class="main-header">📊 Comparativo de Ativos</h1>', unsafe_allow_html=True)
    
    df = load_data()
    if df.empty:
        st.warning("Dados não disponíveis.")
        return
    
    st.markdown("Selecione até 5 ativos para comparar")
    
    df['Display'] = df['Ticker'] + ' - ' + df['Nome']
    display_list = sorted([str(x) for x in df['Display'].tolist()])
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        ativo1 = st.selectbox("Ativo 1", ["Selecione..."] + display_list, key="comp_1")
    with col2:
        ativo2 = st.selectbox("Ativo 2", ["Selecione..."] + display_list, key="comp_2")
    with col3:
        ativo3 = st.selectbox("Ativo 3", ["Selecione..."] + display_list, key="comp_3")
    with col4:
        ativo4 = st.selectbox("Ativo 4", ["Selecione..."] + display_list, key="comp_4")
    with col5:
        ativo5 = st.selectbox("Ativo 5", ["Selecione..."] + display_list, key="comp_5")
    
    selecionados = [ativo1, ativo2, ativo3, ativo4, ativo5]
    selecionados = [s for s in selecionados if s != "Selecione..."]
    
    if len(selecionados) == 0:
        st.info("Selecione pelo menos um ativo para comparar.")
        return
    
    # Extrair tickers
    tickers = [s.split(' - ')[0] for s in selecionados]
    
    # Criar dataframe comparativo
    indicadores = ['Ticker', 'Nome', 'Setor', 'PL', 'PVP', 'ROE', 'ROIC', 'DY', 
                   'MargemLiquida', 'DivLiquida_EBITDA', 'CAGR_Lucros_5a', 'Score_CS']
    
    dados_comparativos = []
    for ticker in tickers:
        ativo = df[df['Ticker'] == ticker]
        if not ativo.empty:
            ativo = ativo.iloc[0]
            linha = {ind: ativo.get(ind, 'N/A') for ind in indicadores}
            dados_comparativos.append(linha)
    
    if dados_comparativos:
        df_comp = pd.DataFrame(dados_comparativos)
        
        st.markdown("### 📈 Comparação")
        st.dataframe(df_comp, use_container_width=True, hide_index=True)
        
        # Gráfico comparativo de Score CS
        if 'Score_CS' in df_comp.columns:
            st.markdown("### 📊 Score CS Comparativo")
            st.bar_chart(df_comp.set_index('Ticker')['Score_CS'])
