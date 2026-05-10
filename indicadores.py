import numpy as np

def calcular_indicadores(data):
    indicadores = {}
    try:
        preco = data.get("regularMarketPrice", 0)

        # Dividendos e múltiplos
        dy = data.get("dividendYield", 0)
        pl = data.get("priceEarnings", 0)
        pvp = data.get("priceToBook", 0)
        ev_ebitda = data.get("enterpriseToEbitda", 0)

        # Rentabilidade
        roe = data.get("returnOnEquity", 0)
        roa = data.get("returnOnAssets", 0)

        # Margens
        margem_liquida = data.get("profitMargins", 0)
        margem_ebit = data.get("operatingMargins", 0)
        margem_bruta = data.get("grossMargins", 0)

        # Estrutura de capital
        divida_pl = data.get("debtToEquity", 0)

        # Crescimento
        receita_growth = data.get("revenueGrowth", 0)
        lucro_growth = data.get("earningsGrowth", 0)

        # Liquidez
        liquidez_corrente = data.get("currentRatio", 0)

        # ROIC (aproximação)
        ebit = data.get("ebit", 0)
        taxa_imposto = data.get("taxRate", 0)
        total_debt = data.get("totalDebt", 0)
        total_cash = data.get("totalCash", 0)
        total_equity = data.get("totalStockholderEquity", 0)

        capital_investido = (total_debt - total_cash) + total_equity
        roic = None
        if ebit and capital_investido:
            roic = (ebit * (1 - taxa_imposto)) / capital_investido

        indicadores = {
            "Cotacao": preco,

            # Valuation
            "DY": dy,
            "PL": pl,
            "PVP": pvp,
            "EV_EBITDA": ev_ebitda,

            # Rentabilidade
            "ROE": roe,
            "ROA": roa,
            "ROIC": roic,

            # Margens
            "Margem_Liquida": margem_liquida,
            "Margem_EBIT": margem_ebit,
            "Margem_Bruta": margem_bruta,

            # Dívida
            "Divida_PL": divida_pl,

            # Crescimento
            "Receita_CAGR": receita_growth,
            "Lucro_CAGR": lucro_growth,

            # Liquidez
            "Liquidez_Corrente": liquidez_corrente
        }

    except Exception as e:
        print("Erro indicadores:", e)

    return indicadores
