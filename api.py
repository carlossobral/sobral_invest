from flask import Flask, jsonify
import json
import time

app = Flask(__name__)

# =========================
# 🔄 CACHE
# =========================

CACHE = {}
CACHE_TEMPO = 300

def get_base():
    with open("base.json") as f:
        return json.load(f)

def cache_response(key, data):
    CACHE[key] = {
        "data": data,
        "time": time.time()
    }

def get_cache(key):
    if key in CACHE:
        if time.time() - CACHE[key]["time"] < CACHE_TEMPO:
            return CACHE[key]["data"]
    return None

# =========================
# 🔎 NORMALIZA TICKER
# =========================

def normalizar(t):
    return t.upper().strip()

# =========================
# 📊 BUSCA AÇÃO
# =========================

@app.route("/acao/<ticker>")
def acao(ticker):
    ticker = normalizar(ticker)

    cache = get_cache(ticker)
    if cache:
        return jsonify(cache)

    base = get_base()

    for a in base:
        if a["ticker"] == ticker:
            cache_response(ticker, a)
            return jsonify(a)

    return jsonify({"erro": "não encontrado"}), 404

# =========================
# 🔎 AUTOCOMPLETE
# =========================

@app.route("/buscar/<texto>")
def buscar(texto):
    texto = normalizar(texto)

    base = get_base()

    resultado = [
        a["ticker"]
        for a in base
        if texto in a["ticker"]
    ]

    return jsonify(resultado[:10])

# =========================
# 🏆 TOP 10 (MELHOR DY)
# =========================

@app.route("/top10")
def top10():
    cache = get_cache("top10")
    if cache:
        return jsonify(cache)

    base = get_base()

    ranking = sorted(base, key=lambda x: x.get("dy", 0), reverse=True)[:10]

    cache_response("top10", ranking)
    return jsonify(ranking)

# =========================
# 💰 MAIORES DY
# =========================

@app.route("/maiores-dy")
def maiores_dy():
    base = get_base()
    ranking = sorted(base, key=lambda x: x.get("dy", 0), reverse=True)[:20]
    return jsonify(ranking)

# =========================
# 📈 MAIOR ROE
# =========================

@app.route("/maior-roe")
def maior_roe():
    base = get_base()
    ranking = sorted(base, key=lambda x: x.get("roe", 0), reverse=True)[:20]
    return jsonify(ranking)

# =========================
# 🧠 GRAHAM
# =========================

@app.route("/graham")
def graham():
    base = get_base()

    ranking = [
        a for a in base
        if a.get("pl", 0) > 0 and a.get("pvp", 0) > 0
    ]

    for a in ranking:
        a["graham"] = (22.5 / (a["pl"] * a["pvp"])) if a["pl"] and a["pvp"] else 0

    ranking = sorted(ranking, key=lambda x: x["graham"], reverse=True)[:20]

    return jsonify(ranking)

# =========================
# 💎 BAZIN
# =========================

@app.route("/bazin")
def bazin():
    base = get_base()

    ranking = sorted(base, key=lambda x: x.get("dy", 0), reverse=True)

    for a in ranking:
        a["bazin"] = a.get("dy", 0) * 16.67

    return jsonify(ranking[:20])

# =========================
# 🚀 PETER LYNCH
# =========================

@app.route("/lynch")
def lynch():
    base = get_base()

    ranking = []

    for a in base:
        pl = a.get("pl", 0)
        roe = a.get("roe", 0)

        if pl > 0:
            score = roe / pl
        else:
            score = 0

        a["lynch"] = score
        ranking.append(a)

    ranking = sorted(ranking, key=lambda x: x["lynch"], reverse=True)[:20]

    return jsonify(ranking)

# =========================
# 🚀 START
# =========================

@app.route("/")
def home():
    return {"status": "API ONLINE 🚀"}

if __name__ == "__main__":
    app.run()
