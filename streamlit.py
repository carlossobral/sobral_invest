import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import yfinance as yf
from io import BytesIO
import os
from datetime import datetime, timedelta

from usebolsai_client import buscar_acoes_usebolsai
from indicadores import calcular_indicadores
from checklist import checklist_buy_hold
from valuation import calcular_graham, calcular_graham_br, calcular_bazin, calcular_lynch, calcular_agf

# ─── Configuração ────────────────────────────────
st.set_page_config(
    page_title="Sobral Invest",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Helpers ───────────────────────────────────────────────────────────────

@st.cache_data
def obter_ibovespa():
    """Obtém dados do IBOVESPA (^BVSP) de hoje"""
    try:
        ibov = yf.Ticker("^BVSP")
        hist = ibov.history(period="1d")
        info = ibov.info
        
        if hist.empty:
            return None
        
        preco_fechamento = hist["Close"].iloc[-1]
        preco_abertura = hist["Open"].iloc[-1]
        variacao_pontos = preco_fechamento - preco_abertura
        variacao_percentual = (variacao_pontos / preco_abertura * 100) if preco_abertura != 0 else 0
        
        return {
            "preco": preco_fechamento,
            "variacao_pontos": variacao_pontos,
            "variacao_percentual": variacao_percentual,
            "preço_abertura": preco_abertura
        }
    except Exception as e:
        print(f"Erro ao obter IBOVESPA: {e}")
        return None


@st.cache_data
def obter_historico_ibovespa_30d():
    """Obtém histórico do IBOVESPA dos últimos 30 dias"""
    try:
        ibov = yf.Ticker("^BVSP")
        hist = ibov.history(period="30d")
        
        if hist.empty:
            return None
        
        # Reset index para ter data como coluna
        hist = hist.reset_index()
        hist["Date"] = pd.to_datetime(hist["Date"]).dt.strftime("%d/%m")
        
        return hist
    except Exception as e:
        print(f"Erro ao obter histórico IBOVESPA: {e}")
        return None


@st.cache_data
def obter_maiores_altas_baixas():
    """Obtém maiores altas e baixas do dia dos tickers B3"""
    try:
        # Lista dos principais tickers B3
        tickers_b3 = [
            "PETR4", "VALE3", "IVVB11", "ABEV3", "WEGE3", "ITUB4", "BBDC4",
            "MGLU3", "BBAS3", "LREN3", "USIM5", "GOLL4", "GGBR4", "PCAR3",
            "HYPE3", "MOVI3", "ASAI3", "SLCE3", "CPLE6", "RAIZ4", "B3SA3",
            "RRRP3", "MYPK3", "VIIA3", "TRPL4", "AMBP3", "ELET3", "CMIG4",
            "ENGI11", "BRFS3", "SUZB3", "KLABIN11", "RADL3", "RENT3", "POSI3",
            "NTCO3", "CSAN3", "CSNA3", "METAL5", "JBSS3", "BEEF3", "RAIL3",
            "LINX3", "ALSO11", "KLBN11", "TAEE11", "ENAT3", "EQTL3", "ELET6",
            "MXRF11", "MFII11", "SFIL11", "RBIV11", "FPRI11"
        ]
        
        dados_altas_baixas = []
        
        for ticker in tickers_b3:
            try:
                acao = yf.Ticker(f"{ticker}.SA")
                hist = acao.history(period="1d")
                
                if hist.empty:
                    continue
                
                preco_fechamento = hist["Close"].iloc[-1]
                preco_abertura = hist["Open"].iloc[-1]
                variacao = ((preco_fechamento - preco_abertura) / preco_abertura * 100) if preco_abertura != 0 else 0
                
                dados_altas_baixas.append({
                    "ticker": ticker,
                    "preco": preco_fechamento,
                    "variacao": variacao
                })
            except Exception:
                continue
        
        df_dados = pd.DataFrame(dados_altas_baixas)
        if df_dados.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        maiores_altas = df_dados.nlargest(10, "variacao")
        maiores_baixas = df_dados.nsmallest(10, "variacao")
        
        return maiores_altas, maiores_baixas
    except Exception as e:
        print(f"Erro ao obter altas/baixas: {e}")
        return pd.DataFrame(), pd.DataFrame()


def render_card_acao(ticker, preco, variacao):
    """Renderiza um card de ação com ticker, preço e variação - estilo Tradar"""
    cor_bg = '#10b981' if variacao >= 0 else '#ef4444'  # Verde ou vermelho
    cor_texto = '#10b981' if variacao >= 0 else '#ef4444'
    sinal = "+" if variacao >= 0 else ""
    
    return f"""
    <div style="
        background-color: rgba({('16, 185, 129' if variacao >= 0 else '239, 68, 68')}, 0.08);
        border: 1px solid rgba({('16, 185, 129' if variacao >= 0 else '239, 68, 68')}, 0.3);
        padding: 14px;
        border-radius: 8px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: all 0.2s ease;
    ">
        <div style="flex: 1;">
            <div style="font-weight: 700; font-size: 15px; color: #ffffff; margin-bottom: 4px;">
                {ticker}
            </div>
            <div style="font-size: 13px; color: #9ca3af;">
                R$ {preco:.2f}
            </div>
        </div>
        <div style="
            text-align: right;
            min-width: 70px;
        ">
            <div style="
                font-size: 18px;
                font-weight: 700;
                color: {cor_texto};
                margin-bottom: 4px;
            ">
                {sinal}{variacao:.2f}%
            </div>
        </div>
    </div>
    """


def formatar_percentual_dec(valor):
    try:
        if valor is None:
            return "—"
        valor = float(valor)
    except Exception:
        return "—"
    if abs(valor) <= 1:
        return f"{valor * 100:.2f}%"
    return f"{valor:.2f}%"


def obter_detalhes_ticker(ticker):
    try:
        info = yf.Ticker(f"{ticker}.SA").info
        name = info.get("shortName") or info.get("longName") or ticker
        pl = info.get("trailingPE")
        pvp = info.get("priceToBook")
        dy = info.get("dividendYield")
        roe = info.get("returnOnEquity")
        return {
            "name": name,
            "logo": info.get("logo_url"),
            "pl": pl,
            "pvp": pvp,
            "dy": dy,
            "roe": roe
        }
    except Exception:
        return {
            "name": ticker,
            "logo": None,
            "pl": None,
            "pvp": None,
            "dy": None,
            "roe": None
        }


def render_highlow_top_card(ticker, name, preco, variacao, pl, pvp, dy, roe, positive=True):
    cor = "#22c55e" if positive else "#ef4444"
    label = ''.join([part[0] for part in name.split()[:2]]).upper()
    logo_html = f"<div class='stock-logo'>{label}</div>"
    
    return f"""
    <div class='top-stock-card'>
        {logo_html}
        <div class='stock-name'>{name} - {ticker}</div>
        <div class='stock-subtitle'>Principais indicadores</div>
        <div class='metrics'>
            <div class='metric-item'>P/L<span>{pl if pl is not None else '—'}</span></div>
            <div class='metric-item'>P/VP<span>{pvp if pvp is not None else '—'}</span></div>
            <div class='metric-item'>DY<span>{formatar_percentual_dec(dy)}</span></div>
            <div class='metric-item'>ROE<span>{formatar_percentual_dec(roe)}</span></div>
        </div>
        <div class='stock-footer'>
            <div class='stock-price'>R$ {preco:.2f}</div>
            <div class='stock-variation {'positive' if positive else 'negative'}'>{variacao:+.2f}%</div>
        </div>
    </div>
    """


def render_highlow_line(ticker, preco, variacao, positive=True):
    cor_class = 'positive' if positive else 'negative'
    sinal = '+' if variacao >= 0 else ''
    return f"""
    <div class='stock-line'>
        <div class='stock-info'>
            <div class='stock-badge'>{ticker}</div>
            <div class='stock-meta'>
                <div>{ticker}</div>
                <span>R$ {preco:.2f}</span>
            </div>
        </div>
        <div class='stock-variation {cor_class}'>{sinal}{variacao:.2f}%</div>
    </div>
    """


# ─── PÁGINA INICIAL ───────────────────────────────────────────────────────────────

st.markdown("# 📊 Sobral Invest")
st.markdown("**Acompanhe em tempo real o mercado da B3**")
st.markdown("---")

# Seção IBOVESPA
st.markdown("## 📈 IBOVESPA")

ibov_dados = obter_ibovespa()

if ibov_dados:
    # CSS para o card e métricas
    st.markdown("""
    <style>
    .ibov-card {
        background: #071114;
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 24px;
        padding: 24px;
        margin: 18px 0;
    }
    .ibov-title {
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: #94a3b8;
        margin-bottom: 18px;
    }
    .ibov-value {
        font-size: 64px;
        font-weight: 800;
        color: #ffffff;
        line-height: 0.9;
        margin-bottom: 18px;
    }
    .ibov-value span {
        font-size: 22px;
        font-weight: 600;
        color: #6b7280;
        margin-left: 8px;
    }
    .ibov-change {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-top: 10px;
    }
    .ibov-change-pill {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border-radius: 999px;
        padding: 10px 16px;
        font-weight: 700;
        display: inline-block;
    }
    .ibov-change-text {
        color: #94a3b8;
        font-weight: 600;
    }
    .ibov-chart-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        padding: 16px;
    }
    .ibov-chart-title {
        color: #94a3b8;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='ibov-card'>", unsafe_allow_html=True)
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("<div class='ibov-title'>Ibovespa</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='ibov-value'>{ibov_dados['preco']:,.2f}<span>pts</span></div>",
            unsafe_allow_html=True
        )

        variacao = ibov_dados["variacao_percentual"]
        variacao_pontos = ibov_dados["variacao_pontos"]
        sinal = "+" if variacao >= 0 else ""
        cor_classe = "ibov-change-pill"
        st.markdown(
            "<div class='ibov-change'>"
            f"<div class='{cor_classe}'>{sinal}{variacao:.2f}%</div>"
            f"<div class='ibov-change-text'>{sinal}{variacao_pontos:,.2f} pts</div>"
            "</div>",
            unsafe_allow_html=True
        )

    with col_right:
        st.markdown("<div class='ibov-chart-card'>", unsafe_allow_html=True)
        st.markdown("<div class='ibov-chart-title'>Últimos 30 dias</div>", unsafe_allow_html=True)
        hist_30d = obter_historico_ibovespa_30d()

        if hist_30d is not None and not hist_30d.empty:
            fig = px.line(
                hist_30d,
                x="Date",
                y="Close",
                title="",
                labels={"Close": "", "Date": ""},
                markers=False,
                height=220
            )
            fig.update_traces(line=dict(color="#10b981", width=2))
            fig.update_layout(
                hovermode="x unified",
                template="plotly_dark",
                xaxis_title="",
                yaxis_title="",
                font=dict(size=10),
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, visible=False),
                yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, visible=False)
            )
            components.html(fig.to_html(full_html=False, include_plotlyjs='cdn'), height=240)
        else:
            st.info("⏳ Carregando gráfico...")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("⏳ Carregando dados do IBOVESPA...")

st.markdown("---")

st.markdown("""
<style>
.highlow-container {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 24px;
}
.highlow-column {
    background: #071218;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 24px;
    padding: 22px;
}
.highlow-column h3 {
    margin-top: 0;
    margin-bottom: 18px;
    font-size: 18px;
}
.highlow-column.positive h3 {
    color: #22c55e;
}
.highlow-column.negative h3 {
    color: #ef4444;
}
.top-stock-card {
    background: #0e1a25;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px;
    padding: 20px;
    margin-bottom: 20px;
}
.stock-logo {
    width: 56px;
    height: 56px;
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.95);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-weight: 800;
    font-size: 18px;
    margin-bottom: 18px;
}
.stock-name {
    font-size: 16px;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 4px;
}
.stock-subtitle {
    color: #94a3b8;
    font-size: 13px;
    margin-bottom: 18px;
}
.metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 20px;
}
.metric-item {
    color: #94a3b8;
    font-size: 12px;
}
.metric-item span {
    display: block;
    margin-top: 6px;
    color: #f8fafc;
    font-weight: 700;
    font-size: 14px;
}
.stock-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
}
.stock-price {
    color: #f8fafc;
    font-size: 18px;
    font-weight: 700;
}
.stock-variation.positive {
    color: #22c55e;
}
.stock-variation.negative {
    color: #ef4444;
}
.stock-line {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-top: 1px solid rgba(255,255,255,0.05);
}
.stock-line:first-child {
    border-top: none;
}
.stock-info {
    display: flex;
    align-items: center;
    gap: 12px;
}
.stock-badge {
    width: 36px;
    height: 36px;
    border-radius: 12px;
    background: rgba(255,255,255,0.05);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #f8fafc;
    font-weight: 700;
    font-size: 13px;
}
.stock-meta {
    display: flex;
    flex-direction: column;
}
.stock-meta div {
    color: #f8fafc;
    font-weight: 700;
    font-size: 14px;
}
.stock-meta span,
.stock-price-small {
    color: #94a3b8;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

# Seção Maiores Altas e Baixas
st.markdown("## 📊 Maiores Altas / Maiores Baixas do Dia")

maiores_altas, maiores_baixas = obter_maiores_altas_baixas()

if not maiores_altas.empty and not maiores_baixas.empty:
    col_altas, col_baixas = st.columns(2)

    with col_altas:
        html = "<div class='highlow-column positive'>"
        html += "<h3>Maiores Altas</h3>"
        top = maiores_altas.iloc[0]
        info = obter_detalhes_ticker(top["ticker"])
        html += render_highlow_top_card(
            top["ticker"],
            info["name"],
            top["preco"],
            top["variacao"],
            info["pl"],
            info["pvp"],
            info["dy"],
            info["roe"],
            positive=True
        )
        for _, row in maiores_altas.iloc[1:7].iterrows():
            html += render_highlow_line(row["ticker"], row["preco"], row["variacao"], positive=True)
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    with col_baixas:
        html = "<div class='highlow-column negative'>"
        html += "<h3>Maiores Baixas</h3>"
        top = maiores_baixas.iloc[0]
        info = obter_detalhes_ticker(top["ticker"])
        html += render_highlow_top_card(
            top["ticker"],
            info["name"],
            top["preco"],
            top["variacao"],
            info["pl"],
            info["pvp"],
            info["dy"],
            info["roe"],
            positive=False
        )
        for _, row in maiores_baixas.iloc[1:7].iterrows():
            html += render_highlow_line(row["ticker"], row["preco"], row["variacao"], positive=False)
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
else:
    st.info("⏳ Carregando dados das ações...")

st.markdown("---")

# Seção Busca de Ticker (análise detalhada)
st.markdown("## 🔎 Buscar Ativo para Análise Detalhada")

ticker_options = []
if os.path.exists("ativos.xlsx"):
    try:
        preview_df = pd.read_excel("ativos.xlsx", sheet_name="Ativos")
        ticker_options = sorted(preview_df["Ticker"].dropna().astype(str).unique().tolist())
    except Exception:
        ticker_options = []

if ticker_options:
    selected_ticker = st.selectbox(
        "Digite ou selecione um ticker",
        options=[""] + ticker_options,
        index=0,
        placeholder="Ex: PETR4, VALE3, ITUB4..."
    )
else:
    st.info("📁 Nenhum ticker disponível. Execute `app.py` para gerar análise da B3.")
    selected_ticker = ""
