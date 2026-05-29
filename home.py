import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# ============================================================
# SELIC - LEITURA EXCLUSIVA DO JSON (SEM API EM TEMPO REAL)
# ============================================================

def get_selic_historico():
    """
    Lê SELIC APENAS de data/selic.json.
    NUNCA chama a API do BCB em tempo real.
    Retorna DataFrame vazio se não houver dados válidos.
    """
    selic_file = Path("data/selic.json")
    
    if not selic_file.exists():
        return pd.DataFrame()
    
    try:
        with open(selic_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Tenta ler a série histórica (chave "historico")
        historico = data.get("historico", [])
        
        if historico and isinstance(historico, list) and len(historico) > 0:
            df = pd.DataFrame(historico)
            # Garante que as colunas necessárias existem
            if 'data' in df.columns and 'valor_anual' in df.columns:
                df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
                df = df.dropna(subset=['data', 'valor_anual'])
                return df.sort_values('data').reset_index(drop=True)
        
        # Se não houver histórico válido, retorna vazio (não quebra)
        return pd.DataFrame()
        
    except Exception as e:
        st.warning(f"Erro ao ler selic.json: {e}")
        return pd.DataFrame()

def plot_selic(df):
    """Plota gráfico de área da SELIC histórica."""
    if df.empty:
        return None
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['data'],
        y=df['valor_anual'],
        fill='tozeroy',
        mode='lines',
        line=dict(color='#10b981', width=2),
        fillcolor='rgba(16, 185, 129, 0.15)',
        name='SELIC % a.a.'
    ))
    fig.update_layout(
        title=dict(text='Taxa SELIC Histórica (% ao ano)', font=dict(size=16, color='#f1f5f9'), x=0.5),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8', size=11),
        xaxis=dict(showgrid=True, gridcolor='rgba(51, 65, 85, 0.3)', gridwidth=1, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(51, 65, 85, 0.3)', gridwidth=1, zeroline=False, ticksuffix='%'),
        margin=dict(l=40, r=40, t=50, b=40),
        height=320,
        hovermode='x unified'
    )
    return fig

def pagina_inicial():
    """Dashboard principal: Ibovespa -> Maiores Altas/Baixas -> SELIC."""
    st.markdown('<h1 class="main-header">SOBRAL Invest</h1>', unsafe_allow_html=True)

    # 1. WIDGET TRADINGVIEW - IBOVESPA
    st.subheader("Ibovespa")
    tv_ibov = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
      {
        "symbols": [["BMFBOVESPA:IBOV|1D"]],
        "chartOnly": false,
        "width": "960",
        "height": "400",
        "locale": "br",
        "colorTheme": "dark",
        "autosize": false,
        "showVolume": true,
        "showMA": false,
        "hideDateRanges": false,
        "hideMarketStatus": false,
        "hideSymbolLogo": false,
        "scalePosition": "right",
        "scaleMode": "Normal",
        "fontFamily": "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif",
        "fontSize": "10",
        "noTimeScale": false,
        "valuesTracking": "1",
        "changeMode": "price-and-percent",
        "chartType": "area",
        "maLineColor": "#2962FF",
        "maLineWidth": 1,
        "maLength": 9,
        "lineWidth": 2,
        "lineType": 0,
        "dateRanges": ["1d|1", "1m|30", "3m|60", "12m|1D", "60m|1W", "all|1M"]
      }
      </script>
    </div>
    """
    components.html(tv_ibov, height=410)

    # 2. WIDGET TRADINGVIEW - HOTLISTS
    st.subheader("Maiores Altas e Baixas")
    tv_hotlists = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-hotlists.js" async>
      {
        "colorTheme": "dark",
        "dateRange": "1D",
        "exchange": "BMFBOVESPA",
        "showChart": true,
        "locale": "br",
        "largeChartUrl": "",
        "isTransparent": false,
        "showSymbolLogo": true,
        "showFloatingTooltip": true,
        "width": "960",
        "height": "550",
        "plotLineColorGrowing": "rgba(41, 98, 255, 1)",
        "plotLineColorFalling": "rgba(41, 98, 255, 1)",
        "plotLineColorGrowingBottom": "rgba(41, 98, 255, 0)",
        "plotLineColorFallingBottom": "rgba(41, 98, 255, 0)",
        "gridLineColor": "rgba(42, 46, 57, 0)",
        "scaleFontColor": "rgba(120, 123, 134, 1)",
        "belowLineFillColorGrowing": "rgba(41, 98, 255, 0.12)",
        "belowLineFillColorFalling": "rgba(41, 98, 255, 0.12)",
        "belowLineFillColorGrowingBottom": "rgba(41, 98, 255, 0)",
        "belowLineFillColorFallingBottom": "rgba(41, 98, 255, 0)",
        "symbolActiveColor": "rgba(41, 98, 255, 0.12)",
        "tabs": [
          {
            "title": "Mais Negociadas",
            "symbols": [
              { "s": "BMFBOVESPA:PETR4", "d": "Petrobras" },
              { "s": "BMFBOVESPA:VALE3", "d": "Vale" },
              { "s": "BMFBOVESPA:ITUB4", "d": "Itau Unibanco" },
              { "s": "BMFBOVESPA:BBDC4", "d": "Bradesco" },
              { "s": "BMFBOVESPA:ABEV3", "d": "Ambev" },
              { "s": "BMFBOVESPA:WEGE3", "d": "Weg" },
              { "s": "BMFBOVESPA:BBAS3", "d": "Banco do Brasil" }
            ],
            "originalTitle": "Equities"
          },
          {
            "title": "Maiores Altas",
            "symbols": [{ "s": "BMFBOVESPA:IBOV", "d": "Ibovespa" }]
          },
          {
            "title": "Maiores Baixas",
            "symbols": [{ "s": "BMFBOVESPA:IBOV", "d": "Ibovespa" }]
          }
        ]
      }
      </script>
    </div>
    """
    components.html(tv_hotlists, height=560)

    # 3. GRAFICO SELIC HISTORICA (LEITURA APENAS DO JSON)
    st.markdown("---")
    st.subheader("Taxa SELIC")
    
    df_selic = get_selic_historico()
    
    if not df_selic.empty:
        fig = plot_selic(df_selic)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        
        # Métricas seguras (só acessa se houver dados)
        try:
            selic_atual = df_selic['valor_anual'].iloc[-1]
            selic_min = df_selic['valor_anual'].min()
            selic_max = df_selic['valor_anual'].max()
            selic_media = df_selic['valor_anual'].mean()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Atual", f"{selic_atual:.2f}%")
            c2.metric("Mínima", f"{selic_min:.2f}%")
            c3.metric("Máxima", f"{selic_max:.2f}%")
            c4.metric("Média", f"{selic_media:.2f}%")
        except:
            st.info("Métricas da SELIC indisponíveis no momento.")
    else:
        st.info("Dados históricos da SELIC não disponíveis. Execute o coletor (app.py) para atualizar.")

    # Rodapé informativo
    st.markdown("""
    <div style='margin-top: 40px; padding-top: 20px; border-top: 1px solid #334155; text-align: center; color: #64748b; font-size: 0.75rem;'>
        Dados da SELIC atualizados apenas quando o coletor (app.py) é executado. 
        Última atualização: <code>data/selic.json</code>
    </div>
    """, unsafe_allow_html=True)
