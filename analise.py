import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from data import load_data

# Dicionario de descricoes para tooltips
TOOLTIP_DESC = {
    "P/L (PL)": "Preco / Lucro. Indica quantos anos de lucro seriam necessarios para pagar o preco da acao. Quanto menor, mais barata.",
    "P/VP (PVP)": "Preco / Valor Patrimonial. Mostra se a acao esta negociando acima ou abaixo do valor contabil. < 1 = abaixo do patrimonio.",
    "P/E (PE)": "Price / Earnings Ratio. Versao americana do P/L. Mesma interpretacao: quanto menor, mais barata.",
    "EPS": "Earnings Per Share. Lucro liquido dividido pelo numero de acoes. Quanto maior, mais lucrativa a empresa por acao.",
    "PSR (P/Receita)": "Preco / Receita. Util para empresas que ainda nao tem lucro. < 1 e considerado atraente.",
    "P/Ativo": "Preco / Ativo Total. Indica quanto o mercado paga pelos ativos da empresa. Util para holdings.",
    "P/Cap.Giro": "Preco / Capital de Giro. Mede a relacao entre preco e o capital de giro da empresa.",
    "P/Ativo Circ. Liq.": "Preco / Ativo Circulante Liquido. Negativo pode indicar empresa com mais caixa que dividas de curto prazo.",
    "P/EBIT": "Preco / EBIT. Valuation baseado no lucro operacional antes de juros e impostos.",
    "P/EBITDA": "Preco / EBITDA. Elimina efeitos de depreciacao. Util para comparar empresas de setores diferentes.",
    "EV/EBIT": "Enterprise Value / EBIT. Considera divida liquida. Melhor que P/EBIT para comparar empresas alavancadas.",
    "EV/EBITDA": "EV / EBITDA. O valuation mais completo: considera divida, depreciacao e lucro operacional.",
    "ROE": "Return on Equity. Retorno sobre o Patrimonio Liquido. > 15% e excelente. Mede eficiencia na geracao de lucro.",
    "ROA": "Return on Assets. Retorno sobre Ativos. Mede eficiencia total da empresa em gerar lucro com todos os recursos.",
    "ROIC": "Return on Invested Capital. Retorno sobre Capital Investido. > 10% e bom. Considera divida + patrimonio.",
    "Giro Ativos": "Receita / Ativos Totais. Mede quantas vezes a empresa 'gira' seus ativos em receita no ano.",
    "Margem Bruta": "(Receita - CMV) / Receita. Lucro antes de despesas operacionais. > 30% e bom para maioria dos setores.",
    "Margem EBITDA": "EBITDA / Receita. Lucro operacional antes de depreciacao. Mostra eficiencia operacional pura.",
    "Margem EBIT": "EBIT / Receita. Lucro operacional. > 10% indica empresa com bom controle de custos.",
    "Margem Liquida": "Lucro Liquido / Receita. Lucro final apos todas as despesas e impostos. > 5% e saudavel.",
    "Div.Liq / Ativos": "Divida Liquida / Ativos. < 0.5 indica empresa com pouca alavancagem financeira.",
    "Div.Liq / PL": "Divida Liquida / Patrimonio. < 1 e ideal: patrimonio maior que divida.",
    "Div.Liq / EBIT": "Divida Liquida / EBIT. Indica quantos anos de lucro operacional levaria para quitar dividas. < 3 e bom.",
    "Div.Liq / EBITDA": "Divida Liquida / EBITDA. < 2.5 e considerado saudavel pelo Score CS. Principal indicador de endividamento.",
    "Liquidez Corrente": "Ativo Circulante / Passivo Circulante. > 1 indica capacidade de pagar dividas de curto prazo.",
    "Passivos / Ativos": "Passivo Total / Ativo Total. < 0.7 indica estrutura de capital conservadora.",
    "PL / Ativos": "Patrimonio / Ativos. Quanto maior, mais capital proprio a empresa tem vs. capital de terceiros.",
    "LPA": "Lucro Por Acao. Lucro liquido dividido por numero de acoes. Base para calculo do P/L.",
    "VPA": "Valor Patrimonial Por Acao. Patrimonio liquido dividido por acoes. Base para calculo do P/VP.",
    "Patrimonio Liq.": "Patrimonio Liquido total da empresa. Ativos - Passivos. Representa o valor contabil.",
    "Lucro Liquido": "Lucro apos todas as despesas, impostos e juros. O resultado final para acionistas.",
    "EBIT": "Earnings Before Interest and Taxes. Lucro operacional antes de juros e impostos. Mede eficiencia do negocio.",
    "Receita Liq.": "Receita Liquida total. Faturamento bruto menos impostos, devolucoes e descontos.",
    "CAGR Receitas 5a": "Compound Annual Growth Rate de Receitas. Taxa media anual de crescimento nos ultimos 5 anos.",
    "CAGR Lucros 5a": "CAGR de Lucros. Taxa media anual de crescimento do lucro nos ultimos 5 anos. > 5% e positivo.",
    "Qtd. de Acoes": "Numero total de acoes emitidas pela empresa. Usado para calcular LPA, VPA e EPS.",
    "DY Atual": "Dividend Yield dos ultimos 12 meses. Dividendos pagos / Preco atual. > 6% e atrativo para renda.",
    "DY 12 meses": "Dividend Yield medio dos ultimos 12 meses. Media historica mais estavel que o DY atual.",
    "Div. Medio 12m": "Media dos dividendos pagos nos ultimos 12 meses. Indica previsibilidade de renda.",
    "Div. Total 12m": "Soma total dos dividendos pagos nos ultimos 12 meses. Util para projecao anual.",
    "Div. Ultimo": "Valor do ultimo dividendo pago. Util para identificar tendencia de aumento ou reducao.",
    "Qtd. Div. 12m": "Quantidade de pagamentos de dividendos no ano. Mensal = 12, trimestral = 4, semestral = 2.",
    "Graham": "Preco Justo por Graham: raiz(22.5 x VPA x LPA). Formula classica de Benjamin Graham para valor intrinseco.",
    "Graham BR": "Preco Justo Graham ajustado para Brasil. Considera peculiaridades do mercado brasileiro.",
    "Bazin": "Preco Justo por Bazin: Dividendo Medio / 0.06. Baseado em DY de 6% (teto de Bazin para compra).",
    "Lynch": "Preco Justo por Lynch: PEG Ratio. Relaciona crescimento com valuation. < 1 indica subvalorizada.",
    "AGF Medio": "Preco Justo Medio das 4 formulas (Graham, Graham_BR, Bazin, Lynch). Consenso de valuation.",
}

