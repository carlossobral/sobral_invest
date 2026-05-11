# logo_get.py
import os
from pathlib import Path
import streamlit as st

LOGOS_DIR = Path("logos")

def ticker_to_safe(ticker: str) -> str:
    return "".join(c for c in ticker if c.isalnum() or c in ("-", "_")).upper()

def get_logo_path(ticker: str) -> Path | None:
    """Retorna o caminho da logo local (PNG ou SVG) se existir."""
    t = ticker_to_safe(ticker)
    png = LOGOS_DIR / f"{t}.png"
    svg = LOGOS_DIR / f"{t}.svg"
    if png.exists() and png.stat().st_size > 0:
        return png
    if svg.exists() and svg.stat().st_size > 0:
        return svg
    return None

def render_logo(ticker: str, width: int = 48):
    """Renderiza a logo no Streamlit, se existir."""
    path = get_logo_path(ticker)
    if path:
        if path.suffix.lower() == ".png":
            st.image(str(path), width=width)
        elif path.suffix.lower() == ".svg":
            # Streamlit não renderiza SVG direto, usamos markdown com <img>
            st.markdown(
                f'<img src="{path.as_posix()}" width="{width}" style="vertical-align:middle;">',
                unsafe_allow_html=True
            )
    else:
        # Placeholder simples se não houver logo
        st.markdown(
            f'<div style="width:{width}px;height:{width}px;background:#ccc;display:inline-block;"></div>',
            unsafe_allow_html=True
        )
