"""
Cliente MFinance API - v3.0 (REFATORADO)
Simplificado para 3 endpoints confirmados:
- GET /stocks → todos os ativos com dados basicos
- GET /stocks/indicators → todos os indicadores fundamentais
- GET /stocks/dividends/{symbol} → dividendos por ticker

Removidos (codigo morto):
- get_all_symbols() / /stocks/symbols/ → desnecessario, batch funciona sem lista
- get_details() / /stocks/details/ → nunca chamado no app.py
- get_stock_single() / /stocks/{symbol} → fallback nunca usado
- get_indicators_single() / /stocks/indicators/{symbol} → fallback nunca usado
- get_all_stocks_single() → fallback removido
- get_all_indicators_single() → fallback removido
- Camada de teste batch → batch sempre funciona, simplificado

Correcoes mantidas:
- PL <-> PVP trocados no parse_mfinance_indicator()
- DivLiquida_Ativos renomeado (netDebtToAssets = Divida/Ativos)
"""

import requests
import time
from typing import List, Dict, Any, Optional

BASE_URL = "https://mfinance.com.br/api/v1"
DEFAULT_TIMEOUT = 25
DEFAULT_RETRY = 3
BATCH_SIZE = 10


class MFinanceClient:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRY):
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "SOBRAL-Invest/1.0"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Any]:
        """Faz request com retry automatico."""
        url = f"{BASE_URL}{endpoint}"
        for attempt in range(self.retries):
            try:
                response = self.session.request(
                    method, url, timeout=self.timeout, **kwargs
                )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict):
                    keys = list(data.keys())
                    print(f" DEBUG {url}: keys={keys[:5]}")
                elif isinstance(data, list):
                    print(f" DEBUG {url}: list len={len(data)}")
                else:
                    print(f" DEBUG {url}: type={type(data).__name__}, value={str(data)[:100]}")
                return data
            except requests.exceptions.Timeout:
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                print(f"⚠️ Timeout apos {self.retries} tentativas: {url}")
                return None
            except requests.exceptions.HTTPError as e:
                print(f"⚠️ HTTP {e.response.status_code}: {url}")
                try:
                    print(f" Response: {e.response.text[:200]}")
                except:
                    pass
                return None
            except Exception as e:
                print(f"⚠️ Erro em {url}: {e}")
                return None
        return None

    def get_stocks(self) -> List[Dict]:
        """Busca TODOS os ativos do MFinance (dados basicos).

        GET /stocks → retorna {"stocks": [{"symbol": "PETR4", ...}, ...]}
        Nao precisa de symbols= → retorna todos os 648 tickers.
        """
        data = self._request("GET", "/stocks")
        if isinstance(data, dict) and "stocks" in data and data["stocks"] is not None:
            stocks = data["stocks"]
            print(f"✅ /stocks: {len(stocks)} ativos")
            return stocks
        print("❌ /stocks retornou vazio ou formato inesperado")
        return []

    def get_indicators(self) -> List[Dict]:
        """Busca TODOS os indicadores fundamentais do MFinance.

        GET /stocks/indicators → retorna {"indicators": [{"symbol": "PETR4", ...}, ...]}
        Nao precisa de symbols= → retorna todos os 648 tickers.
        Cada indicador contem "symbol" para merge posterior.
        """
        data = self._request("GET", "/stocks/indicators")
        if isinstance(data, dict) and "indicators" in data and data["indicators"] is not None:
            indicators = data["indicators"]
            print(f"✅ /stocks/indicators: {len(indicators)} indicadores")
            return indicators
        print("❌ /stocks/indicators retornou vazio ou formato inesperado")
        return []

    def get_dividends(self, symbol: str) -> Dict[str, Any]:
        """Busca dividendos de 1 ticker.

        GET /stocks/dividends/{symbol} → {"symbol": "...", "dividends": [...]}
        """
        data = self._request("GET", f"/stocks/dividends/{symbol}")
        if isinstance(data, dict) and "dividends" in data:
            return data
        return {"symbol": symbol, "dividends": []}

    def get_all_dividends(self, symbols: List[str]) -> Dict[str, Dict]:
        """Busca dividendos para uma lista de tickers (1 por 1).

        Args:
            symbols: Lista de tickers (obtida do /stocks ou /stocks/indicators)

        Returns:
            Dict mapeando ticker → dados de dividendos
        """
        dividends_map = {}
        total = len(symbols)
        print(f"💰 Buscando dividendos para {total} tickers...")

        for i, symbol in enumerate(symbols):
            if i % 50 == 0 and i > 0:
                print(f"   {i}/{total} dividendos...")
            div_data = self.get_dividends(symbol)
            dividends_map[symbol] = parse_mfinance_dividends(div_data)
            time.sleep(0.1)  # Rate limiting gentil

        print(f"✅ Dividendos: {len(dividends_map)} tickers")
        return dividends_map


