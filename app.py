"""
Sobral Invest - Coletor de Dados de Ativos B3
Atualiza data/ativos.xlsx e data/selic.json
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
SELIC_FILE = OUTPUT_DIR / "selic.json"

# MFinance API
MF_BASE = "https://mfinance.com.br/api/v1"

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
        logger.info("Buscando /stocks...")
        data = self._get(f"{MF_BASE}/stocks")
        stocks = data if isinstance(data, list) else data.get("stocks", [])
        logger.info(f" -> {len(stocks)} ativos de /stocks")
        return stocks

    def get_indicators(self):
        logger.info("Buscando /stocks/indicators...")
        data = self._get(f"{MF_BASE}/stocks/indicators")
        indicators = data if isinstance(data, list) else data.get("indicators", [])
        logger.info(f" -> {len(indicators)} indicadores")
        return indicators

    def get_dividends(self, symbol):
        url = f"{MF_BASE}/stocks/dividends/{symbol}"
        try:
            data = self._get(url, retries=2, delay=1)
            return data
        except Exception as e:
            logger.debug(f"Erro dividendos {symbol}: {e}")
            return None

    def get_all_dividends(self, symbols, delay=0.3):
        logger.info(f"Buscando dividendos para {len(symbols)} tickers...")
        results = {}
        for i, sym in enumerate(symbols):
            if i % 50 == 0 and i > 0:
                logger.info(f" -> {i}/{len(symbols)} dividendos...")
            data = self.get_dividends(sym)
            if data:
                results[sym] = data
            time.sleep(delay)
        logger.info(f" -> {len(results)} tickers com dividendos")
        return results

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
    """Extrai .value de campos aninhados da API MFinance"""
    def get_val(key, default=0.0):
        field = ind.get(key)
        if isinstance(field, dict):
            return safe_float(field.get("value"), default)
        return safe_float(field, default)
    
    return {
        "Ticker": ind.get("symbol", ""),
        "PL": get_val("priceEarningsRatio"),
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
        "Patrimonio": get_val("equity"),
        "Lucro_Liquido": get_val("netProfit"),
        "EBIT": get_val("ebit"),
        "Receita_Liquida": get_val("netRevenue"),
        "ROE": get_val("returnOnEquity"),
        "ROA": get_val("returnOnAssets"),
        "ROIC": get_val("returnOnInvestedCapital"),
        "GiroAtivos": get_val("assetTurnoverRatio"),
        "MargemBruta": get_val("grossMargin"),
        "MargemEBITDA": get_val("ebitdaMargin"),
        "MargemEBIT": get_val("ebitMargin"),
        "MargemLiquida": get_val("netMargin"),
        "DivLiquida_Ativos": get_val("netDebtToAssets"),
        "DivLiquida_PL": get_val("netDebtToEquity"),
        "DivLiquida_EBIT": get_val("netDebtToEbit"),
        "DivLiquida_EBITDA": get_val("netDebtToEbitda"),
        "LiquidezCorrente": get_val("currentLiquidity"),
        "Passivos_Ativos": get_val("liabilitiesToAssetsRatio"),
        "PL_Ativos": get_val("equityToAssetsRatio"),
        "CAGR_Receitas_5a": get_val("cagrRecipesFiveYears"),
        "CAGR_Lucros_5a": get_val("cagrProfitsFiveYears"),
        "Qtd_Acoes": get_val("sharesOutstanding"),
    }

def parse_mfinance_dividends(data):
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

        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
        except:
            continue

        if dt >= cutoff_12m:
            total_12m += value
            qtd_12m += 1

        if dt >= cutoff_6a:
            total_6a += value
            qtd_6a += 1

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
    stock_map = {s.get("symbol"): parse_mfinance_stock(s) for s in stocks}
    ind_map = {i.get("symbol"): parse_mfinance_indicators(i) for i in indicators}

    all_tickers = set(stock_map.keys()) | set(ind_map.keys())
    logger.info(f"Total de tickers unicos: {len(all_tickers)}")

    merged = []
    for ticker in sorted(all_tickers):
        parsed_stock = stock_map.get(ticker, {})
        parsed_ind = ind_map.get(ticker, {})
        row = {**parsed_ind, **parsed_stock}
        div_data = parse_mfinance_dividends(dividends_map.get(ticker))
        row.update(div_data)
        row["Ticker"] = ticker
        merged.append(row)

    return merged

def calcular_dy_12m(row):
    cotacao = row.get("Cotacao", 0)
    div_medio = row.get("Dividendo_Medio_12m", 0)
    if cotacao and cotacao > 0:
        return (div_medio * 12 / cotacao) * 100
    return 0

def calcular_score_cs(row):
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

    if score >= 8: classif = "Excelente"
    elif score >= 6: classif = "Bom"
    elif score >= 4: classif = "Regular"
    elif score >= 2: classif = "Fraco"
    else: classif = "Pessimo"

    return score, classif, checks

def calcular_valuation(row, selic):
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

    return {
        "Graham": round(graham, 2), "Graham_BR": round(graham_br, 2),
        "Bazin": round(bazin, 2), "Lynch": round(lynch, 2), "AGF_Medio": round(agf_medio, 2),
        "Upside_Graham": round(((graham / cotacao) - 1) * 100, 2) if cotacao > 0 and graham > 0 else 0,
        "Upside_Graham_BR": round(((graham_br / cotacao) - 1) * 100, 2) if cotacao > 0 and graham_br > 0 else 0,
        "Upside_Bazin": round(((bazin / cotacao) - 1) * 100, 2) if cotacao > 0 and bazin > 0 else 0,
        "Upside_Lynch": round(((lynch / cotacao) - 1) * 100, 2) if cotacao > 0 and lynch > 0 else 0,
        "Upside_AGF_Medio": round(((agf_medio / cotacao) - 1) * 100, 2) if cotacao > 0 and agf_medio > 0 else 0,
    }

# ---------------------------------------------------------------------------
# SELIC HISTORICA (serie 432 - META SELIC % ao ano)
# ---------------------------------------------------------------------------

def get_selic_historico():
    hoje = datetime.now()
    data_inicial = hoje.replace(year=hoje.year - 10)
    data_inicial_str = data_inicial.strftime("%d/%m/%Y")
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial={data_inicial_str}"

    for attempt in range(3):
        try:
            logger.info(f"Tentativa {attempt+1}/3 - BCB SELIC 432...")
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            dados = resp.json()
            registros = []
            for d in dados:
                valor_ano = safe_float(d.get("valor"), 0.0)
                if valor_ano > 0:
                    registros.append({
                        "data": d.get("data"),
                        "valor_dia": None,
                        "valor_anual": round(valor_ano, 2)
                    })
            logger.info(f"SELIC 432 OK: {len(registros)} registros")
            return registros
        except Exception as e:
            logger.warning(f"Tentativa {attempt+1} falhou: {e}")
            if attempt < 2: time.sleep(5)
            else: logger.error("Todas as tentativas falharam para SELIC 432")
            return []

def salvar_selic_json(historico):
    if not historico: return
    selic_data = {
        "atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fonte": "BCB - SGS Serie 432 (Meta SELIC)",
        "periodo_dias": 10,
        "total_registros": len(historico),
        "atual": historico[-1]["valor_anual"] if historico else 0,
        "minima": min(r["valor_anual"] for r in historico) if historico else 0,
        "maxima": max(r["valor_anual"] for r in historico) if historico else 0,
        "media": round(sum(r["valor_anual"] for r in historico) / len(historico), 2) if historico else 0,
        "historico": historico
    }
    with open(SELIC_FILE, "w", encoding="utf-8") as f:
        json.dump(selic_data, f, ensure_ascii=False, indent=2)
    logger.info(f"SELIC salva: {SELIC_FILE} ({len(historico)} registros)")

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 60)
    logger.info("SOBRAL INVEST - Atualizacao de Ativos")
    logger.info("=" * 60)

    logger.info("Buscando SELIC historica (serie 432 - Meta SELIC)...")
    selic_historico = get_selic_historico()
    salvar_selic_json(selic_historico)
    selic = selic_historico[-1]["valor_anual"] if selic_historico else 13.75
    logger.info(f"SELIC atual (serie 432 - Meta): {selic}%")

    client = MFinanceClient()
    stocks = client.get_stocks()
    indicators = client.get_indicators()

    stock_symbols = {s.get("symbol") for s in stocks if s.get("symbol")}
    ind_symbols = {i.get("symbol") for i in indicators if i.get("symbol")}
    all_symbols = sorted(stock_symbols | ind_symbols)
    dividends_map = client.get_all_dividends(all_symbols, delay=0.2)

    merged = merge_mfinance_data(stocks, indicators, dividends_map)
    logger.info(f"Total antes do filtro: {len(merged)} tickers")

    for row in merged:
        row["DY_12m"] = round(calcular_dy_12m(row), 2)
        score, classif, checks = calcular_score_cs(row)
        row["Score_CS"] = score
        row["Score_CS_Classificacao"] = classif
        for k, v in checks.items():
            row[k] = 1 if v else 0
        row.update(calcular_valuation(row, selic))

    merged_filtrado = [r for r in merged if r.get("Nome") and r.get("Nome") != "#N/A"]
    logger.info(f"Removidos {len(merged) - len(merged_filtrado)} tickers com Nome=#N/A")
    logger.info(f"Total apos filtro: {len(merged_filtrado)} tickers")

    df = pd.DataFrame(merged_filtrado)

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
    colunas_extras = [c for c in df.columns if c not in colunas_primeiras + colunas_valuation + colunas_score + colunas_checks]

    ordem_final = colunas_primeiras + colunas_valuation + colunas_score + colunas_checks + colunas_extras
    ordem_final = [c for c in ordem_final if c in df.columns]
    df = df[ordem_final]

    df.to_excel(ATIVOS_FILE, index=False, engine="openpyxl", sheet_name="Dados")
    df.to_csv(ATIVOS_CSV, index=False)

    logger.info(f"\nPlanilha salva:")
    logger.info(f" Excel: {ATIVOS_FILE}")
    logger.info(f" CSV: {ATIVOS_CSV}")
    logger.info(f" Linhas: {len(df)} | Colunas: {len(df.columns)}")

    score_counts = df["Score_CS_Classificacao"].value_counts().to_dict()
    logger.info(f"\nDistribuicao Score CS:")
    for cls in ["Excelente", "Bom", "Regular", "Fraco", "Pessimo"]:
        if cls in score_counts:
            logger.info(f" {cls}: {score_counts[cls]}")

    return df

if __name__ == "__main__":
    main()
