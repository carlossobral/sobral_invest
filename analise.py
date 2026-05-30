import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
from data import load_data

TOOLTIPS = {
    # Valuation
    "P/L": "Preço sobre o Lucro. Demonstra quanto o mercado está disposto a pagar pelos lucros da empresa.",
    "P/VP": "Preço sobre o Valor Patrimonial. Indica quanto o mercado está disposto a pagar pelo patrimônio da empresa. Abaixo de 1, indica que a empresa está sendo vendida por menos que seu valor real.",
    "LPA": "Lucro por Ação. Indicador que mostra se a empresa é lucrativa. Quando o número é negativo, indica que a empresa está operando com geração de prejuízo ao invés de lucro.",
    "P/Receita": "Price to Sales Ratio (PSR). Compara o preço da ação com as vendas. Um PSR abaixo de 1 significa que a empresa pode estar sendo negociada a um preço baixo em comparação com suas vendas.",
    "P/Ativo": "Preço sobre Total de Ativos. Medida para avaliar o valor de uma empresa em relação ao seu patrimônio líquido total. Um P/Ativo inferior a 1, quer dizer que o preço da ação está menor que os seus próprios ativos.",
    "P/Cap. Giro": "Mede se a empresa está sendo negociada a um preço justo em comparação com sua capacidade de cobrir suas obrigações de curto prazo.",
    "P/Ativo Circ. Líq.": "Compara o preço da ação com os ativos circulantes líquidos da empresa. Quanto menor, mais descontada a ação pode estar em relação a seus ativos circulantes líquidos.",
    "P/EBIT": "Preço sobre EBIT. Medida da lucratividade que exclui juros e impostos. Quanto maior, mais caro o investidor está pagando pela empresa em relação ao seu EBIT.",
    "P/EBITDA": "Preço sobre EBITDA. Medida da lucratividade que exclui juros, impostos, depreciação e amortização.",
    "EV/EBIT": "Valor da empresa sobre EBIT. Demonstra a capacidade produtiva da empresa com a estrutura atual, tomando por base seu valor de mercado e seu lucro operacional.",
    "EV/EBITDA": "Ele indica quantos anos seriam necessários para que a empresa pagasse o seu próprio valor de mercado utilizando apenas o seu lucro operacional.",

    # Rentabilidade
    "ROE": "Return on Equity, ou Retorno sobre o Patrimônio Líquido mede a eficiência de uma empresa em gerar lucro a partir do capital investido pelos próprios sócios.",
    "ROA": "Retorno sobre o Ativo. Mede a eficiência com que uma empresa utiliza seus ativos para gerar lucro. Quanto maior este indicador, melhor é a eficiência em gerar lucro a partir dos ativos. Valores acima de 10% geralmente são considerados bons.",
    "ROIC": "Retorno sobre o Capital Investido. Mede o retorno sobre o capital investido em uma empresa. Quanto maior este indicador, melhor é o retorno que os investidores estão recebendo sobre o investimento. Valores acima de 10% geralmente são considerados bons.",
    "Giro Ativos": "Mede a capacidade da empresa em gerar receita com seus ativos e a eficiência de seu modelo de negócio.",
    "Margem Bruta": "Indica a eficiência da empresa em transformar suas vendas em lucro, excluindo os custos variáveis.",
    "Margem EBITDA": "É um indicador financeiro que mede a eficiência operacional de uma empresa, revelando qual porcentagem da sua receita se transforma em lucro antes de juros, impostos, depreciação e amortização. Em termos simples, ela mostra quanto dinheiro a empresa gera apenas com sua atividade principal para cada real faturado.",
    "Margem EBIT": "Mede a produtividade e serve como comparação de lucratividade operacional entre empresas do mesmo segmento. É um indicador de margem considerando depreciação e amortização.",
    "Margem Líquida": "Indica quanto da receita é convertida em lucro.",

    # Endividamento
    "Dív. Líq/Ativos": "Dívida Líq / Ativos. < 0.5 bom.",
    "Dív. Líq/PL": "Mede o nível de endividamento de uma empresa em relação ao seu capital próprio. Ele mostra quanto a companhia depende de recursos de terceiros (dívidas) comparado ao que efetivamente pertence aos seus acionistas. < 1 ideal.",
    "Dív. Líq/EBIT": "Mede o grau de endividamento e a alavancagem de uma empresa. Ele mostra, em anos, quanto tempo a companhia levaria para pagar suas dívidas utilizando exclusivamente o seu lucro operacional, caso o endividamento e os ganhos se mantivessem constantes. < 3 bom.",
    "Dív. Líq/EBITDA": "É o principal indicador de alavancagem e saúde financeira de uma empresa. Ele calcula quantos anos a empresa levaria para pagar todas as suas dívidas usando apenas o seu lucro operacional (EBITDA), caso ele se mantivesse constante. < 2.5 saudável.",
    "Liq. Corrente": "Mede a capacidade de uma empresa de pagar suas dívidas correntes (a vencer em um ano ou menos) usando apenas seus ativos correntes (disponíveis em um ano ou menos). Indica se há recursos suficientes para cobrir obrigações de curto prazo.",
    "Passivo/Ativos": "Indica o quanto a empresa está endividada em relação a seus ativos. Quanto menor este número, melhor é a situação financeira da empresa.",
    "Patrimonio/Ativos": "Indica quanto a empresa possui em ativos em comparação com suas obrigações. Quanto maior este número, melhor é a situação financeira da empresa.",

    # Resultado
    "VPA": "Valor Patrimonial por Ação. Representa quanto vale uma ação da empresa em relação a todo seu patrimônio.",
    "Patrim. Líq.": "Patrimônio Líquido da empresa. Ativos menos passivos.",
    "Lucro Líquido": "Lucro após impostos e despesas. Base para dividendos.",
    "EBIT": "Lucro antes de juros e impostos. Mede eficiência operacional.",
    "Receita Líq.": "Receita total da empresa após deduções.",

    # Crescimento & Dividendos
    "CAGR Receitas 5a": "Compound Annual Growth Rate (crescimento anual composto). Mede o crescimento da receita de uma empresa considerando os quatro últimos trimestres em comparação ao período de cinco anos atrás.",
    "CAGR Lucros 5a": "Compound Annual Growth Rate (crescimento anual composto). Mede o crescimento do lucro da empresa considerando os quatro últimos trimestres em comparação ao período equivalente de cinco anos atrás.",
    "📊 Volume (1D)": "Volume financeiro negociado no último dia.",
    " DY 12m": "Dividend Yield. Mostra o rendimento obtido por uma ação através dos proventos distribuídos pela empresa nos últimos 12 meses.",
    "Div 1A": "Dividendos pagos no ano civil de 1 ano atrás.",
    "Div 2A": "Dividendos pagos no ano civil de 2 anos atrás.",
    "Div 3A": "Dividendos pagos no ano civil de 3 anos atrás.",
    "Div 4A": "Dividendos pagos no ano civil de 4 anos atrás.",
    "Div 5A": "Dividendos pagos no ano civil de 5 anos atrás.",
    "Consistência": "Quantos anos (0-5) o ativo pagou dividendos nos últimos 5 anos completos.",

    # Preço Justo
    "Graham": "Preço justo pelo método clássico de Benjamin Graham: √(22.5 × LPA × VPA).",
    "Graham BR": "Preço justo pelo método conservador de Graham para o Brasil: √(15 × LPA × VPA).",
    "Bazin": "Preço teto pelo método de Décio Bazin: foco em dividendos com yield alvo de 6%.",
    "Lynch": "Preço justo pelo método de Peter Lynch: considera crescimento de lucros.",
    "AGF Medio": "Método AGF, utilizado pelo maior investidor PF da B3, Luiz Barsi Filho",

    # SCORE CS
    "ROE > 10%": "Return on Equity. > 10% indica boa rentabilidade sobre o patrimônio.",
    "💸 DY 12m > 6%": "Dividend Yield dos últimos 12 meses. > 6% considerado atrativo.",
    "Dív.Líq/EBITDA < 2.5": "Dívida Líquida sobre EBITDA. < 2.5 indica endividamento controlado.",
    "P/L < 15": "Preço / Lucro. Quanto menor, mais barata. < 15",
    "P/VP < 2": "Preço / Valor Patrimonial. Abaixo de 2 indica proximidade do valor contábil.",
    "Margem > 10%": "Margem Líquida. Indica quanto da receita é convertida em lucro.",
    "Liq.Corrente > 1": "Liquidez Corrente. Indica capacidade de pagamento de curto prazo.",
    "CAGR > 5%": "Crescimento anual composto dos lucros nos últimos 5 anos.",
    "ROIC > 10%": "Retorno sobre o Capital Investido. Mede eficiência do capital.",
    "Volume > 1M": "Volume financeiro diário. Indica liquidez da ação.",
    "Consistência 5A": "Pagou dividendos em pelo menos 3 dos últimos 5 anos completos."
}