def parse_mfinance_stock(stock: Dict) -> Dict[str, Any]:
    """Extrai campos relevantes de um objeto Stock do MFinance."""
    return {
        "Ticker": stock.get("symbol", ""),
        "Nome": stock.get("name", ""),
        "Setor": stock.get("sector", ""),
        "SubSetor": stock.get("subSector", ""),
        "Segmento": stock.get("segment", ""),
        "Cotacao": stock.get("lastPrice", 0),
        "Variacao": stock.get("change", 0),
        "Abertura": stock.get("priceOpen", 0),
        "Maxima": stock.get("high", 0),
        "Minima": stock.get("low", 0),
        "Fechamento_Anterior": stock.get("closingPrice", 0),
        "Volume": stock.get("volume", 0),
        "Volume_Medio": stock.get("volumeAvg", 0),
        "Market_Cap": stock.get("marketCap", 0),
        "PE": stock.get("pe", 0),
        "EPS": stock.get("eps", 0),
        "DY": stock.get("dividendYield", 0),
        "Maxima_52s": stock.get("lastYearHigh", 0),
        "Minima_52s": stock.get("lastYearLow", 0),
        "Qtd_Acoes": stock.get("shares", 0),
    }


def parse_mfinance_indicator(ind: Dict) -> Dict[str, Any]:
    """
    Extrai valores numericos dos indicadores do MFinance.

    CORRECAO v2.1 mantida:
    - PL usa priceEarningsRatio (P/L = Preco/Lucro)
    - PVP usa priceToBookValue (P/VP = Preco/Valor Patrimonial)
    - DivLiquida_Ativos = netDebtToAssets (Divida Liquida / Ativos Totais)
    - DivLiquida_PL sera calculado no app.py
    """
    def get_val(key: str) -> float:
        obj = ind.get(key)
        if isinstance(obj, dict):
            return obj.get("value", 0) or 0
        return obj or 0

    return {
        "Ticker": ind.get("symbol", ""),
        "PL": get_val("priceEarningsRatio"),
        "PVP": get_val("priceToBookValue"),
        "PSR": get_val("priceToSalesRatio"),
        "PAtivo": get_val("priceToAssets"),
        "PCapGiro": get_val("priceToNetCurrentAssets"),
        "PAtivoCircLiq": get_val("priceToNetNetWorkingCapital"),
        "PEBIT": get_val("priceToEbit"),
        "PEBITDA": get_val("priceToEbitda"),
        "EV_EBIT": get_val("enterpriseValueEbit"),
        "EV_EBITDA": get_val("enterpriseValueEbitda"),
        "LPA": get_val("earningsPerShare"),
        "VPA": get_val("bookValuePerShare"),
        "ROE": get_val("returnOnEquity"),
        "ROA": get_val("returnOnAssets"),
        "ROIC": get_val("returnOnInvestedCapital"),
        "GiroAtivos": get_val("assetTurnoverRatio"),
        "MargemBruta": get_val("grossMargin"),
        "MargemEBITDA": get_val("ebitdaMargin"),
        "MargemEBIT": get_val("ebitMargin"),
        "MargemLiquida": get_val("netMargin"),
        "DivLiquida_Ativos": get_val("netDebtToAssets"),
        "DivLiquida_EBIT": get_val("netDebtToEbit"),
        "DivLiquida_EBITDA": get_val("netDebtToEbitda"),
        "LiquidezCorrente": get_val("currentLiquidity"),
        "Passivos_Ativos": get_val("liabilitiesToAssetsRatio"),
        "PL_Ativos": get_val("equityToAssetsRatio"),
        "CAGR_Receitas_5a": get_val("cagrRecipesFiveYears"),
        "CAGR_Lucros_5a": get_val("cagrProfitsFiveYears"),
    }


