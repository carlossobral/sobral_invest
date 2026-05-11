import streamlit as st
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


# ─── PÁGINA INICIAL ───────────────────────────────────────────────────────────────

st.markdown("# 📊 Sobral Invest")
st.markdown("**Acompanhe em tempo real o mercado da B3**")
st.markdown("---")

# Seção IBOVESPA
st.markdown("## 📈 IBOVESPA")

ibov_dados = obter_ibovespa()

if ibov_dados:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Cotação",
            f"{ibov_dados['preco']:,.0f}",
            delta=f"{ibov_dados['variacao_pontos']:+,.0f} pts"
        )
    
    with col2:
        variacao = ibov_dados["variacao_percentual"]
        cor = "🟢" if variacao >= 0 else "🔴"
        st.metric(
            "Variação",
            f"{variacao:+.2f}%",
            delta=cor
        )
    
    with col3:
        st.metric(
            "Abertura",
            f"{ibov_dados['preço_abertura']:,.0f}",
            delta=""
        )
    
    # Gráfico de 30 dias
    st.markdown("### 📊 Últimos 30 dias")
    hist_30d = obter_historico_ibovespa_30d()
    
    if hist_30d is not None and not hist_30d.empty:
        # Criar gráfico com Plotly
        fig = px.line(
            hist_30d,
            x="Date",
            y="Close",
            title="Evolução do IBOVESPA - Últimos 30 dias",
            labels={"Close": "Fechamento", "Date": "Data"},
            markers=False,
            height=400
        )
        
        # Estilizar o gráfico
        fig.update_traces(
            line=dict(color="#10b981", width=2)
        )
        
        fig.update_layout(
            hovermode="x unified",
            template="plotly_dark",
            xaxis_title="Data",
            yaxis_title="Pontos",
            font=dict(size=12),
            margin=dict(l=50, r=50, t=50, b=50),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("⏳ Carregando gráfico histórico...")
else:
    st.info("⏳ Carregando dados do IBOVESPA...")

st.markdown("---")

# Seção Maiores Altas e Baixas
st.markdown("## 📊 Maiores Altas / Maiores Baixas do Dia")

maiores_altas, maiores_baixas = obter_maiores_altas_baixas()

if not maiores_altas.empty and not maiores_baixas.empty:
    col_altas, col_baixas = st.columns(2)
    
    with col_altas:
        st.markdown("### 🟢 Maiores Altas")
        for _, row in maiores_altas.iterrows():
            st.markdown(render_card_acao(row["ticker"], row["preco"], row["variacao"]), unsafe_allow_html=True)
    
    with col_baixas:
        st.markdown("### 🔴 Maiores Baixas")
        for _, row in maiores_baixas.iterrows():
            st.markdown(render_card_acao(row["ticker"], row["preco"], row["variacao"]), unsafe_allow_html=True)
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
