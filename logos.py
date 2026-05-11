# logos.py
"""
Baixa logos para a lista de tickers fornecida e salva todas como PNG em ./logos/.
- Usa yfinance para obter logo_url.
- Faz download com requests.
- Converte SVG -> PNG se cairosvg estiver instalado.
- Converte JPG/WEBP/etc -> PNG se Pillow estiver instalado.
- Se não for possível converter, salva o arquivo original e tenta salvar também um PNG quando possível.
Execução:
    python logos.py
Dependências (recomendadas):
    pip install requests yfinance pillow cairosvg
Se não quiser instalar cairosvg, o script ainda tentará salvar o arquivo original.
"""

import os
import sys
import time
import requests
import traceback

import yfinance as yf

# Tickers fornecidos (lista completa solicitada)
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

# Pasta de destino
LOGOS_DIR = "logos"
os.makedirs(LOGOS_DIR, exist_ok=True)

# Timeouts e retries
REQUEST_TIMEOUT = 12
RETRIES = 2
RETRY_DELAY = 1.2

# Tenta importar bibliotecas opcionais
try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except Exception:
    CAIROSVG_AVAILABLE = False

# Helpers
def safe_name(ticker: str) -> str:
    return "".join(c for c in ticker if c.isalnum() or c in ("-", "_")).upper()

def already_has_png(ticker_safe: str) -> bool:
    return os.path.exists(os.path.join(LOGOS_DIR, ticker_safe + ".png"))

def find_existing_file(ticker_safe: str):
    for ext in (".png", ".jpg", ".jpeg", ".svg", ".webp"):
        p = os.path.join(LOGOS_DIR, ticker_safe + ext)
        if os.path.exists(p):
            return p
    return None

def fetch_logo_url(ticker: str):
    try:
        info = yf.Ticker(f"{ticker}.SA").info
        if not info or not isinstance(info, dict):
            return None
        # yfinance costuma usar logo_url
        logo = info.get("logo_url") or info.get("logo") or info.get("logoURL")
        if logo and isinstance(logo, str) and logo.strip():
            return logo.strip()
    except Exception:
        return None
    return None

def infer_ext_from_content_type(ct: str, url: str) -> str:
    ct = (ct or "").lower()
    if "svg" in ct or url.lower().endswith(".svg"):
        return ".svg"
    if "png" in ct or url.lower().endswith(".png"):
        return ".png"
    if "jpeg" in ct or "jpg" in ct or url.lower().endswith((".jpg", ".jpeg")):
        return ".jpg"
    if "webp" in ct or url.lower().endswith(".webp"):
        return ".webp"
    return ".bin"

