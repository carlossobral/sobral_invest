"""
Sobral Invest - Coletor de Dados de Ativos B3
Atualiza data/ativos.xlsx (aba DADOS!), data/ativos.csv e data/selic.json
"""

import os
import json
import time
import logging
import numpy as np
import requests
import yfinance as yf
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

MF_BASE = "https://mfinance.com.br/api/v1"
BCB_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"

# ---------------------------------------------------------------------------
# MAPEAMENTO E ORDEM DE COLUNAS
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
    'DIV_0A_': 'Div_0A', 'DIV_1A_': 'Div_1A', 'DIV_2A_': 'Div_2A', 'DIV_3A_': 'Div_3A',
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
    'Div_0A', 'Div_1A', 'Div_2A', 'Div_3A', 'Div_4A', 'Div_5A', 'Consistencia_5A',
    'Anos_Listagem', 'Score_CS', 'Classificacao_CS',
    # Colunas de Valuation (novas)
    'Graham', 'GrahamBR', 'Bazin', 'Lynch', 'Agf',
    'Graham_dif', 'GrahamBR_dif', 'Bazin_dif', 'Lynch_dif', 'Agf_dif'
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

# ---------------------------------------------------------------------------
# FUNÇÕES SELIC (COM CACHE INTELIGENTE + RETRY)
# ---------------------------------------------------------------------------
def coletar_selic_historico():
    hoje = datetime.now()
    data_inicial = hoje.replace(year=hoje.year - 10)
    data_inicial_str = data_inicial.strftime("%d/%m/%Y")
    url = f"{BCB_BASE}?formato=json&dataInicial={data_inicial_str}"
    
    for attempt in range(3):
        try:
            logger.info(f"SELIC: tentativa {attempt+1}/3...")
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            dados = resp.json()
            registros = []
            for d in dados:
                try:
                    valor = float(d.get("valor", 0))
                    if valor > 0:
                        registros.append({"data": d.get("data"), "valor_anual": round(valor, 2)})
                except: continue
            if registros:
                logger.info(f"✓ SELIC: {len(registros)} registros coletados")
                return registros
        except Exception as e:
            logger.warning(f"SELIC falha tentativa {attempt+1}: {e}")
            if attempt < 2: time.sleep(5 * (2 ** attempt))
            
    logger.error("SELIC: falha definitiva. Mantendo cache anterior.")
    return None

