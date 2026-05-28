"""
Sobral Invest - Coletor de Dados de Ativos B3
Atualiza data/ativos.xlsx, data/ativos.csv e data/selic.json
Inclui: Anos de Listagem (Brapi), Histórico de Dividendos 5 Anos e Score CS Atualizado
"""

import os
import json
import time
import logging
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/coleta.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

ATIVOS_FILE = OUTPUT_DIR / "ativos.xlsx"
ATIVOS_CSV = OUTPUT_DIR / "ativos.csv"
SELIC_FILE = OUTPUT_DIR / "selic.json"
FALHAS_LOG = OUTPUT_DIR / "falhas_dividendos.log"

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

    def _get(self, url, params=None, retries=3, delay=1, exponential_backoff=True):
        """Requisição GET com retry exponencial e throttling."""
        last_error = None
        for attempt in range(retries):
            try:
                resp = self.session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_error = e
                logger.warning(f"Tentativa {attempt+1}/{retries} falhou para {url}: {e}")
                if attempt < retries - 1:
                    # Backoff exponencial: 1s, 2s, 4s...
                    wait_time = delay * (2 ** attempt)
                    logger.info(f"Aguardando {wait_time}s antes da próxima tentativa...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Falha definitiva para {url} após {retries} tentativas")
                    return None
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
        """Busca dividendos de um ticker com throttling e retry."""
        url = f"{MF_BASE}/stocks/dividends/{symbol}"
        # Throttling: aguarda 0.75s antes de cada chamada de dividendos
        time.sleep(0.75)
        return self._get(url, retries=3, delay=1, exponential_backoff=True)

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
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------------------

def extract_indicator_value(indicator_data):
    """Extrai apenas o valor numérico de um indicador da API MFinance."""
    if indicator_data is None:
        return None
    if isinstance(indicator_data, dict):
        val = indicator_data.get('value')
        return float(val) if val is not None else None
    try:
        return float(indicator_data)
    except (ValueError, TypeError):
        return None

def calculate_dividends_by_year(dividends_data, current_year=None):
    """
    Calcula totais de dividendos por ano civil (2021-2025) e conta anos com pagamento.
    Retorna dict com DIV_1A_ a DIV_5A_ e DY_5A_PG.
    Se falhar, retorna None para permitir fallback adequado.
    """
    if current_year is None:
        current_year = datetime.now().year
    
    if not dividends_data:
        return None

    div_list = dividends_data.get("dividends", []) if isinstance(dividends_data, dict) else []
    if not div_list:
        return None

    # Anos alvo: 2021, 2022, 2023, 2024, 2025 (considerando 2026 como ano atual)
    target_years = [current_year - 5, current_year - 4, current_year - 3, current_year - 2, current_year - 1]
    yearly_totals = {y: 0.0 for y in target_years}

    for d in div_list:
        try:
            d_date_str = d.get("date")
            if not d_date_str:
                continue
            # Extrair ano da data ISO 8601: "2025-01-31T00:00:00Z" → 2025
            d_year = int(d_date_str[:4])
            if d_year not in target_years:
                continue
            d_val = d.get("value")
            if d_val is None:
                continue
            yearly_totals[d_year] += float(d_val)
        except Exception as e:
            logger.debug(f"Erro ao processar dividendo de {d}: {e}")
            continue

    return {
        'DIV_1A_': round(yearly_totals.get(current_year - 1, 0.0), 4),
        'DIV_2A_': round(yearly_totals.get(current_year - 2, 0.0), 4),
        'DIV_3A_': round(yearly_totals.get(current_year - 3, 0.0), 4),
        'DIV_4A_': round(yearly_totals.get(current_year - 4, 0.0), 4),
        'DIV_5A_': round(yearly_totals.get(current_year - 5, 0.0), 4),
        'DY_5A_PG': sum(1 for v in yearly_totals.values() if v is not None and v > 0)
    }

