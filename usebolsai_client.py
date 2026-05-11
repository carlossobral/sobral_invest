import os
import json
import requests
from datetime import date
from brapi_client import obter_dados_yfinance, obter_dados_brapi

BASE_URL  = "https://api.usebolsai.com/api/v1"
TOP_N     = 160   # 160 req fundamentals + margem de segurança dentro de 200/dia
CACHE_FILE = "cache_bolsai.json"


# ─── Cache ────────────────────────────────────────────────────────────────────

def _carregar_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("data") == str(date.today()):
            print(f"✅ Cache válido ({CACHE_FILE}) — pulando chamadas à API.")
            return cache.get("resultados", [])
    except Exception as e:
        print(f"⚠️ Erro ao ler cache: {e}")
    return None


def _salvar_cache(resultados):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"data": str(date.today()), "resultados": resultados}, f, ensure_ascii=False)
        print(f"💾 Cache salvo em {CACHE_FILE}")
    except Exception as e:
        print(f"⚠️ Erro ao salvar cache: {e}")


# ─── Score básico (yfinance) ──────────────────────────────────────────────────

def _score_basico(dados_yf):
    score = 0
    roe        = dados_yf.get("ROE") or 0
    dy         = dados_yf.get("DY") or 0
    pl         = dados_yf.get("PL") or 999
    pvp        = dados_yf.get("PVP") or 999
    net_margin = dados_yf.get("Margem_Liquida") or 0
    debt_eq    = dados_yf.get("Divida_PL") or 999

    if dy > 1: dy = dy / 100  # normaliza percentual → decimal

    if roe > 0.12:        score += 2
    if dy > 0.07:         score += 2
    if 0 < pl < 15:       score += 1
    if 0 < pvp < 2:       score += 1
    if net_margin > 0.10: score += 1
    if 0 < debt_eq < 1:   score += 1
    return score


# ─── UsebolsaI fundamentals ───────────────────────────────────────────────────

def _buscar_fundamentals(ticker, headers):
    try:
        resp = requests.get(
            f"{BASE_URL}/fundamentals/{ticker}",
            headers=headers,
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"   ⚠️ Fundamentals {ticker}: {resp.status_code}")
    except Exception as e:
        print(f"   ⚠️ Erro fundamentals {ticker}: {e}")
    return {}


def _enriquecer(dados_yf, fund):
    """Substitui campos do yfinance pelos do UsebolsaI quando disponíveis."""
    def pegar(chave_fund, chave_yf):
        return fund.get(chave_fund) or dados_yf.get(chave_yf)

    return {
        **dados_yf,
        "PL":              pegar("pl",              "PL"),
        "PVP":             pegar("pvp",             "PVP"),
        "LPA":             pegar("lpa",             "LPA"),
        "VPA":             pegar("vpa",             "VPA"),
        "DY":              pegar("dividend_yield",  "DY"),
        "ROE":             pegar("roe",             "ROE"),
        "ROA":             pegar("roa",             "ROA"),
        "ROIC":            pegar("roic",            "ROIC"),
        "Margem_Bruta":    pegar("gross_margin",    "Margem_Bruta"),
        "Margem_EBIT":     pegar("ebit_margin",     "Margem_EBIT"),
        "Margem_EBITDA":   fund.get("ebitda_margin"),
        "Margem_Liquida":  pegar("net_margin",      "Margem_Liquida"),
        "Divida_PL":       pegar("debt_equity",     "Divida_PL"),
        "Liquidez_Corrente": pegar("current_ratio", "Liquidez_Corrente"),
        "Receita_CAGR":    pegar("cagr_revenue_5y", "Receita_CAGR"),
        "Lucro_CAGR":      pegar("cagr_earnings_5y","Lucro_CAGR"),
        "EV_EBITDA":       fund.get("ev_ebitda"),
        "EV_EBIT":         fund.get("ev_ebit"),
        "EBITDA":          pegar("ebitda",          "EBITDA"),
        "EBIT":            pegar("ebit",            "EBIT"),
        "Patrimonio":      pegar("equity",          "Patrimonio"),
        "Receita_Liquida": pegar("net_revenue",     "Receita_Liquida"),
        "Lucro_Liquido":   pegar("net_income",      "Lucro_Liquido"),
        "Divida_Liquida":  pegar("net_debt",        "Divida_Liquida"),
        "Caixa":           pegar("cash",            "Caixa"),
        "Ativos_Totais":   pegar("total_assets",    "Ativos_Totais"),
    }


# ─── Entrada principal ────────────────────────────────────────────────────────

def buscar_acoes_usebolsai(tickers):
    """
    1. Cache: se já rodou hoje, retorna direto.
    2. yfinance: busca todos os tickers (gratuito).
    3. Score básico: rankeia os melhores.
    4. Top 160: enriquece com /fundamentals/{ticker} do UsebolsaI.
    5. Salva cache do dia.
    Retorna: list[dict] com todos os ativos normalizados.
    """
    cache = _carregar_cache()
    if cache is not None:
        return cache, []

    api_key = os.getenv("USEBOLSAI_API_KEY")
    headers = {"X-API-Key": api_key} if api_key else {}
    if not api_key:
        print("⚠️ USEBOLSAI_API_KEY não configurada — usando apenas yfinance.")

    # Passo 1: yfinance para todos
    print(f"📡 Buscando {len(tickers)} ativos via yfinance...")
    dados_yf = {}
    for i, ticker in enumerate(tickers, 1):
        print(f"   [{i}/{len(tickers)}] {ticker}", end="\r")
        yf = obter_dados_yfinance(ticker)
        yf["Ticker"] = ticker
        brapi = obter_dados_brapi(ticker)
        yf["Segmento"] = brapi.get("sector") or brapi.get("industry") or brapi.get("segment") or "Desconhecido"
        yf["_score"] = _score_basico(yf)
        dados_yf[ticker] = yf
    print()

    # Passo 2: rankeia e separa top N
    ranking = sorted(dados_yf.values(), key=lambda x: x["_score"], reverse=True)
    top     = ranking[:TOP_N]
    resto   = ranking[TOP_N:]

    # Passo 3: enriquece top N com UsebolsaI
    if api_key:
        print(f"📡 Enriquecendo top {len(top)} com UsebolsaI fundamentals...")
        for i, item in enumerate(top, 1):
            ticker = item["Ticker"]
            print(f"   [{i}/{len(top)}] {ticker}", end="\r")
            fund = _buscar_fundamentals(ticker, headers)
            top[i-1] = _enriquecer(item, fund)
        print()
    else:
        print("⚠️ Sem API key — sem enriquecimento UsebolsaI.")

    resultados = top + resto

    # Remove campo interno de score
    for r in resultados:
        r.pop("_score", None)

    _salvar_cache(resultados)
    print(f"✅ {len(resultados)} ativos prontos.")
    return resultados, []
