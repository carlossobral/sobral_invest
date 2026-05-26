"""
Sobral Invest - Coletor de Dados de Ativos B3
Atualiza ativos.xlsx com dados de multiplas fontes + Fundamentus (Kanitz)
"""

import os
import sys
import json
import time
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# pyfundamentus para dados do balanco
from fundamentus import Pipeline

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIGURACOES
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

ATIVOS_FILE = OUTPUT_DIR / "ativos.xlsx"
ATIVOS_CSV = OUTPUT_DIR / "ativos.csv"

# MFinance API
MF_BASE = "https://mfinance.com.br/api/v1"

# BRAPI (fallback cotacao)
BRAPI_BASE = "https://brapi.dev/api/quote"

# SELIC
SELIC_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=01/01/2016&dataFinal=31/12/2026"

# ---------------------------------------------------------------------------
# CLIENTE MFINANCE (3 endpoints)
# ---------------------------------------------------------------------------
class MFinanceClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })

    def _get(self, url, retries=3, delay=2):
        for attempt in range(retries):
            try:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning(f"Tentativa {attempt+1}/{retries} falhou para {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                else:
                    raise

    def get_stocks(self):
        """GET /stocks -> todos os ativos com cotacao, setor, etc."""
        logger.info("Buscando /stocks...")
        data = self._get(f"{MF_BASE}/stocks")
        stocks = data if isinstance(data, list) else data.get("stocks", [])
        logger.info(f"  -> {len(stocks)} ativos de /stocks")
        return stocks

    def get_indicators(self):
        """GET /stocks/indicators -> todos os indicadores fundamentais"""
        logger.info("Buscando /stocks/indicators...")
        data = self._get(f"{MF_BASE}/stocks/indicators")
        indicators = data if isinstance(data, list) else data.get("indicators", [])
        logger.info(f"  -> {len(indicators)} indicadores")
        return indicators

    def get_dividends(self, symbol):
        """GET /stocks/dividends/{symbol} -> dividendos de 1 ticker"""
        url = f"{MF_BASE}/stocks/dividends/{symbol}"
        try:
            data = self._get(url, retries=2, delay=1)
            return data
        except Exception as e:
            logger.debug(f"Erro dividendos {symbol}: {e}")
            return None

    def get_all_dividends(self, symbols, delay=0.3):
        """Busca dividendos para lista de tickers (1 por 1)"""
        logger.info(f"Buscando dividendos para {len(symbols)} tickers...")
        results = {}
        for i, sym in enumerate(symbols):
            if i % 50 == 0 and i > 0:
                logger.info(f"  -> {i}/{len(symbols)} dividendos...")
            data = self.get_dividends(sym)
            if data:
                results[sym] = data
            time.sleep(delay)
        logger.info(f"  -> {len(results)} tickers com dividendos")
        return results


# ---------------------------------------------------------------------------
# FUNDOFUNDAMENTUS - DADOS DO BALANCO PARA KANITZ
# ---------------------------------------------------------------------------

def get_fundamentus_balance(ticker):
    """
    Busca dados do balanco patrimonial via pyfundamentus.
    Retorna dict com: Ativo_Circulante, Realizavel_LP, Passivo_Circulante,
                      Exigivel_LP, Estoques, Patrimonio_Liquido, Lucro_Liquido
    """
    try:
        pipeline = Pipeline(ticker)
        response = pipeline.get_all_information()
        bs = response.transformed_information['balance_sheet']

        # Mapear nomes do Fundamentus para nossas colunas
        mapping = {
            'Ativo Circulante': 'Ativo_Circulante',
            'Realizavel Longo Prazo': 'Realizavel_LP',
            'Passivo Circulante': 'Passivo_Circulante',
            'Exigivel Longo Prazo': 'Exigivel_LP',
            'Estoques': 'Estoques',
            'Patrimonio Liquido': 'Patrimonio_Liquido',
            'Lucro Liquido': 'Lucro_Liquido_Kanitz',
        }

        result = {}
        for fund_key, our_key in mapping.items():
            val = bs.get(fund_key, 0)
            # Converter de string formatada para float
            if isinstance(val, str):
                val = val.replace('.', '').replace(',', '.').replace('R$', '').strip()
                try:
                    val = float(val)
                except:
                    val = 0
            result[our_key] = float(val) if val else 0

        return result
    except Exception as e:
        logger.debug(f"Fundamentus falhou para {ticker}: {e}")
        return {}


def get_all_fundamentus_data(tickers, delay=1.0):
    """Busca dados do balanco para todos os tickers"""
    logger.info(f"Buscando dados do Fundamentus para {len(tickers)} tickers...")
    results = {}
    for i, ticker in enumerate(tickers):
        if i % 50 == 0 and i > 0:
            logger.info(f"  -> {i}/{len(tickers)} fundamentus...")
        data = get_fundamentus_balance(ticker)
        if data:
            results[ticker] = data
        time.sleep(delay)
    logger.info(f"  -> {len(results)} tickers com dados do Fundamentus")
    return results


# ---------------------------------------------------------------------------
# CALCULO DO TERMOmetro DE KANITZ
# ---------------------------------------------------------------------------

def calcular_kanitz(row):
    """
    Termometro de Kanitz - Fator de Insolvencia

    X1 = ROE * 0.05
    X2 = Liquidez Geral * 1.65
    X3 = Liquidez Seca * 3.55
    X4 = Liquidez Corrente * 1.06
    X5 = Alavancagem do PL * 0.33

    Fator = X1 + X2 + X3 - X4 - X5

    Escala:
    -7 a -3: Vermelho (Risco de falencia)
    -3 a 0: Amarelo (Penumbra)
    0 a 7: Verde (Solvencia)
    """
    # Dados do balanco (do Fundamentus)
    ativo_circ = row.get('Ativo_Circulante', 0)
    realizavel_lp = row.get('Realizavel_LP', 0)
    passivo_circ = row.get('Passivo_Circulante', 0)
    exigivel_lp = row.get('Exigivel_LP', 0)
    estoques = row.get('Estoques', 0)
    patrimonio = row.get('Patrimonio_Liquido', 0)
    lucro_liq = row.get('Lucro_Liquido_Kanitz', 0)

    # Se nao tem dados do Fundamentus, retorna vazio
    if patrimonio == 0 or passivo_circ == 0:
        return {
            'Kanitz_X1': 0, 'Kanitz_X2': 0, 'Kanitz_X3': 0,
            'Kanitz_X4': 0, 'Kanitz_X5': 0,
            'Kanitz_Fator': None, 'Kanitz_Status': 'Sem Dados'
        }

    # X1 - ROE * 0.05 (usamos ROE do MFinance se disponivel, senao calculamos)
    roe = row.get('ROE', 0)
    if roe == 0 and patrimonio > 0:
        roe = (lucro_liq / patrimonio) * 100
    x1 = roe * 0.05

    # X2 - Liquidez Geral * 1.65
    # Liquidez Geral = (Ativo Circulante + Realizavel LP) / (Passivo Circulante + Exigivel LP)
    liquidez_geral = (ativo_circ + realizavel_lp) / (passivo_circ + exigivel_lp) if (passivo_circ + exigivel_lp) > 0 else 0
    x2 = liquidez_geral * 1.65

    # X3 - Liquidez Seca * 3.55
    # Liquidez Seca = (Ativo Circulante - Estoques) / Passivo Circulante
    liquidez_seca = (ativo_circ - estoques) / passivo_circ if passivo_circ > 0 else 0
    x3 = liquidez_seca * 3.55

    # X4 - Liquidez Corrente * 1.06
    # Liquidez Corrente = Ativo Circulante / Passivo Circulante
    liquidez_corrente = ativo_circ / passivo_circ if passivo_circ > 0 else 0
    x4 = liquidez_corrente * 1.06

    # X5 - Alavancagem do PL * 0.33
    # Alavancagem = Exigivel LP / Patrimonio Liquido
    alavancagem = exigivel_lp / patrimonio if patrimonio > 0 else 0
    x5 = alavancagem * 0.33

    # Fator de Insolvencia
    fator = x1 + x2 + x3 - x4 - x5

    # Status
    if fator >= 0:
        status = 'Solvencia'
    elif fator >= -3:
        status = 'Penumbra'
    else:
        status = 'Risco de Falencia'

    return {
        'Kanitz_X1': round(x1, 4),
        'Kanitz_X2': round(x2, 4),
        'Kanitz_X3': round(x3, 4),
        'Kanitz_X4': round(x4, 4),
        'Kanitz_X5': round(x5, 4),
        'Kanitz_Fator': round(fator, 4),
        'Kanitz_Status': status,
        'Kanitz_Liquidez_Geral': round(liquidez_geral, 4),
        'Kanitz_Liquidez_Seca': round(liquidez_seca, 4),
        'Kanitz_Liquidez_Corrente': round(liquidez_corrente, 4),
        'Kanitz_Alavancagem': round(alavancagem, 4),
    }


# ---------------------------------------------------------------------------
# PARSERS
# ---------------------------------------------------------------------------

def safe_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def parse_mfinance_stock(stock):
    """Parse dos dados de /stocks"""
    return {
        "Ticker": stock.get("symbol", ""),
        "Nome": stock.get("name", "#N/A"),
        "Setor": stock.get("sector", ""),
        "SubSetor": stock.get("subSector", ""),
        "Segmento": stock.get("segment", ""),
        "Cotacao": safe_float(stock.get("lastPrice")),
        "Variacao": safe_float(stock.get("change")),
        "Abertura": safe_float(stock.get("priceOpen")),
        "Maxima": safe_float(stock.get("high")),
        "Minima": safe_float(stock.get("low")),
        "Fechamento_Anterior": safe_float(stock.get("closingPrice")),
        "Volume": safe_float(stock.get("volume")),
        "Volume_Medio": safe_float(stock.get("volumeAvg")),
        "Maxima_52s": safe_float(stock.get("lastYearHigh")),
        "Minima_52s": safe_float(stock.get("lastYearLow")),
        "Market_Cap": safe_float(stock.get("marketCap")),
        "PE": safe_float(stock.get("pe")),
        "EPS": safe_float(stock.get("eps")),
        "DY": safe_float(stock.get("dividendYield")),
    }


def parse_mfinance_indicators(ind):
    """Parse dos dados de /stocks/indicators"""
    return {
        "Ticker": ind.get("symbol", ""),
        "PL": safe_float(ind.get("p_L")),
        "PVP": safe_float(ind.get("p_VP")),
        "PSR": safe_float(ind.get("p_SR")),
        "PAtivo": safe_float(ind.get("p_Ativos")),
        "PCapGiro": safe_float(ind.get("p_CapitalGiro")),
        "PAtivoCircLiq": safe_float(ind.get("p_AtivCircLiq")),
        "PEBIT": safe_float(ind.get("p_EBIT")),
        "PEBITDA": safe_float(ind.get("p_EBITDA")),
        "EV_EBIT": safe_float(ind.get("ev_EBIT")),
        "EV_EBITDA": safe_float(ind.get("ev_EBITDA")),
        "LPA": safe_float(ind.get("lpa")),
        "VPA": safe_float(ind.get("vpa")),
        "Patrimonio": safe_float(ind.get("patrimonio")),
        "Lucro_Liquido": safe_float(ind.get("lucroLiquido")),
        "EBIT": safe_float(ind.get("ebit")),
        "Receita_Liquida": safe_float(ind.get("receitaLiquida")),
        "ROE": safe_float(ind.get("roe")),
        "ROA": safe_float(ind.get("roa")),
        "ROIC": safe_float(ind.get("roic")),
        "GiroAtivos": safe_float(ind.get("giroAtivos")),
        "MargemBruta": safe_float(ind.get("margemBruta")),
        "MargemEBITDA": safe_float(ind.get("margemEBITDA")),
        "MargemEBIT": safe_float(ind.get("margemEBIT")),
        "MargemLiquida": safe_float(ind.get("margemLiquida")),
        "DivLiquida_Ativos": safe_float(ind.get("divLiquida_Ativos")),
        "DivLiquida_PL": safe_float(ind.get("divLiquida_Patrimonio")),
        "DivLiquida_EBIT": safe_float(ind.get("divLiquida_EBIT")),
        "DivLiquida_EBITDA": safe_float(ind.get("divLiquida_EBITDA")),
        "LiquidezCorrente": safe_float(ind.get("liquidezCorrente")),
        "Passivos_Ativos": safe_float(ind.get("passivos_Ativos")),
        "PL_Ativos": safe_float(ind.get("patrimonio_Ativos")),
        "CAGR_Receitas_5a": safe_float(ind.get("cagr_Receitas_5a")),
        "CAGR_Lucros_5a": safe_float(ind.get("cagr_Lucros_5a")),
        "Qtd_Acoes": safe_float(ind.get("quantidadeAcoes")),
    }


def parse_mfinance_dividends(data):
    """
    Parse dos dividendos.
    Retorna: total_12m, media_12m, ultimo, qtd_12m, media_6a (real)
    Soma JCP + Dividendo (tudo eh rendimento)
    """
    if not data:
        return {"Dividendo_Medio_12m": 0, "Dividendo_Total_12m": 0,
                "Dividendo_Ultimo": 0, "Qtd_Dividendos_12m": 0,
                "Dividendo_Medio_6a": 0}

    dividends = data.get("dividends", []) if isinstance(data, dict) else []
    if not dividends:
        return {"Dividendo_Medio_12m": 0, "Dividendo_Total_12m": 0,
                "Dividendo_Ultimo": 0, "Qtd_Dividendos_12m": 0,
                "Dividendo_Medio_6a": 0}

    now = datetime.now()
    cutoff_12m = now - timedelta(days=365)
    cutoff_6a = now - timedelta(days=365 * 6)

    total_12m = 0.0
    qtd_12m = 0
    total_6a = 0.0
    qtd_6a = 0
    ultimo = 0.0
    ultima_data = None

    for d in dividends:
        date_str = d.get("date")
        value = safe_float(d.get("value"), 0.0)
        if value <= 0 or not date_str:
            continue

        # Parse da data (pode vir com ou sem timezone)
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # Remover timezone para comparar com cutoff (que eh naive)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
        except:
            continue

        # Soma tudo (JCP + Dividendo) — rendimento total
        if dt >= cutoff_12m:
            total_12m += value
            qtd_12m += 1

        if dt >= cutoff_6a:
            total_6a += value
            qtd_6a += 1

        # Ultimo dividendo (mais recente)
        if ultima_data is None or dt > ultima_data:
            ultima_data = dt
            ultimo = value

    media_12m = total_12m / qtd_12m if qtd_12m > 0 else 0
    media_6a = total_6a / qtd_6a if qtd_6a > 0 else 0

    return {
        "Dividendo_Medio_12m": round(media_12m, 4),
        "Dividendo_Total_12m": round(total_12m, 4),
        "Dividendo_Ultimo": round(ultimo, 4),
        "Qtd_Dividendos_12m": qtd_12m,
        "Dividendo_Medio_6a": round(media_6a, 4),
    }


# ---------------------------------------------------------------------------
# MERGE E CALCULOS
# ---------------------------------------------------------------------------

def merge_mfinance_data(stocks, indicators, dividends_map):
    """Merge dos 3 endpoints em um unico dict por ticker"""
    stock_map = {s.get("symbol"): parse_mfinance_stock(s) for s in stocks}
    ind_map = {i.get("symbol"): parse_mfinance_indicators(i) for i in indicators}

    all_tickers = set(stock_map.keys()) | set(ind_map.keys())
    logger.info(f"Total de tickers unicos: {len(all_tickers)}")

    merged = []
    for ticker in sorted(all_tickers):
        parsed_stock = stock_map.get(ticker, {})
        parsed_ind = ind_map.get(ticker, {})

        # Merge: indicadores primeiro, depois stocks sobrescreve
        row = {**parsed_ind, **parsed_stock}

        # Adiciona dividendos
        div_data = parse_mfinance_dividends(dividends_map.get(ticker))
        row.update(div_data)

        # Garante que Ticker existe
        row["Ticker"] = ticker
        merged.append(row)

    return merged


def calcular_dy_12m(row):
    """DY_12m = (Dividendo_Medio_12m * 12 / Cotacao) * 100"""
    cotacao = row.get("Cotacao", 0)
    div_medio = row.get("Dividendo_Medio_12m", 0)
    if cotacao and cotacao > 0:
        return (div_medio * 12 / cotacao) * 100
    return 0


def calcular_score_cs(row):
    """
    Score CS (Carlos Sobral) — 0 a 10
    """
    score = 0
    checks = {
        "ROE_10pct": row.get("ROE", 0) > 10,
        "DY_6pct": row.get("DY_12m", 0) > 6,
        "DivLiq_EBITDA_2_5": row.get("DivLiquida_EBITDA", 999) < 2.5,
        "PL_15": 0 < row.get("PL", 999) < 15,
        "PVP_2": 0 < row.get("PVP", 999) < 2,
        "Margem_10pct": row.get("MargemLiquida", 0) > 10,
        "LiqCorrente_1": row.get("LiquidezCorrente", 0) > 1,
        "CAGR_5pct": row.get("CAGR_Receitas_5a", 0) > 5,
        "ROIC_10pct": row.get("ROIC", 0) > 10,
        "Volume_1M": row.get("Volume", 0) > 1000000,
    }
    score = sum(1 for v in checks.values() if v)

    if score >= 8:
        classif = "Excelente"
    elif score >= 6:
        classif = "Bom"
    elif score >= 4:
        classif = "Regular"
    elif score >= 2:
        classif = "Fraco"
    else:
        classif = "Pessimo"

    return score, classif, checks


def calcular_valuation(row, selic):
    """Calculos de valuation"""
    cotacao = row.get("Cotacao", 0)
    vpa = row.get("VPA", 0)
    lpa = row.get("LPA", 0)
    dy_12m = row.get("DY_12m", 0)
    div_medio_12m = row.get("Dividendo_Medio_12m", 0)

    tlr = selic / 100 if selic else 0.06

    graham = (22.5 * lpa * vpa) ** 0.5 if lpa > 0 and vpa > 0 else 0
    graham_br = (15 * lpa * vpa) ** 0.5 if lpa > 0 and vpa > 0 else 0
    bazin = (div_medio_12m * 12) / tlr if tlr > 0 else 0
    cagr_lucros = row.get("CAGR_Lucros_5a", 0)
    lynch = lpa * (cagr_lucros + dy_12m) if lpa > 0 else 0

    valuations = [graham, graham_br, bazin, lynch]
    agf_medio = sum(v for v in valuations if v > 0) / len([v for v in valuations if v > 0]) if any(v > 0 for v in valuations) else 0

    upside_graham = ((graham / cotacao) - 1) * 100 if cotacao > 0 and graham > 0 else 0
    upside_graham_br = ((graham_br / cotacao) - 1) * 100 if cotacao > 0 and graham_br > 0 else 0
    upside_bazin = ((bazin / cotacao) - 1) * 100 if cotacao > 0 and bazin > 0 else 0
    upside_lynch = ((lynch / cotacao) - 1) * 100 if cotacao > 0 and lynch > 0 else 0
    upside_agf = ((agf_medio / cotacao) - 1) * 100 if cotacao > 0 and agf_medio > 0 else 0

    return {
        "Graham": round(graham, 2),
        "Graham_BR": round(graham_br, 2),
        "Bazin": round(bazin, 2),
        "Lynch": round(lynch, 2),
        "AGF_Medio": round(agf_medio, 2),
        "Upside_Graham": round(upside_graham, 2),
        "Upside_Graham_BR": round(upside_graham_br, 2),
        "Upside_Bazin": round(upside_bazin, 2),
        "Upside_Lynch": round(upside_lynch, 2),
        "Upside_AGF_Medio": round(upside_agf, 2),
    }


# ---------------------------------------------------------------------------
# SELIC
# ---------------------------------------------------------------------------

def get_selic():
    """Busca SELIC atual do BCB"""
    try:
        resp = requests.get(SELIC_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data and len(data) > 0:
            valor_str = data[-1].get("valor", "0")
            return safe_float(valor_str.replace(",", "."))
    except Exception as e:
        logger.warning(f"Erro ao buscar SELIC: {e}")
    return 13.75


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 60)
    logger.info("SOBRAL INVEST - Atualizacao de Ativos")
    logger.info("=" * 60)

    client = MFinanceClient()

    # 1. Busca SELIC
    selic = get_selic()
    logger.info(f"SELIC: {selic}%")

    # 2. Busca dados MFinance
    stocks = client.get_stocks()
    indicators = client.get_indicators()

    # 3. Lista de tickers
    stock_symbols = {s.get("symbol") for s in stocks if s.get("symbol")}
    ind_symbols = {i.get("symbol") for i in indicators if i.get("symbol")}
    all_symbols = sorted(stock_symbols | ind_symbols)

    # 4. Busca dividendos
    dividends_map = client.get_all_dividends(all_symbols, delay=0.2)

    # 5. Merge MFinance
    merged = merge_mfinance_data(stocks, indicators, dividends_map)
    logger.info(f"Total antes do filtro: {len(merged)} tickers")

    # 6. Busca dados do Fundamentus (balanco para Kanitz)
    fundamentus_map = get_all_fundamentus_data(all_symbols, delay=1.0)

    # 7. Calcula metricas adicionais
    for row in merged:
        # DY_12m
        row["DY_12m"] = round(calcular_dy_12m(row), 2)

        # Score CS
        score, classif, checks = calcular_score_cs(row)
        row["Score_CS"] = score
        row["Score_CS_Classificacao"] = classif
        for k, v in checks.items():
            row[k] = 1 if v else 0

        # Valuation
        val = calcular_valuation(row, selic)
        row.update(val)

        # Fundamentus (balanco)
        fund_data = fundamentus_map.get(row["Ticker"], {})
        row.update(fund_data)

        # Kanitz
        kanitz = calcular_kanitz(row)
        row.update(kanitz)

    # 8. FILTRO: Remove tickers com Nome = "#N/A" ou vazio
    merged_filtrado = [r for r in merged if r.get("Nome") and r.get("Nome") != "#N/A"]
    removidos = len(merged) - len(merged_filtrado)
    logger.info(f"Removidos {removidos} tickers com Nome=#N/A")
    logger.info(f"Total apos filtro: {len(merged_filtrado)} tickers")

    # 9. Cria DataFrame
    df = pd.DataFrame(merged_filtrado)

    # Reordena colunas
    colunas_primeiras = [
        "Ticker", "Nome", "Setor", "SubSetor", "Segmento",
        "Cotacao", "Variacao", "Abertura", "Maxima", "Minima",
        "Fechamento_Anterior", "Volume", "Volume_Medio",
        "Maxima_52s", "Minima_52s", "Market_Cap",
        "PE", "EPS", "DY", "DY_12m",
        "PL", "PVP", "PSR", "PAtivo", "PCapGiro", "PAtivoCircLiq",
        "PEBIT", "PEBITDA", "EV_EBIT", "EV_EBITDA",
        "LPA", "VPA", "Patrimonio", "Lucro_Liquido", "EBIT", "Receita_Liquida",
        "ROE", "ROA", "ROIC", "GiroAtivos",
        "MargemBruta", "MargemEBITDA", "MargemEBIT", "MargemLiquida",
        "DivLiquida_Ativos", "DivLiquida_PL", "DivLiquida_EBIT", "DivLiquida_EBITDA",
        "LiquidezCorrente", "Passivos_Ativos", "PL_Ativos",
        "CAGR_Receitas_5a", "CAGR_Lucros_5a", "Qtd_Acoes",
        "Dividendo_Medio_12m", "Dividendo_Total_12m", "Dividendo_Ultimo",
        "Qtd_Dividendos_12m", "Dividendo_Medio_6a",
    ]
    colunas_valuation = [
        "Graham", "Graham_BR", "Bazin", "Lynch", "AGF_Medio",
        "Upside_Graham", "Upside_Graham_BR", "Upside_Bazin", "Upside_Lynch", "Upside_AGF_Medio",
    ]
    colunas_score = ["Score_CS", "Score_CS_Classificacao"]
    colunas_checks = [
        "ROE_10pct", "DY_6pct", "DivLiq_EBITDA_2_5", "PL_15", "PVP_2",
        "Margem_10pct", "LiqCorrente_1", "CAGR_5pct", "ROIC_10pct", "Volume_1M",
    ]
    colunas_kanitz = [
        "Ativo_Circulante", "Realizavel_LP", "Passivo_Circulante", "Exigivel_LP", "Estoques",
        "Patrimonio_Liquido", "Lucro_Liquido_Kanitz",
        "Kanitz_X1", "Kanitz_X2", "Kanitz_X3", "Kanitz_X4", "Kanitz_X5",
        "Kanitz_Fator", "Kanitz_Status",
        "Kanitz_Liquidez_Geral", "Kanitz_Liquidez_Seca", "Kanitz_Liquidez_Corrente", "Kanitz_Alavancagem",
    ]

    colunas_extras = [c for c in df.columns if c not in colunas_primeiras + colunas_valuation + colunas_score + colunas_checks + colunas_kanitz]

    ordem_final = colunas_primeiras + colunas_valuation + colunas_score + colunas_checks + colunas_kanitz + colunas_extras
    ordem_final = [c for c in ordem_final if c in df.columns]
    df = df[ordem_final]

    # 10. Salva
    df.to_excel(ATIVOS_FILE, index=False, engine="openpyxl")
    df.to_csv(ATIVOS_CSV, index=False)

    logger.info(f"\n✅ Planilha salva:")
    logger.info(f"   Excel: {ATIVOS_FILE}")
    logger.info(f"   CSV:   {ATIVOS_CSV}")
    logger.info(f"   Linhas: {len(df)}")
    logger.info(f"   Colunas: {len(df.columns)}")

    # Estatisticas do Score CS
    score_counts = df["Score_CS_Classificacao"].value_counts().to_dict()
    logger.info(f"\n📊 Distribuicao Score CS:")
    for cls in ["Excelente", "Bom", "Regular", "Fraco", "Pessimo"]:
        if cls in score_counts:
            logger.info(f"   {cls}: {score_counts[cls]}")

    # Estatisticas Kanitz
    kanitz_counts = df["Kanitz_Status"].value_counts().to_dict()
    logger.info(f"\n🌡️ Distribuicao Kanitz:")
    for status in ["Solvencia", "Penumbra", "Risco de Falencia", "Sem Dados"]:
        if status in kanitz_counts:
            logger.info(f"   {status}: {kanitz_counts[status]}")

    return df


if __name__ == "__main__":
    main()
