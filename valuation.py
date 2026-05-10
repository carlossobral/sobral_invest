def calcular_graham(lpa, vpa):
    try:
        lpa = lpa or 0
        vpa = vpa or 0
        if lpa <= 0 or vpa <= 0:
            return 0
        return (22.5 * lpa * vpa) ** 0.5
    except:
        return 0

def calcular_graham_br(graham, roe, divida_pl, margem_liquida, crescimento_receita):
    try:
        graham = graham or 0
        roe = roe or 0
        divida_pl = divida_pl or 0
        margem_liquida = margem_liquida or 0
        crescimento_receita = crescimento_receita or 0
        fator = 1
        if roe > 0.15:
            fator += 0.10
        if divida_pl < 0.5:
            fator += 0.10
        if margem_liquida > 0.10:
            fator += 0.05
        if crescimento_receita > 0:
            fator += 0.05
        return graham * fator
    except:
        return 0

def calcular_bazin(dividendos_anuais):
    try:
        dividendos_anuais = dividendos_anuais or 0
        if dividendos_anuais <= 0:
            return 0
        return dividendos_anuais / 0.07
    except:
        return 0

def calcular_lynch(pl, crescimento):
    try:
        pl = pl or 0
        crescimento = crescimento or 0
        if crescimento == 0:
            return 0
        return pl / crescimento
    except:
        return 0

def calcular_agf(dividendo_atual, crescimento_dividendos):
    try:
        dividendo_atual = dividendo_atual or 0
        crescimento_dividendos = crescimento_dividendos or 0
        dividendo_futuro = dividendo_atual * ((1 + crescimento_dividendos) ** 5)
        if dividendo_futuro <= 0:
            return 0
        return dividendo_futuro / 0.07
    except:
        return 0
