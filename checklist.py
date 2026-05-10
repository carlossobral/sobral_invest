def checklist_buy_hold(ind):

    score = 0

    checklist = {}

    checklist["ROE > 12%"] = ind["ROE"] > 0.12
    checklist["DY > 7%"] = ind["DY"] > 0.07
    checklist["Dívida baixa"] = ind["Divida_PL"] < 1
    checklist["Liquidez Corrente"] = ind["Liquidez_Corrente"] > 1

    for item in checklist.values():

        if item:
            score += 10

    return checklist, score
