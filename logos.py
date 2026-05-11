# logos.py
"""
Baixa logos para a lista de tickers e salva arquivos SVG em ./logos/.
Fluxos implementados (na ordem):
 1) public.tradar.com.br — tenta https://public.tradar.com.br/logos/{TICKER}.svg
 2) brapi.dev (sem token) — tenta endpoints públicos e usa campo logourl quando presente
Conversões:
 - Se cairosvg estiver instalado, converte SVG -> PNG e salva ./logos/{TICKER}.png
Regras solicitadas:
 - Não usar yfinance, Clearbit ou qualquer token privado
 - Não gerar imagens com iniciais (nenhum fallback gráfico)
 - Não criar arquivos PNG vazios
 - Salva SVGs quando encontrados; salva PNG apenas se a conversão for bem-sucedida
Uso:
    python logos.py
Dependências opcionais (recomendado para conversão):
    pip install requests cairosvg
"""

import os
import time
import requests
import traceback
from urllib.parse import urljoin

# Lista de tickers (substitua/adicione conforme necessário)
TICKERS = [
"AALR3","ABCB4","ABEV3","AERI3","AGRO3","AGXY3","ALLD3","ALOS3","ALPA4","ALPK3",
"ALUP11","ALUP4","AMAR3","AMBP3","AMER3","AMOB3","ANIM3","ARML3","ASAI3","ATED3",
"AURA33","AURE3","AZEV4","AZTE3","AZZA3","B3SA3","BAZA3","BBAS3","BBDC3","BBDC4",
"BBSE3","BEEF3","BEES4","BGIP4","BHIA3","BIOM3","BLAU3","BMEB4","BMGB4","BMOB3",
"BPAC11","BRAP3","BRAP4","BRAV3","BRBI11","BRKM3","BRKM5","BRSR6","BRST3","BSLI4",
"CAMB3","CAML3","CASH3","CBAV3","CEAB3","CGRA4","CLSC4","CMIG3","CMIG4","CMIN3",
"COCE5","COGN3","CPFE3","CPLE3","CSAN3","CSED3","CSMG3","CSNA3","CURY3","CVCB3",
"CXSE3","CYRE3","DASA3","DESK3","DEXP3","DEXP4","DIRR3","DMVF3","DOTZ3","DXCO3",
"EALT4","ECOR3","EGIE3","EMAE4","ENEV3","ENGI11","ENGI3","ENJU3","EQPA3","EQTL3",
"ESPA3","EUCA3","EUCA4","EVEN3","EZTC3","FESA4","FHER3","FICT3","FIQE3","FLRY3",
"FRAS3","G2DI33","GFSA3","GGBR3","GGBR4","GGPS3","GMAT3","GOAU3","GOAU4","GRND3",
"HAPV3","HBOR3","HBRE3","HBSA3","HYPE3","IFCM3","IGTI11","IGTI3","INTB3","IRBR3",
"ISAE4","ITSA4","ITUB4","JALL3","JHSF3","JSLG3","KEPL3","KLBN11","KLBN4","LAND3",
"LAVV3","LEVE3","LIGT3","LJQQ3","LOGG3","LOGN3","LPSB3","LREN3","LUPA3","LWSA3",
"MATD3","MBRF3","MDIA3","MDNE3","MEAL3","MELK3","MGLU3","MILS3","MLAS3","MOTV3",
"MOVI3","MRVE3","MTRE3","MULT3","MYPK3","NATU3","NEOE3","NGRD3","ODPV3","OFSA3",
"OIBR3","ONCO3","OPCT3","ORVR3","PCAR3","PDGR3","PDTC3","PETR3","PETR4","PFRM3",
"PGMN3","PINE4","PLPL3","PMAM3","PNVL3","POMO3","POMO4","POSI3","PRIO3","PRNR3",
"PSSA3","PTBL3","PTNT4","QUAL3","RADL3","RAIL3","RAIZ4","RANI3","RAPT3","RAPT4",
"RCSL4","RDOR3","RECV3","RENT3","ROMI3","SANB11","SAPR11","SAPR4","SBFG3","SBSP3",
"SCAR3","SEER3","SEQL3","SHOW3","SHUL4","SIMH3","SLCE3","SMFT3","SMTO3","SOJA3",
"SUZB3","SYNE3","TAEE11","TAEE4","TCSA3","TECN3","TEND3","TFCO4","TGMA3","TIMS3",
"TOTS3","TPIS3","TRAD3","TRIS3","TTEN3","TUPY3","UCAS3","UGPA3","UNIP6","USIM3",
"USIM5","VALE3","VAMO3","VBBR3","VITT3","VIVA3","VIVR3","VIVT3","VLID3","VSTE3",
"VTRU3","VULC3","VVEO3","WEGE3","WEST3","WIZC3","YDUQ3"
]