def download_bytes(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (LogoDownloader)"}
    attempt = 0
    while attempt <= RETRIES:
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200 and resp.content:
                return resp.content, resp.headers.get("Content-Type", "")
            else:
                attempt += 1
                time.sleep(RETRY_DELAY)
        except Exception:
            attempt += 1
            time.sleep(RETRY_DELAY)
    return None, None

def save_bytes_to_file(b: bytes, path: str):
    with open(path, "wb") as f:
        f.write(b)

def convert_svg_bytes_to_png_bytes(svg_bytes: bytes):
    if not CAIROSVG_AVAILABLE:
        return None
    try:
        png_bytes = cairosvg.svg2png(bytestring=svg_bytes)
        return png_bytes
    except Exception:
        return None

def convert_image_bytes_to_png_bytes(img_bytes: bytes, src_ext: str):
    if not PIL_AVAILABLE:
        return None
    try:
        from io import BytesIO
        bio = BytesIO(img_bytes)
        img = Image.open(bio).convert("RGBA")
        out = BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return None

def ensure_png_for_ticker(ticker: str, logo_url: str):
    ticker_safe = safe_name(ticker)
    png_path = os.path.join(LOGOS_DIR, ticker_safe + ".png")
    if already_has_png(ticker_safe):
        return {"ticker": ticker, "status": "exists", "path": png_path}

    # se já existe qualquer arquivo, tenta convertê-lo para png (se necessário)
    existing = find_existing_file(ticker_safe)
    if existing:
        ext = os.path.splitext(existing)[1].lower()
        if ext == ".png":
            return {"ticker": ticker, "status": "exists", "path": existing}
        # tenta converter arquivo existente
        try:
            with open(existing, "rb") as f:
                data = f.read()
            if ext == ".svg":
                png_bytes = convert_svg_bytes_to_png_bytes(data)
                if png_bytes:
                    save_bytes_to_file(png_bytes, png_path)
                    return {"ticker": ticker, "status": "converted_from_svg", "path": png_path}
            else:
                png_bytes = convert_image_bytes_to_png_bytes(data, ext)
                if png_bytes:
                    save_bytes_to_file(png_bytes, png_path)
                    return {"ticker": ticker, "status": "converted_from_image", "path": png_path}
        except Exception:
            pass
        # se não conseguiu converter, continua para tentar baixar direto

    # baixa bytes da URL
    b, content_type = download_bytes(logo_url)
    if not b:
        return {"ticker": ticker, "status": "download_failed", "path": None}

    ext = infer_ext_from_content_type(content_type, logo_url)
    # se for svg, tenta converter para png
    if ext == ".svg" or (b.strip().startswith(b"<") and b.strip().lower().find(b"<svg") != -1):
        # salva svg temporariamente
        tmp_svg = os.path.join(LOGOS_DIR, ticker_safe + ".svg")
        try:
            save_bytes_to_file(b, tmp_svg)
        except Exception:
            pass
        png_bytes = convert_svg_bytes_to_png_bytes(b)
        if png_bytes:
            save_bytes_to_file(png_bytes, png_path)
            return {"ticker": ticker, "status": "downloaded_converted_svg", "path": png_path}
        else:
            # se não conseguiu converter, mantém o svg salvo e tenta salvar também como .png via PIL (improvável)
            if PIL_AVAILABLE:
                png_bytes = convert_image_bytes_to_png_bytes(b, ".svg")
                if png_bytes:
                    save_bytes_to_file(png_bytes, png_path)
                    return {"ticker": ticker, "status": "downloaded_converted_svg_via_pil", "path": png_path}
            return {"ticker": ticker, "status": "downloaded_svg_saved", "path": tmp_svg}

    # se for imagem raster (png/jpg/webp), tenta converter para png
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".bin"):
        # tenta converter com PIL
        png_bytes = convert_image_bytes_to_png_bytes(b, ext)
        if png_bytes:
            save_bytes_to_file(png_bytes, png_path)
            return {"ticker": ticker, "status": "downloaded_converted_image", "path": png_path}
        else:
            # salva no formato original e, se for png, renomeia
            orig_path = os.path.join(LOGOS_DIR, ticker_safe + ext)
            try:
                save_bytes_to_file(b, orig_path)
                # se já era png, garantir nome .png
                if ext == ".png":
                    return {"ticker": ticker, "status": "downloaded_png", "path": orig_path}
                # tenta abrir com PIL e salvar como png
                if PIL_AVAILABLE:
                    png_bytes = convert_image_bytes_to_png_bytes(b, ext)
                    if png_bytes:
                        save_bytes_to_file(png_bytes, png_path)
                        return {"ticker": ticker, "status": "downloaded_saved_and_converted", "path": png_path}
                return {"ticker": ticker, "status": "downloaded_saved_original", "path": orig_path}
            except Exception:
                return {"ticker": ticker, "status": "save_failed", "path": None}

    return {"ticker": ticker, "status": "unknown_format", "path": None}

def main():
    total = len(TICKERS)
    print(f"Starting download/conversion for {total} tickers. PNGs will be saved in ./{LOGOS_DIR}/")
    print(f"Pillow available: {PIL_AVAILABLE}; cairosvg available: {CAIROSVG_AVAILABLE}")
    results = []
    for idx, t in enumerate(TICKERS, 1):
        ticker = t.strip().upper()
        ticker_safe = safe_name(ticker)
        try:
            # se já existe PNG, pula
            if already_has_png(ticker_safe):
                print(f"[{idx}/{total}] {ticker} - already has PNG, skipped")
                results.append({"ticker": ticker, "status": "exists", "path": os.path.join(LOGOS_DIR, ticker_safe + ".png")})
                continue

            logo_url = fetch_logo_url(ticker)
            if not logo_url:
                print(f"[{idx}/{total}] {ticker} - logo_url not found")
                results.append({"ticker": ticker, "status": "no_logo_url", "path": None})
                continue

            print(f"[{idx}/{total}] {ticker} - fetching {logo_url}")
            res = ensure_png_for_ticker(ticker, logo_url)
            status = res.get("status")
            path = res.get("path")
            print(f"    -> {status}; path: {path}")
            results.append(res)
        except Exception:
            traceback.print_exc()
            results.append({"ticker": ticker, "status": "error", "path": None})
    # resumo
    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    print("\nSummary:")
    for k, v in sorted(summary.items(), key=lambda x: x[0]):
        print(f"  {k}: {v}")
    print(f"\nLogos directory: {os.path.abspath(LOGOS_DIR)}")

if __name__ == "__main__":
    main()
