import os
import json
import requests
from datetime import date

BASE_URL = "https://api.usebolsai.com/api/v1"
TOP_N = 200
CACHE_FILE = "cache_bolsai.json"


def _headers():
    api_key = os.getenv("USEBOLSAI_API_KEY")
    if not api_key:
        raise EnvironmentError("⚠️ USEBOLSAI_API_KEY não configurada.")
    return {"X-API-Key": api_key}


def _carregar_cache():
    """Retorna dados do cache se foram gerados hoje, senão None."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("data") == str(date.today()):
            print(f"✅ Cache válido encontrado ({CACHE_FILE}) — pulando chamadas à API.")
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


def _score_basico(item):
    """Score rápido com dados do screener para rankear antes de chamar fundamentals."""
    score = 0
    roe = item.get("roe") or 0
    dy  = item.get("dividend_yield") or 0
    pl  = item.get("pl") or 999
    pvp = item.get("pvp") or 999
    net_margin = item.get("net_margin") or 0
    debt_equity = item.get("debt_equity") or 999

    if dy > 1:
        dy = dy / 100  # normaliza se vier como percentual

    if roe > 0.12:       score += 2
    if dy > 0.07:        score += 2
    if pl < 15:          score += 1
    if pvp < 2:          score += 1
    if net_margin > 0.1: score += 1
    if debt_equity < 1:  score += 1
    return score


def _buscar_screener(tickers_set):
    """Busca todos os ativos via screener (1 requisição)."""
    headers = _headers()
    resultados = []
    offset = 0
    limit = 500

    print("📡 Buscando screener (1 requisição)...")
    while True:
        resp = requests.get(
            f"{BASE_URL}/screener/",
            headers=headers,
            params={"limit": limit, "offset": offset, "sort": "market_cap", "order": "desc"},
            timeout=30
        )
        if resp.status_code != 200:
            print(f"⚠️ Screener erro {resp.status_code}: {resp.text[:200]}")
            break

        data = resp.json()
        items = data if isinstance(data, list) else data.get("data", data.get("results", []))
        if not items:
            break

        for item in items:
            ticker = (item.get("ticker") or item.get("symbol") or "").upper()
            if ticker in tickers_set:
                item["ticker"] = ticker
                item["_score_basico"] = _score_basico(item)
                resultados.append(item)

        if len(items) < limit:
            break
        offset += limit

    print(f"   → {len(resultados)}/{len(tickers_set)} ativos encontrados no screener.")
    return resultados


def _buscar_fundamentals(ticker, headers):
    """Busca fundamentals detalhados de um único ticker."""
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


def _normalizar(item, fund=None):
    """Monta dict padronizado mesclando screener + fundamentals."""
    f = fund or {}
    return {
        "ticker":           item.get("ticker"),
        "close_price":      item.get("close") or item.get("price") or item.get("close_price") or f.get("close_price"),
        "pl":               f.get("pl") or item.get("pl") or item.get("price_to_earnings"),
        "pvp":              f.get("pvp") or item.get("pvp") or item.get("price_to_book"),
        "ev_ebitda":        f.get("ev_ebitda") or item.get("ev_ebitda"),
        "ev_ebit":          f.get("ev_ebit") or item.get("ev_ebit"),
        "lpa":              f.get("lpa") or item.get("lpa") or item.get("eps"),
        "vpa":              f.get("vpa") or item.get("vpa"),
        "dividend_yield":   f.get("dividend_yield") or item.get("dividend_yield") or item.get("dy"),
        "roe":              f.get("roe") or item.get("roe"),
        "roa":              f.get("roa") or item.get("roa"),
        "roic":             f.get("roic") or item.get("roic"),
        "gross_margin":     f.get("gross_margin") or item.get("gross_margin"),
        "ebit_margin":      f.get("ebit_margin") or item.get("ebit_margin"),
        "ebitda_margin":    f.get("ebitda_margin") or item.get("ebitda_margin"),
        "net_margin":       f.get("net_margin") or item.get("net_margin"),
        "debt_equity":      f.get("debt_equity") or item.get("debt_equity"),
        "current_ratio":    f.get("current_ratio") or item.get("current_ratio"),
        "cagr_revenue_5y":  f.get("cagr_revenue_5y") or item.get("cagr_revenue_5y"),
        "cagr_earnings_5y": f.get("cagr_earnings_5y") or item.get("cagr_earnings_5y"),
        "market_cap":       f.get("market_cap") or item.get("market_cap"),
        "equity":           f.get("equity") or item.get("equity"),
        "net_revenue":      f.get("net_revenue") or item.get("net_revenue"),
        "net_income":       f.get("net_income") or item.get("net_income"),
        "ebitda":           f.get("ebitda") or item.get("ebitda"),
        "ebit":             f.get("ebit") or item.get("ebit"),
        "net_debt":         f.get("net_debt") or item.get("net_debt"),
        "cash":             f.get("cash") or item.get("cash"),
        "total_assets":     f.get("total_assets") or item.get("total_assets"),
    }


def buscar_acoes_usebolsai(tickers):
    """
    Estratégia:
      1. Tenta carregar cache do dia — se existir, retorna direto.
      2. Screener (1 req) → score básico para todos os ativos.
      3. Top 200 por score → /fundamentals/{ticker} (até 200 req).
      4. Restante fica só com dados do screener.
      5. Salva tudo em cache JSON para o dia.
    Retorna: (list[dict], list[str] não encontrados)
    """
    # Cache
    cache = _carregar_cache()
    if cache is not None:
        nao_encontrados = sorted(set(t.upper() for t in tickers) - {r["ticker"] for r in cache})
        return cache, nao_encontrados

    tickers_set = set(t.upper() for t in tickers)
    headers = _headers()

    # Passo 1: screener
    screener_items = _buscar_screener(tickers_set)

    # Passo 2: rankeia e separa top N
    screener_items.sort(key=lambda x: x.get("_score_basico", 0), reverse=True)
    top_items    = screener_items[:TOP_N]
    resto_items  = screener_items[TOP_N:]

    # Passo 3: fundamentals para o top N
    print(f"📡 Buscando fundamentals dos top {len(top_items)} ativos ({len(top_items)} requisições)...")
    resultados = []
    for i, item in enumerate(top_items, 1):
        ticker = item["ticker"]
        print(f"   [{i}/{len(top_items)}] {ticker}")
        fund = _buscar_fundamentals(ticker, headers)
        resultados.append(_normalizar(item, fund))

    # Passo 4: resto só com screener
    print(f"📋 Usando apenas screener para os demais {len(resto_items)} ativos.")
    for item in resto_items:
        resultados.append(_normalizar(item))

    # Passo 5: cache
    _salvar_cache(resultados)

    nao_encontrados = sorted(tickers_set - {r["ticker"] for r in resultados})
    if nao_encontrados:
        print(f"⚠️ Não encontrados (fallback yfinance): {nao_encontrados}")

    print(f"✅ Total: {len(resultados)} ativos processados.")
    return resultados, nao_encontrados