LOGOS_DIR = "logos"
os.makedirs(LOGOS_DIR, exist_ok=True)

REQUEST_TIMEOUT = 12
RETRIES = 2
RETRY_DELAY = 1.0

# Optional converter: cairosvg for SVG -> PNG
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except Exception:
    CAIROSVG_AVAILABLE = False

# Helpers
def safe_name(ticker: str) -> str:
    return "".join(c for c in ticker if c.isalnum() or c in ("-", "_")).upper()

def svg_path_for(ticker_safe: str) -> str:
    return os.path.join(LOGOS_DIR, ticker_safe + ".svg")

def png_path_for(ticker_safe: str) -> str:
    return os.path.join(LOGOS_DIR, ticker_safe + ".png")

def try_download(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (LogoDownloader)"}
    attempt = 0
    while attempt <= RETRIES:
        try:
            r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200 and r.content:
                return r.content, r.headers.get("Content-Type", "")
            attempt += 1
            time.sleep(RETRY_DELAY)
        except Exception:
            attempt += 1
            time.sleep(RETRY_DELAY)
    return None, None

def save_bytes(path: str, b: bytes):
    with open(path, "wb") as f:
        f.write(b)

def convert_svg_to_png_bytes(svg_bytes: bytes):
    if not CAIROSVG_AVAILABLE:
        return None
    try:
        return cairosvg.svg2png(bytestring=svg_bytes)
    except Exception:
        return None

# Source 1: public.tradar.com.br (SVG only)
def try_tradar_svg(ticker: str):
    base = "https://public.tradar.com.br/logos"
    url = f"{base}/{ticker}.svg"
    b, ct = try_download(url)
    if b:
        return b, ct, url
    return None, None, None

# Source 2: brapi.dev (sem token) - tenta endpoints públicos e usa campo logourl quando presente
def try_brapi_public(ticker: str):
    candidates = [
        f"https://brapi.dev/api/quote/{ticker}",
        f"https://brapi.dev/api/stock/{ticker}",
        f"https://brapi.dev/api/stock?symbol={ticker}"
    ]
    for url in candidates:
        try:
            r = requests.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                continue
            data = r.json()
            # tenta caminhos comuns
            if isinstance(data, dict):
                if "results" in data and isinstance(data["results"], list) and data["results"]:
                    first = data["results"][0]
                    logo = first.get("logourl") or first.get("logo") or first.get("logo_url")
                    if logo:
                        b, ct = try_download(logo)
                        if b:
                            return b, ct, logo
                logo = data.get("logourl") or data.get("logo") or data.get("logo_url")
                if logo:
                    b, ct = try_download(logo)
                    if b:
                        return b, ct, logo
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    logo = first.get("logourl") or first.get("logo") or first.get("logo_url")
                    if logo:
                        b, ct = try_download(logo)
                        if b:
                            return b, ct, logo
        except Exception:
            continue
    return None, None, None

# Core per-ticker logic (apenas SVG via tradar e brapi public; sem fallbacks gráficos)
def ensure_logo_svg_and_convert(ticker: str):
    ticker_safe = safe_name(ticker)
    svg_path = svg_path_for(ticker_safe)
    png_path = png_path_for(ticker_safe)

    # Se já existe SVG salvo e não está vazio, tenta converter (se necessário)
    if os.path.exists(svg_path) and os.path.getsize(svg_path) > 0:
        # tenta converter se cairosvg disponível e PNG não existe
        if CAIROSVG_AVAILABLE and (not os.path.exists(png_path) or os.path.getsize(png_path) == 0):
            try:
                with open(svg_path, "rb") as f:
                    svg_bytes = f.read()
                png_bytes = convert_svg_to_png_bytes(svg_bytes)
                if png_bytes:
                    save_bytes(png_path, png_bytes)
                    return {"ticker": ticker, "status": "svg_exists_converted", "svg": svg_path, "png": png_path}
            except Exception:
                pass
        return {"ticker": ticker, "status": "svg_exists", "svg": svg_path, "png": None}

    # 1) tentar public.tradar (SVG)
    b, ct, src = try_tradar_svg(ticker)
    if b:
        # salva SVG
        try:
            save_bytes(svg_path, b)
        except Exception:
            return {"ticker": ticker, "status": "tradar_save_failed", "svg": None, "png": None}
        # tenta converter para PNG se possível
        if CAIROSVG_AVAILABLE:
            png_bytes = convert_svg_to_png_bytes(b)
            if png_bytes:
                save_bytes(png_path, png_bytes)
                return {"ticker": ticker, "status": "tradar_svg_converted", "svg": svg_path, "png": png_path}
            else:
                return {"ticker": ticker, "status": "tradar_svg_saved_no_convert", "svg": svg_path, "png": None}
        else:
            return {"ticker": ticker, "status": "tradar_svg_saved_no_cairosvg", "svg": svg_path, "png": None}

    # 2) tentar brapi.dev (sem token)
    b, ct, src = try_brapi_public(ticker)
    if b:
        # se for SVG, salva e tenta converter
        is_svg = False
        if (ct and "svg" in ct.lower()) or (src and src.lower().endswith(".svg")) or (b.strip().startswith(b"<") and b.strip().lower().find(b"<svg") != -1):
            is_svg = True
        if is_svg:
            try:
                save_bytes(svg_path, b)
            except Exception:
                return {"ticker": ticker, "status": "brapi_svg_save_failed", "svg": None, "png": None}
            if CAIROSVG_AVAILABLE:
                png_bytes = convert_svg_to_png_bytes(b)
                if png_bytes:
                    save_bytes(png_path, png_bytes)
                    return {"ticker": ticker, "status": "brapi_svg_converted", "svg": svg_path, "png": png_path}
                else:
                    return {"ticker": ticker, "status": "brapi_svg_saved_no_convert", "svg": svg_path, "png": None}
            else:
                return {"ticker": ticker, "status": "brapi_svg_saved_no_cairosvg", "svg": svg_path, "png": None}
        else:
            # brapi retornou imagem raster (png/jpg). Salvamos apenas se for PNG/JPEG (mas não convertemos)
            ext = ".png" if (ct and "png" in ct.lower()) or (src and src.lower().endswith(".png")) else ".jpg"
            out_path = os.path.join(LOGOS_DIR, ticker_safe + ext)
            try:
                save_bytes(out_path, b)
                return {"ticker": ticker, "status": "brapi_raster_saved", "svg": None, "png": out_path if ext==".png" else None}
            except Exception:
                return {"ticker": ticker, "status": "brapi_raster_save_failed", "svg": None, "png": None}

    # Nenhuma fonte retornou SVG/raster; não criar arquivos vazios e reportar falha
    return {"ticker": ticker, "status": "not_found", "svg": None, "png": None}

def main():
    total = len(TICKERS)
    print(f"Starting: {total} tickers. Saving SVGs in ./{LOGOS_DIR}/", flush=True)
    print(f"cairosvg available: {CAIROSVG_AVAILABLE}", flush=True)
    results = []
    for idx, t in enumerate(TICKERS, 1):
        ticker = t.strip().upper()
        try:
            print(f"[{idx}/{total}] {ticker} - start", flush=True)
            res = ensure_logo_svg_and_convert(ticker)
            print(f"[{idx}/{total}] {ticker} - {res['status']} -> svg: {res.get('svg')} png: {res.get('png')}", flush=True)
            results.append(res)
        except Exception:
            traceback.print_exc()
            results.append({"ticker": ticker, "status": "error", "svg": None, "png": None})

    # resumo
    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    print("\nSummary:", flush=True)
    for k, v in sorted(summary.items()):
        print(f"  {k}: {v}", flush=True)
    print(f"\nLogos directory: {os.path.abspath(LOGOS_DIR)}", flush=True)

if __name__ == "__main__":
    main()
