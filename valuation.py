"""
valuation.py --- Metodos de Preco Teto e Valor Justo v3.0
====================================================
Correcoes v3.0:
- Bazin: taxa ajustada para 6% (padrao Bazin Brasil)
- AGF Medio: taxa ajustada para 6%, DPA medio dos ultimos 6 anos
- Remove AGF Projetivo (sem fonte de projeção)
- Mantem Peter Lynch (preco teto PEG=1)

Metodos:
 1. Graham Classico -> sqrt(22.5 * LPA * VPA)
 2. Graham BR -> LPA * (8.5 + 2g) * (4.4 / Selic)
 3. Bazin -> DPA / 0.06
 4. Peter Lynch -> LPA * Crescimento(%)
 5. AGF Medio -> Dividendo_Medio_6a / 0.06

A Selic e lida do selic.json gerado pelo GitHub Actions (update.yml)
todos os dias via API do Banco Central. Sem config.py, sem chamadas
em runtime.
"""

import json
import os

# ── Parametros ────────────────────────────────────────────────────
BAZIN_TAXA = 0.06  # CORRIGIDO: 6% padrao Bazin Brasil
AGF_TAXA = 0.06    # CORRIGIDO: 6% padrao AGF
AGF_ANOS = 6       # CORRIGIDO: 6 anos de historico
GRAHAM_BR_G_MAX = 15.0  # crescimento maximo no Graham BR (%)
SELIC_FALLBACK = 13.25  # usado apenas se selic.json nao existir


def _obter_selic() -> float:
    """Le a Selic do selic.json gravado pelo GitHub Actions."""
    try:
        caminho = os.path.join(os.path.dirname(__file__), "selic.json")
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        selic = float(dados["selic"])
        if 2.0 <= selic <= 30.0:
            return selic
    except Exception:
        pass
    return SELIC_FALLBACK


# ─────────────────────────────────────────────────────────────────
# 1. GRAHAM CLASSICO
# ─────────────────────────────────────────────────────────────────
def calcular_graham(lpa, vpa):
    try:
        lpa = _f(lpa)
        vpa = _f(vpa)
        if lpa <= 0 or vpa <= 0:
            return 0
        return (22.5 * lpa * vpa) ** 0.5
    except Exception:
        return 0


# ─────────────────────────────────────────────────────────────────
# 2. GRAHAM BR
# ─────────────────────────────────────────────────────────────────
def calcular_graham_br(lpa, crescimento):
    """
    lpa -> Lucro Por Acao (R$)
    crescimento -> CAGR de lucros (%, ex: 15 para 15% ou 0.15)
    """
    try:
        lpa = _f(lpa)
        crescimento = _f(crescimento)
        selic = _obter_selic()

        if lpa <= 0 or selic <= 0:
            return 0

        if crescimento <= 1:
            crescimento = crescimento * 100

        g = min(crescimento, GRAHAM_BR_G_MAX)
        return lpa * (8.5 + 2 * g) * (4.4 / selic)
    except Exception:
        return 0


# ─────────────────────────────────────────────────────────────────
# 3. BAZIN (CORRIGIDO: 6%)
# ─────────────────────────────────────────────────────────────────
def calcular_bazin(dpa):
    """dpa -> Dividendo Por Acao anual (R$)"""
    try:
        dpa = _f(dpa)
        if dpa <= 0:
            return 0
        return dpa / BAZIN_TAXA
    except Exception:
        return 0


# ─────────────────────────────────────────────────────────────────
# 4. PETER LYNCH (MANTIDO: Preco Teto PEG=1)
# ─────────────────────────────────────────────────────────────────
def calcular_lynch(lpa, crescimento):
    """
    lpa -> Lucro Por Acao (R$)
    crescimento -> crescimento esperado de lucros (% ou decimal)
    Preco justo quando PEG = 1: Preco = LPA * g
    """
    try:
        lpa = _f(lpa)
        crescimento = _f(crescimento)

        if lpa <= 0 or crescimento <= 0:
            return 0

        if crescimento <= 1:
            crescimento = crescimento * 100

        return lpa * crescimento
    except Exception:
        return 0


# ─────────────────────────────────────────────────────────────────
# 5. AGF MEDIO (CORRIGIDO: 6 anos, 6%)
# ─────────────────────────────────────────────────────────────────
def calcular_agf_medio(historico_dpa):
    """
    historico_dpa -> lista de DPA dos ultimos 6 anos
    ou um unico float (DPA medio ja calculado)
    Formula: Media DPA (6 anos) / 6%
    """
    try:
        if isinstance(historico_dpa, (list, tuple)):
            valores = [_f(v) for v in historico_dpa if _f(v) > 0]
            if not valores:
                return 0
            valores = valores[-AGF_ANOS:]
            media_dpa = sum(valores) / len(valores)
        else:
            media_dpa = _f(historico_dpa)

        if media_dpa <= 0:
            return 0
        return media_dpa / AGF_TAXA
    except Exception:
        return 0


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def calcular_upside(preco_atual, preco_teto):
    """Retorna upside (+) ou downside (-) em %."""
    try:
        p = _f(preco_atual)
        t = _f(preco_teto)
        if p <= 0 or t <= 0:
            return None
        return ((t - p) / p) * 100
    except Exception:
        return None


def classificar_upside(pct):
    """Retorna (label, valor_formatado) para exibir no Streamlit."""
    if pct is None:
        return "—", "—"
    if pct >= 20:
        return "🟢 Compra", f"+{pct:.1f}%"
    if pct >= 0:
        return "🟡 Atencao", f"+{pct:.1f}%"
    return "🔴 Acima do teto", f"{pct:.1f}%"


def _f(val):
    """Converte para float com seguranca."""
    try:
        return float(val) if val is not None else 0.0
    except (TypeError, ValueError):
        return 0.0
