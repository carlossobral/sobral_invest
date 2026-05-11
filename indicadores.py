def _get(data, *chaves):
    """Tenta múltiplas chaves em ordem, retorna o primeiro valor não-None."""
    for chave in chaves:
        v = data.get(chave)
        if v is not None:
            return v
    return None


def calcular_indicadores(data):
    indicadores = {}
    try:
        indicadores = {
            # Cotação
            "Cotacao":           _get(data, "Cotacao", "close_price", "close", "price") or 0,
            # Múltiplos
            "PL":                _get(data, "PL", "pl", "price_to_earnings") or 0,
            "PVP":               _get(data, "PVP", "pvp", "price_to_book") or 0,
            "EV_EBITDA":         _get(data, "EV_EBITDA", "ev_ebitda") or 0,
            "EV_EBIT":           _get(data, "EV_EBIT", "ev_ebit") or 0,
            # Por ação
            "LPA":               _get(data, "LPA", "lpa", "eps") or 0,
            "VPA":               _get(data, "VPA", "vpa") or 0,
            # Proventos
            "DY":                _get(data, "DY", "dividend_yield") or 0,
            # Rentabilidade
            "ROE":               _get(data, "ROE", "roe") or 0,
            "ROA":               _get(data, "ROA", "roa") or 0,
            "ROIC":              _get(data, "ROIC", "roic") or 0,
            # Margens
            "Margem_Bruta":      _get(data, "Margem_Bruta", "gross_margin") or 0,
            "Margem_EBIT":       _get(data, "Margem_EBIT", "ebit_margin") or 0,
            "Margem_EBITDA":     _get(data, "Margem_EBITDA", "ebitda_margin") or 0,
            "Margem_Liquida":    _get(data, "Margem_Liquida", "net_margin") or 0,
            # Endividamento / liquidez
            "Divida_PL":         _get(data, "Divida_PL", "debt_equity") or 0,
            "Liquidez_Corrente": _get(data, "Liquidez_Corrente", "current_ratio") or 0,
            # Crescimento
            "Receita_CAGR":      _get(data, "Receita_CAGR", "cagr_revenue_5y") or 0,
            "Lucro_CAGR":        _get(data, "Lucro_CAGR", "cagr_earnings_5y") or 0,
            # Balanço
            "Market_Cap":        _get(data, "MarketCap", "market_cap") or 0,
            "Patrimonio":        _get(data, "Patrimonio", "equity") or 0,
            "Receita_Liquida":   _get(data, "Receita_Liquida", "net_revenue") or 0,
            "Lucro_Liquido":     _get(data, "Lucro_Liquido", "net_income") or 0,
            "EBITDA":            _get(data, "EBITDA", "ebitda") or 0,
            "EBIT":              _get(data, "EBIT", "ebit") or 0,
            "Divida_Liquida":    _get(data, "Divida_Liquida", "net_debt") or 0,
            "Caixa":             _get(data, "Caixa", "cash") or 0,
            "Ativos_Totais":     _get(data, "Ativos_Totais", "total_assets") or 0,
            "Segmento":          _get(data, "Segmento", "segmento", "sector", "industry") or "Desconhecido",
        }
    except Exception as e:
        print("Erro indicadores:", e)
    return indicadores
