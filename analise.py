import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import ast
from datetime import datetime
from data import load_data

# ============================================================
# HELPER: Extração segura de valores (float, dict ou string-dict)
# ============================================================
def safe_val(val, default=0.0):
    """Extrai valor numérico de forma segura, lidando com floats, dicts ou strings de dict."""
    if pd.isna(val): return default
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        val = val.strip()
        if not val: return default
        try:
            d = ast.literal_eval(val)
            return float(d.get('value', default))
        except: pass
    if isinstance(val, dict):
        return float(val.get('value', default))
    try: return float(val)
    except: return default

# ============================================================
# TOOLTIPS
# ============================================================
TOOLTIP_DESC = {
    "P/L (PL)": "Preco / Lucro. Quanto menor, mais barata.",
    "P/VP (PVP)": "Preco / Valor Patrimonial. < 1 = abaixo do patrimonio.",
    "P/E (PE)": "Price / Earnings. Versao americana do P/L.",
    "EPS": "Earnings Per Share. Lucro por acao.",
    "PSR (P/Receita)": "Preco / Receita. < 1 e atrativo.",
    "P/Ativo": "Preco / Ativo Total. Quanto menor, melhor.",
    "P/Cap.Giro": "Preco / Capital de Giro.",
    "P/Ativo Circ. Liq.": "Preco / Ativo Circulante Liquido.",
    "P/EBIT": "Preco / EBIT. Valuation operacional.",
    "P/EBITDA": "Preco / EBITDA. Elimina depreciacao.",
    "EV/EBIT": "Enterprise Value / EBIT. Considera divida.",
    "EV/EBITDA": "EV / EBITDA. Valuation completo.",
    "ROE": "Return on Equity. > 15% excelente.",
    "ROA": "Return on Assets. Eficiencia total.",
    "ROIC": "Return on Invested Capital. > 10% bom.",
    "Giro Ativos": "Receita / Ativos. Eficiencia operacional.",
    "Margem Bruta": "Lucro antes de despesas operacionais.",
    "Margem EBITDA": "EBITDA / Receita. Eficiencia pura.",
    "Margem EBIT": "EBIT / Receita. Controle de custos.",
    "Margem Liquida": "Lucro Liquido / Receita. > 5% saudavel.",
    "Div.Liq / Ativos": "Divida Liquida / Ativos. < 0.5 bom.",
    "Div.Liq / PL": "Divida Liquida / Patrimonio. < 1 ideal.",
    "Div.Liq / EBIT": "Divida Liquida / EBIT. < 3 bom.",
    "Div.Liq / EBITDA": "Divida Liquida / EBITDA. < 2.5 saudavel.",
    "Liquidez Corrente": "Ativo Circ / Passivo Circ. > 1 capacidade de pagamento.",
    "Passivos / Ativos": "Passivo / Ativo. < 0.7 conservador.",
    "PL / Ativos": "Patrimonio / Ativos. Capital proprio.",
    "LPA": "Lucro Por Acao. Base do P/L.",
    "VPA": "Valor Patrimonial Por Acao. Base do P/VP.",
    "Patrimonio Liq.": "Valor contabil da empresa.",
    "Lucro Liquido": "Resultado final para acionistas.",
    "EBIT": "Lucro operacional antes de juros/impostos.",
    "Receita Liq.": "Faturamento bruto menos impostos.",
    "CAGR Receitas 5a": "Crescimento medio anual de receitas.",
    "CAGR Lucros 5a": "Crescimento medio anual de lucros.",
    "Qtd. de Acoes": "Total de acoes emitidas.",
    "DY Atual": "Dividend Yield 12 meses. > 6% atrativo.",
    "DY 12 meses": "Media historica de DY.",
    "Div. Medio 12m": "Media de dividendos 12m.",
    "Div. Total 12m": "Soma total 12m.",
    "Div. Ultimo": "Ultimo pagamento.",
    "Qtd. Div. 12m": "Frequencia de pagamentos.",
    "Graham": "Raiz(22.5 x VPA x LPA).",
    "Bazin": "Dividendo Medio / 0.06.",
    "Lynch": "PEG Ratio. < 1 subvalorizada.",
    "AGF Medio": "Media dos 4 valuation.",
}

