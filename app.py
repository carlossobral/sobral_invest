"""
Sobral Invest - Coletor de Dados de Ativos B3
Atualiza data/ativos.xlsx, data/ativos.csv e data/selic.json
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

MF_BASE = "https://mfinance.com.br/api/v1"
BRAPI_BASE = "https://brapi.dev/api/v2/quote"
BRAPI_TOKEN = os.getenv("BRAPI_TOKEN", "")
BCB_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"

# ---------------------------------------------------------------------------
# MAPEAMENTO DE COLUNAS
# ---------------------------------------------------------------------------
COLUNAS_MAPEAMENTO = {
    'symbol': 'Ticker', 'name': 'Nome', 'sector': 'Setor', 'subSector': 'SubSetor',
    'segment': 'Segmento', 'type': 'Tipo', 'lastPrice': 'Preco_Atual',
    'marketCap': 'Valor_Mercado', 'volume': 'Volume', 'shares': 'Qtd_Acoes',
    'dividendYield': 'DY_Atual', 'priceEarningsRatio': 'P_L', 'priceToBookValue': 'P_VP',
    'priceToSales': 'P_Receita', 'priceToAssets': 'P_Ativo', 'priceToNetNetWorkingCapital': 'P_Cap_Giro',
    'priceToNetCurrentAssets': 'P_Ativo_Circ_Liq', 'priceToEbit': 'P_EBIT', 'priceToEbitda': 'P_EBITDA',
    'enterpriseValueEbit': 'EV_EBIT', 'enterpriseValueEbitda': 'EV_EBITDA',
    'returnOnEquity': 'ROE', 'returnOnAssets': 'ROA', 'returnOnInvestedCapital': 'ROIC',
    'assetTurnoverRatio': 'Giro_Ativos', 'grossMargin': 'Margem_Bruta', 'ebitdaMargin': 'Margem_EBITDA',
    'ebitMargin': 'Margem_EBIT', 'netMargin': 'Margem_Liquida', 'netDebtToAssets': 'Div_Liq_Ativos',
    'netDebtToEquity': 'Div_Liq_PL', 'netDebtToEbit': 'Div_Liq_EBIT', 'netDebtToEbitda': 'Div_Liq_EBITDA',
    'currentLiquidity': 'Liquidez_Corrente', 'liabilitiesToAssetsRatio': 'Passivos_Ativos',
    'equityToAssetsRatio': 'PL_Ativos', 'cagrRecipesFiveYears': 'CAGR_Receitas_5a',
    'cagrProfitsFiveYears': 'CAGR_Lucros_5a', 'netRevenue': 'Receita_Liquida',
    'netIncome': 'Lucro_Liquido', 'ebit': 'EBIT', 'earningsPerShare': 'LPA',
    'bookValuePerShare': 'VPA',
    'DIV_1A_': 'Div_1A', 'DIV_2A_': 'Div_2A', 'DIV_3A_': 'Div_3A',
    'DIV_4A_': 'Div_4A', 'DIV_5A_': 'Div_5A', 'DY_5A_PG': 'Consistencia_5A',
    'anos_listagem': 'Anos_Listagem', 'Score_CS': 'Score_CS',
    'Score_CS_Classificacao': 'Classificacao_CS'
}

ORDEM_FINAL = [
    'Ticker', 'Nome', 'Setor', 'SubSetor', 'Segmento', 'Tipo',
    'Preco_Atual', 'Valor_Mercado', 'Volume', 'Qtd_Acoes', 'DY_Atual',
    'P_L', 'P_VP', 'P_Receita', 'P_Ativo', 'P_Cap_Giro', 'P_Ativo_Circ_Liq',
    'P_EBIT', 'P_EBITDA', 'EV_EBIT', 'EV_EBITDA',
    'ROE', 'ROA', 'ROIC', 'Giro_Ativos',
    'Margem_Bruta', 'Margem_EBITDA', 'Margem_EBIT', 'Margem_Liquida',
    'Div_Liq_Ativos', 'Div_Liq_PL', 'Div_Liq_EBIT', 'Div_Liq_EBITDA',
    'Liquidez_Corrente', 'Passivos_Ativos', 'PL_Ativos',
    'CAGR_Receitas_5a', 'CAGR_Lucros_5a', 'Receita_Liquida', 'Lucro_Liquido', 'EBIT',
    'Div_1A', 'Div_2A', 'Div_3A', 'Div_4A', 'Div_5A', 'Consistencia_5A',
    'Anos_Listagem', 'Score_CS', 'Classificacao_CS'
]

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
                    time.sleep(delay * (2 ** attempt))
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
        time.sleep(0.75)
        return self._get(f"{MF_BASE}/stocks/dividends/{symbol}", retries=3, delay=1)

class BrapiClient:
    def __init__(self, token):
        self.token = token
        self.session = requests.Session()
        if not self.token:
            logger.warning("⚠ BRAPI_TOKEN não configurado.")

    def get_listing_date(self, ticker):
        if not self.token: return None
        try:
            resp = self.session.get(f"{BRAPI_BASE}/{ticker}", params={"token": self.token}, timeout=15)
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                ms = results[0].get("firstTradeDateMilliseconds")
                if ms: return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")
                return results[0].get("listingDate")
        except Exception as e:
            logger.debug(f"Erro Brapi {ticker}: {e}")
        return None

# ---------------------------------------------------------------------------
# FUNÇÕES SELIC (COM CACHE INTELIGENTE + RETRY)
# ---------------------------------------------------------------------------
def coletar_selic_historico():
    """
    Coleta série histórica da SELIC (10 anos) da API do BCB.
    - Timeout: 60s
    - Retries: 3 com backoff exponencial (5s → 10s → 20s)
    - Retorna lista de dicts: [{"data": "DD/MM/YYYY", "valor_anual": 10.75}, ...]
    """
    hoje = datetime.now()
    data_inicial = hoje.replace(year=hoje.year - 10)
    data_inicial_str = data_inicial.strftime("%d/%m/%Y")
    url = f"{BCB_BASE}?formato=json&dataInicial={data_inicial_str}"
    
    last_error = None
    for attempt in range(3):
        try:
            logger.info(f"Buscando SELIC na API BCB (tentativa {attempt+1}/3)...")
            # Timeout aumentado para 60s
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            dados = resp.json()
            
            registros = []
            for d in dados:
                try:
                    valor = float(d.get("valor", 0))
                    if valor > 0:
                        registros.append({
                            "data": d.get("data"),  # Formato: "DD/MM/YYYY"
                            "valor_anual": round(valor, 2)
                        })
                except:
                    continue
            
            if registros:
                logger.info(f"✓ SELIC: {len(registros)} registros coletados com sucesso")
                return registros
            else:
                logger.warning("SELIC: API retornou, mas sem dados válidos")
                
        except requests.exceptions.Timeout:
            last_error = "Timeout"
            logger.warning(f"SELIC: Timeout na tentativa {attempt+1}/3")
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP {e.response.status_code}"
            logger.warning(f"SELIC: Erro HTTP na tentativa {attempt+1}/3: {e}")
        except Exception as e:
            last_error = str(e)
            logger.warning(f"SELIC: Erro na tentativa {attempt+1}/3: {e}")
        
        if attempt < 2:
            # Backoff exponencial: 5s, 10s, 20s
            wait = 5 * (2 ** attempt)
            logger.info(f"SELIC: Aguardando {wait}s antes da próxima tentativa...")
            time.sleep(wait)
    
    logger.error(f"SELIC: Falha após 3 tentativas. Último erro: {last_error}")
    return None

def salvar_selic_json(novos_dados=None):
    """
    Salva selic.json com cache inteligente:
    - Se novos_dados != None: sobrescreve com dados novos + timestamp de sucesso
    - Se novos_dados == None: NÃO sobrescreve, mantém arquivo existente intacto
    """
    agora = datetime.now().isoformat()
    
    if novos_dados is not None:
        # Coleta bem-sucedida: salva novos dados
        payload = {
            "taxa_atual": novos_dados[-1]["valor_anual"] if novos_dados else None,
            "data_atualizacao": agora,
            "ultima_coleta_sucesso": agora,
            "historico": novos_dados
        }
        try:
            with open(SELIC_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info(f"✓ selic.json atualizado com {len(novos_dados)} registros")
            return True
        except Exception as e:
            logger.error(f"✗ Erro ao salvar selic.json: {e}")
            return False
    else:
        # Coleta falhou: NÃO sobrescreve, apenas loga
        logger.warning("⚠ SELIC: coleta falhou. Mantendo selic.json anterior intacto.")
        # Opcional: atualizar apenas o timestamp de última tentativa (sem apagar histórico)
        try:
            if SELIC_FILE.exists():
                with open(SELIC_FILE, "r", encoding="utf-8") as f:
                    existente = json.load(f)
                existente["ultima_tentativa"] = agora
                with open(SELIC_FILE, "w", encoding="utf-8") as f:
                    json.dump(existente, f, ensure_ascii=False, indent=2)
                logger.info("✓ selic.json: atualizado apenas 'ultima_tentativa'")
        except:
            pass  # Se não der para ler o existente, tudo bem
        return False

# ---------------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------------------
def extract_val(data):
    if data is None: return None
    if isinstance(data, dict):
        v = data.get('value')
        return float(v) if v is not None else None
    try: return float(data)
    except: return None

def calc_divs(div_data, current_year=None):
    if current_year is None: current_year = datetime.now().year
    if not div_data: return None
    divs = div_data.get("dividends", []) if isinstance(div_data, dict) else []
    if not divs: return None
    years = [current_year - i for i in range(5, 0, -1)]
    totals = {y: 0.0 for y in years}
    for d in divs:
        try:
            dt = d.get("date")
            if not dt: continue
            y = int(dt[:4])
            if y in totals: totals[y] += float(d.get("value") or 0)
        except: continue
    return {
        f'DIV_{5-i}A_': round(totals.get(current_year - i, 0.0), 4) for i in range(1, 6)
    } | {'DY_5A_PG': sum(1 for v in totals.values() if v > 0)}

def update_score(row):
    s = 0
    v = lambda k, d=None: extract_val(row.get(k)) or d
    if v('returnOnEquity', 0) > 10: s += 1
    if v('dividendYield', 0) > 6: s += 1
    dv = v('netDebtToEbitda')
    if dv is not None and 0 < dv < 2.5: s += 1
    pe = v('priceEarningsRatio')
    if pe is not None and 0 < pe < 15: s += 1
    pb = v('priceToBookValue')
    if pb is not None and 0 < pb < 2: s += 1
    if v('netMargin', 0) > 10: s += 1
    if v('currentLiquidity', 0) > 1: s += 1
    if v('cagrProfitsFiveYears', 0) > 5: s += 1
    if v('returnOnInvestedCapital', 0) > 10: s += 1
    if v('volume', 0) > 1000000: s += 1
    anos = row.get('Anos_Listagem')
    if anos is not None and anos >= 5: s += 1
    cons = row.get('Consistencia_5A')
    if cons is not None and cons >= 3: s += 1
    return s

def get_class(s):
    if s >= 10: return "Excelente"
    if s >= 8: return "Bom"
    if s >= 6: return "Regular"
    if s >= 4: return "Fraco"
    return "Pessimo"

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 60)
    logger.info("INICIANDO ATUALIZAÇÃO - SOBRAL INVEST")
    logger.info("=" * 60)

    # 1. Coleta SELIC primeiro (com cache inteligente)
    logger.info("Coletando dados da SELIC...")
    selic_novos = coletar_selic_historico()
    salvar_selic_json(selic_novos)  # Só salva se sucesso; se falhar, mantém arquivo anterior

    mf, brapi = MFinanceClient(), BrapiClient(BRAPI_TOKEN)
    stocks, indicators = mf.get_stocks(), mf.get_indicators()
    if not stocks or not indicators:
        logger.error("Falha ao obter dados iniciais."); return

    s_map = {s['symbol']: s for s in stocks if 'symbol' in s}
    i_map = {i['symbol']: i for i in indicators if 'symbol' in i}
    tickers = sorted(set(s_map.keys()) | set(i_map.keys()))
    results, current_year, falhas = [], datetime.now().year, 0

    logger.info(f"Processando {len(tickers)} ativos...")
    for i, t in enumerate(tickers):
        if i % 50 == 0 and i > 0: logger.info(f"Processados: {i}/{len(tickers)} | Falhas div: {falhas}")
        
        row = {**s_map.get(t, {}), **i_map.get(t, {})}
        listing = brapi.get_listing_date(t)
        row['Anos_Listagem'] = round((datetime.now() - datetime.strptime(listing, "%Y-%m-%d")).days / 365.25, 2) if listing else None
        
        for k, v in i_map.get(t, {}).items():
            if k not in ['symbol','name','sector','subSector','segment','type']:
                row[k] = extract_val(v)

        divs = mf.get_dividends(t)
        d_calc = calc_divs(divs, current_year) if divs else None
        if not d_calc:
            falhas += 1
            with open(FALHAS_LOG, 'a') as f: f.write(f"{datetime.now().isoformat()}|{t}|Falha API\n")
            d_calc = {f'DIV_{x}A_': None for x in range(1,6)} | {'DY_5A_PG': None}
        row.update(d_calc)
        
        row['Score_CS'] = update_score(row)
        row['Classificacao_CS'] = get_class(row['Score_CS'])
        results.append(row)

    df = pd.DataFrame(results)
    df = df[df['name'].notna() & (df['name'] != '') & (df.get('lastPrice', pd.Series([1])) > 0)]
    
    # Renomear e Reordenar
    df.rename(columns=COLUNAS_MAPEAMENTO, inplace=True)
    existentes = [c for c in ORDEM_FINAL if c in df.columns]
    extras = [c for c in df.columns if c not in existentes]
    df = df[existentes + extras]

    logger.info(f"Total válidos: {len(df)} | Colunas: {len(df.columns)}")
    try:
        with pd.ExcelWriter(ATIVOS_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='DADOS!', index=False)
        df.to_csv(ATIVOS_CSV, index=False, encoding='utf-8-sig')
        logger.info("✓ Arquivos de ativos salvos com sucesso!")
    except Exception as e:
        logger.error(f"✗ Erro ao salvar ativos: {e}")

    logger.info("✓ ATUALIZAÇÃO CONCLUÍDA!")
    if falhas > 0:
        logger.warning(f"⚠ {falhas} tickers tiveram falha na coleta de dividendos.")

if __name__ == "__main__":
    main()
