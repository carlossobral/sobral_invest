# logos.py
"""
Baixa logos para a lista de tickers e garante que exista um arquivo PNG para cada ticker em ./logos/.
Fluxo por ticker:
 1. tenta logo_url via yfinance
 2. se não houver, tenta obter website via yfinance e usar Clearbit (logo.clearbit.com/{domain})
 3. se ainda não houver imagem, gera um PNG com as INICIAIS do ticker (fallback local, sem custo)
Conversões:
 - SVG -> PNG via cairosvg (se instalado)
 - Outros formatos -> PNG via Pillow (se instalado)
Uso:
    python logos.py
Dependências recomendadas (opcionais para melhores resultados):
    pip install requests yfinance pillow cairosvg
Se não instalar cairosvg/Pillow, o script ainda gera PNGs com iniciais.
"""

import os
import time
import requests
import traceback
from urllib.parse import urlparse

import yfinance as yf

# Lista completa de tickers solicitada
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

# bibliotecas opcionais
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except Exception:
    CAIROSVG_AVAILABLE = False

# helpers
def safe_name(ticker: str) -> str:
    return "".join(c for c in ticker if c.isalnum() or c in ("-", "_")).upper()

def png_path_for(ticker_safe: str) -> str:
    return os.path.join(LOGOS_DIR, ticker_safe + ".png")

def any_existing_file(ticker_safe: str):
    for ext in (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"):
        p = os.path.join(LOGOS_DIR, ticker_safe + ext)
        if os.path.exists(p):
            return p
    return None

def fetch_yfinance_info(ticker: str):
    try:
        tkr = yf.Ticker(f"{ticker}.SA")
        info = tkr.info or {}
        return info
    except Exception:
        return {}

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

def infer_ext(content_type: str, url: str):
    ct = (content_type or "").lower()
    if "svg" in ct or url.lower().endswith(".svg"):
        return ".svg"
    if "png" in ct or url.lower().endswith(".png"):
        return ".png"
    if "jpeg" in ct or "jpg" in ct or url.lower().endswith((".jpg", ".jpeg")):
        return ".jpg"
    if "webp" in ct or url.lower().endswith(".webp"):
        return ".webp"
    return ".bin"

def save_bytes(path: str, b: bytes):
    with open(path, "wb") as f:
        f.write(b)

def convert_svg_to_png_bytes(svg_bytes: bytes):
    if not CAIROSVG_AVAILABLE:
        return None
    try:
        png = cairosvg.svg2png(bytestring=svg_bytes)
        return png
    except Exception:
        return None

def convert_image_bytes_to_png_bytes(img_bytes: bytes):
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

def try_clearbit_logo_from_website(website: str):
    # extrai domínio e usa logo.clearbit.com/{domain}
    try:
        parsed = urlparse(website)
        domain = parsed.netloc or parsed.path
        domain = domain.split(":")[0]
        if not domain:
            return None
        return f"https://logo.clearbit.com/{domain}"
    except Exception:
        return None

def generate_initials_png(ticker: str, size=128, bg_color="#0f172a", fg_color="#ffffff"):
    """
    Gera um PNG com as iniciais do ticker (ex: 'PETR4' -> 'PE' ou 'P4' dependendo).
    Retorna bytes PNG.
    """
    if not PIL_AVAILABLE:
        return None
    try:
        from io import BytesIO
        # tenta extrair 2 caracteres representativos: letras iniciais do nome do ticker
        label = "".join([c for c in ticker if c.isalpha()])[:2].upper()
        if not label:
            label = ticker[:2].upper()
        img = Image.new("RGBA", (size, size), bg_color)
        draw = ImageDraw.Draw(img)
        # tenta fonte padrão; se não houver, usa fonte básica
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(size * 0.45))
        except Exception:
            font = ImageFont.load_default()
        w, h = draw.textsize(label, font=font)
        draw.text(((size - w) / 2, (size - h) / 2 - 4), label, font=font, fill=fg_color)
        out = BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return None

