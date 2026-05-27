import streamlit as st
import streamlit.components.v1 as components

def pagina_inicial():
    """Dashboard principal com TradingView widgets."""
    st.markdown('<h1 class="main-header">📈 SOBRAL Invest</h1>', unsafe_allow_html=True)

    # Widget TradingView - Ibovespa Symbol Overview
    st.subheader("📊 Ibovespa")
    tv_ibov = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
      {
        "symbols": [
          ["BMFBOVESPA:IBOV|1D"]
        ],
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
        "dateRanges": [
          "1d|1",
          "1m|30",
          "3m|60",
          "12m|1D",
          "60m|1W",
          "all|1M"
        ]
      }
      </script>
    </div>
    """
    components.html(tv_ibov, height=410)

    # Widget TradingView - Hotlists (Maiores Altas/Baixas)
    st.subheader("🔥 Maiores Altas e Baixas")
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
            "symbols": [
              { "s": "BMFBOVESPA:IBOV", "d": "Ibovespa" }
            ]
          },
          {
            "title": "Maiores Baixas",
            "symbols": [
              { "s": "BMFBOVESPA:IBOV", "d": "Ibovespa" }
            ]
          }
        ]
      }
      </script>
    </div>
    """
    components.html(tv_hotlists, height=560)
