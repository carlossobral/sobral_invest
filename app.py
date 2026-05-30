"""
Sobral Invest - Coletor de Dados de Ativos B3 (Pipeline Modular)
Correções: Extração correta de valores da API + AGF Barsi + Merge sem duplicatas
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
# CONFIGURAÇÕES GERAIS
# ---------------------------------------------------------------------------
USE_YFINANCE = os.getenv("USE_YFINANCE", "false").lower() in ("true", "1", "yes")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/coleta.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
# FUNÇÕES AUXILIARES - LIMPEZA CRÍTICA DA API
# ---------------------------------------------------------------------------
def extrair_valor_api(item):
    """
    A API MFinance retorna: {'name': 'P/VP', 'value': 2.85, 'description': '...'}
    Esta função extrai APENAS o número do campo 'value'.
    """
    if item is None:
        return None
    if isinstance(item, dict):
        val = item.get('value')
        if val is not None:
            try:
                return float(val)
            except:
                return None
    try:
        return float(item)
    except:
        return None

def limpar_dataframe_api(df_raw, colunas_texto=None):
    """
    Converte todas as colunas numéricas de um DataFrame vindo da API,
    extraindo o 'value' de dicionários aninhados.
    """
    if colunas_texto is None:
        colunas_texto = ['symbol', 'name', 'sector', 'subSector', 'segment', 'type']
    
    df = df_raw.copy()
    for col in df.columns:
        if col in colunas_texto:
            continue
        df[col] = df[col].apply(extrair_valor_api)
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def safe_div(a, b):
    """Divisão segura vetorizada."""
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.where(b != 0, a / b, 0)
        return np.where(np.isfinite(result), result, 0)

def ensure_column(df, col_name, default=0.0):
    """Garante que uma coluna exista no DataFrame."""
    if col_name not in df.columns:
        df[col_name] = default
    return df

# ---------------------------------------------------------------------------
# ETAPA 0: SELIC
# ---------------------------------------------------------------------------
def etapa_0_selic():
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
# ETAPA 1: STOCKS (MFinance) - COM LIMPEZA
# ---------------------------------------------------------------------------
def etapa_1_stocks(mf_client):
    logger.info("🟦 ETAPA 1: Buscando lista de ativos (MFinance)...")
    stocks = mf_client.get_stocks()
    if not stocks:
        logger.error("✗ Falha ao obter lista de ativos.")
        return None
    
    df = pd.DataFrame(stocks)
    
    # Limpar colunas numéricas da lista de stocks
    cols_numericas_stocks = ['lastPrice', 'marketCap', 'volume', 'shares', 'dividendYield']
    for col in cols_numericas_stocks:
        if col in df.columns:
            df[col] = df[col].apply(extrair_valor_api)
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    logger.info(f"✓ {len(df)} ativos carregados e limpos.")
    return df

# ---------------------------------------------------------------------------
# ETAPA 2: INDICATORS (MFinance) - CORREÇÃO CRÍTICA
# ---------------------------------------------------------------------------
def etapa_2_indicators(mf_client, df_stocks):
    """
    CORREÇÃO: Extrai apenas o campo 'value' dos dicionários da API,
    converte para numérico e faz merge SEM criar colunas duplicadas.
    """
    logger.info("🟨 ETAPA 2: Buscando e limpando indicadores fundamentais...")
    
    indicators = mf_client.get_indicators()
    if not indicators:
        logger.error("✗ Falha ao obter indicadores.")
        return df_stocks
    
    # 1️⃣ Criar DataFrame e LIMPAR dados aninhados da API
    df_ind = pd.DataFrame(indicators)
    df_ind = limpar_dataframe_api(df_ind)
    
    # 2️⃣ Merge SEGURO: usar symbol como índice para evitar sufixos (_stocks/_ind)
    df_stocks = df_stocks.set_index('symbol')
    df_ind = df_ind.set_index('symbol')
    
    # combine_first preenche df_stocks com dados de df_ind, sem duplicar colunas
    df_merged = df_stocks.combine_first(df_ind)
    df_merged = df_merged.reset_index()
    
    logger.info(f"✓ Indicadores mesclados. Total colunas: {len(df_merged.columns)}")
    return df_merged

# ---------------------------------------------------------------------------
# ETAPA 3: FILTRO DE LIMPEZA
# ---------------------------------------------------------------------------
def etapa_3_filtro_limpeza(df):
    logger.info("🟨 ETAPA 3: Filtrando ativos válidos...")
    antes = len(df)
    
    col_nome = 'name' if 'name' in df.columns else 'Nome'
    col_preco = 'lastPrice' if 'lastPrice' in df.columns else 'Preco_Atual'
    col_roe = 'returnOnEquity' if 'returnOnEquity' in df.columns else 'ROE'
    
    mask_nome = df[col_nome].notna() & (df[col_nome].astype(str).str.strip() != '')
    mask_preco = pd.to_numeric(df[col_preco], errors='coerce') > 0
    mask_fund = pd.to_numeric(df[col_roe], errors='coerce').notna()
    
    df_filtrado = df[mask_nome & mask_preco & mask_fund].copy()
    depois = len(df_filtrado)
    
    logger.info(f"✓ Removidos {antes - depois} ativos inválidos. Restam {depois}.")
    return df_filtrado

# ---------------------------------------------------------------------------
# ETAPA 4: DIVIDENDOS (MFinance)
# ---------------------------------------------------------------------------
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

def etapa_4_dividendos(mf_client, df):
    logger.info("🟥 ETAPA 4: Coletando dividendos...")
    falhas = 0
    current_year = datetime.now().year
    
    tickers = df['symbol'].dropna().unique().tolist() if 'symbol' in df.columns else df['Ticker'].dropna().unique().tolist()
    
    for i, ticker in enumerate(tickers):
        if i % 50 == 0 and i > 0:
            logger.info(f"Dividendos: {i}/{len(tickers)} | Falhas: {falhas}")
        
        div_data = mf_client.get_dividends(ticker)
        d_calc = calc_divs(div_data, current_year) if div_data else None
        
        if not d_calc:
            falhas += 1
            with open(FALHAS_LOG, 'a') as f:
                f.write(f"{datetime.now().isoformat()}|{ticker}|Falha API\n")
            d_calc = {f'DIV_{x}A_': 0.0 for x in range(6)} | {'DY_5A_PG': 0}
        
        mask = df['symbol'] == ticker if 'symbol' in df.columns else df['Ticker'] == ticker
        for k, v in d_calc.items():
            df.loc[mask, k] = v
    
    logger.info(f"✓ Dividendos coletados. Falhas: {falhas}/{len(tickers)}")
    return df

# ---------------------------------------------------------------------------
# ETAPA 5: MATEMÁTICA REVERSA
# ---------------------------------------------------------------------------
def etapa_5_matematica_reversa(df):
    logger.info("🟪 ETAPA 5: Calculando matemática reversa...")
    
    cols_essenciais = {
        'LPA': 0.0, 'Qtd_Acoes': 0.0, 'Valor_Mercado': 0.0,
        'P_EBIT': 0.0, 'P_EBITDA': 0.0, 'Margem_Liquida': 0.0,
        'Margem_EBITDA': 0.0, 'P_L': 0.0, 'P_Receita': 0.0
    }
    for col, default in cols_essenciais.items():
        df = ensure_column(df, col, default)
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Lucro Líquido
    df['Lucro_Liquido'] = df['LPA'] * df['Qtd_Acoes']
    mask_lucro = (df['Lucro_Liquido'] <= 0) | (df['Lucro_Liquido'].isna())
    df.loc[mask_lucro, 'Lucro_Liquido'] = safe_div(df.loc[mask_lucro, 'Valor_Mercado'], df.loc[mask_lucro, 'P_L'])
    
    # EBIT
    df['EBIT'] = safe_div(df['Valor_Mercado'], df['P_EBIT'])
    
    # Receita Líquida
    df['Receita_Liquida'] = safe_div(df['Valor_Mercado'], df['P_Receita'])
    mask_rec = (df['Receita_Liquida'] <= 0) | (df['Receita_Liquida'].isna())
    df.loc[mask_rec, 'Receita_Liquida'] = safe_div(df.loc[mask_rec, 'Lucro_Liquido'], df.loc[mask_rec, 'Margem_Liquida'] / 100)
    
    mask_rec2 = mask_rec & (df['Receita_Liquida'] <= 0)
    if mask_rec2.any():
        ebitda_est = safe_div(df.loc[mask_rec2, 'Valor_Mercado'], df.loc[mask_rec2, 'P_EBITDA'])
        df.loc[mask_rec2, 'Receita_Liquida'] = safe_div(ebitda_est, df.loc[mask_rec2, 'Margem_EBITDA'] / 100)
    
    # P/Receita
    df['P_Receita'] = safe_div(df['Valor_Mercado'], df['Receita_Liquida'])
    
    # Limpar
    for col in ['Lucro_Liquido', 'EBIT', 'Receita_Liquida', 'P_Receita']:
        df[col] = df[col].replace([np.inf, -np.inf], 0).fillna(0)
    
    logger.info("✓ Matemática reversa concluída.")
    return df

# ---------------------------------------------------------------------------
# ETAPA 6: SCORE + VALUATION + EXPORTAÇÃO
# ---------------------------------------------------------------------------
def update_score(row):
    s = 0
    v = lambda k, d=None: extrair_valor_api(row.get(k)) or d
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
    """
    Calcula valuation com fórmulas corretas.
    AGF = Método Ações Garantem o Futuro (Luiz Barsi):
          Preço Teto = Média dos últimos 6 dividendos ÷ 0.06
    """
    logger.info("🟪 ETAPA 6b: Calculando valuation...")
    
    cols_val = ['Preco_Atual', 'LPA', 'VPA', 'DY_Atual', 'CAGR_Lucros_5a',
                'Div_0A', 'Div_1A', 'Div_2A', 'Div_3A', 'Div_4A', 'Div_5A']
    for col in cols_val:
        df = ensure_column(df, col, 0.0)
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Graham clássico: √(22.5 × LPA × VPA)
    df['Graham'] = np.sqrt(22.5 * df['LPA'] * df['VPA'])
    
    # Graham BR conservador: √(15 × LPA × VPA)
    df['GrahamBR'] = np.sqrt(15 * df['LPA'] * df['VPA'])
    
    # Bazin: Preço × DY / 6 (yield alvo 6%)
    df['Bazin'] = df['Preco_Atual'] * df['DY_Atual'] / 6.0
    
    # Lynch: LPA × (1 + CAGR_Lucros_5a/100)
    df['Lynch'] = df['LPA'] * (1 + df['CAGR_Lucros_5a'] / 100.0)
    
    # ✅ AGF CORRETO - Método Ações Garantem o Futuro (Luiz Barsi)
    # Preço Teto = Média dos últimos 6 dividendos ÷ 0.06 (yield alvo 6%)
    cols_div = ['Div_0A', 'Div_1A', 'Div_2A', 'Div_3A', 'Div_4A', 'Div_5A']
    df['Media_Div_6A'] = df[cols_div].mean(axis=1)
    df['Agf'] = df['Media_Div_6A'] / 0.06  # Yield alvo de 6%
    
    # Diferenças percentuais (Upside/Downside)
    for metodo in ['Graham', 'GrahamBR', 'Bazin', 'Lynch', 'Agf']:
        df[f'{metodo}_dif'] = (safe_div(df[metodo], df['Preco_Atual']) - 1) * 100
    
    # Arredondar e limpar
    for col in ['Graham', 'GrahamBR', 'Bazin', 'Lynch', 'Agf', 
                'Graham_dif', 'GrahamBR_dif', 'Bazin_dif', 'Lynch_dif', 'Agf_dif']:
        if col in df.columns:
            df[col] = df[col].round(2).replace([np.inf, -np.inf], 0).fillna(0)
    
    # Remover coluna auxiliar
    if 'Media_Div_6A' in df.columns:
        df.drop(columns=['Media_Div_6A'], inplace=True)
    
    logger.info("✓ Valuation calculado com fórmulas corretas.")
    return df

def etapa_6_exportacao(df):
    logger.info("🟪 ETAPA 6: Calculando Score_CS e exportando...")
    
    df['Score_CS'] = df.apply(update_score, axis=1)
    df['Classificacao_CS'] = df['Score_CS'].apply(get_class)
    
    df.rename(columns=COLUNAS_MAPEAMENTO, inplace=True)
    
    existentes = [c for c in ORDEM_FINAL if c in df.columns]
    extras = [c for c in df.columns if c not in existentes]
    df = df[existentes + extras]
    
    numeric_targets = ['Div_0A', 'Div_1A', 'Div_2A', 'Div_3A', 'Div_4A', 'Div_5A', 
                       'Consistencia_5A', 'Anos_Listagem', 'Lucro_Liquido', 'EBIT', 
                       'Receita_Liquida', 'P_Receita', 'Graham', 'GrahamBR', 'Bazin', 
                       'Lynch', 'Agf', 'Graham_dif', 'GrahamBR_dif', 'Bazin_dif', 
                       'Lynch_dif', 'Agf_dif']
    for col in numeric_targets:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    try:
        ATIVOS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(ATIVOS_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='DADOS!', index=False)
        df.to_csv(ATIVOS_CSV, index=False, encoding='utf-8-sig')
        logger.info(f"✓ Arquivos salvos: {len(df)} ativos, {len(df.columns)} colunas")
        return df
    except Exception as e:
        import traceback
        logger.error(f"✗ Erro ao salvar: {e}")
        logger.error(traceback.format_exc())
        try:
            df.to_csv(ATIVOS_CSV, index=False, encoding='utf-8-sig')
            logger.info("✓ CSV salvo como fallback")
            return df
        except:
            logger.error("✗ Falha total ao salvar")
            return df

# ---------------------------------------------------------------------------
# ETAPA 7: LISTAGEM YF (COM FLAG)
# ---------------------------------------------------------------------------
def carregar_cache_listagem():
    if CACHE_LISTAGEM_FILE.exists():
        try:
            with open(CACHE_LISTAGEM_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def salvar_cache_listagem(cache):
    try:
        CACHE_LISTAGEM_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_LISTAGEM_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except: pass

def get_listing_date_yf(ticker, cache):
    if ticker in cache:
        cached_val = cache[ticker]
        if cached_val == "N/A": return 0.0
        try:
            first_date = datetime.strptime(cached_val, "%Y-%m-%d").date()
            anos = (datetime.now().date() - first_date).days / 365.25
            return round(anos, 2)
        except: return 0.0
    
    if not USE_YFINANCE:
        return 0.0
    
    try:
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
        logger.warning(f"yfinance falhou para {ticker}: {e}")
    return 0.0

def etapa_7_listagem_yf(df):
    logger.info("🟩 ETAPA 7: Calculando Anos_Listagem...")
    
    if not USE_YFINANCE:
        logger.info("⏭️ yfinance desativado: pulando")
        return df
    
    cache = carregar_cache_listagem()
    cache_modificado = False
    col_ticker = 'Ticker' if 'Ticker' in df.columns else 'symbol'
    
    for i, ticker in enumerate(df[col_ticker].dropna().unique()):
        if i % 50 == 0 and i > 0:
            logger.info(f"Listagem: {i} tickers...")
        
        anos = get_listing_date_yf(ticker, cache)
        mask = df[col_ticker] == ticker
        df.loc[mask, 'Anos_Listagem'] = anos
        
        if ticker not in cache:
            cache_modificado = True
        if cache_modificado and i > 0 and i % 20 == 0:
            salvar_cache_listagem(cache)
    
    if cache_modificado:
        salvar_cache_listagem(cache)
    
    logger.info("✓ Anos_Listagem calculado.")
    return df

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 70)
    logger.info("🚀 INICIANDO PIPELINE SOBRAL INVEST")
    logger.info(f"🎛️ USE_YFINANCE = {USE_YFINANCE}")
    logger.info(f"📁 Diretório: {SCRIPT_DIR}")
    logger.info("=" * 70)
    
    mf = MFinanceClient()
    
    # ETAPA 0
    selic_novos = etapa_0_selic()
    salvar_selic_json(selic_novos)
    
    # ETAPA 1
    df = etapa_1_stocks(mf)
    if df is None:
        logger.error("✗ Pipeline interrompido: etapa 1.")
        return
    
    # ETAPA 2 (CORRIGIDA)
    df = etapa_2_indicators(mf, df)
    
    # ETAPA 3
    df = etapa_3_filtro_limpeza(df)
    
    # ETAPA 4
    df = etapa_4_dividendos(mf, df)
    
    # ETAPA 5
    df = etapa_5_matematica_reversa(df)
    
    # ETAPA 6
    df = calcular_valuation(df)
    df = etapa_6_exportacao(df)
    
    # ETAPA 7
    df = etapa_7_listagem_yf(df)
    
    # Exportação final
    try:
        with pd.ExcelWriter(ATIVOS_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='DADOS!', index=False)
        df.to_csv(ATIVOS_CSV, index=False, encoding='utf-8-sig')
        logger.info("✓ Arquivos finais atualizados")
    except Exception as e:
        logger.error(f"✗ Erro na exportação final: {e}")
    
    logger.info("✅ PIPELINE CONCLUÍDO!")

if __name__ == "__main__":
    main()