def ensure_png_for_ticker(ticker: str):
    ticker_safe = safe_name(ticker)
    png_path = png_path_for(ticker_safe)
    if os.path.exists(png_path):
        return {"ticker": ticker, "status": "exists", "path": png_path}

    # 1) tenta obter info yfinance
    info = fetch_yfinance_info(ticker)
    logo_url = None
    website = None
    if isinstance(info, dict):
        logo_url = info.get("logo_url") or info.get("logo") or info.get("logoURL")
        website = info.get("website") or info.get("website_url") or info.get("url")

    # 2) se não houver logo_url, tenta Clearbit via website
    tried_urls = []
    if not logo_url and website:
        cb = try_clearbit_logo_from_website(website)
        if cb:
            logo_url = cb

    # 3) se ainda não houver, tenta Clearbit com ticker domain common patterns (ex: empresa.com.br)
    # (opcional) - não forçar domínios inventados

    # 4) se já existe arquivo salvo em outro formato, tenta converter
    existing = any_existing_file(ticker_safe)
    if existing:
        ext = os.path.splitext(existing)[1].lower()
        try:
            with open(existing, "rb") as f:
                b = f.read()
            if ext == ".svg":
                png_bytes = convert_svg_to_png_bytes(b)
                if png_bytes:
                    save_bytes(png_path, png_bytes)
                    return {"ticker": ticker, "status": "converted_existing_svg", "path": png_path}
            else:
                png_bytes = convert_image_bytes_to_png_bytes(b)
                if png_bytes:
                    save_bytes(png_path, png_bytes)
                    return {"ticker": ticker, "status": "converted_existing_image", "path": png_path}
        except Exception:
            pass
        # se não conseguiu converter, continua para tentar baixar

    # 5) tenta baixar logo_url (se houver)
    if logo_url:
        tried_urls.append(logo_url)
        b, ct = try_download(logo_url)
        if b:
            ext = infer_ext(ct, logo_url)
            # se svg, tenta converter
            if ext == ".svg" or (b.strip().startswith(b"<") and b.strip().lower().find(b"<svg") != -1):
                png_bytes = convert_svg_to_png_bytes(b)
                if png_bytes:
                    save_bytes(png_path, png_bytes)
                    return {"ticker": ticker, "status": "downloaded_converted_svg", "path": png_path}
                else:
                    # salva svg como fallback
                    svg_path = os.path.join(LOGOS_DIR, ticker_safe + ".svg")
                    save_bytes(svg_path, b)
                    # tenta converter com PIL (improvável)
                    png_bytes = convert_image_bytes_to_png_bytes(b)
                    if png_bytes:
                        save_bytes(png_path, png_bytes)
                        return {"ticker": ticker, "status": "downloaded_svg_converted_via_pil", "path": png_path}
                    return {"ticker": ticker, "status": "downloaded_svg_saved", "path": svg_path}
            else:
                # raster image: tenta converter para PNG
                png_bytes = convert_image_bytes_to_png_bytes(b)
                if png_bytes:
                    save_bytes(png_path, png_bytes)
                    return {"ticker": ticker, "status": "downloaded_converted_image", "path": png_path}
                else:
                    # salva original e, se for png, renomeia
                    ext = infer_ext(ct, logo_url)
                    orig_path = os.path.join(LOGOS_DIR, ticker_safe + ext)
                    save_bytes(orig_path, b)
                    # tenta converter com PIL agora
                    png_bytes = convert_image_bytes_to_png_bytes(b)
                    if png_bytes:
                        save_bytes(png_path, png_bytes)
                        return {"ticker": ticker, "status": "downloaded_saved_and_converted", "path": png_path}
                    return {"ticker": ticker, "status": "downloaded_saved_original", "path": orig_path}

    # 6) se tudo falhar, gera PNG com iniciais (fallback local, sem custo)
    png_bytes = generate_initials_png(ticker, size=128)
    if png_bytes:
        save_bytes(png_path, png_bytes)
        return {"ticker": ticker, "status": "generated_initials", "path": png_path}
    else:
        # se Pillow não disponível, cria um arquivo PNG mínimo com bytes vazios (não ideal)
        try:
            with open(png_path, "wb") as f:
                f.write(b"")
            return {"ticker": ticker, "status": "generated_empty_png", "path": png_path}
        except Exception:
            return {"ticker": ticker, "status": "failed", "path": None}

def main():
    total = len(TICKERS)
    print(f"Começando: {total} tickers. Salvando PNGs em ./{LOGOS_DIR}/")
    print(f"Pillow disponível: {PIL_AVAILABLE}; cairosvg disponível: {CAIROSVG_AVAILABLE}")
    results = []
    for idx, t in enumerate(TICKERS, 1):
        ticker = t.strip().upper()
        try:
            res = ensure_png_for_ticker(ticker)
            status = res.get("status")
            path = res.get("path")
            print(f"[{idx}/{total}] {ticker} - {status} -> {path}")
            results.append(res)
        except Exception:
            traceback.print_exc()
            results.append({"ticker": ticker, "status": "error", "path": None})
    # resumo
    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    print("\nResumo:")
    for k, v in sorted(summary.items()):
        print(f"  {k}: {v}")
    print(f"\nDiretório de logos: {os.path.abspath(LOGOS_DIR)}")

if __name__ == "__main__":
    main()
