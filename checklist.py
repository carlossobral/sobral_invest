def checklist_buy_hold(ind):
    score = 0
    checklist = {}

    roe = ind.get("ROE") or 0
    dy = ind.get("DY") or 0
    divida_pl = ind.get("Divida_PL") or 0
    liquidez = ind.get("Liquidez_Corrente") or 0

    checklist["ROE > 12%"] = roe > 12
    checklist["DY > 7%"] = dy > 7
    checklist["Dívida baixa"] = divida_pl < 1
    checklist["Liquidez Corrente > 1"] = liquidez > 1

    for item in checklist.values():
        if item:
            score += 10

    return checklist, score
