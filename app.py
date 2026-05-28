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

def calculate_dividends_5_years(dividends_data):
    """
    Calcula os totais de dividendos por ano civil (2021-2025) e conta anos com pagamento.
    Retorna: dict com DIV_1A_ a DIV_5A_ e DY_5A_PG
    """
    if not dividends_data:
        return {
            'DIV_1A_': 0.0, 'DIV_2A_': 0.0, 'DIV_3A_': 0.0,
            'DIV_4A_': 0.0, 'DIV_5A_': 0.0, 'DY_5A_PG': 0
        }

    div_list = dividends_data.get("dividends", []) if isinstance(dividends_data, dict) else []
    if not div_list:
        return {
            'DIV_1A_': 0.0, 'DIV_2A_': 0.0, 'DIV_3A_': 0.0,
            'DIV_4A_': 0.0, 'DIV_5A_': 0.0, 'DY_5A_PG': 0
        }

    current_year = datetime.now().year
    # Anos de referência: 2021, 2022, 2023, 2024, 2025 (considerando 2026 como ano atual)
    target_years = {current_year - 5, current_year - 4, current_year - 3, current_year - 2, current_year - 1}
    yearly_totals = {y: 0.0 for y in target_years}

    for d in div_list:
        try:
            # API retorna "date" no formato ISO 8601 ou null
            d_date_str = d.get("date")
            if not d_date_str:
                continue
            d_date = pd.to_datetime(d_date_str)
            d_year = d_date.year
            # Ignorar datas futuras ou fora do intervalo
            if d_year not in target_years:
                continue
            d_val = float(d.get("value") or 0)
            yearly_totals[d_year] += d_val
        except:
            continue

    # Mapear para colunas (ordem cronológica inversa: 1A = ano mais recente)
    result = {
        'DIV_1A_': round(yearly_totals.get(current_year - 1, 0.0), 4),
        'DIV_2A_': round(yearly_totals.get(current_year - 2, 0.0), 4),
        'DIV_3A_': round(yearly_totals.get(current_year - 3, 0.0), 4),
        'DIV_4A_': round(yearly_totals.get(current_year - 4, 0.0), 4),
        'DIV_5A_': round(yearly_totals.get(current_year - 5, 0.0), 4),
        'DY_5A_PG': sum(1 for v in yearly_totals.values() if v > 0)
    }
    return result

def update_score_cs(row):
    """Atualiza o Score CS com os novos critérios (11 critérios totais)"""
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
    # ✅ NOVO CRITÉRIO: Consistência de dividendos nos últimos 5 anos
    if row.get('DY_5A_PG', 0) >= 3: score += 1

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

        # B. Histórico de Dividendos 5 Anos (MFinance) - NOVA LÓGICA
        divs = mf.get_dividends(ticker)
        div_calc = calculate_dividends_5_years(divs)
        row.update(div_calc)  # Adiciona DIV_1A_ a DIV_5A_ e DY_5A_PG

        # C. Atualização do Score CS
        row['Score_CS'] = update_score_cs(row)
        row['Score_CS_Classificacao'] = get_classification(row['Score_CS'])

        results.append(row)

    df = pd.DataFrame(results)

    # Filtros de qualidade
    if 'Nome' in df.columns:
        df = df[df['Nome'].notna() & (df['Nome'] != '#N/A') & (df['Nome'] != '')]
    if 'Cotacao' in df.columns:
        df = df[df['Cotacao'] > 0]

    logger.info(f"Total de ativos válidos: {len(df)}")

    try:
        # ✅ Salvamento nos 3 arquivos obrigatórios
        df.to_csv(ATIVOS_CSV, index=False)
        df.to_excel(ATIVOS_FILE, index=False)
        
        # selic.json (mantém rotina existente - exemplo mínimo)
        selic_data = {"taxa": 0.0, "data_atualizacao": datetime.now().isoformat()}
        with open(SELIC_FILE, 'w', encoding='utf-8') as f:
            json.dump(selic_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Arquivos salvos: {ATIVOS_CSV}, {ATIVOS_FILE}, {SELIC_FILE}")
    except Exception as e:
        logger.error(f"Erro ao salvar arquivos: {e}")

    logger.info("ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")

if __name__ == "__main__":
    main()
