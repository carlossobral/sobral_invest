import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import textwrap
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


def obter_maiores_altas_baixas():
    """Obtém maiores altas e baixas do dia dos tickers B3"""
    try:
        # Lista dos principais tickers B3
        tickers_b3 = [
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
    
    return textwrap.dedent(f"""
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
    """)


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
    
    return textwrap.dedent(f"""
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
    """)


def render_highlow_line(ticker, preco, variacao, positive=True):
    cor_class = 'positive' if positive else 'negative'
    sinal = '+' if variacao >= 0 else ''
    return textwrap.dedent(f"""
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
    """)


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
        min-height: 300px;
    }
    .ibov-chart-title {
        color: #94a3b8;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1.4, 1])

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
        st.markdown("**Últimos 30 dias**")
        hist_30d = obter_historico_ibovespa_30d()

        if hist_30d is not None and not hist_30d.empty:
            fig = px.line(
                hist_30d,
                x="Date",
                y="Close",
                title="",
                labels={"Close": "", "Date": ""},
                markers=False,
                height=300
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
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("⏳ Carregando gráfico...")

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
