def checklist_buy_hold(ind):
    """
    Checklist Buy & Hold com 9 critérios.

    Parâmetros esperados em `ind`:
        ROE              → float (ex: 0.15 para 15%)
        DY               → float (ex: 0.08 para 8%, ou 8.0 — normalizado internamente)
        Divida_PL        → float (ex: 0.8)
        Liquidez_Corrente→ float (ex: 1.5)
        Lucro_CAGR       → float (ex: 0.10 para 10% de crescimento em 5 anos)
        Receita_CAGR     → float (ex: 0.08)
        Anos_Bolsa       → int   (ex: 12) — anos listado na B3
        Lucro_Positivo   → bool  — True se nunca teve prejuízo anual
        Lucro_28T        → bool  — True se teve lucro nos últimos 28 trimestres
        Volume_Medio     → float — volume financeiro médio diário em R$

    Retorna:
        checklist → dict com nome do critério: bool
        score     → int de 0 a 9
    """

    checklist = {}

    # ── Extrair e normalizar valores ─────────────────────────────────────────

    roe              = _f(ind.get("ROE"))
    dy               = _f(ind.get("DY"))
    divida_pl        = _f(ind.get("Divida_PL"))
    liquidez         = _f(ind.get("Liquidez_Corrente"))
    lucro_cagr       = _f(ind.get("Lucro_CAGR"))
    receita_cagr     = _f(ind.get("Receita_CAGR"))
    anos_bolsa       = int(ind.get("Anos_Bolsa") or 0)
    lucro_positivo   = bool(ind.get("Lucro_Positivo"))
    lucro_28t        = bool(ind.get("Lucro_28T"))
    volume_medio     = _f(ind.get("Volume_Medio"))

    # DY pode vir como decimal (0.08) ou percentual (8.0) — normaliza
    if dy > 1:
        dy = dy / 100

    # ROE idem
    if roe > 1:
        roe = roe / 100

    # Lucro_CAGR e Receita_CAGR idem
    if lucro_cagr > 1:
        lucro_cagr = lucro_cagr / 100
    if receita_cagr > 1:
        receita_cagr = receita_cagr / 100

    # ── 9 Critérios ──────────────────────────────────────────────────────────

    # 1. Empresa com mais de 7 anos de Bolsa
    checklist["Mais de 7 anos de Bolsa"] = anos_bolsa >= 7

    # 2. Empresa nunca deu prejuízo (ano fiscal)
    checklist["Nunca teve prejuízo anual"] = lucro_positivo

    # 3. Lucro nos últimos 28 trimestres (7 anos)
    checklist["Lucro nos últimos 28 trimestres"] = lucro_28t

    # 4. Pagou +7% de dividendos/ano nos últimos 7 anos
    checklist["Dividendos > 7% ao ano (últimos 7 anos)"] = dy > 0.07

    # 5. ROE acima de 12%
    checklist["ROE acima de 12%"] = roe > 0.12

    # 6. Dívida menor que patrimônio (Dívida/PL < 1)
    checklist["Dívida menor que patrimônio (Dív/PL < 1)"] = 0 < divida_pl < 1

    # 7. Crescimento de receita nos últimos 7 anos
    checklist["Crescimento de receita (últimos 7 anos)"] = receita_cagr > 0

    # 8. Crescimento de lucros nos últimos 7 anos
    checklist["Crescimento de lucros (últimos 7 anos)"] = lucro_cagr > 0

    # 9. Liquidez diária acima de R$ 1 milhão
    checklist["Liquidez diária > R$ 1 milhão"] = volume_medio >= 1_000_000

    # ── Score: 1 ponto por critério aprovado ─────────────────────────────────
    score = sum(1 for v in checklist.values() if v is True)

    return checklist, score


def _f(val):
    """Converte para float com segurança, retorna 0.0 se inválido."""
    try:
        return float(val) if val is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def classificar_score(score):
    """Retorna label e emoji baseado no score de 0-9."""
    if score >= 8:
        return "🏆 Excelente para Buy & Hold"
    elif score >= 6:
        return "✅ Bom para Buy & Hold"
    elif score >= 4:
        return "📊 Regular — analise com cuidado"
    else:
        return "⚠️ Não recomendado para Buy & Hold"
