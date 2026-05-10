def calcular_graham(lpa, vpa):

    try:
        return (22.5 * lpa * vpa) ** 0.5
    except:
        return 0


def calcular_graham_br(graham, roe, divida_pl,
                        margem_liquida,
                        crescimento_receita):

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


def calcular_bazin(dividendos_anuais):

    return dividendos_anuais / 0.07


def calcular_lynch(pl, crescimento):

    if crescimento == 0:
        return 0

    return pl / crescimento


def calcular_agf(dividendo_atual,
                 crescimento_dividendos):

    dividendo_futuro = dividendo_atual * (
        (1 + crescimento_dividendos) ** 5
    )

    return dividendo_futuro / 0.07