def get_semantic_color(metric_label, value_str):
    """Retorna cor semantica financeira baseada no tipo do indicador."""
    try:
        clean = value_str.replace('R$', '').replace('x', '').replace('%', '').replace('+', '').replace('-', '').strip()
        val = float(clean)
    except:
        return "#94a3b8"  # Cinza neutro para erros ou N/A

    label = metric_label.lower()
    
    # Indicadores onde MENOR é melhor (Dívida, Multiplos de Preço)
    if any(k in label for k in ["p/l", "p/vp", "ev/ebit", "div.liq", "passivos", "psr"]):
        if val < 10: return "#10b981"  # Verde (Bom)
        if val < 20: return "#f59e0b"  # Amarelo (Atencao)
        return "#ef4444"               # Vermelho (Alto/Ruim)
    
    # Indicadores onde MAIOR é melhor (Rentabilidade, Margens, Crescimento, DY)
    if any(k in label for k in ["roe", "roic", "margem", "dy ", "cagr", "upside", "score", "roa"]):
        if val > 15: return "#10b981"  # Verde (Bom)
        if val > 5:  return "#f59e0b"  # Amarelo (Medio)
        return "#ef4444"               # Vermelho (Baixo/Ruim)
        
    # Neutros (Preços, Volumes, Nomes, LPA, VPA, Quantidades)
    return "#38bdf8"

def tooltip_html(label_text):
    desc = TOOLTIP_DESC.get(label_text, "")
    if desc:
        return f'<span class="tooltip-container"><span class="tooltip-icon">?</span><span class="tooltip-text">{desc}</span></span>'
    return ""