def tooltip_html(label_text):
    desc = TOOLTIP_DESC.get(label_text, "")
    return f'<span class="tooltip-container"><span class="tooltip-icon">?</span><span class="tooltip-text">{desc}</span></span>' if desc else ""

def get_semantic_color(metric_label, value_str):
    try:
        clean = value_str.replace('R$', '').replace('x', '').replace('%', '').replace('+', '').replace('-', '').strip()
        val = float(clean)
    except:
        return "#94a3b8"
    label = metric_label.lower()
    if any(k in label for k in ["p/l", "p/vp", "ev/ebit", "div.liq", "passivos", "psr"]):
        if val < 10: return "#10b981"
        if val < 20: return "#f59e0b"
        return "#ef4444"
    if any(k in label for k in ["roe", "roic", "margem", "dy ", "cagr", "upside", "score", "roa"]):
        if val > 15: return "#10b981"
        if val > 5:  return "#f59e0b"
        return "#ef4444"
    return "#38bdf8"

def pagina_analise():
    """Pagina de analise de ativo - Layout v2.0 Cards (Ajustado para ativos.csv/xlsx)"""

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    .analise-container * { font-family: 'Inter', sans-serif; }
    .analise-container { padding: 0 8px 40px 8px; }
    .section-title-v2 { font-size: 1.05rem; font-weight: 700; color: #f1f5f9; text-transform: uppercase; letter-spacing: 0.1em; margin: 40px 0 22px 0; padding-bottom: 10px; border-bottom: 2px solid #334155; display: flex; align-items: center; gap: 10px; }
    .metric-card-v2 { background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 12px; padding: 18px 16px; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.1); height: 100%; display: flex; flex-direction: column; justify-content: space-between; min-height: 95px; }
    .metric-card-v2:hover { transform: translateY(-2px); box-shadow: 0 8px 12px rgba(0,0,0,0.25); border-color: #3b82f6; }
    .metric-label-v2 { font-size: 0.72rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; line-height: 1.3; }
    .metric-value-v2 { font-size: 1.45rem; font-weight: 700; color: #f1f5f9; line-height: 1.1; letter-spacing: -0.02em; }
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

    # SELETOR DE ATIVO
    df['Display'] = df['symbol'].astype(str) + ' - ' + df['name'].astype(str)
    display_list = sorted([str(x) for x in df['Display'].tolist()])

    ticker_from_ranking = st.session_state.get("ticker_destino")
    default_index = 0
    if ticker_from_ranking:
        for i, disp in enumerate(display_list):
            if disp.startswith(ticker_from_ranking + ' -'):
                default_index = i
                break
        st.session_state.pop("ticker_destino", None)

    ativo_selecionado = st.selectbox("Selecione o ativo", options=display_list, index=default_index, key="ativo_selector_v2")
    ticker = ativo_selecionado.split(' - ')[0]
    match = df[df['symbol'] == ticker]
    if match.empty:
        st.error("Ativo nao encontrado.")
        return
    ativo = match.iloc[0]

    # INFO SETOR/SUBSETOR/SEGMENTO
    st.markdown(f"""
    <div style="display: flex; gap: 24px; margin: 8px 0 16px 0; padding: 0;">
        <div><span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Setor</span><span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('sector', 'N/A')}</span></div>
        <div style="color: #475569;">&rsaquo;</div>
        <div><span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">SubSetor</span><span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('subSector', 'N/A')}</span></div>
        <div style="color: #475569;">&rsaquo;</div>
        <div><span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Segmento</span><span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('segment', 'N/A')}</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 16px 0;'></div>", unsafe_allow_html=True)

    # TRADINGVIEW
    tv_chart = f"""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
      {{"symbols": [["BMFBOVESPA:{ticker}|1D"]], "chartOnly": false, "width": "100%", "height": "350", "locale": "br", "colorTheme": "dark", "autosize": false, "showVolume": true, "showMA": false, "hideDateRanges": false, "hideMarketStatus": false, "hideSymbolLogo": false, "scalePosition": "right", "scaleMode": "Normal", "fontFamily": "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif", "fontSize": "10", "noTimeScale": false, "valuesTracking": "1", "changeMode": "price-and-percent", "chartType": "area", "maLineColor": "#2962FF", "maLineWidth": 1, "maLength": 9, "lineWidth": 2, "lineType": 0, "dateRanges": ["1d|1", "1m|30", "3m|60", "12m|1D", "60m|1W", "all|1M"]}}
      </script>
    </div>
    """
    components.html(tv_chart, height=360)

    # VALUATION
    st.markdown('<div class="section-title-v2">Valuation</div>', unsafe_allow_html=True)
    valuation_data = [
        ("P/L (PL)", f"{safe_val(ativo.get('pe')):.2f}x"),
        ("P/VP (PVP)", f"{safe_val(ativo.get('priceToBookValue')):.2f}x"),
        ("P/E (PE)", f"{safe_val(ativo.get('priceEarningsRatio', ativo.get('pe'))):.2f}x"),
        ("EPS", f"R$ {safe_val(ativo.get('eps')):.2f}"),
        ("PSR (P/Receita)", f"{safe_val(ativo.get('priceToSales')):.2f}x"),
        ("P/Ativo", f"{safe_val(ativo.get('priceToAssets')):.2f}x"),
        ("P/Cap.Giro", f"{safe_val(ativo.get('priceToNetNetWorkingCapital')):.2f}x"),
        ("P/Ativo Circ. Liq.", f"{safe_val(ativo.get('priceToNetCurrentAssets')):.2f}x"),
        ("P/EBIT", f"{safe_val(ativo.get('priceToEbit')):.2f}x"),
        ("P/EBITDA", f"{safe_val(ativo.get('priceToEbitda')):.2f}x"),
        ("EV/EBIT", f"{safe_val(ativo.get('enterpriseValueEbit')):.2f}x"),
        ("EV/EBITDA", f"{safe_val(ativo.get('enterpriseValueEbitda')):.2f}x"),
    ]
    for r in range(2):
        cols = st.columns(6)
        for c in range(6):
            idx = r * 6 + c
            if idx < len(valuation_data):
                lbl, val = valuation_data[idx]
                col = get_semantic_color(lbl, val)
                cols[c].markdown(f"""<div class="metric-card-v2" style="border-left: 4px solid {col};"><div class="metric-label-v2">{lbl}{tooltip_html(lbl)}</div><div class="metric-value-v2" style="color: {col};">{val}</div></div>""", unsafe_allow_html=True)

    # RENTABILIDADE
    st.markdown('<div class="section-title-v2">Rentabilidade</div>', unsafe_allow_html=True)
    rent_data = [
        ("ROE", f"{safe_val(ativo.get('ROE', ativo.get('returnOnEquity'))):.2f}%"),
        ("ROA", f"{safe_val(ativo.get('ROA', ativo.get('returnOnAssets'))):.2f}%"),
        ("ROIC", f"{safe_val(ativo.get('ROIC', ativo.get('returnOnInvestedCapital'))):.2f}%"),
        ("Giro Ativos", f"{safe_val(ativo.get('Giro ativos', ativo.get('assetTurnoverRatio'))):.2f}x"),
        ("Margem Bruta", f"{safe_val(ativo.get('M. Bruta', ativo.get('grossMargin'))):.2f}%"),
        ("Margem EBITDA", f"{safe_val(ativo.get('M. EBITDA', ativo.get('ebitdaMargin'))):.2f}%"),
        ("Margem EBIT", f"{safe_val(ativo.get('M. EBIT', ativo.get('ebitMargin'))):.2f}%"),
        ("Margem Liquida", f"{safe_val(ativo.get('M. Líquida', ativo.get('netMargin'))):.2f}%"),
    ]
    for r in range(2):
        cols = st.columns(4)
        for c in range(4):
            idx = r * 4 + c
            if idx < len(rent_data):
                lbl, val = rent_data[idx]
                col = get_semantic_color(lbl, val)
                cols[c].markdown(f"""<div class="metric-card-v2" style="border-left: 4px solid {col};"><div class="metric-label-v2">{lbl}{tooltip_html(lbl)}</div><div class="metric-value-v2" style="color: {col};">{val}</div></div>""", unsafe_allow_html=True)

    # ENDIVIDAMENTO
    st.markdown('<div class="section-title-v2">Endividamento</div>', unsafe_allow_html=True)
    endiv_data = [
        ("Div.Liq / Ativos", f"{safe_val(ativo.get('Div. líquida/Ativos', ativo.get('netDebtToAssets'))):.2f}x"),
        ("Div.Liq / PL", f"{safe_val(ativo.get('Dív. líquida/PL', ativo.get('netDebtToEquity'))):.2f}x"),
        ("Div.Liq / EBIT", f"{safe_val(ativo.get('Dív. líquida/EBIT', ativo.get('netDebtToEbit'))):.2f}x"),
        ("Div.Liq / EBITDA", f"{safe_val(ativo.get('Dív. líquida/EBITDA', ativo.get('netDebtToEbitda'))):.2f}x"),
        ("Liquidez Corrente", f"{safe_val(ativo.get('Liq. corrente', ativo.get('currentLiquidity'))):.2f}x"),
        ("Passivos / Ativos", f"{safe_val(ativo.get('Passivos/Ativos', ativo.get('liabilitiesToAssetsRatio'))):.2f}x"),
        ("PL / Ativos", f"{safe_val(ativo.get('PL/Ativos', ativo.get('equityToAssetsRatio'))):.2f}x"),
    ]
    for r in range(2):
        cols = st.columns(4)
        for c in range(4):
            idx = r * 4 + c
            if idx < len(endiv_data):
                lbl, val = endiv_data[idx]
                col = get_semantic_color(lbl, val)
                cols[c].markdown(f"""<div class="metric-card-v2" style="border-left: 4px solid {col};"><div class="metric-label-v2">{lbl}{tooltip_html(lbl)}</div><div class="metric-value-v2" style="color: {col};">{val}</div></div>""", unsafe_allow_html=True)

    # RESULTADO
    st.markdown('<div class="section-title-v2">Resultado</div>', unsafe_allow_html=True)
    res_data = [
        ("LPA", f"R$ {safe_val(ativo.get('earningsPerShare')):.2f}"),
        ("VPA", f"R$ {safe_val(ativo.get('bookValuePerShare')):.2f}"),
        ("Patrimonio Liq.", f"R$ {safe_val(ativo.get('Patrimonio_Liquido', ativo.get('marketCap')))/1e9:.2f}B"),
        ("Lucro Liquido", f"R$ {safe_val(ativo.get('Lucro_Liquido'))/1e9:.2f}B"),
        ("EBIT", f"R$ {safe_val(ativo.get('EBIT'))/1e9:.2f}B"),
        ("Receita Liq.", f"R$ {safe_val(ativo.get('Receita_Liquida'))/1e9:.2f}B"),
    ]
    cols_res = st.columns(6)
    for i, (lbl, val) in enumerate(res_data):
        col = get_semantic_color(lbl, val)
        cols_res[i].markdown(f"""<div class="metric-card-v2" style="border-left: 4px solid {col};"><div class="metric-label-v2">{lbl}{tooltip_html(lbl)}</div><div class="metric-value-v2" style="color: {col};">{val}</div></div>""", unsafe_allow_html=True)

    # CRESCIMENTO
    st.markdown('<div class="section-title-v2">Crescimento</div>', unsafe_allow_html=True)
    cresc_data = [
        ("CAGR Receitas 5a", f"{safe_val(ativo.get('CAGR Receitas 5 anos', ativo.get('cagrRecipesFiveYears'))):.2f}%"),
        ("CAGR Lucros 5a", f"{safe_val(ativo.get('CAGR Lucros 5 anos', ativo.get('cagrProfitsFiveYears'))):.2f}%"),
        ("Qtd. de Acoes", f"{safe_val(ativo.get('shares'))/1e9:.2f}B"),
    ]
    cols_cresc = st.columns(3)
    for i, (lbl, val) in enumerate(cresc_data):
        col = get_semantic_color(lbl, val)
        cols_cresc[i].markdown(f"""<div class="metric-card-v2" style="border-left: 4px solid {col};"><div class="metric-label-v2">{lbl}{tooltip_html(lbl)}</div><div class="metric-value-v2" style="color: {col};">{val}</div></div>""", unsafe_allow_html=True)

    # DIVIDENDOS (5 CARDS + BADGE NA MESMA LINHA)
    st.markdown('<div class="section-title-v2">Dividendos</div>', unsafe_allow_html=True)
    current_year = datetime.now().year
    div_cards = [
        ("DIVI 1A", f"R$ {safe_val(ativo.get('DIV_1A_')):.4f}", str(safe_val(ativo.get('DIV_1A_')) > 0), current_year - 1),
        ("DIVI 2A", f"R$ {safe_val(ativo.get('DIV_2A_')):.4f}", str(safe_val(ativo.get('DIV_2A_')) > 0), current_year - 2),
        ("DIVI 3A", f"R$ {safe_val(ativo.get('DIV_3A_')):.4f}", str(safe_val(ativo.get('DIV_3A_')) > 0), current_year - 3),
        ("DIVI 4A", f"R$ {safe_val(ativo.get('DIV_4A_')):.4f}", str(safe_val(ativo.get('DIV_4A_')) > 0), current_year - 4),
        ("DIVI 5A", f"R$ {safe_val(ativo.get('DIV_5A_')):.4f}", str(safe_val(ativo.get('DIV_5A_')) > 0), current_year - 5),
    ]
    anos_pagos = int(safe_val(ativo.get('DY_5A_PG')))
    cons_badge = f"✅ {anos_pagos}/5" if anos_pagos >= 3 else f"⚠️ {anos_pagos}/5"
    cons_color = "#10b981" if anos_pagos >= 3 else "#f59e0b"
    div_cards.append(("CONSISTÊNCIA", cons_badge, "true", None))

    cols_div = st.columns(6)
    for i, (lbl, val, paid, year) in enumerate(div_cards):
        is_cons = (i == 5)
        color = cons_color if is_cons else ("#10b981" if paid == "True" else "#475569")
        year_txt = f"<div style='font-size: 0.65rem; color: #64748b; margin-top: 4px;'>Ano: {year}</div>" if year else ""
        cols_div[i].markdown(f"""<div class="metric-card-v2" style="border-left: 4px solid {color};"><div class="metric-label-v2">{lbl}</div><div class="metric-value-v2" style="color: {color};">{val}</div>{year_txt}</div>""", unsafe_allow_html=True)

    # PRECO JUSTO
    st.markdown('<div class="section-title-v2">Preco Justo</div>', unsafe_allow_html=True)
    vpa = safe_val(ativo.get('bookValuePerShare'))
    lpa = safe_val(ativo.get('earningsPerShare'))
    dy = safe_val(ativo.get('dividendYield')) / 100
    preco_atual = safe_val(ativo.get('lastPrice'))

    def calc_upside(justo): return ((justo / preco_atual) - 1) * 100 if preco_atual > 0 else 0
    def upside_str(v): return f"{v:+.1f}%" if preco_atual > 0 else "-"

    graham = (22.5 * vpa * lpa)**0.5 if vpa > 0 and lpa > 0 else 0
    bazin = (dy / 0.06) * preco_atual if dy > 0 else 0 # Aproximacao baseada no DY atual
    lynch = lpa * (1 + safe_val(ativo.get('CAGR Lucros 5 anos', ativo.get('cagrProfitsFiveYears')))/100) if lpa > 0 else 0
    agf = (graham + bazin + lynch + preco_atual*0.8) / 4 # Media ponderada segura

    pj_data = [
        ("Graham", graham, calc_upside(graham)),
        ("Bazin", bazin, calc_upside(bazin)),
        ("Lynch", lynch, calc_upside(lynch)),
        ("AGF Medio", agf, calc_upside(agf)),
    ]
    cols_pj = st.columns(4)
    for i, (title, preco, up) in enumerate(pj_data):
        col, bg = ("#10b981", "#065f46") if up > 0 else (("#ef4444", "#991b1b") if up < 0 else ("#94a3b8", "#475569"))
        cols_pj[i].markdown(f"""<div class="pj-card-v2" style="border-left: 4px solid {col};"><div class="pj-title-v2">{title}</div><div class="pj-valor-v2">R$ {preco:.2f} if preco > 0 else N/A</div><div class="pj-upside-v2" style="background: {bg}40; color: {col};">{upside_str(up)}</div></div>""", unsafe_allow_html=True)

    # SCORE CS (11 CRITÉRIOS)
    st.markdown('<div class="section-title-v2">SCORE CS</div>', unsafe_allow_html=True)
    bh_items = [
        ("ROE > 10%", 1 if safe_val(ativo.get('ROE', ativo.get('returnOnEquity'))) > 10 else 0, "Rentabilidade do patrimonio"),
        ("DY > 6%", 1 if safe_val(ativo.get('dividendYield')) > 6 else 0, "Dividend Yield atrativo"),
        ("Div.Liq/EBITDA < 2.5", 1 if 0 < safe_val(ativo.get('Dív. líquida/EBITDA', ativo.get('netDebtToEbitda'))) < 2.5 else 0, "Endividamento controlado"),
        ("PL < 15", 1 if 0 < safe_val(ativo.get('pe')) < 15 else 0, "Preco nao esta caro"),
        ("PVP < 2", 1 if 0 < safe_val(ativo.get('priceToBookValue')) < 2 else 0, "Proximo do valor patrimonial"),
        ("Margem > 10%", 1 if safe_val(ativo.get('M. Líquida', ativo.get('netMargin'))) > 10 else 0, "Lucratividade saudavel"),
        ("Liq.Corrente > 1", 1 if safe_val(ativo.get('Liq. corrente', ativo.get('currentLiquidity'))) > 1 else 0, "Capacidade de pagamento"),
        ("CAGR > 5%", 1 if safe_val(ativo.get('CAGR Lucros 5 anos', ativo.get('cagrProfitsFiveYears'))) > 5 else 0, "Crescimento consistente"),
        ("ROIC > 10%", 1 if safe_val(ativo.get('ROIC', ativo.get('returnOnInvestedCapital'))) > 10 else 0, "Retorno sobre capital"),
        ("Volume > 1M", 1 if safe_val(ativo.get('volume')) > 1000000 else 0, "Liquidez diaria"),
        ("Consistência 5A", 1 if anos_pagos >= 3 else 0, "Pagou dividendos em pelo menos 3 dos ultimos 5 anos"),
    ]

    score = sum(item[1] for item in bh_items)
    if score >= 9: col, bg, lbl = "#10b981", "#065f46", "Excelente"
    elif score >= 7: col, bg, lbl = "#84cc16", "#3f6212", "Bom"
    elif score >= 5: col, bg, lbl = "#f59e0b", "#92400e", "Regular"
    elif score >= 3: col, bg, lbl = "#f97316", "#7c2d12", "Fraco"
    else: col, bg, lbl = "#dc2626", "#7f1d1d", "Pessimo"

    st.markdown(f"""<div class="score-card-v2" style="background: linear-gradient(135deg, {bg} 0%, {col}20 100%); border: 2px solid {col}; max-width: 300px; margin: 0 auto 24px auto;"><div class="score-number-v2" style="color: {col};">{score}</div><div class="score-label-v2" style="color: {col};">{lbl}</div><div class="score-desc-v2">de 11 pontos</div></div>""", unsafe_allow_html=True)

    cols_bh = st.columns(5)
    for i, (title, val, desc) in enumerate(bh_items):
        is_ok = bool(val)
        icon, border, bg_i = ("V", "#10b981", "#10b981") if is_ok else ("X", "#ef4444", "#ef4444")
        cols_bh[i % 5].markdown(f"""<div class="bh-card-v2" style="border-color: {border}60;"><div class="bh-icon-v2" style="background: {bg_i};">{icon}</div><div class="bh-title-v2">{title}</div><div class="bh-desc-v2">{desc}</div></div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
