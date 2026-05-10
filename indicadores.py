def calcular_indicadores(data):
    indicadores = {}
    try:
        indicadores = {
            "Cotacao": data.get("close_price") or 0,
            "PL": data.get("pl") or 0,
            "PVP": data.get("pvp") or 0,
            "EV_EBITDA": data.get("ev_ebitda") or 0,
            "EV_EBIT": data.get("ev_ebit") or 0,
            "LPA": data.get("lpa") or 0,
            "VPA": data.get("vpa") or 0,
            "DY": data.get("dividend_yield") or 0,
            "ROE": data.get("roe") or 0,
            "ROA": data.get("roa") or 0,
            "ROIC": data.get("roic") or 0,
            "Margem_Bruta": data.get("gross_margin") or 0,
            "Margem_EBIT": data.get("ebit_margin") or 0,
            "Margem_EBITDA": data.get("ebitda_margin") or 0,
            "Margem_Liquida": data.get("net_margin") or 0,
            "Divida_PL": data.get("debt_equity") or 0,
            "Liquidez_Corrente": data.get("current_ratio") or 0,
            "Receita_CAGR": data.get("cagr_revenue_5y") or 0,
            "Lucro_CAGR": data.get("cagr_earnings_5y") or 0,
            "Market_Cap": data.get("market_cap") or 0,
            "Patrimonio": data.get("equity") or 0,
            "Receita_Liquida": data.get("net_revenue") or 0,
            "Lucro_Liquido": data.get("net_income") or 0,
            "EBITDA": data.get("ebitda") or 0,
            "EBIT": data.get("ebit") or 0,
            "Divida_Liquida": data.get("net_debt") or 0,
            "Caixa": data.get("cash") or 0,
            "Ativos_Totais": data.get("total_assets") or 0
        }
    except Exception as e:
        print("Erro indicadores:", e)

    return indicadores
