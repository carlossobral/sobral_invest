"""
Cliente para API MFinance (mfinance.com.br)
API pública sem token - batch requests suportados
"""
import requests
import time
from typing import List, Dict, Optional

BASE_URL = "https://mfinance.com.br/api/v1"

class MFinanceClient:
    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "SobralInvest/1.0",
            "Accept": "application/json"
        })

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        url = f"{BASE_URL}{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro MFinance {endpoint}: {e}")
            return {}
        finally:
            time.sleep(self.delay)

    def get_all_symbols(self) -> List[str]:
        """Retorna lista de todos os tickers disponíveis"""
        data = self._get("/stocks/symbols/")
        # A API retorna lista de strings diretamente: ["PETR4", "VALE3", ...]
        if isinstance(data, list):
            return [s for s in data if isinstance(s, str) and s]
        return []

    def get_stocks_batch(self, symbols: List[str]) -> List[Dict]:
        """Busca dados básicos de múltiplos tickers (batch)"""
        symbols_str = ",".join(symbols)
        data = self._get("/stocks", params={"symbols": symbols_str})
        return data if isinstance(data, list) else []

    def get_stock(self, symbol: str) -> Dict:
        """Busca dados básicos de 1 ticker"""
        data = self._get(f"/stocks/{symbol}")
        return data if isinstance(data, dict) else {}

    def get_indicators_batch(self, symbols: List[str]) -> List[Dict]:
        """Busca indicadores de múltiplos tickers (batch)"""
        symbols_str = ",".join(symbols)
        data = self._get("/stocks/indicators", params={"symbols": symbols_str})
        return data if isinstance(data, list) else []

    def get_indicators(self, symbol: str) -> Dict:
        """Busca indicadores de 1 ticker"""
        data = self._get(f"/stocks/indicators/{symbol}")
        return data if isinstance(data, dict) else {}

    def get_details(self, symbol: str) -> Dict:
        """Busca detalhes (setor, subsetor, segmento)"""
        data = self._get(f"/stocks/details/{symbol}")
        return data if isinstance(data, dict) else {}

    def get_dividends(self, symbol: str) -> Dict:
        """Busca histórico de dividendos"""
        data = self._get(f"/stocks/dividends/{symbol}")
        return data if isinstance(data, dict) else {}

    def get_historical(self, symbol: str, months: int = 12) -> List[Dict]:
        """Busca histórico de preços"""
        data = self._get(f"/stocks/historicals/{symbol}", params={"months": months})
        return data if isinstance(data, list) else []

    def get_all_stocks_full(self, batch_size: int = 50) -> List[Dict]:
        """
        Busca TODOS os ativos com dados completos (básicos + indicadores)
        Usa batch para eficiência
        """
        symbols = self.get_all_symbols()
        print(f"Total de tickers disponíveis: {len(symbols)}")

        if not symbols:
            print("⚠️ Nenhum ticker encontrado!")
            return []

        all_data = []

        # Buscar dados básicos em batch
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            print(f"Buscando dados básicos {i+1}-{min(i+batch_size, len(symbols))}...")
            stocks = self.get_stocks_batch(batch)
            all_data.extend(stocks)

        # Buscar indicadores em batch
        indicators_map = {}
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            print(f"Buscando indicadores {i+1}-{min(i+batch_size, len(symbols))}...")
            indicators = self.get_indicators_batch(batch)
            for ind in indicators:
                sym = ind.get("symbol", "")
                if sym:
                    indicators_map[sym] = ind

        # Mesclar dados básicos + indicadores
        merged = []
        for stock in all_data:
            sym = stock.get("symbol", "")
            if sym in indicators_map:
                stock.update(indicators_map[sym])
            merged.append(stock)

        return merged


