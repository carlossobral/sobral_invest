"""
Cliente MFinance API - v2.1 (CORRIGIDO)
Correções:
- PL ↔ PVP trocados no parse_mfinance_indicator()
- DivLiquida_PL renomeado para DivLiquida_Ativos (netDebtToAssets = Dívida/Ativos)
- Adicionado cálculo manual de Dívida/PL quando possível

Formatos confirmados:
- /stocks/symbols/ -> ["PETR4", "VALE3", ...] (lista de strings)
- /stocks?symbols=... -> {"stocks": [{...}, {...}]} (objeto com array 'stocks')
- /stocks/indicators?symbols=... -> {"indicators": [{symbol, ...}, ...]} (objeto com array 'indicators')
- /stocks/dividends/{symbol} -> {"symbol": "...", "dividends": [{...}]}
- /stocks/details/{symbol} -> {"details": [{...}]} (inferido do schema)
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
        """Faz request com retry automático."""
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
                    print(f"  DEBUG {url}: keys={keys[:5]}")
                elif isinstance(data, list):
                    print(f"  DEBUG {url}: list len={len(data)}")
                else:
                    print(f"  DEBUG {url}: type={type(data).__name__}, value={str(data)[:100]}")
                return data
            except requests.exceptions.Timeout:
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                print(f"⚠️ Timeout após {self.retries} tentativas: {url}")
                return None
            except requests.exceptions.HTTPError as e:
                print(f"⚠️ HTTP {e.response.status_code}: {url}")
                try:
                    print(f"  Response: {e.response.text[:200]}")
                except:
                    pass
                return None
            except Exception as e:
                print(f"⚠️ Erro em {url}: {e}")
                return None
        return None

    def get_all_symbols(self) -> List[str]:
        """Retorna lista de todos os tickers de ações."""
        data = self._request("GET", "/stocks/symbols/")
        if isinstance(data, list):
            return [s for s in data if isinstance(s, str) and s]
        return []

    def get_stocks_batch(self, symbols: List[str]) -> List[Dict]:
        """Busca dados básicos de múltiplos tickers. Retorna lista de dicts."""
        if not symbols:
            return []
        symbols_str = ",".join(symbols)
        data = self._request("GET", f"/stocks?symbols={symbols_str}")
        if isinstance(data, dict) and "stocks" in data and data["stocks"] is not None:
            return data["stocks"]
        return []

    def get_indicators_batch(self, symbols: List[str]) -> List[Dict]:
        """Busca indicadores de múltiplos tickers. Retorna lista de dicts."""
        if not symbols:
            return []
        symbols_str = ",".join(symbols)
        data = self._request("GET", f"/stocks/indicators?symbols={symbols_str}")
        if isinstance(data, dict) and "indicators" in data and data["indicators"] is not None:
            return data["indicators"]
        return []

    def get_dividends(self, symbol: str) -> Dict[str, Any]:
        """Busca dividendos de 1 ticker. Retorna {"symbol": "...", "dividends": [...]}."""
        data = self._request("GET", f"/stocks/dividends/{symbol}")
        if isinstance(data, dict) and "dividends" in data:
            return data
        return {"symbol": symbol, "dividends": []}

    def get_details(self, symbol: str) -> Dict[str, Any]:
        """Busca detalhes de 1 ticker. Retorna dict com type, subSector, segment."""
        data = self._request("GET", f"/stocks/details/{symbol}")
        if isinstance(data, dict) and "details" in data:
            details_list = data["details"]
            if details_list and isinstance(details_list, list):
                return details_list[0]
        return {}

    def get_all_stocks(self, batch_size: int = BATCH_SIZE) -> List[Dict]:
        """Busca TODOS os ativos do MFinance (dados básicos)."""
        symbols = self.get_all_symbols()
        if not symbols:
            return []
        print(f"📊 Total de tickers disponíveis: {len(symbols)}")

        all_stocks = []
        batch_worked = False
        test_batch = symbols[:10]
        print(f"  [CAMADA 1] Testando batch com {len(test_batch)} tickers...")
        stocks = self.get_stocks_batch(test_batch)
        if stocks and len(stocks) > 0:
            all_stocks.extend(stocks)
            batch_worked = True
            print(f"  ✅ Batch funcionou! {len(stocks)} ativos")
        else:
            print(f"  ❌ Batch falhou")

        if batch_worked:
            print("  ✅ Modo batch ativado. Processando todos...")
            for i in range(10, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                print(f"  Batch {i+1}-{min(i+batch_size, len(symbols))}...")
                stocks = self.get_stocks_batch(batch)
                if stocks is not None and len(stocks) > 0:
                    all_stocks.extend(stocks)
                time.sleep(0.3)
        else:
            print("  ⚠️ CAMADA 2: Modo individual...")
            all_stocks = self.get_all_stocks_single(symbols)

        print(f"✅ Total coletado: {len(all_stocks)} ativos")
        return all_stocks

    def get_stock_single(self, symbol: str) -> Optional[Dict]:
        """Busca dados de 1 ticker individualmente (fallback se batch falhar)."""
        data = self._request("GET", f"/stocks/{symbol}")
        if isinstance(data, dict):
            return data
        return None

    def get_indicators_single(self, symbol: str) -> Optional[Dict]:
        """Busca indicadores de 1 ticker individualmente."""
        data = self._request("GET", f"/stocks/indicators/{symbol}")
        if isinstance(data, dict):
            return data
        return None

    def get_all_stocks_single(self, symbols: List[str]) -> List[Dict]:
        """Busca TODOS os ativos 1 por 1 (fallback quando batch falha)."""
        print(f"Usando modo individual para {len(symbols)} ativos...")
        all_stocks = []
        for i, sym in enumerate(symbols):
            if i % 50 == 0:
                print(f"  {i+1}/{len(symbols)}...")
            stock = self.get_stock_single(sym)
            if stock:
                all_stocks.append(stock)
            time.sleep(0.2)
        return all_stocks

    def get_all_indicators_single(self, symbols: List[str]) -> List[Dict]:
        """Busca indicadores 1 por 1 (fallback quando batch falha)."""
        print(f"Usando modo individual para {len(symbols)} indicadores...")
        all_indicators = []
        for i, sym in enumerate(symbols):
            if i % 50 == 0:
                print(f"  {i+1}/{len(symbols)}...")
            ind = self.get_indicators_single(sym)
            if ind:
                all_indicators.append(ind)
            time.sleep(0.2)
        return all_indicators

    def get_all_indicators(self, symbols: List[str], batch_size: int = BATCH_SIZE) -> List[Dict]:
        """Busca indicadores para uma lista de símbolos."""
        if not symbols:
            return []

        all_indicators = []
        batch_worked = False
        test_batch = symbols[:10]
        print(f"  [CAMADA 1] Testando batch indicadores {len(test_batch)} tickers...")
        indicators = self.get_indicators_batch(test_batch)
        if indicators and len(indicators) > 0:
            all_indicators.extend(indicators)
            batch_worked = True
            print(f"  ✅ Batch funcionou! {len(indicators)} indicadores")
        else:
            print(f"  ❌ Batch falhou")

        if batch_worked:
            print("  ✅ Modo batch ativado. Processando todos...")
            for i in range(10, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                print(f"  Indicadores {i+1}-{min(i+batch_size, len(symbols))}...")
                indicators = self.get_indicators_batch(batch)
                if indicators is not None and len(indicators) > 0:
                    all_indicators.extend(indicators)
                time.sleep(0.3)
        else:
            print("  ⚠️ CAMADA 2: Modo individual...")
            all_indicators = self.get_all_indicators_single(symbols)

        print(f"✅ Total indicadores: {len(all_indicators)}")
        return all_indicators


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
    Extrai valores numéricos dos indicadores do MFinance.

    CORREÇÃO v2.1:
    - PL agora usa priceEarningsRatio (P/L = Preço/Lucro)
    - PVP agora usa priceToBookValue (P/VP = Preço/Valor Patrimonial)
    - DivLiquida_Ativos = netDebtToAssets (Dívida Líquida / Ativos Totais)
    - DivLiquida_PL será calculado no app.py (MFinance não tem diretamente)
    """
    def get_val(key: str) -> float:
        obj = ind.get(key)
        if isinstance(obj, dict):
            return obj.get("value", 0) or 0
        return obj or 0

    return {
        "Ticker": ind.get("symbol", ""),
        # CORRIGIDO: PL = P/L = priceEarningsRatio
        "PL": get_val("priceEarningsRatio"),
        # CORRIGIDO: PVP = P/VP = priceToBookValue
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
        # RENOMEADO: netDebtToAssets = Dívida/Ativos (não Dívida/PL)
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
    """Calcula métricas de dividendos a partir da lista de dividendos."""
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
    """Mescla dados básicos + indicadores + dividendos em registros únicos."""
    stock_map = {s.get("symbol", ""): s for s in stocks}
    ind_map = {i.get("symbol", ""): i for i in indicators}

    all_tickers = set(stock_map.keys()) | set(ind_map.keys())

    result = []
    for ticker in sorted(all_tickers):
        stock = stock_map.get(ticker, {})
        ind = ind_map.get(ticker, {})
        div = dividends_map.get(ticker, {"Ticker": ticker, "DY_12m": 0, "Dividendo_Medio_12m": 0,
                                         "Dividendo_Total_12m": 0, "Dividendo_Ultimo": 0,
                                         "Qtd_Dividendos_12m": 0})

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