def salvar_selic_json(novos_dados=None):
    agora = datetime.now().isoformat()
    if novos_dados is not None:
        payload = {
            "taxa_atual": novos_dados[-1]["valor_anual"],
            "data_atualizacao": agora,
            "ultima_coleta_sucesso": agora,
            "historico": novos_dados
        }
        try:
            with open(SELIC_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info("✓ selic.json atualizado com sucesso")
        except Exception as e:
            logger.error(f"✗ Erro ao salvar selic.json: {e}")
    else:
        logger.warning("⚠ SELIC: coleta falhou. Arquivo anterior mantido.")
        try:
            if SELIC_FILE.exists():
                with open(SELIC_FILE, "r", encoding="utf-8") as f: existente = json.load(f)
                existente["ultima_tentativa"] = agora
                with open(SELIC_FILE, "w", encoding="utf-8") as f: json.dump(existente, f, ensure_ascii=False, indent=2)
        except: pass

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

def safe_div(a, b):
    """Divisão segura que retorna 0 se b for 0 ou NaN."""
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.where(b != 0, a / b, 0)
        return np.where(np.isfinite(result), result, 0)

CACHE_LISTAGEM_FILE = OUTPUT_DIR / "listagem.json"

def carregar_cache_listagem():
    if CACHE_LISTAGEM_FILE.exists():
        try:
            with open(CACHE_LISTAGEM_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar cache de listagem: {e}")
    return {}

def salvar_cache_listagem(cache):
    try:
        with open(CACHE_LISTAGEM_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info("✓ Cache de listagem salvo com sucesso")
    except Exception as e:
        logger.error(f"Erro ao salvar cache de listagem: {e}")

def get_listing_date_yf(ticker, cache, force_update=False):
    """Calcula anos de listagem usando cache local e, opcionalmente, yfinance."""
    if ticker in cache:
        cached_val = cache[ticker]
        if cached_val == "N/A": return 0.0
        try:
            first_date = datetime.strptime(cached_val, "%Y-%m-%d").date()
            anos = (datetime.now().date() - first_date).days / 365.25
            return round(anos, 2)
        except Exception as e:
            logger.warning(f"Erro ao converter data do cache para {ticker}: {e}")
            
    if not force_update: return 0.0
    
    try:
        logger.info(f"yfinance: buscando data de listagem para {ticker}...")
        yf_ticker = yf.Ticker(f"{ticker}.SA")
        hist = yf_ticker.history(period="max")
        if not hist.empty:
            first_date = hist.index[0].date()
            cache[ticker] = first_date.strftime("%Y-%m-%d")
            anos = (datetime.now().date() - first_date).days / 365.25
            time.sleep(0.5)
            return round(anos, 2)
        else:
            cache[ticker] = "N/A"
    except Exception as e:
        logger.warning(f"yfinance falhou ao buscar listagem para {ticker}: {e}")
    return 0.0

def calc_divs(div_data, current_year=None):
    if current_year is None: current_year = datetime.now().year
    if not div_data: return None
    divs = div_data.get("dividends", []) if isinstance(div_data, dict) else []
    if not divs: return None
    
    years = [current_year - i for i in range(6)]
    totals = {y: 0.0 for y in years}
    
    for d in divs:
        try:
            dt = d.get("date")
            if not dt: continue
            y = int(dt[:4])
            if y in totals: totals[y] += float(d.get("value") or 0)
        except: continue
        
    return {
        'DIV_0A_': round(totals.get(current_year, 0.0), 4),
        'DIV_1A_': round(totals.get(current_year - 1, 0.0), 4),
        'DIV_2A_': round(totals.get(current_year - 2, 0.0), 4),
        'DIV_3A_': round(totals.get(current_year - 3, 0.0), 4),
        'DIV_4A_': round(totals.get(current_year - 4, 0.0), 4),
        'DIV_5A_': round(totals.get(current_year - 5, 0.0), 4),
        'DY_5A_PG': sum(1 for i in range(1, 6) if totals.get(current_year - i, 0) > 0)
    }

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
    anos = row.get('Anos_Listagem', 0)
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
# CÁLCULO DE VALUATION (NOVAS COLUNAS)
# ---------------------------------------------------------------------------
def calcular_valuation(df):
    """Calcula as 10 colunas de valuation solicitadas."""
    logger.info("Calculando indicadores de valuation (Graham, Bazin, Lynch, AGF)...")
    
    # Garantir tipos numéricos
    cols_numericas = ['Preco_Atual', 'LPA', 'VPA', 'DY_Atual', 'CAGR_Lucros_5a']
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 1. Graham Clássico: √(22.5 × LPA × VPA)
    df['Graham'] = np.sqrt(22.5 * df['LPA'] * df['VPA'])
    
    # 2. Graham BR (Conservador): √(15 × LPA × VPA)
    df['GrahamBR'] = np.sqrt(15 * df['LPA'] * df['VPA'])
    
    # 3. Bazin: (DY / 6%) × Preço
    # Fórmula: Preço Justo = Dividendo por Ação / 0.06
    # Como temos DY% = (Div/Preço)*100 -> Div = (DY * Preço) / 100
    # Logo: Preço Justo = (DY * Preço / 100) / 0.06 = Preço * DY / 6
    df['Bazin'] = df['Preco_Atual'] * df['DY_Atual'] / 6.0
    
    # 4. Lynch: LPA × (1 + CAGR_Lucros_5a/100)
    df['Lynch'] = df['LPA'] * (1 + df['CAGR_Lucros_5a'] / 100.0)
    
    # 5. AGF (Média Ponderada): (Graham + GrahamBR + Bazin + Lynch + Preço*0.8) / 5
    df['Agf'] = (df['Graham'] + df['GrahamBR'] + df['Bazin'] + df['Lynch'] + (df['Preco_Atual'] * 0.8)) / 5.0
    
    # 6. Diferenças Percentuais (Upside/Downside): (Preço Justo / Preço Atual - 1) * 100
    df['Graham_dif'] = (safe_div(df['Graham'], df['Preco_Atual']) - 1) * 100
    df['GrahamBR_dif'] = (safe_div(df['GrahamBR'], df['Preco_Atual']) - 1) * 100
    df['Bazin_dif'] = (safe_div(df['Bazin'], df['Preco_Atual']) - 1) * 100
    df['Lynch_dif'] = (safe_div(df['Lynch'], df['Preco_Atual']) - 1) * 100
    df['Agf_dif'] = (safe_div(df['Agf'], df['Preco_Atual']) - 1) * 100
    
    # Arredondar para 2 casas decimais
    cols_valuation = ['Graham', 'GrahamBR', 'Bazin', 'Lynch', 'Agf', 
                      'Graham_dif', 'GrahamBR_dif', 'Bazin_dif', 'Lynch_dif', 'Agf_dif']
    for col in cols_valuation:
        if col in df.columns:
            df[col] = df[col].round(2)
    
    return df

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 60)
    logger.info("INICIANDO ATUALIZAÇÃO - SOBRAL INVEST")
    logger.info("=" * 60)

    # 1. SELIC
    logger.info("Coletando SELIC...")
    selic_novos = coletar_selic_historico()
    salvar_selic_json(selic_novos)

    mf = MFinanceClient()
    stocks, indicators = mf.get_stocks(), mf.get_indicators()
    if not stocks or not indicators:
        logger.error("Falha ao obter dados iniciais."); return

    s_map = {s['symbol']: s for s in stocks if 'symbol' in s}
    i_map = {i['symbol']: i for i in indicators if 'symbol' in i}
    tickers = sorted(set(s_map.keys()) | set(i_map.keys()))
    results, current_year, falhas = [], datetime.now().year, 0

    # Carregar cache de listagem
    cache_listagem = carregar_cache_listagem()
    cache_modificado = False

    logger.info(f"Processando {len(tickers)} ativos...")
    for i, t in enumerate(tickers):
        if i % 50 == 0 and i > 0: 
            logger.info(f"Processados: {i}/{len(tickers)} | Falhas div: {falhas}")
        
        row = {**s_map.get(t, {}), **i_map.get(t, {})}
        
        tamanho_cache_antes = len(cache_listagem)
        row['Anos_Listagem'] = get_listing_date_yf(t, cache_listagem, force_update=(t not in cache_listagem))
        if len(cache_listagem) > tamanho_cache_antes:
            cache_modificado = True

        for k, v in i_map.get(t, {}).items():
            if k not in ['symbol','name','sector','subSector','segment','type']:
                row[k] = extract_val(v)

        divs = mf.get_dividends(t)
        d_calc = calc_divs(divs, current_year) if divs else None
        if not d_calc:
            falhas += 1
            with open(FALHAS_LOG, 'a') as f: f.write(f"{datetime.now().isoformat()}|{t}|Falha API\n")
            d_calc = {f'DIV_{x}A_': 0.0 for x in range(6)} | {'DY_5A_PG': 0}
        row.update(d_calc)
        
        row['Score_CS'] = update_score(row)
        row['Classificacao_CS'] = get_class(row['Score_CS'])
        results.append(row)
        
        if cache_modificado and i > 0 and i % 10 == 0:
            salvar_cache_listagem(cache_listagem)
            
        time.sleep(0.3)

    df = pd.DataFrame(results)
    df = df[df['name'].notna() & (df['name'] != '') & (df.get('lastPrice', pd.Series([1])) > 0)]
    
    df.rename(columns=COLUNAS_MAPEAMENTO, inplace=True)
    
    # ==========================================================
    # 🧮 MATEMÁTICA REVERSA (Indicadores Ausentes)
    # ==========================================================
    logger.info("Calculando indicadores por matemática reversa...")
    for col in ['LPA', 'Qtd_Acoes', 'Valor_Mercado', 'P_EBIT', 'P_EBITDA', 'Margem_Liquida', 'Margem_EBITDA', 'P_L']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 1. Lucro Líquido (LPA * Qtd_Acoes)
    df['Lucro_Liquido'] = df['LPA'] * df['Qtd_Acoes']
    df.loc[df['Lucro_Liquido'].isna(), 'Lucro_Liquido'] = safe_div(df['Valor_Mercado'], df['P_L'])

    # 2. EBIT (Valor_Mercado / P_EBIT)
    df['EBIT'] = safe_div(df['Valor_Mercado'], df['P_EBIT'])

    # 3. Receita Líquida (Valor_Mercado / P_Receita ou margens)
    df['Receita_Liquida'] = safe_div(df['Valor_Mercado'], df['P_Receita'])
    mask_rec = df['Receita_Liquida'].isna() | (df['Receita_Liquida'] == 0)
    df.loc[mask_rec, 'Receita_Liquida'] = safe_div(df['Lucro_Liquido'], df['Margem_Liquida'] / 100)
    ebitda_est = safe_div(df['Valor_Mercado'], df['P_EBITDA'])
    df.loc[mask_rec & df['Receita_Liquida'].isna(), 'Receita_Liquida'] = safe_div(ebitda_est, df['Margem_EBITDA'] / 100)

    # 4. P/Receita (Recalcular para consistência)
    df['P_Receita'] = safe_div(df['Valor_Mercado'], df['Receita_Liquida'])

    # Limpar infinitos e nulos gerados por divisões inválidas
    for col in ['Lucro_Liquido', 'EBIT', 'Receita_Liquida', 'P_Receita']:
        df[col] = df[col].replace([np.inf, -np.inf], 0).fillna(0)

    # ==========================================================
    # 📊 CÁLCULO DE VALUATION (NOVAS COLUNAS)
    # ==========================================================
    df = calcular_valuation(df)

    # Reordenar colunas
    existentes = [c for c in ORDEM_FINAL if c in df.columns]
    extras = [c for c in df.columns if c not in existentes]
    df = df[existentes + extras]

    # Conversão numérica forçada
    numeric_targets = ['Div_0A', 'Div_1A', 'Div_2A', 'Div_3A', 'Div_4A', 'Div_5A', 'Consistencia_5A', 'Anos_Listagem', 
                       'Lucro_Liquido', 'EBIT', 'Receita_Liquida', 'P_Receita',
                       'Graham', 'GrahamBR', 'Bazin', 'Lynch', 'Agf',
                       'Graham_dif', 'GrahamBR_dif', 'Bazin_dif', 'Lynch_dif', 'Agf_dif']
    for col in numeric_targets:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    logger.info(f"Total válidos: {len(df)} | Colunas: {len(df.columns)}")
    try:
        with pd.ExcelWriter(ATIVOS_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='DADOS!', index=False)
        df.to_csv(ATIVOS_CSV, index=False, encoding='utf-8-sig')
        logger.info("✓ Arquivos salvos com sucesso!")
    except Exception as e:
        logger.error(f"✗ Erro ao salvar: {e}")

    if cache_modificado:
        salvar_cache_listagem(cache_listagem)

    logger.info("✓ ATUALIZAÇÃO CONCLUÍDA!")
    if falhas > 0:
        logger.warning(f"⚠ {falhas} tickers tiveram falha na coleta de dividendos.")

if __name__ == "__main__":
    main()