def parse_mfinance_data(raw_data: List[Dict]) -> List[Dict]:
    """
    Converte dados brutos do MFinance para formato padronizado da planilha
    """
    parsed = []

    for item in raw_data:
        if not item or not item.get("symbol"):
            continue

        # Dados básicos
        symbol = item.get("symbol", "")

        # Helper para converter valores
        def safe_float(val, default=0.0):
            if val is None or val == "":
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        def safe_pct(val, default=0.0):
            """Converte percentual (0.15 -> 15.0)"""
            v = safe_float(val, default)
            if v < 1 and v != 0:  # Provavelmente decimal
                return round(v * 100, 2)
            return round(v, 2)

        record = {
            # IDENTIFICAÇÃO
            "Ticker": symbol,
            "Nome_Empresa": item.get("name", ""),
            "Nome_Curto": item.get("shortName", item.get("name", "")),

            # COTAÇÃO
            "Cotacao": safe_float(item.get("lastPrice")),
            "Abertura": safe_float(item.get("priceOpen")),
            "Maxima": safe_float(item.get("high")),
            "Minima": safe_float(item.get("low")),
            "Variacao": safe_pct(item.get("change")),
            "Volume": safe_float(item.get("volume")),
            "Volume_Medio": safe_float(item.get("volumeAvg")),
            "Qtd_Acoes": safe_float(item.get("shares")),

            # INDICADORES DE VALUATION
            "PL": safe_float(item.get("priceEarningsRatio")),
            "PVP": safe_float(item.get("priceToBookValue")),
            "PSR": safe_float(item.get("priceToSalesRatio")),
            "P_EBIT": safe_float(item.get("priceToEbit")),
            "P_EBITDA": safe_float(item.get("priceToEbitda")),
            "EV_EBIT": safe_float(item.get("enterpriseValueEbit")),
            "EV_EBITDA": safe_float(item.get("enterpriseValueEbitda")),
            "DY": safe_pct(item.get("dividendYield")),
            "DY_TTM": safe_pct(item.get("dividendYield")),  # Mesmo campo no MFinance
            "Payout": safe_pct(item.get("payoutRatio")),

            # INDICADORES DE RENTABILIDADE
            "ROE": safe_pct(item.get("returnOnEquity")),
            "ROA": safe_pct(item.get("returnOnAssets")),
            "ROIC": safe_pct(item.get("returnOnInvestedCapital")),
            "Margem_Bruta": safe_pct(item.get("grossMargin")),
            "Margem_EBIT": safe_pct(item.get("ebitMargin")),
            "Margem_EBITDA": safe_pct(item.get("ebitdaMargin")),
            "Margem_Liquida": safe_pct(item.get("netMargin")),

            # INDICADORES DE ENDIVIDAMENTO
            "Divida_PL": safe_float(item.get("debtEquityRatio")),
            "Divida_Liquida": safe_float(item.get("netDebt")),
            "DL_EBITDA": safe_float(item.get("netDebtToEbitda")),
            "DL_EBIT": safe_float(item.get("netDebtToEbit")),
            "Liquidez_Corrente": safe_float(item.get("currentLiquidity")),

            # INDICADORES DE EFICIÊNCIA
            "Giro_Ativos": safe_float(item.get("assetTurnoverRatio")),
            "Receita_CAGR": safe_pct(item.get("cagrRecipesFiveYears")),
            "Lucro_CAGR": safe_pct(item.get("cagrProfitsFiveYears")),

            # DADOS FINANCEIROS (calculados ou diretos)
            "Market_Cap": safe_float(item.get("marketCap")),
            "Receita_TTM": safe_float(item.get("totalRevenue")),
            "EBITDA": safe_float(item.get("ebitda")),
            "Caixa": safe_float(item.get("totalCash")),

            # ANÁLISE TÉCNICA
            "Maxima_52s": safe_float(item.get("lastYearHigh")),
            "Minima_52s": safe_float(item.get("lastYearLow")),
            "Media_50d": safe_float(item.get("fiftyDayAverage")),
            "Media_200d": safe_float(item.get("twoHundredDayAverage")),
            "Beta": safe_float(item.get("beta")),

            # CLASSIFICAÇÃO
            "Setor": item.get("sector", ""),
            "SubSetor": item.get("subSector", ""),
            "Segmento": item.get("segment", ""),
            "Descricao": item.get("description", ""),
        }

        # Calcular campos derivados
        qtd_acoes = record["Qtd_Acoes"]
        if qtd_acoes > 0:
            record["Patrimonio"] = round(safe_float(item.get("bookValuePerShare")) * qtd_acoes, 2)
            record["Lucro_Liquido"] = round(safe_float(item.get("earningsPerShare")) * qtd_acoes, 2)
        else:
            record["Patrimonio"] = 0.0
            record["Lucro_Liquido"] = 0.0

        # EBIT calculado: MarketCap / (EV/EBIT) quando possível
        ev_ebit = record["EV_EBIT"]
        market_cap = record["Market_Cap"]
        if ev_ebit > 0 and market_cap > 0:
            record["EBIT"] = round(market_cap / ev_ebit, 2)
        else:
            record["EBIT"] = 0.0

        # FCO e FCL (do BRAPI se disponível, senão 0)
        record["FCO"] = safe_float(item.get("operatingCashflow"))
        record["FCL"] = safe_float(item.get("freeCashflow"))

        # CNPJ e Segmento de Listagem (do UseBolsai se disponível)
        record["CNPJ"] = item.get("cnpj", "")
        record["Segmento_Listagem"] = item.get("listing_segment", "")

        # Recomendação de analysts (do BRAPI)
        record["Recomendacao_Analysts"] = item.get("recommendationKey", "")
        record["Qtd_Analysts"] = safe_float(item.get("numberOfAnalystOpinions"))
        record["Preco_Alvo_Medio"] = safe_float(item.get("targetMeanPrice"))

        parsed.append(record)

    return parsed


if __name__ == "__main__":
    client = MFinanceClient()
    symbols = client.get_all_symbols()
    print(f"Tickers disponíveis: {len(symbols)}")
    print(f"Primeiros 10: {symbols[:10]}")
