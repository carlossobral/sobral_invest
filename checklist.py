def checklist_buy_hold(ind):
    score = 0
    checklist = {}

    roe = ind.get("ROE") or 0
    dy = ind.get("DY") or 0
    divida_pl = ind.get("Divida_PL") or 0
    liquidez = ind.get("Liquidez_Corrente") or 0

    # DY pode vir como decimal (0.08) ou percentual (8.0) — normalizando
    if dy > 1:
        dy = dy / 100  # era percentual, converte para decimal

    checklist["ROE > 12%"] = roe > 0.12
    checklist["DY > 7%"] = dy > 0.07
    checklist["Dívida baixa"] = 0 < divida_pl < 1
    checklist["Liquidez Corrente > 1"] = liquidez > 1

    for item in checklist.values():
        if item:
            score += 10

    return checklist, score
