import requests
import yfinance as yf
from config import BRAPI_TOKEN

BASE_URL = "https://brapi.dev/api/quote"

def obter_dados_brapi(ticker):
    url = f"{BASE_URL}/{ticker}"
    params = {"token": BRAPI_TOKEN}
    r = requests.get(url, params=params)
    if r.status_code == 200 and r.text.strip():
        try:
            data = r.json()
            results = data.get("results", [])
            if results:
                return results[0]
            else:
                print(f"⚠️ Nenhum resultado BRAPI para {ticker}")
                return {}
        except Exception as e:
            print(f"⚠️ Erro ao decodificar JSON para {ticker}: {e}")
            return {}
    else:
        print(f"⚠️ Erro BRAPI {ticker}: {r.status_code}")
        return {}


def obter_dados_yfinance(ticker):
    try:
        acao = yf.Ticker(f"{ticker}.SA")
        info = acao.info

        # Campos básicos
        cotacao    = info.get("currentPrice") or info.get("regularMarketPrice")
        market_cap = info.get("marketCap")
        ebitda     = info.get("ebitda")
        total_debt = info.get("totalDebt") or 0
        total_cash = info.get("totalCash") or 0
        equity     = info.get("totalStockholderEquity") or info.get("bookValue")
        net_income = info.get("netIncomeToCommon")
        revenue    = info.get("totalRevenue")
        total_assets = info.get("totalAssets")

        # EBIT estimado (EBITDA - depreciação, ou operatingIncome)
        ebit = info.get("operatingIncome") or (
            ebitda - (info.get("depreciationAndAmortization") or 0)
            if ebitda else None
        )

        # Dívida líquida
        net_debt = (total_debt - total_cash) if (total_debt or total_cash) else None

        # LPA e VPA
        lpa = info.get("trailingEps")
        shares = info.get("sharesOutstanding") or 1
        vpa = (equity / shares) if equity and shares else None

        # ROIC calculado
        roic = _calcular_roic(info)

        return {
            "Cotacao":           cotacao,
            "PL":                info.get("forwardPE") or info.get("trailingPE"),
            "LPA":               lpa,
            "VPA":               vpa,
            "DY":                info.get("dividendYield"),
            "PVP":               info.get("priceToBook"),
            "MarketCap":         market_cap,
            "ROE":               info.get("returnOnEquity"),
            "ROA":               info.get("returnOnAssets"),
            "ROIC":              roic,
            "Margem_Bruta":      info.get("grossMargins"),
            "Margem_EBIT":       info.get("operatingMargins"),
            "Margem_Liquida":    info.get("profitMargins"),
            "Divida_PL":         info.get("debtToEquity"),
            "Liquidez_Corrente": info.get("currentRatio"),
            "Receita_CAGR":      info.get("revenueGrowth"),
            "Lucro_CAGR":        info.get("earningsGrowth"),
            # Campos extras agora incluídos
            "EBITDA":            ebitda,
            "EBIT":              ebit,
            "Patrimonio":        equity,
            "Receita_Liquida":   revenue,
            "Lucro_Liquido":     net_income,
            "Divida_Liquida":    net_debt,
            "Caixa":             total_cash,
            "Ativos_Totais":     total_assets,
        }
    except Exception as e:
        print(f"⚠️ Erro yfinance {ticker}: {e}")
        return {}


def _calcular_roic(info):
    try:
        ebit       = info.get("operatingIncome") or 0
        tax_rate   = info.get("effectiveTaxRate") or 0.34
        total_debt = info.get("totalDebt") or 0
        total_cash = info.get("totalCash") or 0
        equity     = info.get("totalStockholderEquity") or 0
        capital    = (total_debt - total_cash) + equity
        if ebit and capital:
            return (ebit * (1 - tax_rate)) / capital
    except:
        pass
    return None


def buscar_acoes(lista_tickers):
    resultados = []
    for ticker in lista_tickers:
        print(f"Buscando {ticker}...")
        dados_brapi = obter_dados_brapi(ticker)
        dados_yf    = obter_dados_yfinance(ticker)

        consolidado = {
            "ticker":    ticker,
            "close_price":      dados_brapi.get("regularMarketPrice") or dados_yf.get("Cotacao") or 0,
            "pl":               dados_brapi.get("priceEarnings")      or dados_yf.get("PL") or 0,
            "lpa":              dados_brapi.get("earningsPerShare")    or dados_yf.get("LPA") or 0,
            "vpa":              dados_yf.get("VPA") or 0,
            "dividend_yield":   dados_brapi.get("dividendYield")      or dados_yf.get("DY") or 0,
            "pvp":              dados_brapi.get("priceToBook")         or dados_yf.get("PVP") or 0,
            "market_cap":       dados_brapi.get("marketCap")          or dados_yf.get("MarketCap") or 0,
            "roe":              dados_yf.get("ROE"),
            "roa":              dados_yf.get("ROA"),
            "roic":             dados_yf.get("ROIC"),
            "gross_margin":     dados_yf.get("Margem_Bruta"),
            "ebit_margin":      dados_yf.get("Margem_EBIT"),
            "net_margin":       dados_yf.get("Margem_Liquida"),
            "debt_equity":      dados_yf.get("Divida_PL"),
            "current_ratio":    dados_yf.get("Liquidez_Corrente"),
            "cagr_revenue_5y":  dados_yf.get("Receita_CAGR"),
            "cagr_earnings_5y": dados_yf.get("Lucro_CAGR"),
            # Campos novos
            "ebitda":           dados_yf.get("EBITDA"),
            "ebit":             dados_yf.get("EBIT"),
            "equity":           dados_yf.get("Patrimonio"),
            "net_revenue":      dados_yf.get("Receita_Liquida"),
            "net_income":       dados_yf.get("Lucro_Liquido"),
            "net_debt":         dados_yf.get("Divida_Liquida"),
            "cash":             dados_yf.get("Caixa"),
            "total_assets":     dados_yf.get("Ativos_Totais"),
        }
        resultados.append(consolidado)

    print(f"TOTAL RESULTADOS: {len(resultados)}")
    return resultados