def update_score_cs(row):
    """Atualiza o Score CS com 11 critérios (incluindo consistência 5A)."""
    score = 0
    
    # Helper para extrair valor com fallback seguro
    def val(key, default=None):
        v = extract_indicator_value(row.get(key))
        return v if v is not None else default
    
    if val('returnOnEquity', 0) > 10: score += 1
    if val('dividendYield', 0) > 6: score += 1
    
    dv_ebitda = val('netDebtToEbitda')
    if dv_ebitda is not None and 0 < dv_ebitda < 2.5: score += 1
    
    pe = val('priceEarningsRatio')
    if pe is not None and 0 < pe < 15: score += 1
    
    pb = val('priceToBookValue')
    if pb is not None and 0 < pb < 2: score += 1
    
    if val('netMargin', 0) > 10: score += 1
    if val('currentLiquidity', 0) > 1: score += 1
    if val('cagrProfitsFiveYears', 0) > 5: score += 1
    if val('returnOnInvestedCapital', 0) > 10: score += 1
    if val('volume', 0) > 1000000: score += 1
    
    anos = row.get('anos_listagem')
    if anos is not None and anos >= 5: score += 1
    
    # Critério de consistência: só pontua se tiver dados válidos
    dy_pg = row.get('DY_5A_PG')
    if dy_pg is not None and dy_pg >= 3: score += 1
    
    return score

def get_classification(score):
    if score >= 10: return "Excelente"
    elif score >= 8: return "Bom"
    elif score >= 6: return "Regular"
    elif score >= 4: return "Fraco"
    else: return "Pessimo"

def define_column_order():
    """Define ordem explícita das colunas para garantir consistência."""
    # Colunas básicas de identificação e mercado
    basic = ['symbol', 'name', 'sector', 'subSector', 'segment', 'type',
             'lastPrice', 'marketCap', 'volume', 'dividendYield', 'eps']
    
    # Indicadores fundamentais (API keys do MFinance) - ordem alfabética para consistência
    indicators = [
        'assetTurnoverRatio', 'bookValuePerShare', 'cagrProfitsFiveYears',
        'cagrRecipesFiveYears', 'currentLiquidity', 'ebit', 'ebitdaMargin',
        'ebitMargin', 'earningsPerShare', 'enterpriseValueEbit',
        'enterpriseValueEbitda', 'equityToAssetsRatio', 'grossMargin',
        'liabilitiesToAssetsRatio', 'marketCap', 'netDebtToAssets',
        'netDebtToEbit', 'netDebtToEbitda', 'netDebtToEquity', 'netIncome',
        'netMargin', 'netRevenue', 'priceEarningsGrowthRatio',
        'priceEarningsRatio', 'priceToAssets', 'priceToBookValue',
        'priceToEbit', 'priceToEbitda', 'priceToNetCurrentAssets',
        'priceToNetNetWorkingCapital', 'priceToSales', 'returnOnAssets',
        'returnOnEquity', 'returnOnInvestedCapital', 'shares'
    ]
    
    # Novas colunas de dividendos
    dividends = ['DIV_1A_', 'DIV_2A_', 'DIV_3A_', 'DIV_4A_', 'DIV_5A_', 'DY_5A_PG']
    
    # Score e metadados
    score_cols = ['anos_listagem', 'Score_CS', 'Score_CS_Classificacao']
    
    return basic + indicators + dividends + score_cols