def safe(v, d=0.0):
    try: return float(v) if pd.notna(v) else d
    except: return d

def sem_color(label, val_str):
    try: val = float(val_str.replace('R$','').replace('x','').replace('%','').strip())
    except: return "#94a3b8"
    l = label.lower()
    if any(k in l for k in ["p/l", "p/vp", "ev_", "div_liq", "passivos", "psr"]):
        return "#10b981" if val < 10 else ("#f59e0b" if val < 20 else "#ef4444")
    if any(k in l for k in ["roe", "roic", "margem", "dy ", "cagr", "upside", "score", "roa"]):
        return "#10b981" if val > 15 else ("#f59e0b" if val > 5 else "#ef4444")
    return "#38bdf8"

def tooltip(t):
    d = TOOLTIPS.get(t, "")
    return f'<span class="tt"><span class="tt-i">?</span><span class="tt-t">{d}</span></span>' if d else ""

def pagina_analise():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    .c * { font-family: 'Inter', sans-serif; } .c { padding: 0 8px 40px 8px; }
    .st { font-size: 1.05rem; font-weight: 700; color: #f1f5f9; text-transform: uppercase; letter-spacing: 0.1em; margin: 40px 0 22px 0; padding-bottom: 10px; border-bottom: 2px solid #334155; display: flex; align-items: center; gap: 10px; }
    .mc { background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 12px; padding: 18px 16px; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.1); height: 100%; display: flex; flex-direction: column; justify-content: space-between; min-height: 95px; }
    .mc:hover { transform: translateY(-2px); box-shadow: 0 8px 12px rgba(0,0,0,0.25); border-color: #3b82f6; }
    .ml { font-size: 0.72rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; line-height: 1.3; }
    .mv { font-size: 1.45rem; font-weight: 700; color: #f1f5f9; line-height: 1.1; letter-spacing: -0.02em; }
    .sc { border-radius: 16px; padding: 24px; text-align: center; box-shadow: 0 10px 15px rgba(0,0,0,0.2); }
    .sn { font-size: 3.5rem; font-weight: 800; line-height: 1; margin-bottom: 8px; }
    .sl { font-size: 1.1rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; }
    .sd { font-size: 0.8rem; color: #94a3b8; margin-top: 6px; }
    .bc { background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border: 2px solid; border-radius: 12px; padding: 14px; text-align: center; transition: all 0.3s ease; }
    .bc:hover { transform: translateY(-2px); box-shadow: 0 6px 10px rgba(0,0,0,0.2); }
    .bi { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-size: 16px; font-weight: 700; color: white; }
    .bt { font-size: 0.75rem; font-weight: 600; color: #f1f5f9; margin-bottom: 2px; line-height: 1.2; }
    .bd { font-size: 0.65rem; color: #94a3b8; line-height: 1.2; }
    .pc { background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 12px; padding: 16px; text-align: center; transition: all 0.3s ease; }
    .pc:hover { transform: translateY(-2px); box-shadow: 0 8px 12px rgba(0,0,0,0.2); }
    .pt { font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; }
    .pv { font-size: 1.2rem; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
    .pu { font-size: 0.9rem; font-weight: 600; padding: 3px 10px; border-radius: 12px; display: inline-block; }
    .tt { position: relative; display: inline-block; }
    .tt-i { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; border-radius: 50%; background: #475569; color: #f1f5f9; font-size: 11px; font-weight: 700; cursor: help; margin-left: 6px; }
    .tt-i:hover { background: #3b82f6; }
    .tt-t { visibility: hidden; width: 280px; background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border: 1px solid #475569; color: #e2e8f0; text-align: left; border-radius: 10px; padding: 12px 14px; position: absolute; z-index: 1000; bottom: 125%; left: 50%; margin-left: -140px; opacity: 0; transition: opacity 0.3s; font-size: 0.8rem; line-height: 1.4; box-shadow: 0 10px 15px rgba(0,0,0,0.3); }
    .tt-t::after { content: ""; position: absolute; top: 100%; left: 50%; margin-left: -5px; border-width: 5px; border-style: solid; border-color: #475569 transparent transparent transparent; }
    .tt:hover .tt-t { visibility: visible; opacity: 1; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="c">', unsafe_allow_html=True)
    df = load_data()
    if df.empty:
        st.warning("Dados não disponíveis."); return

    df['Disp'] = (df['Ticker'].astype(str).fillna('') + ' - ' + df['Nome'].astype(str).fillna('')).astype(str)
    opts = sorted(df['Disp'].tolist())
    idx = 0
    ticker_dest = st.session_state.get("ticker_destino")
    if ticker_dest:
        for i, o in enumerate(opts):
            if o.startswith(ticker_dest + ' -'):
                idx = i
                break
        st.session_state.pop("ticker_destino", None)

    sel = st.selectbox("Selecione o ativo", options=opts, index=idx, key="sel_v2")
    ticker = sel.split(' - ')[0]
    ativo = df[df['Ticker'] == ticker].iloc[0] if not df[df['Ticker'] == ticker].empty else None
    if ativo is None: st.error("Ativo não encontrado."); return

    st.markdown(f"""
    <div style="display: flex; gap: 24px; margin: 8px 0 16px 0;">
        <div><span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase;">Setor</span><span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('Setor', 'N/A')}</span></div>
        <div style="color: #475569;">&rsaquo;</div>
        <div><span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase;">SubSetor</span><span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('SubSetor', 'N/A')}</span></div>
        <div style="color: #475569;">&rsaquo;</div>
        <div><span style="font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase;">Segmento</span><span style="font-size: 0.85rem; font-weight: 500; color: #f1f5f9; margin-left: 8px;">{ativo.get('Segmento', 'N/A')}</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 16px 0;'></div>", unsafe_allow_html=True)
    components.html(f"""<div class="tradingview-widget-container"><div class="tradingview-widget-container__widget"></div><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>{{"symbols": [["BMFBOVESPA:{ticker}|1D"]], "chartOnly": false, "width": "100%", "height": "350", "locale": "br", "colorTheme": "dark", "autosize": false, "showVolume": true, "showMA": false, "hideDateRanges": false, "hideMarketStatus": false, "hideSymbolLogo": false, "scalePosition": "right", "scaleMode": "Normal", "fontFamily": "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif", "fontSize": "10", "noTimeScale": false, "valuesTracking": "1", "changeMode": "price-and-percent", "chartType": "area", "maLineColor": "#2962FF", "maLineWidth": 1, "maLength": 9, "lineWidth": 2, "lineType": 0, "dateRanges": ["1d|1", "1m|30", "3m|60", "12m|1D", "60m|1W", "all|1M"]}}</script></div>""", height=360)

    def sec(title, data, cols):
        st.markdown(f'<div class="st">{title}</div>', unsafe_allow_html=True)
        for r in range(2 if len(data) > cols else 1):
            cs = st.columns(cols)
            for c in range(cols):
                i = r * cols + c
                if i < len(data):
                    lbl, val = data[i]
                    cl = sem_color(lbl, val)
                    cs[c].markdown(f"""<div class="mc" style="border-left: 4px solid {cl};"><div class="ml">{lbl}{tooltip(lbl)}</div><div class="mv" style="color: {cl};">{val}</div></div>""", unsafe_allow_html=True)

    # ✅ P/E removido conforme solicitado
    sec("Valuation", [
        ("P/L", f"{safe(ativo.get('P_L')):.2f}x"), 
        ("P/VP", f"{safe(ativo.get('P_VP')):.2f}x"), 
        ("LPA", f"R$ {safe(ativo.get('LPA')):.2f}"), 
        ("P/Receita", f"{safe(ativo.get('P_Receita')):.2f}x"), 
        ("P/Ativo", f"{safe(ativo.get('P_Ativo')):.2f}x"), 
        ("P/Cap. Giro", f"{safe(ativo.get('P_Cap_Giro')):.2f}x"), 
        ("P/Ativo Circ. Líq.", f"{safe(ativo.get('P_Ativo_Circ_Liq')):.2f}x"), 
        ("P/EBIT", f"{safe(ativo.get('P_EBIT')):.2f}x"), 
        ("P/EBITDA", f"{safe(ativo.get('P_EBITDA')):.2f}x"), 
        ("EV/EBIT", f"{safe(ativo.get('EV_EBIT')):.2f}x"), 
        ("EV/EBITDA", f"{safe(ativo.get('EV_EBITDA')):.2f}x")
    ], 6)
    
    sec("Rentabilidade", [
        ("ROE", f"{safe(ativo.get('ROE')):.2f}%"), 
        ("ROA", f"{safe(ativo.get('ROA')):.2f}%"), 
        ("ROIC", f"{safe(ativo.get('ROIC')):.2f}%"), 
        ("Giro Ativos", f"{safe(ativo.get('Giro_Ativos')):.2f}x"), 
        ("Margem Bruta", f"{safe(ativo.get('Margem_Bruta')):.2f}%"), 
        ("Margem EBITDA", f"{safe(ativo.get('Margem_EBITDA')):.2f}%"), 
        ("Margem EBIT", f"{safe(ativo.get('Margem_EBIT')):.2f}%"), 
        ("Margem Líquida", f"{safe(ativo.get('Margem_Liquida')):.2f}%")
    ], 4)
    
    sec("Endividamento", [
        ("Dív. Líq/Ativos", f"{safe(ativo.get('Div_Liq_Ativos')):.2f}x"), 
        ("Dív. Líq/PL", f"{safe(ativo.get('Div_Liq_PL')):.2f}x"), 
        ("Dív. Líq/EBIT", f"{safe(ativo.get('Div_Liq_EBIT')):.2f}x"), 
        ("Dív. Líq/EBITDA", f"{safe(ativo.get('Div_Liq_EBITDA')):.2f}x"), 
        ("Liq. Corrente", f"{safe(ativo.get('Liquidez_Corrente')):.2f}x"), 
        ("Passivo/Ativos", f"{safe(ativo.get('Passivos_Ativos')):.2f}x"), 
        ("Patrimonio/Ativos", f"{safe(ativo.get('PL_Ativos')):.2f}x")
    ], 4)
    
    sec("Resultado", [
        ("LPA", f"R$ {safe(ativo.get('LPA')):.2f}"), 
        ("VPA", f"R$ {safe(ativo.get('VPA')):.2f}"), 
        ("Patrim. Líq.", f"R$ {safe(ativo.get('Valor_Mercado'))/1e9:.2f}B"), 
        ("Lucro Líquido", f"R$ {safe(ativo.get('Lucro_Liquido'))/1e9:.2f}B"), 
        ("EBIT", f"R$ {safe(ativo.get('EBIT'))/1e9:.2f}B"), 
        ("Receita Líq.", f"R$ {safe(ativo.get('Receita_Liquida'))/1e9:.2f}B")
    ], 6)
    
    sec("Crescimento", [
        ("CAGR Receitas 5a", f"{safe(ativo.get('CAGR_Receitas_5a')):.2f}%"), 
        ("CAGR Lucros 5a", f"{safe(ativo.get('CAGR_Lucros_5a')):.2f}%"), 
        ("📊 Volume (1D)", f"R$ {safe(ativo.get('Volume'))/1e6:.2f}M")
    ], 3)

    st.markdown('<div class="st">Dividendos</div>', unsafe_allow_html=True)
    cy = datetime.now().year
    cards = [(f"Div {i}A", f"R$ {safe(ativo.get(f'Div_{i}A')):.4f}", str(safe(ativo.get(f'Div_{i}A')) > 0), cy-i) for i in range(1,6)]
    cons = int(safe(ativo.get('Consistencia_5A'), 0))
    cb, cc = (f"✅ {cons}/5", "#10b981") if cons >= 3 else (f"️ {cons}/5", "#f59e0b")
    cards.append(("Consistência", cb, "True", None))
    cs = st.columns(6)
    for i, (l, v, p, y) in enumerate(cards):
        cl = cc if i==5 else ("#10b981" if p=="True" else "#475569")
        yt = f"<div style='font-size: 0.65rem; color: #64748b; margin-top: 4px;'>Ano: {y}</div>" if y else ""
        cs[i].markdown(f"""<div class="mc" style="border-left: 4px solid {cl};"><div class="ml">{l}</div><div class="mv" style="color: {cl};">{v}</div>{yt}</div>""", unsafe_allow_html=True)

    st.markdown('<div class="st">Preço Justo</div>', unsafe_allow_html=True)
    vpa, lpa, dy, pr = safe(ativo.get('VPA')), safe(ativo.get('LPA')), safe(ativo.get('DY_Atual'))/100, safe(ativo.get('Preco_Atual'))
    graham = (22.5 * vpa * lpa)**0.5 if vpa > 0 and lpa > 0 else 0
    graham_br = (15 * vpa * lpa)**0.5 if vpa > 0 and lpa > 0 else 0
    bazin = (dy / 0.06) * pr if dy > 0 else 0
    lynch = lpa * (1 + safe(ativo.get('CAGR_Lucros_5a'))/100) if lpa > 0 else 0
    agf = (graham + graham_br + bazin + lynch + pr*0.8) / 5
    ups = lambda j: ((j/pr)-1)*100 if pr > 0 else 0
    pj = [("Graham", graham, ups(graham)), ("Graham BR", graham_br, ups(graham_br)), ("Bazin", bazin, ups(bazin)), ("Lynch", lynch, ups(lynch)), ("AGF Medio", agf, ups(agf))]
    cps = st.columns(5)
    for i, (t, p, u) in enumerate(pj):
        c, b = ("#10b981", "#065f46") if u > 0 else (("#ef4444", "#991b1b") if u < 0 else ("#94a3b8", "#475569"))
        price_str = f"R$ {p:.2f}" if p > 0 else "N/A"
        cps[i].markdown(f"""<div class="pc" style="border-left: 4px solid {c};"><div class="pt">{t}{tooltip(t)}</div><div class="pv">{price_str}</div><div class="pu" style="background: {b}40; color: {c};">{u:+.1f}%</div></div>""", unsafe_allow_html=True)

    st.markdown('<div class="st">SCORE CS</div>', unsafe_allow_html=True)
    items = [
        ("ROE > 10%", 1 if safe(ativo.get('ROE')) > 10 else 0, "Rentabilidade do patrimônio"),
        (" DY 12m > 6%", 1 if safe(ativo.get('DY_Atual')) > 6 else 0, "Dividend Yield atrativo"),
        ("Dív.Líq/EBITDA < 2.5", 1 if 0 < safe(ativo.get('Div_Liq_EBITDA')) < 2.5 else 0, "Endividamento controlado"),
        ("P/L < 15", 1 if 0 < safe(ativo.get('P_L')) < 15 else 0, "Preço não está caro"),
        ("P/VP < 2", 1 if 0 < safe(ativo.get('P_VP')) < 2 else 0, "Próximo do valor patrimonial"),
        ("Margem > 10%", 1 if safe(ativo.get('Margem_Liquida')) > 10 else 0, "Lucratividade saudável"),
        ("Liq.Corrente > 1", 1 if safe(ativo.get('Liquidez_Corrente')) > 1 else 0, "Capacidade de pagamento"),
        ("CAGR > 5%", 1 if safe(ativo.get('CAGR_Lucros_5a')) > 5 else 0, "Crescimento consistente"),
        ("ROIC > 10%", 1 if safe(ativo.get('ROIC')) > 10 else 0, "Retorno sobre capital"),
        ("Volume > 1M", 1 if safe(ativo.get('Volume')) > 1000000 else 0, "Liquidez diária"),
        ("Consistência 5A", 1 if cons >= 3 else 0, "Pagou em pelo menos 3 dos últimos 5 anos completos"),
    ]
    score = sum(x[1] for x in items)
    col, bg, lbl = ("#10b981", "#065f46", "Excelente") if score >= 9 else (("#84cc16", "#3f6212", "Bom") if score >= 7 else (("#f59e0b", "#92400e", "Regular") if score >= 5 else (("#f97316", "#7c2d12", "Fraco") if score >= 3 else ("#dc2626", "#7f1d1d", "Péssimo"))))
    
    st.markdown(f"""<div class="sc" style="background: linear-gradient(135deg, {bg} 0%, {col}20 100%); border: 2px solid {col}; max-width: 300px; margin: 0 auto 24px auto;"><div class="sn" style="color: {col};">{score}</div><div class="sl" style="color: {col};">{lbl}</div><div class="sd">de 11 pontos</div></div>""", unsafe_allow_html=True)
    
    cbs = st.columns(5)
    for i, (t, v, d) in enumerate(items):
        ok = bool(v)
        ic, bc, bgc = ("V", "#10b981", "#10b981") if ok else ("X", "#ef4444", "#ef4444")
        cbs[i%5].markdown(f"""<div class="bc" style="border-color: {bc}60;"><div class="bi" style="background: {bgc};">{ic}</div><div class="bt">{t}</div><div class="bd">{d}</div></div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