def pagina_analise():
    """Pagina de analise de ativo estilo Investidor10 - Layout v2.0 Cards."""

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    .analise-container * { font-family: 'Inter', sans-serif; }
    .analise-container { padding: 0 8px 40px 8px; }

    .section-title-v2 {
        font-size: 1.05rem;
        font-weight: 700;
        color: #f1f5f9;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 40px 0 22px 0;
        padding-bottom: 10px;
        border-bottom: 2px solid #334155;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .metric-card-v2 {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px 16px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 95px;
    }
    .metric-card-v2:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(0,0,0,0.25);
        border-color: #3b82f6;
    }

    .metric-label-v2 {
        font-size: 0.72rem;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 10px;
        line-height: 1.3;
    }

    .metric-value-v2 {
        font-size: 1.45rem;
        font-weight: 700;
        color: #f1f5f9;
        line-height: 1.1;
        letter-spacing: -0.02em;
    }

    .score-card-v2 { border-radius: 16px; padding: 24px; text-align: center; box-shadow: 0 10px 15px rgba(0,0,0,0.2); }
    .score-number-v2 { font-size: 3.5rem; font-weight: 800; line-height: 1; margin-bottom: 8px; }
    .score-label-v2 { font-size: 1.1rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; }
    .score-desc-v2 { font-size: 0.8rem; color: #94a3b8; margin-top: 6px; }
    
    .bh-card-v2 { background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border: 2px solid; border-radius: 12px; padding: 14px; text-align: center; transition: all 0.3s ease; }
    .bh-card-v2:hover { transform: translateY(-2px); box-shadow: 0 6px 10px rgba(0,0,0,0.2); }
    .bh-icon-v2 { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-size: 16px; font-weight: 700; color: white; }
    .bh-title-v2 { font-size: 0.75rem; font-weight: 600; color: #f1f5f9; margin-bottom: 2px; line-height: 1.2; }
    .bh-desc-v2 { font-size: 0.65rem; color: #94a3b8; line-height: 1.2; }
    
    .pj-card-v2 { background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 12px; padding: 16px; text-align: center; transition: all 0.3s ease; }
    .pj-card-v2:hover { transform: translateY(-2px); box-shadow: 0 8px 12px rgba(0,0,0,0.2); }
    .pj-title-v2 { font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; }
    .pj-valor-v2 { font-size: 1.2rem; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
    .pj-upside-v2 { font-size: 0.9rem; font-weight: 600; padding: 3px 10px; border-radius: 12px; display: inline-block; }
    
    .tooltip-container { position: relative; display: inline-block; }
    .tooltip-icon { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; border-radius: 50%; background: #475569; color: #f1f5f9; font-size: 11px; font-weight: 700; cursor: help; margin-left: 6px; transition: all 0.2s ease; }
    .tooltip-icon:hover { background: #3b82f6; }
    .tooltip-text { visibility: hidden; width: 280px; background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border: 1px solid #475569; color: #e2e8f0; text-align: left; border-radius: 10px; padding: 12px 14px; position: absolute; z-index: 1000; bottom: 125%; left: 50%; margin-left: -140px; opacity: 0; transition: opacity 0.3s; font-size: 0.8rem; line-height: 1.4; box-shadow: 0 10px 15px rgba(0,0,0,0.3); }
    .tooltip-text::after { content: ""; position: absolute; top: 100%; left: 50%; margin-left: -5px; border-width: 5px; border-style: solid; border-color: #475569 transparent transparent transparent; }
    .tooltip-container:hover .tooltip-text { visibility: visible; opacity: 1; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="analise-container">', unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("Dados nao disponiveis.")
        return

    # ============================================================
    # 1. SELETOR DE ATIVO
    # ============================================================
    df['Display'] = df['Ticker'] + ' - ' + df['Nome']
    display_list = sorted([str(x) for x in df['Display'].tolist()])

    ticker_from_ranking = st.session_state.get("ticker_destino")

    default_index = 0
    if ticker_from_ranking:
        for i, disp in enumerate(display_list):
            if disp.startswith(ticker_from_ranking + ' -'):
                default_index = i
                break
        if "ticker_destino" in st.session_state:
            del st.session_state["ticker_destino"]

    ativo_selecionado = st.selectbox(
        "Selecione o ativo",
        options=display_list,
        index=default_index,
        key="ativo_selector_v2"
    )

    ticker = ativo_selecionado.split(' - ')[0]
    ativo = df[df['Ticker'] == ticker].iloc[0] if len(df[df['Ticker'] == ticker]) > 0 else None

    if ativo is None:
        st.error("Ativo nao encontrado.")
        return

    # ============================================================
    # INFO DO ATIVO - SETOR/SUBSETOR/SEGMENTO
    # ============================================================
    st.markdown(f"""
    <div style="display: flex; gap: 24px; margin: 8px 0 16px 0; padding: 0;">
        <div><span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Setor</span><span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('Setor', 'N/A')}</span></div>
        <div style="color: #475569;">&rsaquo;</div>
        <div><span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">SubSetor</span><span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('SubSetor', 'N/A')}</span></div>
        <div style="color: #475569;">&rsaquo;</div>
        <div><span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Segmento</span><span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('Segmento', 'N/A')}</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 16px 0;'></div>", unsafe_allow_html=True)

    # ============================================================
    # WIDGET TRADINGVIEW DO ATIVO
    # ============================================================
    tv_symbol = f"BMFBOVESPA:{ticker}"
    tv_chart = f"""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
      {{"symbols": [["{tv_symbol}|1D"]], "chartOnly": false, "width": "100%", "height": "350", "locale": "br", "colorTheme": "dark", "autosize": false, "showVolume": true, "showMA": false, "hideDateRanges": false, "hideMarketStatus": false, "hideSymbolLogo": false, "scalePosition": "right", "scaleMode": "Normal", "fontFamily": "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif", "fontSize": "10", "noTimeScale": false, "valuesTracking": "1", "changeMode": "price-and-percent", "chartType": "area", "maLineColor": "#2962FF", "maLineWidth": 1, "maLength": 9, "lineWidth": 2, "lineType": 0, "dateRanges": ["1d|1", "1m|30", "3m|60", "12m|1D", "60m|1W", "all|1M"]}}
      </script>
    </div>
    """
    components.html(tv_chart, height=360)

    # ============================================================
    # 3. VALUATION - 6 colunas x 2 linhas
    # ============================================================
    st.markdown('<div class="section-title-v2">Valuation</div>', unsafe_allow_html=True)

    valuation_data = [
        ("P/L (PL)", f"{ativo.get('PL', 0):.2f}x"),
        ("P/VP (PVP)", f"{ativo.get('PVP', 0):.2f}x"),
        ("P/E (PE)", f"{ativo.get('PE', 0):.2f}x"),
        ("EPS", f"R$ {ativo.get('EPS', 0):.2f}"),
        ("PSR (P/Receita)", f"{ativo.get('PSR', 0):.2f}x"),
        ("P/Ativo", f"{ativo.get('PAtivo', 0):.2f}x"),
        ("P/Cap.Giro", f"{ativo.get('PCapGiro', 0):.2f}x"),
        ("P/Ativo Circ. Liq.", f"{ativo.get('PAtivoCircLiq', 0):.2f}x"),
        ("P/EBIT", f"{ativo.get('PEBIT', 0):.2f}x"),
        ("P/EBITDA", f"{ativo.get('PEBITDA', 0):.2f}x"),
        ("EV/EBIT", f"{ativo.get('EV_EBIT', 0):.2f}x"),
        ("EV/EBITDA", f"{ativo.get('EV_EBITDA', 0):.2f}x"),
    ]

    for row_idx in range(2):
        cols = st.columns(6)
        for col_idx in range(6):
            idx = row_idx * 6 + col_idx
            if idx < len(valuation_data):
                label, value = valuation_data[idx]
                sem_color = get_semantic_color(label, value)
                cols[col_idx].markdown(f"""
                <div class="metric-card-v2" style="border-left: 4px solid {sem_color};">
                    <div class="metric-label-v2">{label}{tooltip_html(label)}</div>
                    <div class="metric-value-v2" style="color: {sem_color};">{value}</div>
                </div>
                """, unsafe_allow_html=True)

    # ============================================================
    # 4. RENTABILIDADE - 4 colunas x 2 linhas
    # ============================================================
    st.markdown('<div class="section-title-v2">Rentabilidade</div>', unsafe_allow_html=True)

    rent_data = [
        ("ROE", f"{ativo.get('ROE', 0):.2f}%"),
        ("ROA", f"{ativo.get('ROA', 0):.2f}%"),
        ("ROIC", f"{ativo.get('ROIC', 0):.2f}%"),
        ("Giro Ativos", f"{ativo.get('GiroAtivos', 0):.2f}x"),
        ("Margem Bruta", f"{ativo.get('MargemBruta', 0):.2f}%"),
        ("Margem EBITDA", f"{ativo.get('MargemEBITDA', 0):.2f}%"),
        ("Margem EBIT", f"{ativo.get('MargemEBIT', 0):.2f}%"),
        ("Margem Liquida", f"{ativo.get('MargemLiquida', 0):.2f}%"),
    ]

    for row_idx in range(2):
        cols = st.columns(4)
        for col_idx in range(4):
            idx = row_idx * 4 + col_idx
            if idx < len(rent_data):
                label, value = rent_data[idx]
                sem_color = get_semantic_color(label, value)
                cols[col_idx].markdown(f"""
                <div class="metric-card-v2" style="border-left: 4px solid {sem_color};">
                    <div class="metric-label-v2">{label}{tooltip_html(label)}</div>
                    <div class="metric-value-v2" style="color: {sem_color};">{value}</div>
                </div>
                """, unsafe_allow_html=True)

    # ============================================================
    # 5. ENDIVIDAMENTO - 4 colunas x 2 linhas
    # ============================================================
    st.markdown('<div class="section-title-v2">Endividamento</div>', unsafe_allow_html=True)

    endiv_data = [
        ("Div.Liq / Ativos", f"{ativo.get('DivLiquida_Ativos', 0):.2f}x"),
        ("Div.Liq / PL", f"{ativo.get('DivLiquida_PL', 0):.2f}x"),
        ("Div.Liq / EBIT", f"{ativo.get('DivLiquida_EBIT', 0):.2f}x"),
        ("Div.Liq / EBITDA", f"{ativo.get('DivLiquida_EBITDA', 0):.2f}x"),
        ("Liquidez Corrente", f"{ativo.get('LiquidezCorrente', 0):.2f}x"),
        ("Passivos / Ativos", f"{ativo.get('Passivos_Ativos', 0):.2f}x"),
        ("PL / Ativos", f"{ativo.get('PL_Ativos', 0):.2f}x"),
    ]

    for row_idx in range(2):
        cols = st.columns(4)
        for col_idx in range(4):
            idx = row_idx * 4 + col_idx
            if idx < len(endiv_data):
                label, value = endiv_data[idx]
                sem_color = get_semantic_color(label, value)
                cols[col_idx].markdown(f"""
                <div class="metric-card-v2" style="border-left: 4px solid {sem_color};">
                    <div class="metric-label-v2">{label}{tooltip_html(label)}</div>
                    <div class="metric-value-v2" style="color: {sem_color};">{value}</div>
                </div>
                """, unsafe_allow_html=True)

    # ============================================================
    # 6. RESULTADO - 6 colunas x 1 linha
    # ============================================================
    st.markdown('<div class="section-title-v2">Resultado</div>', unsafe_allow_html=True)

    res_data = [
        ("LPA", f"R$ {ativo.get('LPA', 0):.2f}"),
        ("VPA", f"R$ {ativo.get('VPA', 0):.2f}"),
        ("Patrimonio Liq.", f"R$ {ativo.get('Patrimonio', 0)/1e9:.2f}B"),
        ("Lucro Liquido", f"R$ {ativo.get('Lucro_Liquido', 0)/1e9:.2f}B"),
        ("EBIT", f"R$ {ativo.get('EBIT', 0)/1e9:.2f}B"),
        ("Receita Liq.", f"R$ {ativo.get('Receita_Liquida', 0)/1e9:.2f}B"),
    ]

    cols_res = st.columns(6)
    for i, (label, value) in enumerate(res_data):
        sem_color = get_semantic_color(label, value)
        cols_res[i].markdown(f"""
        <div class="metric-card-v2" style="border-left: 4px solid {sem_color};">
            <div class="metric-label-v2">{label}{tooltip_html(label)}</div>
            <div class="metric-value-v2" style="color: {sem_color};">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # 7. CRESCIMENTO - 1 linha
    # ============================================================
    st.markdown('<div class="section-title-v2">Crescimento</div>', unsafe_allow_html=True)

    cresc_data = [
        ("CAGR Receitas 5a", f"{ativo.get('CAGR_Receitas_5a', 0):.2f}%"),
        ("CAGR Lucros 5a", f"{ativo.get('CAGR_Lucros_5a', 0):.2f}%"),
        ("Qtd. de Acoes", f"{ativo.get('Qtd_Acoes', 0)/1e9:.2f}B"),
    ]

    cols_cresc = st.columns(3)
    for i, (label, value) in enumerate(cresc_data):
        sem_color = get_semantic_color(label, value)
        cols_cresc[i].markdown(f"""
        <div class="metric-card-v2" style="border-left: 4px solid {sem_color};">
            <div class="metric-label-v2">{label}{tooltip_html(label)}</div>
            <div class="metric-value-v2" style="color: {sem_color};">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # 8. DIVIDENDOS - Linha Única (5 cards + badge de consistência)
    # ============================================================
    st.markdown('<div class="section-title-v2">Dividendos</div>', unsafe_allow_html=True)

    current_year = datetime.now().year
    div_cards = [
        ("DIVI 1A", f"R$ {ativo.get('DIV_1A_', 0):.4f}", str(ativo.get('DIV_1A_', 0) > 0), current_year - 1),
        ("DIVI 2A", f"R$ {ativo.get('DIV_2A_', 0):.4f}", str(ativo.get('DIV_2A_', 0) > 0), current_year - 2),
        ("DIVI 3A", f"R$ {ativo.get('DIV_3A_', 0):.4f}", str(ativo.get('DIV_3A_', 0) > 0), current_year - 3),
        ("DIVI 4A", f"R$ {ativo.get('DIV_4A_', 0):.4f}", str(ativo.get('DIV_4A_', 0) > 0), current_year - 4),
        ("DIVI 5A", f"R$ {ativo.get('DIV_5A_', 0):.4f}", str(ativo.get('DIV_5A_', 0) > 0), current_year - 5),
    ]

    # Badge de consistência (6ª coluna)
    anos_pagos = int(ativo.get('DY_5A_PG', 0))
    cons_badge = f"✅ {anos_pagos}/5" if anos_pagos >= 3 else f"⚠️ {anos_pagos}/5"
    cons_color = "#10b981" if anos_pagos >= 3 else "#f59e0b"
    div_cards.append(("CONSISTÊNCIA", cons_badge, "true", None))

    cols_div = st.columns(6)
    for i, (label, value, has_payment, year) in enumerate(div_cards):
        is_consistency = (i == 5)
        sem_color = cons_color if is_consistency else ("#10b981" if has_payment == "True" else "#475569")
        
        year_display = f"<div style='font-size: 0.65rem; color: #64748b; margin-top: 4px;'>Ano: {year}</div>" if year else ""
        
        cols_div[i].markdown(f"""
        <div class="metric-card-v2" style="border-left: 4px solid {sem_color};">
            <div class="metric-label-v2">{label}</div>
            <div class="metric-value-v2" style="color: {sem_color};">{value}</div>
            {year_display}
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # 9. PRECO JUSTO - lado a lado com upside
    # ============================================================
    st.markdown('<div class="section-title-v2">Preco Justo</div>', unsafe_allow_html=True)

    pj_data = [
        ("Graham", ativo.get('Graham', 0), ativo.get('Upside_Graham', 0)),
        ("Graham BR", ativo.get('Graham_BR', 0), ativo.get('Upside_Graham_BR', 0)),
        ("Bazin", ativo.get('Bazin', 0), ativo.get('Upside_Bazin', 0)),
        ("Lynch", ativo.get('Lynch', 0), ativo.get('Upside_Lynch', 0)),
        ("AGF Medio", ativo.get('AGF_Medio', 0), ativo.get('Upside_AGF_Medio', 0)),
    ]

    cols_pj = st.columns(5)
    for i, (title, preco, upside) in enumerate(pj_data):
        try:
            upside_val = float(upside)
            if upside_val > 0:
                up_color, up_bg = "#10b981", "#065f46"
            elif upside_val < 0:
                up_color, up_bg = "#ef4444", "#991b1b"
            else:
                up_color, up_bg = "#94a3b8", "#475569"
        except:
            up_color, up_bg = "#94a3b8", "#475569"
            upside_val = 0

        preco_str = f"R$ {preco:.2f}" if preco > 0 else "N/A"
        upside_str = f"{upside_val:+.1f}%" if preco > 0 else "-"

        cols_pj[i].markdown(f"""
        <div class="pj-card-v2" style="border-left: 4px solid {up_color};">
            <div class="pj-title-v2">{title}</div>
            <div class="pj-valor-v2">{preco_str}</div>
            <div class="pj-upside-v2" style="background: {up_bg}40; color: {up_color};">{upside_str}</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # 10. SCORE CS (11 CRITÉRIOS - Consistência 5A ADICIONADO)
    # ============================================================
    st.markdown('<div class="section-title-v2">SCORE CS</div>', unsafe_allow_html=True)

    bh_items = [
        ("ROE > 10%", ativo.get('ROE_10pct', 0), "Rentabilidade do patrimonio"),
        ("DY > 6%", ativo.get('DY_6pct', 0), "Dividend Yield atrativo"),
        ("Div.Liq/EBITDA < 2.5", ativo.get('DivLiq_EBITDA_2_5', 0), "Endividamento controlado"),
        ("PL < 15", ativo.get('PL_15', 0), "Preco nao esta caro"),
        ("PVP < 2", ativo.get('PVP_2', 0), "Proximo do valor patrimonial"),
        ("Margem > 10%", ativo.get('Margem_10pct', 0), "Lucratividade saudavel"),
        ("Liq.Corrente > 1", ativo.get('LiqCorrente_1', 0), "Capacidade de pagamento"),
        ("CAGR > 5%", ativo.get('CAGR_5pct', 0), "Crescimento consistente"),
        ("ROIC > 10%", ativo.get('ROIC_10pct', 0), "Retorno sobre capital"),
        ("Volume > 1M", ativo.get('Volume_1M', 0), "Liquidez diaria"),
        
        # ✅ NOVO CRITÉRIO: Consistência de Dividendos 5 Anos
        ("Consistência 5A", 
         1 if (pd.notna(ativo.get('DY_5A_PG')) and int(ativo.get('DY_5A_PG', 0)) >= 3) else 0, 
         "Pagou dividendos em pelo menos 3 dos ultimos 5 anos"),
    ]

    # Calcula o score somando todos os criterios (11 no total)
    score = sum(item[1] for item in bh_items)

    # Classificacao visual do score
    if score >= 9:
        score_color, score_bg, score_label = "#10b981", "#065f46", "Excelente"
    elif score >= 7:
        score_color, score_bg, score_label = "#84cc16", "#3f6212", "Bom"
    elif score >= 5:
        score_color, score_bg, score_label = "#f59e0b", "#92400e", "Regular"
    elif score >= 3:
        score_color, score_bg, score_label = "#f97316", "#7c2d12", "Fraco"
    else:
        score_color, score_bg, score_label = "#dc2626", "#7f1d1d", "Pessimo"

    # Exibicao do card principal do Score
    score_cols = st.columns([2, 3, 2])
    with score_cols[1]:
        st.markdown(f"""
        <div class="score-card-v2" style="background: linear-gradient(135deg, {score_bg} 0%, {score_color}20 100%); border: 2px solid {score_color};">
            <div class="score-number-v2" style="color: {score_color};">{score}</div>
            <div class="score-label-v2" style="color: {score_color};">{score_label}</div>
            <div class="score-desc-v2">de 11 pontos</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

    # Exibicao dos cards individuais de cada criterio
    cols_bh = st.columns(5)
    for i, (title, value, desc) in enumerate(bh_items):
        is_true = bool(value) if not pd.isna(value) else False
        icon = "V" if is_true else "X"
        border_color = "#10b981" if is_true else "#ef4444"
        bg_icon = "#10b981" if is_true else "#ef4444"

        cols_bh[i % 5].markdown(f"""
        <div class="bh-card-v2" style="border-color: {border_color}60;">
            <div class="bh-icon-v2" style="background: {bg_icon};">{icon}</div>
            <div class="bh-title-v2">{title}</div>
            <div class="bh-desc-v2">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