def log_failure(ticker, error_msg):
    """Registra falha de coleta de dividendos em arquivo separado."""
    try:
        with open(FALHAS_LOG, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"{timestamp}|{ticker}|{error_msg}\n")
    except Exception as e:
        logger.error(f"Erro ao logar falha para {ticker}: {e}")

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
    current_year = datetime.now().year
    falhas_count = 0

    logger.info(f"Processando {len(all_tickers)} ativos...")

    for i, ticker in enumerate(all_tickers):
        if i % 50 == 0 and i > 0:
            logger.info(f"Processados: {i}/{len(all_tickers)} | Falhas em dividendos: {falhas_count}")

        stock_info = stocks_map.get(ticker, {})
        ind_info = ind_map.get(ticker, {})
        
        row = {**stock_info, **ind_info}
        row['Ticker'] = ticker

        # A. Anos de Listagem (Brapi)
        listing_date_str = brapi.get_listing_date(ticker)
        anos_listagem = None
        if listing_date_str:
            try:
                dt = datetime.strptime(listing_date_str, "%Y-%m-%d")
                anos_listagem = round((datetime.now() - dt).days / 365.25, 2)
            except: 
                pass
        row['anos_listagem'] = anos_listagem

        # B. Extrair TODOS os indicadores fundamentais (apenas o valor numérico)
        for key, data in ind_info.items():
            if key not in ['symbol', 'name', 'sector', 'subSector', 'segment', 'type']:
                row[key] = extract_indicator_value(data)

        # C. Calcular dividendos por ano civil (2021-2025) COM FALLBACK
        divs = mf.get_dividends(ticker)
        if divs is None:
            # API falhou: registrar e usar None para não distorcer Score
            log_failure(ticker, "API retornou None ou erro de conexão")
            falhas_count += 1
            div_calc = None
        else:
            div_calc = calculate_dividends_by_year(divs, current_year)
            if div_calc is None:
                # Dados vazios ou inválidos
                log_failure(ticker, "Dados de dividendos vazios ou inválidos")
                falhas_count += 1
        
        if div_calc:
            row.update(div_calc)
        else:
            # Fallback: None para não distorcer cálculos
            for col in ['DIV_1A_', 'DIV_2A_', 'DIV_3A_', 'DIV_4A_', 'DIV_5A_']:
                row[col] = None
            row['DY_5A_PG'] = None

        # D. Score CS (só calcula com dados válidos)
        row['Score_CS'] = update_score_cs(row)
        row['Score_CS_Classificacao'] = get_classification(row['Score_CS'])

        results.append(row)

    df = pd.DataFrame(results)

    # Filtros de qualidade
    if 'name' in df.columns:
        df = df[df['name'].notna() & (df['name'] != '#N/A') & (df['name'] != '')]
    if 'lastPrice' in df.columns:
        df = df[df['lastPrice'] > 0]

    # Converter colunas numéricas para float (tratando None/NaN)
    numeric_cols = [c for c in df.columns if c not in ['symbol', 'name', 'sector', 'subSector', 'segment', 'type', 'Score_CS_Classificacao']]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')  # Mantém NaN para dados ausentes

    # Ordenar colunas explicitamente
    col_order = define_column_order()
    existing_cols = [c for c in col_order if c in df.columns]
    extra_cols = [c for c in df.columns if c not in existing_cols]
    df = df[existing_cols + extra_cols]

    logger.info(f"Total de ativos válidos: {len(df)}")
    logger.info(f"Total de colunas: {len(df.columns)}")
    logger.info(f"Falhas na coleta de dividendos: {falhas_count} (ver {FALHAS_LOG})")

    try:
        # Salvar nos 3 arquivos obrigatórios
        df.to_csv(ATIVOS_CSV, index=False, encoding='utf-8-sig')
        df.to_excel(ATIVOS_FILE, index=False)
        
        # selic.json (mantém rotina existente)
        selic_data = {"taxa": 10.75, "data_atualizacao": datetime.now().isoformat()}
        with open(SELIC_FILE, 'w', encoding='utf-8') as f:
            json.dump(selic_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"✓ Arquivos salvos: {ATIVOS_CSV}, {ATIVOS_FILE}, {SELIC_FILE}")
    except Exception as e:
        logger.error(f"✗ Erro ao salvar arquivos: {e}")
        raise

    logger.info("✓ ATUALIZAÇÃO CONCLUÍDA!")
    if falhas_count > 0:
        logger.warning(f"⚠ {falhas_count} tickers tiveram falha na coleta de dividendos. Revise {FALHAS_LOG}")

if __name__ == "__main__":
    main()
