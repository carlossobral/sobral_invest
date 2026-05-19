import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import os
import requests
import time

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SOBRAL Invest",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .positive { color: #00c853; font-weight: 600; }
    .negative { color: #ff1744; font-weight: 600; }
    .neutral { color: #ffab00; font-weight: 600; }
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .score-high { background: #e8f5e9; color: #2e7d32; }
    .score-medium { background: #fff3e0; color: #ef6c00; }
    .score-low { background: #ffebee; color: #c62828; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #667eea !important;
        color: white !important;
    }
    .info-box {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
    }
    .checklist-item {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        background: #f8f9fa;
    }
    .checklist-pass { border-left: 4px solid #00c853; }
    .checklist-fail { border-left: 4px solid #ff1744; }
</style>
""", unsafe_allow_html=True)

# ─── CARREGAR DADOS ───────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    """Carrega ativos.xlsx do repositório GitHub"""
    try:
        df = pd.read_excel("ativos.xlsx", sheet_name="Dados")
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar ativos.xlsx: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_yfinance_data():
    """Busca Ibovespa e cotações via yfinance"""
    try:
        import yfinance as yf

        # Ibovespa
        ibov = yf.Ticker("^BVSP")
        ibov_hist = ibov.history(period="1y")
        ibov_info = ibov.info

        ibov_data = {
            "price": ibov_info.get("regularMarketPrice", ibov_info.get("previousClose", 0)),
            "change": ibov_info.get("regularMarketChange", 0),
            "change_pct": ibov_info.get("regularMarketChangePercent", 0),
            "prev_close": ibov_info.get("previousClose", 0),
            "high": ibov_info.get("regularMarketDayHigh", 0),
            "low": ibov_info.get("regularMarketDayLow", 0),
            "volume": ibov_info.get("regularMarketVolume", 0),
            "history": ibov_hist
        }

        return {"ibov": ibov_data, "available": True}
    except Exception as e:
        return {"ibov": None, "available": False, "error": str(e)}

@st.cache_data(ttl=300)
def get_stock_changes(tickers_list):
    """Busca variação de preço para lista de tickers via yfinance"""
    try:
        import yfinance as yf

        # Buscar em batch
        tickers_str = " ".join(tickers_list)
        data = yf.download(tickers_str, period="2d", progress=False, threads=True)

        results = []
        for ticker in tickers_list:
            try:
                if len(tickers_list) == 1:
                    close_today = data["Close"].iloc[-1]
                    close_yesterday = data["Close"].iloc[-2]
                else:
                    close_today = data["Close"][ticker].iloc[-1]
                    close_yesterday = data["Close"][ticker].iloc[-2]

                change_pct = ((close_today - close_yesterday) / close_yesterday) * 100

                results.append({
                    "ticker": ticker,
                    "price": close_today,
                    "change_pct": change_pct
                })
            except:
                continue

        return pd.DataFrame(results)
    except Exception as e:
        return pd.DataFrame()

# ─── FUNÇÕES DE ANÁLISE ───────────────────────────────────────────────────────
def calcular_preco_justo_graham(row):
    """Preço Justo de Graham = √(22.5 × VPA × LPA)"""
    vpa = row.get("VPA", 0)
    lpa = row.get("LPA", 0)
    if vpa > 0 and lpa > 0:
        return (22.5 * vpa * lpa) ** 0.5
    return None

def calcular_preco_justo_bazin(row, dy_alvo=0.06):
    """Preço Justo de Bazin = Dividendo Anual / DY Alvo"""
    dy = row.get("DY", 0)
    preco = row.get("Preco", 0)
    if dy > 0 and preco > 0:
        div_anual = preco * (dy / 100)
        return div_anual / dy_alvo
    return None

def calcular_upside(preco_atual, preco_justo):
    if preco_justo and preco_atual > 0:
        return ((preco_justo - preco_atual) / preco_atual) * 100
    return None

def classificar_score(score):
    if score >= 7:
        return "score-high", "Excelente"
    elif score >= 4:
        return "score-medium", "Bom"
    else:
        return "score-low", "Fraco"

def formatar_moeda(valor):
    if pd.isna(valor) or valor is None:
        return "N/A"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_pct(valor):
    if pd.isna(valor) or valor is None:
        return "N/A"
    return f"{valor:.2f}%"

def formatar_numero(valor, decimais=2):
    if pd.isna(valor) or valor is None:
        return "N/A"
    return f"{valor:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h1 style='text-align:center; color:#667eea;'>📈 SOBRAL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#888; font-size:0.9rem;'>Plataforma de Análise Fundamentalista</p>", unsafe_allow_html=True)
    st.divider()

    page = st.radio(
        "Navegação",
        ["🏠 Dashboard", "🔍 Análise de Ativo", "📊 Rankings", "📈 Comparativo", "⚙️ Configurações"],
        label_visibility="collapsed"
    )

    st.divider()
    st.markdown("<p style='text-align:center; color:#888; font-size:0.75rem;'>Desenvolvido por Carlos Sobral</p>", unsafe_allow_html=True)

# ─── CARREGAR DADOS GLOBAIS ───────────────────────────────────────────────────
df = load_data()

if df.empty:
    st.error("❌ Não foi possível carregar os dados. Verifique se o arquivo ativos.xlsx está no repositório.")
    st.stop()

# ─── PÁGINA: DASHBOARD ────────────────────────────────────────────────────────
if page == "🏠 Dashboard":
    st.markdown("<div class='main-header'>📈 SOBRAL Invest</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Acompanhe em tempo real o mercado B3</div>", unsafe_allow_html=True)

    # ─── IBOVESPA ─────────────────────────────────────────────────────────────
    yf_data = get_yfinance_data()

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.subheader("📊 Ibovespa")

        if yf_data["available"] and yf_data["ibov"]:
            ibov = yf_data["ibov"]
            price = ibov["price"] or ibov["prev_close"]
            change = ibov["change"]
            change_pct = ibov["change_pct"]

            color = "positive" if change >= 0 else "negative"
            sign = "+" if change >= 0 else ""

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                        border-radius: 15px; padding: 25px; color: white;">
                <div style="font-size: 0.9rem; opacity: 0.8; margin-bottom: 5px;">IBOVESPA</div>
                <div style="font-size: 2.5rem; font-weight: 700;">{formatar_numero(price, 2)} pts</div>
                <div style="font-size: 1.2rem;" class="{color}">{sign}{formatar_numero(change, 2)} pts ({sign}{change_pct:.2f}%)</div>
                <div style="font-size: 0.8rem; opacity: 0.6; margin-top: 10px;">
                    Máx: {formatar_numero(ibov['high'], 2)} | Mín: {formatar_numero(ibov['low'], 2)} | Vol: {formatar_numero(ibov['volume']/1e6, 1)}M
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Gráfico do Ibovespa
            if ibov["history"] is not None and not ibov["history"].empty:
                hist = ibov["history"].reset_index()
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist["Date"],
                    y=hist["Close"],
                    mode="lines",
                    line=dict(color="#667eea", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(102, 126, 234, 0.1)",
                    name="Ibovespa"
                ))
                fig.update_layout(
                    height=300,
                    margin=dict(l=0, r=0, t=0, b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=False, showticklabels=False),
                    yaxis=dict(showgrid=False, showticklabels=False),
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            # Fallback: usar dados do ativos.xlsx
            st.info("ℹ️ Dados do Ibovespa via yfinance indisponíveis. Usando dados do arquivo local.")

            # Simular Ibovespa com média do mercado
            if "Variacao" in df.columns:
                var_media = df["Variacao"].mean()
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                            border-radius: 15px; padding: 25px; color: white;">
                    <div style="font-size: 0.9rem; opacity: 0.8; margin-bottom: 5px;">IBOVESPA (Simulado)</div>
                    <div style="font-size: 2.5rem; font-weight: 700;">—</div>
                    <div style="font-size: 1.2rem;" class="{'positive' if var_media >= 0 else 'negative'}">
                        Variação média do mercado: {var_media:+.2f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with col2:
        st.subheader("🔥 Maiores Altas")

        # Tentar yfinance primeiro
        if yf_data["available"]:
            # Pegar top 50 tickers do ativos.xlsx para buscar variação
            top_tickers = df.nlargest(50, "Volume" if "Volume" in df.columns else "Score CS")["Ticker"].tolist()
            changes_df = get_stock_changes(top_tickers)

            if not changes_df.empty:
                altas = changes_df.nlargest(7, "change_pct")
                for _, row in altas.iterrows():
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; 
                                padding: 8px 12px; margin: 4px 0; background: #f8f9fa; 
                                border-radius: 8px; border-left: 4px solid #00c853;">
                        <div>
                            <span style="font-weight: 700; font-size: 1rem;">{row['ticker']}</span>
                            <span style="font-size: 0.8rem; color: #666;">{df[df['Ticker']==row['ticker']]['Nome'].values[0] if len(df[df['Ticker']==row['ticker']]) > 0 else ''}</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-weight: 700; color: #00c853;">+{row['change_pct']:.2f}%</div>
                            <div style="font-size: 0.8rem; color: #666;">R$ {row['price']:.2f}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Fallback para ativos.xlsx
                if "Variacao" in df.columns:
                    altas = df.nlargest(7, "Variacao")[["Ticker", "Nome", "Variacao", "Preco"]]
                    for _, row in altas.iterrows():
                        st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; align-items:center; 
                                    padding: 8px 12px; margin: 4px 0; background: #f8f9fa; 
                                    border-radius: 8px; border-left: 4px solid #00c853;">
                            <div>
                                <span style="font-weight: 700; font-size: 1rem;">{row['Ticker']}</span>
                                <span style="font-size: 0.8rem; color: #666;">{row['Nome']}</span>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-weight: 700; color: #00c853;">{row['Variacao']:+.2f}%</div>
                                <div style="font-size: 0.8rem; color: #666;">R$ {row['Preco']:.2f}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("yfinance indisponível. Dados do arquivo local.")
            if "Variacao" in df.columns:
                altas = df.nlargest(7, "Variacao")[["Ticker", "Nome", "Variacao", "Preco"]]
                for _, row in altas.iterrows():
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; 
                                padding: 8px 12px; margin: 4px 0; background: #f8f9fa; 
                                border-radius: 8px; border-left: 4px solid #00c853;">
                        <div>
                            <span style="font-weight: 700; font-size: 1rem;">{row['Ticker']}</span>
                            <span style="font-size: 0.8rem; color: #666;">{row['Nome']}</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-weight: 700; color: #00c853;">{row['Variacao']:+.2f}%</div>
                            <div style="font-size: 0.8rem; color: #666;">R$ {row['Preco']:.2f}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    with col3:
        st.subheader("❄️ Maiores Baixas")

        if yf_data["available"]:
            if not changes_df.empty:
                baixas = changes_df.nsmallest(7, "change_pct")
                for _, row in baixas.iterrows():
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; 
                                padding: 8px 12px; margin: 4px 0; background: #f8f9fa; 
                                border-radius: 8px; border-left: 4px solid #ff1744;">
                        <div>
                            <span style="font-weight: 700; font-size: 1rem;">{row['ticker']}</span>
                            <span style="font-size: 0.8rem; color: #666;">{df[df['Ticker']==row['ticker']]['Nome'].values[0] if len(df[df['Ticker']==row['ticker']]) > 0 else ''}</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-weight: 700; color: #ff1744;">{row['change_pct']:.2f}%</div>
                            <div style="font-size: 0.8rem; color: #666;">R$ {row['price']:.2f}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                if "Variacao" in df.columns:
                    baixas = df.nsmallest(7, "Variacao")[["Ticker", "Nome", "Variacao", "Preco"]]
                    for _, row in baixas.iterrows():
                        st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; align-items:center; 
                                    padding: 8px 12px; margin: 4px 0; background: #f8f9fa; 
                                    border-radius: 8px; border-left: 4px solid #ff1744;">
                            <div>
                                <span style="font-weight: 700; font-size: 1rem;">{row['Ticker']}</span>
                                <span style="font-size: 0.8rem; color: #666;">{row['Nome']}</span>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-weight: 700; color: #ff1744;">{row['Variacao']:+.2f}%</div>
                                <div style="font-size: 0.8rem; color: #666;">R$ {row['Preco']:.2f}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("yfinance indisponível. Dados do arquivo local.")
            if "Variacao" in df.columns:
                baixas = df.nsmallest(7, "Variacao")[["Ticker", "Nome", "Variacao", "Preco"]]
                for _, row in baixas.iterrows():
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; 
                                padding: 8px 12px; margin: 4px 0; background: #f8f9fa; 
                                border-radius: 8px; border-left: 4px solid #ff1744;">
                        <div>
                            <span style="font-weight: 700; font-size: 1rem;">{row['Ticker']}</span>
                            <span style="font-size: 0.8rem; color: #666;">{row['Nome']}</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-weight: 700; color: #ff1744;">{row['Variacao']:+.2f}%</div>
                            <div style="font-size: 0.8rem; color: #666;">R$ {row['Preco']:.2f}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    st.divider()

    # ─── RANKINGS RÁPIDOS ─────────────────────────────────────────────────────
    st.subheader("🏆 Rankings Rápidos")

    tabs = st.tabs(["Score CS", "DY", "P/L", "ROE", "Graham"])

    with tabs[0]:
        if "Score CS" in df.columns:
            top = df.nlargest(10, "Score CS")[["Ticker", "Nome", "Score CS", "Preco", "Setor"]]
            fig = px.bar(top, x="Score CS", y="Ticker", orientation="h", 
                        color="Score CS", color_continuous_scale="Greens",
                        text="Score CS", hover_data=["Nome", "Setor", "Preco"])
            fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        if "DY" in df.columns:
            top = df.nlargest(10, "DY")[["Ticker", "Nome", "DY", "Preco"]]
            fig = px.bar(top, x="DY", y="Ticker", orientation="h",
                        color="DY", color_continuous_scale="Blues",
                        text=top["DY"].apply(lambda x: f"{x:.2f}%"))
            fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        if "PL" in df.columns:
            top = df.nsmallest(10, "PL")[["Ticker", "Nome", "PL", "Preco"]]
            fig = px.bar(top, x="PL", y="Ticker", orientation="h",
                        color="PL", color_continuous_scale="RdYlGn_r",
                        text=top["PL"].apply(lambda x: f"{x:.2f}x"))
            fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        if "ROE" in df.columns:
            top = df.nlargest(10, "ROE")[["Ticker", "Nome", "ROE", "Preco"]]
            fig = px.bar(top, x="ROE", y="Ticker", orientation="h",
                        color="ROE", color_continuous_scale="Greens",
                        text=top["ROE"].apply(lambda x: f"{x:.1f}%"))
            fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        if "Upside_Graham" in df.columns:
            top = df.nlargest(10, "Upside_Graham")[["Ticker", "Nome", "Upside_Graham", "Preco"]]
            fig = px.bar(top, x="Upside_Graham", y="Ticker", orientation="h",
                        color="Upside_Graham", color_continuous_scale="Greens",
                        text=top["Upside_Graham"].apply(lambda x: f"{x:.1f}%"))
            fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

# ─── PÁGINA: ANÁLISE DE ATIVO ─────────────────────────────────────────────────
elif page == "🔍 Análise de Ativo":
    st.markdown("<div class='main-header'>🔍 Análise de Ativo</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Análise fundamentalista completa estilo Investidor10</div>", unsafe_allow_html=True)

    ticker = st.selectbox("Selecione um ativo", options=sorted(df["Ticker"].tolist()), index=0)

    if ticker:
        ativo = df[df["Ticker"] == ticker].iloc[0]

        # ─── HEADER DO ATIVO ──────────────────────────────────────────────────
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        with col1:
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:15px;">
                <div style="width:60px; height:60px; background:linear-gradient(135deg, #667eea, #764ba2); 
                            border-radius:12px; display:flex; align-items:center; justify-content:center; 
                            color:white; font-size:1.5rem; font-weight:700;">
                    {ticker[:2]}
                </div>
                <div>
                    <div style="font-size:1.5rem; font-weight:700;">{ticker}</div>
                    <div style="font-size:0.9rem; color:#666;">{ativo.get('Nome', '')}</div>
                    <div style="font-size:0.8rem; color:#888;">{ativo.get('Setor', '')} › {ativo.get('SubSetor', '')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            preco = ativo.get("Preco", 0)
            st.metric("Preço", formatar_moeda(preco))

        with col3:
            if "Variacao" in ativo:
                var = ativo["Variacao"]
                st.metric("Variação", f"{var:+.2f}%", delta=f"{var:+.2f}%")

        with col4:
            if "Score CS" in ativo:
                score = ativo["Score CS"]
                score_class, score_label = classificar_score(score)
                st.markdown(f"""
                <div style="text-align:center;">
                    <div style="font-size:0.8rem; color:#666;">Score CS</div>
                    <div class="score-badge {score_class}" style="font-size:1.5rem; padding:8px 20px;">
                        {score:.1f}
                    </div>
                    <div style="font-size:0.8rem; color:#888;">{score_label}</div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # ─── PREÇO JUSTO ──────────────────────────────────────────────────────
        st.subheader("💰 Preço Justo")

        col1, col2, col3 = st.columns(3)

        with col1:
            preco_justo_g = calcular_preco_justo_graham(ativo)
            upside_g = calcular_upside(preco, preco_justo_g)

            st.markdown(f"""
            <div style="background:#f8f9fa; border-radius:12px; padding:20px; text-align:center;">
                <div style="font-size:0.9rem; color:#666; margin-bottom:5px;">Graham</div>
                <div style="font-size:1.8rem; font-weight:700; color:#667eea;">
                    {formatar_moeda(preco_justo_g) if preco_justo_g else "N/A"}
                </div>
                <div style="font-size:0.9rem; margin-top:5px;" class="{'positive' if upside_g and upside_g > 0 else 'negative' if upside_g and upside_g < 0 else 'neutral'}">
                    {f"Upside: {upside_g:+.1f}%" if upside_g else ""}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            preco_justo_b = calcular_preco_justo_bazin(ativo)
            upside_b = calcular_upside(preco, preco_justo_b)

            st.markdown(f"""
            <div style="background:#f8f9fa; border-radius:12px; padding:20px; text-align:center;">
                <div style="font-size:0.9rem; color:#666; margin-bottom:5px;">Bazin (6% DY)</div>
                <div style="font-size:1.8rem; font-weight:700; color:#667eea;">
                    {formatar_moeda(preco_justo_b) if preco_justo_b else "N/A"}
                </div>
                <div style="font-size:0.9rem; margin-top:5px;" class="{'positive' if upside_b and upside_b > 0 else 'negative' if upside_b and upside_b < 0 else 'neutral'}">
                    {f"Upside: {upside_b:+.1f}%" if upside_b else ""}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            if "Preco_Justo_DCF" in ativo:
                preco_dcf = ativo["Preco_Justo_DCF"]
                upside_dcf = calcular_upside(preco, preco_dcf)

                st.markdown(f"""
                <div style="background:#f8f9fa; border-radius:12px; padding:20px; text-align:center;">
                    <div style="font-size:0.9rem; color:#666; margin-bottom:5px;">DCF</div>
                    <div style="font-size:1.8rem; font-weight:700; color:#667eea;">
                        {formatar_moeda(preco_dcf)}
                    </div>
                    <div style="font-size:0.9rem; margin-top:5px;" class="{'positive' if upside_dcf and upside_dcf > 0 else 'negative' if upside_dcf and upside_dcf < 0 else 'neutral'}">
                        {f"Upside: {upside_dcf:+.1f}%" if upside_dcf else ""}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # ─── INDICADORES ──────────────────────────────────────────────────────
        st.subheader("📊 Indicadores Fundamentalistas")

        indicadores = {
            "P/L": ativo.get("PL", None),
            "P/VP": ativo.get("PVP", None),
            "DY": ativo.get("DY", None),
            "ROE": ativo.get("ROE", None),
            "ROIC": ativo.get("ROIC", None),
            "Margem Líquida": ativo.get("Margem_Liquida", None),
            "Margem Bruta": ativo.get("Margem_Bruta", None),
            "Margem EBIT": ativo.get("Margem_EBIT", None),
            "EV/EBIT": ativo.get("EV_EBIT", None),
            "Dívida/PL": ativo.get("Divida_PL", None),
            "Dívida/EBITDA": ativo.get("Divida_EBITDA", None),
            "Liquidez Corrente": ativo.get("Liquidez_Corrente", None),
            "VPA": ativo.get("VPA", None),
            "LPA": ativo.get("LPA", None),
            "P/Ativo": ativo.get("P_Ativo", None),
            "P/EBIT": ativo.get("P_EBIT", None),
            "P/Ativo Circ": ativo.get("P_Ativo_Circ", None),
            "PSR": ativo.get("PSR", None),
            "Giro Ativos": ativo.get("Giro_Ativos", None),
            "CAGR Receitas": ativo.get("CAGR_Receitas", None),
            "CAGR Lucros": ativo.get("CAGR_Lucros", None),
        }

        cols = st.columns(4)
        idx = 0
        for nome, valor in indicadores.items():
            if valor is not None and not pd.isna(valor):
                with cols[idx % 4]:
                    suffix = "%" if "Margem" in nome or "ROE" in nome or "ROIC" in nome or "CAGR" in nome or "DY" in nome else "x" if nome not in ["VPA", "LPA"] else ""
                    st.markdown(f"""
                    <div style="background:#f8f9fa; border-radius:10px; padding:15px; text-align:center; margin:5px 0;">
                        <div style="font-size:0.8rem; color:#888;">{nome}</div>
                        <div style="font-size:1.4rem; font-weight:700; color:#1a1a2e;">
                            {valor:.2f}{suffix}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                idx += 1

        st.divider()

        # ─── CHECKLIST SCORE CS ───────────────────────────────────────────────
        st.subheader("✅ Checklist Score CS (Carlos Sobral)")

        checklist = []

        # Critérios do Score CS
        criterios = [
            ("ROE > 15%", ativo.get("ROE", 0) > 15),
            ("ROIC > 10%", ativo.get("ROIC", 0) > 10),
            ("Margem Líquida > 10%", ativo.get("Margem_Liquida", 0) > 10),
            ("Dívida/PL < 0.5", ativo.get("Divida_PL", 999) < 0.5),
            ("Dívida/EBITDA < 3", ativo.get("Divida_EBITDA", 999) < 3),
            ("P/L < 15", ativo.get("PL", 999) < 15),
            ("P/VP < 2", ativo.get("PVP", 999) < 2),
            ("DY > 3%", ativo.get("DY", 0) > 3),
            ("Liquidez Corrente > 1", ativo.get("Liquidez_Corrente", 0) > 1),
        ]

        col1, col2 = st.columns(2)
        for i, (criterio, passou) in enumerate(criterios):
            with col1 if i < 5 else col2:
                status = "✅" if passou else "❌"
                classe = "checklist-pass" if passou else "checklist-fail"
                st.markdown(f"""
                <div class="checklist-item {classe}">
                    <span style="font-size:1.2rem; margin-right:10px;">{status}</span>
                    <span style="font-weight:500;">{criterio}</span>
                </div>
                """, unsafe_allow_html=True)

        # Radar de indicadores
        st.subheader("🎯 Radar de Indicadores")

        radar_data = {
            "Indicador": ["ROE", "ROIC", "Margem Líq", "DY", "Crescimento"],
            "Valor": [
                min(ativo.get("ROE", 0) / 30 * 100, 100),
                min(ativo.get("ROIC", 0) / 20 * 100, 100),
                min(ativo.get("Margem_Liquida", 0) / 20 * 100, 100),
                min(ativo.get("DY", 0) / 10 * 100, 100),
                min(ativo.get("CAGR_Lucros", 0) / 20 * 100, 100),
            ],
            "Referência": [100, 100, 100, 100, 100]
        }

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=radar_data["Valor"] + [radar_data["Valor"][0]],
            theta=radar_data["Indicador"] + [radar_data["Indicador"][0]],
            fill="toself",
            fillcolor="rgba(102, 126, 234, 0.3)",
            line=dict(color="#667eea", width=2),
            name=ticker
        ))
        fig.add_trace(go.Scatterpolar(
            r=radar_data["Referência"] + [radar_data["Referência"][0]],
            theta=radar_data["Indicador"] + [radar_data["Indicador"][0]],
            line=dict(color="#ccc", width=1, dash="dash"),
            name="Referência"
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

# ─── PÁGINA: RANKINGS ─────────────────────────────────────────────────────────
elif page == "📊 Rankings":
    st.markdown("<div class='main-header'>📊 Rankings</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Top ativos por categoria</div>", unsafe_allow_html=True)

    categorias = {
        "🏆 Score CS": "Score CS",
        "💰 Maior DY": "DY",
        "📉 Menor P/L": "PL",
        "📈 Maior ROE": "ROE",
        "🎯 Maior ROIC": "ROIC",
        "📊 Maior Margem Líquida": "Margem_Liquida",
        "💎 Graham (Maior Upside)": "Upside_Graham",
        "🏠 Bazin (Maior Upside)": "Upside_Bazin",
    }

    cat = st.selectbox("Categoria", list(categorias.keys()))
    col = categorias[cat]

    if col in df.columns:
        n = st.slider("Quantidade", 5, 50, 20)

        if col in ["PL", "PVP", "Divida_PL", "Divida_EBITDA"]:
            top = df.nsmallest(n, col)
        else:
            top = df.nlargest(n, col)

        # Tabela estilizada
        display_cols = ["Ticker", "Nome", "Setor", col, "Preco", "Score CS"]
        display_cols = [c for c in display_cols if c in top.columns]

        st.dataframe(
            top[display_cols].style.apply(
                lambda x: ["background: #e8f5e9" if i % 2 == 0 else "background: #fff" for i in range(len(x))],
                axis=0
            ),
            use_container_width=True,
            height=600
        )

        # Gráfico
        fig = px.bar(
            top, x=col, y="Ticker", orientation="h",
            color=col, color_continuous_scale="Viridis",
            text=top[col].apply(lambda x: f"{x:.2f}"),
            hover_data=["Nome", "Setor", "Preco"]
        )
        fig.update_layout(height=500, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

# ─── PÁGINA: COMPARATIVO ──────────────────────────────────────────────────────
elif page == "📈 Comparativo":
    st.markdown("<div class='main-header'>📈 Comparativo de Ativos</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Compare múltiplos ativos lado a lado</div>", unsafe_allow_html=True)

    tickers = st.multiselect("Selecione os ativos", options=sorted(df["Ticker"].tolist()), max_selections=5)

    if tickers:
        comp = df[df["Ticker"].isin(tickers)]

        # Tabela comparativa
        cols_comp = ["Ticker", "Nome", "Preco", "PL", "PVP", "DY", "ROE", "ROIC", 
                     "Margem_Liquida", "Divida_PL", "Score CS", "Upside_Graham"]
        cols_comp = [c for c in cols_comp if c in comp.columns]

        st.dataframe(comp[cols_comp], use_container_width=True)

        # Radar comparativo
        indicadores_radar = ["ROE", "ROIC", "Margem_Liquida", "DY", "CAGR_Lucros"]
        indicadores_radar = [c for c in indicadores_radar if c in comp.columns]

        if indicadores_radar:
            fig = go.Figure()
            for _, row in comp.iterrows():
                valores = []
                for ind in indicadores_radar:
                    val = row.get(ind, 0)
                    if "Margem" in ind or "ROE" in ind or "ROIC" in ind or "DY" in ind:
                        valores.append(min(val / 30 * 100, 100))
                    else:
                        valores.append(min(val / 20 * 100, 100))

                fig.add_trace(go.Scatterpolar(
                    r=valores + [valores[0]],
                    theta=indicadores_radar + [indicadores_radar[0]],
                    fill="toself",
                    name=row["Ticker"]
                ))

            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

# ─── PÁGINA: CONFIGURAÇÕES ────────────────────────────────────────────────────
elif page == "⚙️ Configurações":
    st.markdown("<div class='main-header'>⚙️ Configurações</div>", unsafe_allow_html=True)

    st.subheader("📁 Informações dos Dados")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Ativos", len(df))
    with col2:
        st.metric("Colunas", len(df.columns))
    with col3:
        if "Score CS" in df.columns:
            st.metric("Score CS Médio", f"{df['Score CS'].mean():.2f}")

    st.divider()

    st.subheader("📋 Colunas Disponíveis")
    st.write(", ".join(df.columns.tolist()))

    st.divider()

    st.subheader("📊 Estatísticas Gerais")
    stats_cols = ["Preco", "PL", "PVP", "DY", "ROE", "ROIC", "Margem_Liquida", "Score CS"]
    stats_cols = [c for c in stats_cols if c in df.columns]

    if stats_cols:
        st.dataframe(df[stats_cols].describe(), use_container_width=True)

    st.divider()

    st.subheader("🎯 Parâmetros de Valuation")
    st.info("""
    **Métodos utilizados:**
    - **Graham:** √(22.5 × VPA × LPA)
    - **Bazin:** Dividendo Anual / 6% (DY alvo)
    - **DCF:** Fluxo de Caixa Descontado (quando disponível)
    - **Score CS:** 9 critérios fundamentalistas (0-9)
    """)