def parse_mfinance_dividends(div_data: Dict) -> Dict[str, Any]:
    """Calcula metricas de dividendos a partir da lista de dividendos."""
    dividends = div_data.get("dividends", [])
    symbol = div_data.get("symbol", "")

    if not dividends:
        return {
            "Ticker": symbol,
            "DY_12m": 0,
            "Dividendo_Medio_12m": 0,
            "Dividendo_Total_12m": 0,
            "Dividendo_Ultimo": 0,
            "Qtd_Dividendos_12m": 0,
        }

    valid_divs = [d for d in dividends if d.get("date") is not None]

    if not valid_divs:
        return {
            "Ticker": symbol,
            "DY_12m": 0,
            "Dividendo_Medio_12m": 0,
            "Dividendo_Total_12m": 0,
            "Dividendo_Ultimo": 0,
            "Qtd_Dividendos_12m": 0,
        }

    sorted_divs = sorted(valid_divs, key=lambda x: x.get("date", ""), reverse=True)
    recent = sorted_divs[:4]

    total_12m = sum(d.get("value", 0) for d in recent)
    avg_12m = total_12m / len(recent) if recent else 0
    ultimo = sorted_divs[0].get("value", 0) if sorted_divs else 0

    return {
        "Ticker": symbol,
        "DY_12m": 0,
        "Dividendo_Medio_12m": round(avg_12m, 4),
        "Dividendo_Total_12m": round(total_12m, 4),
        "Dividendo_Ultimo": round(ultimo, 4),
        "Qtd_Dividendos_12m": len(recent),
    }


def merge_mfinance_data(
    stocks: List[Dict],
    indicators: List[Dict],
    dividends_map: Dict[str, Dict]
) -> List[Dict[str, Any]]:
    """Mescla dados basicos + indicadores + dividendos em registros unicos."""
    stock_map = {s.get("symbol", ""): s for s in stocks}
    ind_map = {i.get("symbol", ""): i for i in indicators}

    all_tickers = set(stock_map.keys()) | set(ind_map.keys())

    result = []
    for ticker in sorted(all_tickers):
        stock = stock_map.get(ticker, {})
        ind = ind_map.get(ticker, {})
        div = dividends_map.get(ticker, {
            "Ticker": ticker, "DY_12m": 0, "Dividendo_Medio_12m": 0,
            "Dividendo_Total_12m": 0, "Dividendo_Ultimo": 0,
            "Qtd_Dividendos_12m": 0
        })

        parsed_stock = parse_mfinance_stock(stock)
        parsed_ind = parse_mfinance_indicator(ind)

        merged = {**parsed_ind, **parsed_stock}

        merged["DY_12m"] = div.get("DY_12m", 0)
        merged["Dividendo_Medio_12m"] = div.get("Dividendo_Medio_12m", 0)
        merged["Dividendo_Total_12m"] = div.get("Dividendo_Total_12m", 0)
        merged["Dividendo_Ultimo"] = div.get("Dividendo_Ultimo", 0)
        merged["Qtd_Dividendos_12m"] = div.get("Qtd_Dividendos_12m", 0)

        cotacao = merged.get("Cotacao", 0)
        div_total = merged.get("Dividendo_Total_12m", 0)
        if cotacao > 0 and div_total > 0:
            merged["DY_12m"] = round((div_total / cotacao) * 100, 2)

        result.append(merged)

    return result
