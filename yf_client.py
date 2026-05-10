import yfinance as yf


def buscar_historico(ticker):

    ticker_yf = f"{ticker}.SA"

    acao = yf.Ticker(ticker_yf)

    hist = acao.history(period="5y")

    return hist
