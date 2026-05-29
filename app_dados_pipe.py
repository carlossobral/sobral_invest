"""
Sobral Invest - Coletor de Dados de Ativos B3 (Pipeline Modular)
Etapas: SELIC → Stocks → Indicators → Filter → Dividends → Reverse Math → Export → Listagem YF
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
CACHE_LISTAGEM_FILE = OUTPUT_DIR / "listagem.json"

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
    # Valuation
    'Graham', 'GrahamBR', 'Bazin', 'Lynch', 'Agf',
    'Graham_dif', 'GrahamBR_dif', 'Bazin_dif', 'Lynch_dif', 'Agf_dif'
]

# ---------------------------------------------------------------------------
# CLIENTE MFINANCE
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
# FUNÇÕES AUXILIARES GERAIS
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

# ---------------------------------------------------------------------------
# ETAPA 0: SELIC
# ---------------------------------------------------------------------------
def etapa_0_selic():
    """Coleta histórico SELIC do BCB com retry e salva em JSON."""
    logger.info("🟦 ETAPA 0: Coletando SELIC...")
    
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
# ETAPA 1: STOCKS (MFinance)
# ---------------------------------------------------------------------------
def etapa_1_stocks(mf_client):
    """Busca lista de ativos da API MFinance e retorna DataFrame."""
    logger.info("🟦 ETAPA 1: Buscando lista de ativos (MFinance)...")
    stocks = mf_client.get_stocks()
    if not stocks:
        logger.error("✗ Falha ao obter lista de ativos.")
        return None
    df = pd.DataFrame(stocks)
    logger.info(f"✓ {len(df)} ativos carregados da lista.")
    return df

# ---------------------------------------------------------------------------
# ETAPA 2: INDICATORS (MFinance)
# ---------------------------------------------------------------------------
def etapa_2_indicators(mf_client, df_stocks):
    """Busca indicadores fundamentais e merge com lista de ativos."""
    logger.info("🟨 ETAPA 2: Buscando indicadores fundamentais (MFinance)...")
    indicators = mf_client.get_indicators()
    if not indicators:
        logger.error("✗ Falha ao obter indicadores.")
        return df_stocks
    
    df_ind = pd.DataFrame(indicators)
    # Merge por symbol/Ticker
    if 'symbol' in df_stocks.columns and 'symbol' in df_ind.columns:
        df_merged = pd.merge(df_stocks, df_ind, on='symbol', how='left', suffixes=('_stocks', '_ind'))
    else:
        df_merged = df_stocks.copy()
        for col in df_ind.columns:
            if col not in df_merged.columns:
                df_merged[col] = df_ind[col]
    
    logger.info(f"✓ Indicadores mesclados. Total colunas: {len(df_merged.columns)}")
    return df_merged

# ---------------------------------------------------------------------------
# ETAPA 3: FILTRO DE LIMPEZA
# ---------------------------------------------------------------------------
def etapa_3_filtro_limpeza(df):
    """Remove linhas com nome em branco ou nulo."""
    logger.info("🟨 ETAPA 3: Filtrando ativos com nome válido...")
    antes = len(df)
    
    # Filtra por coluna 'name' ou 'Nome' (depende do mapeamento)
    col_nome = 'name' if 'name' in df.columns else 'Nome'
    df_limpo = df[df[col_nome].notna() & (df[col_nome].astype(str).str.strip() != '')].copy()
    
    depois = len(df_limpo)
    logger.info(f"✓ Removidos {antes - depois} ativos sem nome. Restam {depois} ativos válidos.")
    return df_limpo

# ---------------------------------------------------------------------------
# ETAPA 4: DIVIDENDOS (MFinance)
# ---------------------------------------------------------------------------
def calc_divs(div_data, current_year=None):
    """Calcula dividendos por ano civil e consistência."""
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

def etapa_4_dividendos(mf_client, df):
    """Coleta dividendos para cada ativo e calcula métricas anuais."""
    logger.info("🟥 ETAPA 4: Coletando dividendos (lista filtrada)...")
    falhas = 0
    current_year = datetime.now().year
    
    tickers = df['symbol'].dropna().unique().tolist() if 'symbol' in df.columns else df['Ticker'].dropna().unique().tolist()
    
    for i, ticker in enumerate(tickers):
        if i % 50 == 0 and i > 0:
            logger.info(f"Dividendos: processados {i}/{len(tickers)} | Falhas: {falhas}")
        
        div_data = mf_client.get_dividends(ticker)
        d_calc = calc_divs(div_data, current_year) if div_data else None
        
        if not d_calc:
            falhas += 1
            with open(FALHAS_LOG, 'a') as f:
                f.write(f"{datetime.now().isoformat()}|{ticker}|Falha API\n")
            d_calc = {f'DIV_{x}A_': 0.0 for x in range(6)} | {'DY_5A_PG': 0}
        
        # Atualiza DataFrame
        mask = df['symbol'] == ticker if 'symbol' in df.columns else df['Ticker'] == ticker
        for k, v in d_calc.items():
            df.loc[mask, k] = v
    
    logger.info(f"✓ Dividendos coletados. Falhas: {falhas}/{len(tickers)}")
    return df

# ---------------------------------------------------------------------------
# ETAPA 5: MATEMÁTICA REVERSA
# ---------------------------------------------------------------------------
def etapa_5_matematica_reversa(df):
    """Calcula indicadores ausentes via fórmulas reversas."""
    logger.info("🟪 ETAPA 5: Calculando matemática reversa...")
    
    # Garantir colunas numéricas
    for col in ['LPA', 'Qtd_Acoes', 'Valor_Mercado', 'P_EBIT', 'P_EBITDA', 
                'Margem_Liquida', 'Margem_EBITDA', 'P_L', 'P_Receita']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 1. Lucro Líquido
    df['Lucro_Liquido'] = df['LPA'] * df['Qtd_Acoes']
    mask = df['Lucro_Liquido'].isna() | (df['Lucro_Liquido'] == 0)
    df.loc[mask, 'Lucro_Liquido'] = safe_div(df['Valor_Mercado'], df['P_L'])
    
    # 2. EBIT
    df['EBIT'] = safe_div(df['Valor_Mercado'], df['P_EBIT'])
    
    # 3. Receita Líquida (fallback em cascata)
    df['Receita_Liquida'] = safe_div(df['Valor_Mercado'], df['P_Receita'])
    mask_rec = df['Receita_Liquida'].isna() | (df['Receita_Liquida'] == 0)
    df.loc[mask_rec, 'Receita_Liquida'] = safe_div(df['Lucro_Liquido'], df['Margem_Liquida'] / 100)
    ebitda_est = safe_div(df['Valor_Mercado'], df['P_EBITDA'])
    df.loc[mask_rec & df['Receita_Liquida'].isna(), 'Receita_Liquida'] = safe_div(ebitda_est, df['Margem_EBITDA'] / 100)
    
    # 4. P/Receita (recalcular para consistência)
    df['P_Receita'] = safe_div(df['Valor_Mercado'], df['Receita_Liquida'])
    
    # Limpar infinitos/nulos
    for col in ['Lucro_Liquido', 'EBIT', 'Receita_Liquida', 'P_Receita']:
        if col in df.columns:
            df[col] = df[col].replace([np.inf, -np.inf], 0).fillna(0)
    
    logger.info("✓ Matemática reversa concluída.")
    return df

# ---------------------------------------------------------------------------
# ETAPA 6: CÁLCULO DE SCORE E EXPORTAÇÃO
# ---------------------------------------------------------------------------
def update_score(row):
    """Calcula Score_CS com 11 critérios."""
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

def calcular_valuation(df):
    """Calcula as 10 colunas de valuation."""
    logger.info("🟪 ETAPA 6b: Calculando valuation (Graham, Bazin, Lynch, AGF)...")
    
    cols_numericas = ['Preco_Atual', 'LPA', 'VPA', 'DY_Atual', 'CAGR_Lucros_5a']
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Graham clássico
    df['Graham'] = np.sqrt(22.5 * df['LPA'] * df['VPA'])
    # Graham BR conservador
    df['GrahamBR'] = np.sqrt(15 * df['LPA'] * df['VPA'])
    # Bazin
    df['Bazin'] = df['Preco_Atual'] * df['DY_Atual'] / 6.0
    # Lynch
    df['Lynch'] = df['LPA'] * (1 + df['CAGR_Lucros_5a'] / 100.0)
    # AGF (média ponderada)
    df['Agf'] = (df['Graham'] + df['GrahamBR'] + df['Bazin'] + df['Lynch'] + (df['Preco_Atual'] * 0.8)) / 5.0
    
    # Diferenças percentuais
    for metodo in ['Graham', 'GrahamBR', 'Bazin', 'Lynch', 'Agf']:
        df[f'{metodo}_dif'] = (safe_div(df[metodo], df['Preco_Atual']) - 1) * 100
    
    # Arredondar
    for col in ['Graham', 'GrahamBR', 'Bazin', 'Lynch', 'Agf'] + [f'{m}_dif' for m in ['Graham', 'GrahamBR', 'Bazin', 'Lynch', 'Agf']]:
        if col in df.columns:
            df[col] = df[col].round(2)
    
    logger.info("✓ Valuation calculado.")
    return df

def etapa_6_exportacao(df):
    """Calcula Score_CS, aplica mapeamento e salva arquivos finais."""
    logger.info("🟪 ETAPA 6: Calculando Score_CS e exportando...")
    
    # Calcular Score_CS
    df['Score_CS'] = df.apply(update_score, axis=1)
    df['Classificacao_CS'] = df['Score_CS'].apply(get_class)
    
    # Renomear colunas
    df.rename(columns=COLUNAS_MAPEAMENTO, inplace=True)
    
    # Ordenar colunas
    existentes = [c for c in ORDEM_FINAL if c in df.columns]
    extras = [c for c in df.columns if c not in existentes]
    df = df[existentes + extras]
    
    # Converter numérico
    numeric_targets = ['Div_0A', 'Div_1A', 'Div_2A', 'Div_3A', 'Div_4A', 'Div_5A', 
                       'Consistencia_5A', 'Anos_Listagem', 'Lucro_Liquido', 'EBIT', 
                       'Receita_Liquida', 'P_Receita', 'Graham', 'GrahamBR', 'Bazin', 
                       'Lynch', 'Agf', 'Graham_dif', 'GrahamBR_dif', 'Bazin_dif', 
                       'Lynch_dif', 'Agf_dif']
    for col in numeric_targets:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Salvar
    try:
        with pd.ExcelWriter(ATIVOS_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='DADOS!', index=False)
        df.to_csv(ATIVOS_CSV, index=False, encoding='utf-8-sig')
        logger.info(f"✓ Arquivos salvos: {len(df)} ativos, {len(df.columns)} colunas")
    except Exception as e:
        logger.error(f"✗ Erro ao salvar: {e}")
    
    return df

# ---------------------------------------------------------------------------
# ETAPA 7: LISTAGEM YF (COM CACHE RESILIENTE)
# ---------------------------------------------------------------------------
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
        logger.info("✓ Cache de listagem salvo")
    except Exception as e:
        logger.error(f"Erro ao salvar cache: {e}")

def get_listing_date_yf(ticker, cache):
    """
    Busca data de listagem via yfinance.
    REGRA DE OURO: Se já tem no cache e falhar, NÃO faz nada, segue a vida.
    """
    # 1. Tenta ler do cache primeiro
    if ticker in cache:
        cached_val = cache[ticker]
        if cached_val == "N/A":
            return 0.0
        try:
            first_date = datetime.strptime(cached_val, "%Y-%m-%d").date()
            anos = (datetime.now().date() - first_date).days / 365.25
            return round(anos, 2)
        except Exception as e:
            logger.warning(f"Erro ao converter data do cache para {ticker}: {e}")
            # Se falhar na conversão do cache, retorna 0 mas NÃO tenta yfinance
            return 0.0
    
    # 2. Se não tem no cache, tenta yfinance
    try:
        logger.debug(f"yfinance: buscando listagem para {ticker}...")
        yf_ticker = yf.Ticker(f"{ticker}.SA")
        hist = yf_ticker.history(period="max")
        
        if not hist.empty:
            first_date = hist.index[0].date()
            cache[ticker] = first_date.strftime("%Y-%m-%d")
            anos = (datetime.now().date() - first_date).days / 365.25
            time.sleep(0.5)  # Rate limit
            return round(anos, 2)
        else:
            cache[ticker] = "N/A"
    except Exception as e:
        # ⚠️ REGRA CRÍTICA: Se der erro no yfinance, NÃO quebra, apenas loga e segue
        logger.warning(f"yfinance falhou para {ticker} (seguindo com cache): {e}")
        # Não atualiza cache com erro, mantém como estava
    
    return 0.0

def etapa_7_listagem_yf(df):
    """Calcula Anos_Listagem via yfinance com cache resiliente."""
    logger.info("🟩 ETAPA 7: Calculando Anos_Listagem (yfinance + cache)...")
    
    cache = carregar_cache_listagem()
    cache_modificado = False
    
    # Coluna para Ticker (pode ser 'symbol' ou 'Ticker' após mapeamento)
    col_ticker = 'Ticker' if 'Ticker' in df.columns else 'symbol'
    
    for i, ticker in enumerate(df[col_ticker].dropna().unique()):
        if i % 50 == 0 and i >  0:
            logger.info(f"Listagem: processados {i} tickers...")
        
        anos = get_listing_date_yf(ticker, cache)
        mask = df[col_ticker] == ticker
        df.loc[mask, 'Anos_Listagem'] = anos
        
        if ticker not in cache or cache[ticker] != ("N/A" if anos == 0.0 else None):
            cache_modificado = True
        
        # Salvar cache periodicamente
        if cache_modificado and i > 0 and i % 20 == 0:
            salvar_cache_listagem(cache)
    
    # Salvar cache final se houve mudanças
    if cache_modificado:
        salvar_cache_listagem(cache)
    
    logger.info("✓ Anos_Listagem calculado (cache preservado em caso de erro).")
    return df

# ---------------------------------------------------------------------------
# MAIN - ORQUESTRAÇÃO DO PIPELINE
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 70)
    logger.info("🚀 INICIANDO PIPELINE SOBRAL INVEST")
    logger.info("=" * 70)
    
    # Inicializar cliente
    mf = MFinanceClient()
    
    # ETAPA 0: SELIC
    selic_novos = etapa_0_selic()
    salvar_selic_json(selic_novos)
    
    # ETAPA 1: STOCKS
    df = etapa_1_stocks(mf)
    if df is None:
        logger.error("✗ Pipeline interrompido: falha na etapa 1.")
        return
    
    # ETAPA 2: INDICATORS
    df = etapa_2_indicators(mf, df)
    
    # ETAPA 3: FILTRO DE LIMPEZA
    df = etapa_3_filtro_limpeza(df)
    
    # ETAPA 4: DIVIDENDOS (com lista menor)
    df = etapa_4_dividendos(mf, df)
    
    # ETAPA 5: MATEMÁTICA REVERSA
    df = etapa_5_matematica_reversa(df)
    
    # ETAPA 6: SCORE + EXPORTAÇÃO
    df = etapa_6_exportacao(df)
    
    # ETAPA 7: LISTAGEM YF (última, com cache resiliente)
    df = etapa_7_listagem_yf(df)
    
    # Re-exportar com Anos_Listagem atualizado
    try:
        with pd.ExcelWriter(ATIVOS_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='DADOS!', index=False)
        df.to_csv(ATIVOS_CSV, index=False, encoding='utf-8-sig')
        logger.info("✓ Arquivos finais atualizados com Anos_Listagem")
    except Exception as e:
        logger.error(f"✗ Erro na exportação final: {e}")
    
    logger.info("✅ PIPELINE CONCLUÍDO COM SUCESSO!")

if __name__ == "__main__":
    main()
