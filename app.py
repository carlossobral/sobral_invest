"""
Sobral Invest - Coletor de Dados de Ativos B3
Atualiza data/ativos.xlsx, data/ativos.csv e data/selic.json
Inclui: Anos de Listagem (Brapi), DY Médio 6 Anos (MFinance) e Score CS Atualizado
"""

import os
import json
import time
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

ATIVOS_FILE = OUTPUT_DIR / "ativos.xlsx"
ATIVOS_CSV = OUTPUT_DIR / "ativos.csv"
SELIC_FILE = OUTPUT_DIR / "selic.json"

# APIs
MF_BASE = "https://mfinance.com.br/api/v1"
BRAPI_BASE = "https://brapi.dev/api/quote"
BRAPI_TOKEN = os.getenv("BRAPI_TOKEN", "")

# ---------------------------------------------------------------------------
# CLIENTES DE API
# ---------------------------------------------------------------------------

class MFinanceClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def _get(self, url, params=None, retries=3, delay=1):
        for attempt in range(retries):
            try:
                resp = self.session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning(f"Tentativa {attempt+1}/{retries} falhou para {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                else:
                    return None

    def get_stocks(self):
        logger.info("Buscando lista de ativos...")
        data = self._get(f"{MF_BASE}/stocks")
        return data if isinstance(data, list) else data.get("stocks", [])

    def get_indicators(self):
        logger.info("Buscando indicadores fundamentais...")
        data = self._get(f"{MF_BASE}/stocks/indicators")
        return data if isinstance(data, list) else data.get("indicators", [])

    def get_dividends(self, symbol):
        """Busca dividendos de um ticker"""
        url = f"{MF_BASE}/stocks/dividends/{symbol}"
        return self._get(url, retries=2, delay=0.5)

    def get_historical(self, symbol, months=72):
        """Busca histórico de preços via mfinance (CORRETO: usa parâmetro 'months')"""
        # CORREÇÃO: endpoint correto com parâmetro 'months'
        url = f"{MF_BASE}/stocks/historicals/{symbol}"
        params = {"months": months}  # 6 anos = 72 meses
        return self._get(url, params=params, retries=2, delay=0.5)

class BrapiClient:
    def __init__(self, token):
        self.token = token
        self.session = requests.Session()

    def get_listing_date(self, ticker):
        """Busca data de listagem via Brapi"""
        if not self.token:
            return None
        url = f"{BRAPI_BASE}/{ticker}"
        try:
            resp = self.session.get(url, params={"token": self.token}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    return results[0].get("listingDate")
        except Exception as e:
            logger.debug(f"Erro Brapi {ticker}: {e}")
        return None

# ---------------------------------------------------------------------------
# FUNÇÕES DE CÁLCULO
# ---------------------------------------------------------------------------

def calculate_dy_6_years(dividends_data, historical_data):
    """Calcula o Dividend Yield médio dos últimos 6 anos"""
    if not dividends_data or not historical_data:
        return 0.0

    divs = dividends_data.get("dividends", [])
    hist = historical_data if isinstance(historical_data, list) else []
    
    if not divs or not hist:
        return 0.0

    try:
        df_div = pd.DataFrame(divs)
        df_hist = pd.DataFrame(hist)
        
        if df_div.empty or df_hist.empty:
            return 0.0
        
        df_div['date'] = pd.to_datetime(df_div['date'])
        df_hist['date'] = pd.to_datetime(df_hist['date'])

        current_year = datetime.now().year
        years_range = range(current_year - 6, current_year + 1)

        dy_list = []
        for year in years_range:
            d_year = df_div[df_div['date'].dt.year == year]
            h_year = df_hist[df_hist['date'].dt.year == year]

            total_div = d_year['value'].sum()
            avg_price = h_year['close'].mean()

            if total_div > 0 and avg_price > 0 and len(h_year) > 30:
                dy = (total_div / avg_price) * 100
                dy_list.append(dy)

        if len(dy_list) >= 3:
            return sum(dy_list) / len(dy_list)
    except Exception as e:
        logger.error(f"Erro ao calcular DY 6 anos: {e}")
    
    return 0.0

def update_score_cs(row):
    """Atualiza o Score CS com os novos critérios"""
    score = 0
    
    if row.get('ROE', 0) > 10: score += 1
    if row.get('DY_12m', 0) > 6: score += 1
    if 0 < row.get('DivLiquida_EBITDA', 999) < 2.5: score += 1
    if 0 < row.get('PL', 999) < 15: score += 1
    if 0 < row.get('PVP', 999) < 2: score += 1
    if row.get('MargemLiquida', 0) > 10: score += 1
    if row.get('LiquidezCorrente', 0) > 1: score += 1
    if row.get('CAGR_Lucros_5a', 0) > 5: score += 1
    if row.get('ROIC', 0) > 10: score += 1
    if row.get('Volume', 0) > 1000000: score += 1
    if row.get('anos_listagem', 0) >= 5: score += 1
    if row.get('DY_medio_6a', 0) > 6: score += 1

    return score

def get_classification(score):
    if score >= 10: return "Excelente"
    elif score >= 8: return "Bom"
    elif score >= 6: return "Regular"
    elif score >= 4: return "Fraco"
    else: return "Pessimo"

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 60)
    logger.info("INICIANDO ATUALIZAÇÃO - SOBRAL INVEST")
    logger.info("=" * 60)

    mf = MFinanceClient()
    brapi = BrapiClient(BRAPI_TOKEN)

    stocks = mf.get_stocks()
    indicators = mf.get_indicators()

    if not stocks or not indicators:
        logger.error("Falha ao obter dados iniciais do MFinance.")
        return

    stocks_map = {s['symbol']: s for s in stocks if 'symbol' in s}
    ind_map = {i['symbol']: i for i in indicators if 'symbol' in i}
    all_tickers = sorted(set(stocks_map.keys()) | set(ind_map.keys()))

    results = []

    logger.info(f"Processando {len(all_tickers)} ativos...")

    for i, ticker in enumerate(all_tickers):
        if i % 50 == 0:
            logger.info(f"Processados: {i}/{len(all_tickers)}")

        stock_info = stocks_map.get(ticker, {})
        ind_info = ind_map.get(ticker, {})
        
        row = {**stock_info, **ind_info}
        row['Ticker'] = ticker

        # A. Anos de Listagem (Brapi)
        listing_date_str = brapi.get_listing_date(ticker)
        anos_listagem = 0
        if listing_date_str:
            try:
                dt = datetime.strptime(listing_date_str, "%Y-%m-%d")
                anos_listagem = (datetime.now() - dt).days / 365.25
            except: pass
        row['anos_listagem'] = round(anos_listagem, 2)

        # B. DY Médio 6 Anos (MFinance) - CORREÇÃO AQUI
        divs = mf.get_dividends(ticker)
        hist = mf.get_historical(ticker, months=72)  # CORREÇÃO: parâmetro 'months'
        dy_6a = calculate_dy_6_years(divs, hist)
        row['DY_medio_6a'] = round(dy_6a, 2)

        # C. Atualização do Score CS
        row['Score_CS'] = update_score_cs(row)
        row['Score_CS_Classificacao'] = get_classification(row['Score_CS'])

        results.append(row)

    df = pd.DataFrame(results)

    if 'Nome' in df.columns:
        df = df[df['Nome'].notna() & (df['Nome'] != '#N/A') & (df['Nome'] != '')]
    if 'Cotacao' in df.columns:
        df = df[df['Cotacao'] > 0]

    logger.info(f"Total de ativos válidos: {len(df)}")

    try:
        df.to_csv(ATIVOS_CSV, index=False)
        df.to_excel(ATIVOS_FILE, index=False)
        logger.info(f"Arquivos salvos: {ATIVOS_CSV}, {ATIVOS_FILE}")
    except Exception as e:
        logger.error(f"Erro ao salvar arquivos: {e}")

    logger.info("ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")

if __name__ == "__main__":
    main()
