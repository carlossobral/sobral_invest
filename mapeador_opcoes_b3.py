#!/usr/bin/env python3
"""
SOBRAL INVEST — Mapeador de Opções B3 para Ativo-Base
=======================================================
Converte tickers de opções (calls/puts, mensais/semanais) 
para o ativo-objeto correspondente para consolidação de carteira.

Fonte: Documentação oficial B3 + ADVFN + Nelogica
"""

import re
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

# ============================================================
# 1. TABELA DE VENCIMENTO — SÉRIES MENSAIS
# ============================================================

SERIES_MENSAIS = {
    # CALLs (A-L)
    'A': ('Janeiro', 'CALL'),
    'B': ('Fevereiro', 'CALL'),
    'C': ('Marco', 'CALL'),
    'D': ('Abril', 'CALL'),
    'E': ('Maio', 'CALL'),
    'F': ('Junho', 'CALL'),
    'G': ('Julho', 'CALL'),
    'H': ('Agosto', 'CALL'),
    'I': ('Setembro', 'CALL'),
    'J': ('Outubro', 'CALL'),
    'K': ('Novembro', 'CALL'),
    'L': ('Dezembro', 'CALL'),
    # PUTs (M-X)
    'M': ('Janeiro', 'PUT'),
    'N': ('Fevereiro', 'PUT'),
    'O': ('Marco', 'PUT'),
    'P': ('Abril', 'PUT'),
    'Q': ('Maio', 'PUT'),
    'R': ('Junho', 'PUT'),
    'S': ('Julho', 'PUT'),
    'T': ('Agosto', 'PUT'),
    'U': ('Setembro', 'PUT'),
    'V': ('Outubro', 'PUT'),
    'W': ('Novembro', 'PUT'),
    'X': ('Dezembro', 'PUT'),
}

# ============================================================
# 2. MAPEAMENTO DE ATIVOS-OBJETO (4 LETRAS → TICKER B3)
# ============================================================

ATIVOS_OBJETO = {
    # Acoes principais
    'PETR': 'PETR4',
    'VALE': 'VALE3',
    'ITUB': 'ITUB4',
    'BBDC': 'BBDC4',
    'BBAS': 'BBAS3',
    'ABEV': 'ABEV3',
    'WEGE': 'WEGE3',
    'MGLU': 'MGLU3',
    'GGBR': 'GGBR4',
    'GOAU': 'GOAU4',
    'USIM': 'USIM5',
    'CSNA': 'CSNA3',
    'KLBN': 'KLBN4',
    'SUZB': 'SUZB3',
    'RAIL': 'RAIL3',
    'SBSP': 'SBSP3',
    'EQTL': 'EQTL3',
    'CPLE': 'CPLE3',
    'CMIG': 'CMIG4',
    'TAEE': 'TAEE11',
    'TRPL': 'TRPL4',
    'ENBR': 'ENBR3',
    'EGIE': 'EGIE3',
    'CPFE': 'CPFE3',
    'AESB': 'AESB3',
    'NEOE': 'NEOE3',
    'ELET': 'ELET3',
    'ENEV': 'ENEV3',
    'RAIZ': 'RAIZ4',
    'PRIO': 'PRIO3',
    'RECV': 'RECV3',
    'VBBR': 'VBBR3',
    'BRAV': 'BRAV3',
    'RRRP': 'RRRP3',
    'CSAN': 'CSAN3',
    'UGPA': 'UGPA3',
    'VIVT': 'VIVT3',
    'TIMS': 'TIMS3',
    'OIBR': 'OIBR3',
    'TOTS': 'TOTS3',
    'LREN': 'LREN3',
    'AMER': 'AMER3',
    'CEAB': 'CEAB3',
    'GUAR': 'GUAR3',
    'ALPA': 'ALPA4',
    'PTNT': 'PTNT4',
    'TFCO': 'TFCO4',
    'CAML': 'CAML3',
    'MDIA': 'MDIA3',
    'SMTO': 'SMTO3',
    'SLCE': 'SLCE3',
    'SOJA': 'SOJA3',
    'AGXY': 'AGXY3',
    'JALL': 'JALL3',
    'BEEF': 'BEEF3',
    'JBSS': 'JBSS3',
    'BRFS': 'BRFS3',
    'MRFG': 'MRFG3',
    'POMO': 'POMO4',
    'RAPT': 'RAPT4',
    'TUPY': 'TUPY3',
    'LEVE': 'LEVE3',
    'MYPK': 'MYPK3',
    'EMBR': 'EMBR3',
    'AZUL': 'AZUL3',
    'GOLL': 'GOLL4',
    'CVCB': 'CVCB3',
    'RENT': 'RENT3',
    'VAMO': 'VAMO3',
    'MOVI': 'MOVI3',
    'LCAM': 'LCAM3',
    'SIMH': 'SIMH3',
    'ARML': 'ARML3',
    'SYNE': 'SYNE3',
    'ESPA': 'ESPA3',
    'FLRY': 'FLRY3',
    'PARD': 'PARD3',
    'RADL': 'RADL3',
    'HYPE': 'HYPE3',
    'PNVL': 'PNVL3',
    'PGMN': 'PGMN3',
    'OFSA': 'OFSA3',
    'BLAU': 'BLAU3',
    'BIOM': 'BIOM3',
    'VITT': 'VITT3',
    'NUTR': 'NUTR3',
    'CSED': 'CSED3',
    'SEER': 'SEER3',
    'ANIM': 'ANIM3',
    'COGN': 'COGN3',
    'YDUQ': 'YDUQ3',
    'BMOB': 'BMOB3',
    'INTB': 'INTB3',
    'TASA': 'TASA4',
    'NGRD': 'NGRD3',
    'POSI': 'POSI3',
    'WIZS': 'WIZS3',
    'LWSA': 'LWSA3',
    'IFCM': 'IFCM3',
    'CASH': 'CASH3',
    'DOTZ': 'DOTZ3',
    'BOAS': 'BOAS3',
    'DTCY': 'DTCY3',
    'VIVR': 'VIVR3',
    'HBOR': 'HBOR3',
    'CYRE': 'CYRE3',
    'DIRR': 'DIRR3',
    'EZTC': 'EZTC3',
    'JHSF': 'JHSF3',
    'LAVV': 'LAVV3',
    'MTRE': 'MTRE3',
    'TEND': 'TEND3',
    'TRIS': 'TRIS3',
    'ALUP': 'ALUP11',
    'AALR': 'AALR3',
    'AURE': 'AURE3',
    'CEBR': 'CEBR3',
    'CLSC': 'CLSC4',
    'CMIN': 'CMIN3',
    'COCE': 'COCE3',
    'CSMG': 'CSMG3',
    'ELET': 'ELET3',
    'ENGI': 'ENGI11',
    'EQPA': 'EQPA3',
    'LIGT': 'LIGT3',
    'RNEW': 'RNEW4',
    'SAPR': 'SAPR4',
    'SRNA': 'SRNA3',
    'BAZA': 'BAZA3',
    'BMIN': 'BMIN4',
    'BMEB': 'BMEB4',
    'BRSR': 'BRSR6',
    'BBSE': 'BBSE3',
    'BPAC': 'BPAC11',
    'BRBI': 'BRBI11',
    'BSLI': 'BSLI4',
    'ITSA': 'ITSA4',
    'PSSA': 'PSSA3',
    'SANB': 'SANB11',
    'WEST': 'WEST3',
    'AMAR': 'AMAR3',
    'BEES': 'BEES4',
    'BGIP': 'BGIP4',
    'BPAR': 'BPAR3',
    'BRGE': 'BRGE11',
    'CEEB': 'CEEB3',
    'CRPG': 'CRPG5',
    'CSAB': 'CSAB4',
    'CTKA': 'CTKA4',
    'CTNM': 'CTNM4',
    'CTSA': 'CTSA4',
    'DEXP': 'DEXP3',
    'DOHL': 'DOHL4',
    'EALT': 'EALT4',
    'ECOR': 'ECOR3',
    'ENAT': 'ENAT3',
    'ENJU': 'ENJU3',
    'EPAR': 'EPAR3',
    'EUCA': 'EUCA3',
    'EVEN': 'EVEN3',
    'FESA': 'FESA4',
    'FICT': 'FICT3',
    'FRAS': 'FRAS3',
    'GFSA': 'GFSA3',
    'GPAR': 'GPAR3',
    'GPIV': 'GPIV33',
    'GRND': 'GRND3',
    'HAGA': 'HAGA4',
    'HOOT': 'HOOT4',
    'IGBR': 'IGBR3',
    'IGTI': 'IGTI11',
    'INEP': 'INEP3',
    'IRBR': 'IRBR3',
    'JBDU': 'JBDU4',
    'JFEN': 'JFEN3',
    'JOPA': 'JOPA4',
    'JSLG': 'JSLG3',
    'KEPL': 'KEPL3',
    'LAND': 'LAND3',
    'LOGG': 'LOGG3',
    'LOGN': 'LOGN3',
    'LPSB': 'LPSB3',
    'LUPA': 'LUPA3',
    'LUXM': 'LUXM4',
    'LVTC': 'LVTC3',
    'MATD': 'MATD3',
    'MILS': 'MILS3',
    'MLAS': 'MLAS3',
    'MNPR': 'MNPR3',
    'MOUR': 'MOUR3',
    'MRSA': 'MRSA3B',
    'MRVE': 'MRVE3',
    'MTSA': 'MTSA4',
    'MWET': 'MWET4',
    'NORD': 'NORD3',
    'NRTQ': 'NRTQ3',
    'NTCO': 'NTCO3',
    'ODPV': 'ODPV3',
    'OPCT': 'OPCT3',
    'ORVR': 'ORVR3',
    'PATI': 'PATI4',
    'PEAB': 'PEAB4',
    'PETZ': 'PETZ3',
    'PFRM': 'PFRM3',
    'PINE': 'PINE4',
    'PLAS': 'PLAS3',
    'PMAM': 'PMAM3',
    'QUAL': 'QUAL3',
    'RANI': 'RANI3',
    'RDNI': 'RDNI3',
    'RDOR': 'RDOR3',
    'REDE': 'REDE3',
    'ROMI': 'ROMI3',
    'RPAD': 'RPAD3',
    'RPMG': 'RPMG3',
    'RSID': 'RSID3',
    'RSUL': 'RSUL4',
    'SCAR': 'SCAR3',
    'SEQL': 'SEQL3',
    'SHOW': 'SHOW3',
    'SHUL': 'SHUL4',
    'SOND': 'SOND5',
    'SQIA': 'SQIA3',
    'STBP': 'STBP3',
    'SULA': 'SULA11',
    'TGMA': 'TGMA3',
    'TIMP': 'TIMP3',
    'TPIS': 'TPIS3',
    'UCAS': 'UCAS3',
    'UNIP': 'UNIP6',
    'VSTE': 'VSTE3',
    'VULC': 'VULC3',
    'VVAR': 'VVAR3',
    'WDCN': 'WDCN3',
    'WHRL': 'WHRL4',
    'WIZC': 'WIZC3',
    # ETFs
    'BOVA': 'BOVA11',
    'BOVV': 'BOVV11',
    'SMAL': 'SMAL11',
    'MILL': 'MILL11',
    'ECOO': 'ECOO11',
    'FIND': 'FIND11',
    'MATB': 'MATB11',
    'ISUS': 'ISUS11',
    'GOVE': 'GOVE11',
    'FIXA': 'FIXA11',
    'HASH': 'HASH11',
    'NASD': 'NASD11',
    'TECK': 'TECK11',
    'XINA': 'XINA11',
    'EMEG': 'EMEG11',
    'EURP': 'EURP11',
    'ASIA': 'ASIA11',
    # BDRs
    'AAPL': 'AAPL34',
    'MSFT': 'MSFT34',
    'AMZO': 'AMZO34',
    'GOGL': 'GOGL34',
    'TSLA': 'TSLA34',
    'META': 'META34',
    'NFLX': 'NFLX34',
    'NVDC': 'NVDC34',
    'DISB': 'DISB34',
    'BERK': 'BERK34',
    'COLG': 'COLG34',
    'JNJB': 'JNJB34',
    'PFEI': 'PFEI34',
    'PGCO': 'PGCO34',
    'WALM': 'WALM34',
    'COCA': 'COCA34',
    'PEPB': 'PEPB34',
    'MCDO': 'MCDO34',
    'NIKE': 'NIKE34',
    # FIIs (alguns têm opcoes)
    'HGBS': 'HGBS11',
    'HGCR': 'HGCR11',
    'HGFF': 'HGFF11',
    'HGRE': 'HGRE11',
    'HGRU': 'HGRU11',
    'KNRI': 'KNRI11',
    'MXRF': 'MXRF11',
    'XPLG': 'XPLG11',
    'XPML': 'XPML11',
    'TRXF': 'TRXF11',
}

# ============================================================
# 3. CLASSE DE MAPEAMENTO
# ============================================================

@dataclass
class OpcaoInfo:
    """Informacoes parseadas de um ticker de opcao."""
    ticker_original: str
    ativo_base: Optional[str]
    tipo: Optional[str]
    mes_vencimento: Optional[str]
    strike: Optional[float]
    semanal: bool
    semana: Optional[int]
    exercicio_europeu: bool

    def is_valid(self) -> bool:
        return self.ativo_base is not None


class MapeadorOpcoes:
    """Mapeia tickers de opcoes B3 para ativos-objeto."""

    def __init__(self):
        self.ativos_objeto = ATIVOS_OBJETO
        self.series = SERIES_MENSAIS

    def parse_opcao(self, ticker: str) -> OpcaoInfo:
        """
        Parse um ticker de opcao e retorna informacoes estruturadas.

        Formatos suportados:
        - Mensal: AAAA + SERIE(1 letra) + STRIKE(2-3 digitos)
          Ex: PETRC32, GGBRE203, USIME720
        - Semanal: AAAA + SERIE(1 letra) + STRIKE + W + SEMANA(1 digito)
          Ex: B3SAH110W1, PETRF380W2
        - Com exercicio europeu: ... + E
          Ex: B3SAH110W1E
        """
        ticker = ticker.strip().upper()

        # Remover sufixo de exercicio europeu
        exercicio_europeu = ticker.endswith('E')
        if exercicio_europeu:
            ticker = ticker[:-1]

        # Verificar se eh semanal (contem W)
        semanal = 'W' in ticker
        semana = None

        if semanal:
            match = re.match(r'^([A-Z]{4})([A-Z])(\d+)(W)(\d)$', ticker)
            if match:
                ativo_cod, serie, strike_str, _, semana_str = match.groups()
                semana = int(semana_str)
            else:
                return OpcaoInfo(ticker, None, None, None, None, True, None, exercicio_europeu)
        else:
            match = re.match(r'^([A-Z]{4})([A-Z])(\d{2,3})$', ticker)
            if match:
                ativo_cod, serie, strike_str = match.groups()
            else:
                return OpcaoInfo(ticker, None, None, None, None, False, None, exercicio_europeu)

        # Buscar ativo base
        ativo_base = self.ativos_objeto.get(ativo_cod)

        # Parse serie
        info_serie = self.series.get(serie)
        if info_serie:
            mes_vencimento, tipo = info_serie
        else:
            mes_vencimento, tipo = None, None

        # Parse strike
        try:
            strike = float(strike_str)
            if len(strike_str) == 2:
                strike = strike
            elif len(strike_str) == 3:
                strike = strike / 10
        except ValueError:
            strike = None

        return OpcaoInfo(
            ticker_original=ticker,
            ativo_base=ativo_base,
            tipo=tipo,
            mes_vencimento=mes_vencimento,
            strike=strike,
            semanal=semanal,
            semana=semana,
            exercicio_europeu=exercicio_europeu
        )

    def get_ativo_base(self, ticker: str) -> Optional[str]:
        """Retorna o ativo-base para um ticker de opcao."""
        info = self.parse_opcao(ticker)
        return info.ativo_base

    def is_opcao(self, ticker: str) -> bool:
        """Verifica se o ticker eh uma opcao."""
        ticker = ticker.strip().upper()
        if ticker.endswith('E'):
            ticker = ticker[:-1]

        return bool(
            re.match(r'^[A-Z]{4}[A-Z]\d{2,3}$', ticker) or
            re.match(r'^[A-Z]{4}[A-Z]\d+W\d$', ticker)
        )


# ============================================================
# 4. FUNCOES DE MAPEAMENTO PARA IMPORTACAO B3
# ============================================================

def mapear_ticker_b3(ticker_produto: str) -> Tuple[str, str]:
    """
    Mapeia um ticker do arquivo B3 para o ativo consolidado.

    Args:
        ticker_produto: Ex: 'GGBRE203 - GGBR', 'USIME720 - USIM', 'VALE3 - VALE'

    Returns:
        Tuple: (ticker_consolidado, tipo_ativo)
    """
    mapeador = MapeadorOpcoes()

    if ' - ' in ticker_produto:
        ticker = ticker_produto.split(' - ')[0].strip()
    else:
        ticker = ticker_produto.strip()

    ticker = ticker.upper()

    # Verificar se eh opcao
    if mapeador.is_opcao(ticker):
        info = mapeador.parse_opcao(ticker)
        if info.tipo == 'CALL':
            return info.ativo_base or ticker, 'OPCAO_CALL'
        else:
            return info.ativo_base or ticker, 'OPCAO_PUT'

    # Verificar classe do ativo pelo sufixo
    if ticker.endswith('11') and ticker not in ['BOVA11', 'BOVV11', 'SMAL11', 'HASH11', 'NASD11', 'TECK11']:
        if 'AGRO' in ticker_produto.upper() or 'CRA' in ticker_produto.upper() or 'CRI' in ticker_produto.upper():
            return ticker, 'FIAGRO'
        return ticker, 'FII'
    elif ticker.endswith('11') and ticker in ['BOVA11', 'BOVV11', 'SMAL11', 'HASH11', 'NASD11', 'TECK11']:
        return ticker, 'ETF'
    elif ticker.endswith('34') or ticker.endswith('33') or ticker.endswith('35'):
        return ticker, 'BDR'
    elif ticker.endswith('3') or ticker.endswith('4') or ticker.endswith('5') or ticker.endswith('6'):
        return ticker, 'ACAO'
    else:
        return ticker, 'DESCONHECIDO'


# ============================================================
# 5. TESTES COM OS TICKERS DO SEU ARQUIVO B3
# ============================================================

if __name__ == "__main__":
    mapeador = MapeadorOpcoes()

    tickers_teste = [
        "GGBRE203 - GGBR",
        "USIME720 - USIM", 
        "BBASQ245 - BBAS",
        "BBSEJ386 - BBSE",
        "CSANO640 - CSAN",
        "BPACL341 - BPAC",
        "CMIGL131 - CMIG",
        "LRENJ156 - LREN",
        "MGLUD399 - MGLU",
        "PETRP319 - PETR",
        "PETRH304 - PETR",
        "COGNC170 - COGN",
        "BBDCN128 - BBDC",
        "BOVAO920 - BOVA",
        "WEGEC424 - WEGE",
        "VALEQ699 - VALE",
        "MRFGF205 - MRFG",
        "PETRE266 - PETR",
        "PETRQ244 - PETR",
        "MGLUJ500 - MGLU",
        "GGBRK317 - GGBR",
        "GGBRK326 - GGBR",
        "MGLUK159 - MGLU",
        "PETRK321 - PETR",
        "PETRK331 - PETR",
        "PETRU364 - PETR",
        "UGPAF180 - UGPA",
        "BBDCF151 - BBDC",
    ]

    print("=" * 70)
    print("MAPEAMENTO DE OPCOES B3 → ATIVO-BASE")
    print("=" * 70)

    for t in tickers_teste:
        consolidado, tipo = mapear_ticker_b3(t)
        info = mapeador.parse_opcao(t.split(' - ')[0])

        print(f"\n{t}")
        print(f"  → Ativo-base: {consolidado}")
        print(f"  → Tipo: {tipo}")
        if info.is_valid():
            print(f"  → {info.tipo} | Venc: {info.mes_vencimento} | Strike: R$ {info.strike}")
            if info.semanal:
                print(f"  → SEMANAL (semana {info.semana})")

    print("\n" + "=" * 70)
    print("TICKERS DO ARQUIVO B3 (nao-opcoes):")
    print("=" * 70)

    ativos_b3 = [
        "BMGB4 - BANCO BMG S/A",
        "HAPV3 - HAPVIDA PARTICIPACOES E INVESTIMENTOS SA",
        "MLAS3 - GRUPO MULTI S.A.",
        "NATU3 - NATURA COSMETICOS S/A",
        "ENEV3 - ENEVA S.A.",
        "VALE3 - VALE S.A.",
        "VGIR11 - VALORA CRI CDI FUNDO DE INVESTIMENTO IMOBILIARIO",
        "NCHB11 - FII NCH BRASIL RECEBIVEIS IMOBILIARIOS",
        "NCRA11 - NCH RECEBIVEIS DO AGRONEGOCIO – FIAGRO IMOBILIARIO",
        "RZAG11 - RIZA AGRO FIAGRO IMOB",
        "VGIA11 - VALORA CRA FIAGRO-IMOBILIARIO",
        "BBSE3 - BB SEGURIDADE PARTICIPACOES S.A.",
        "KLBN4 - KLABIN S/A",
        "TAEE4 - TRANSMISSORA ALIANCA DE ENERGIA ELETRICA S/A",
        "ITSA4 - ITAUSA S/A",
        "BPAC11 - BANCO BTG PACTUAL S/A",
        "CSMG3 - CIA SANEAMENTO DE MINAS GERAIS",
        "DIRR3 - DIRECIONAL ENGENHARIA S.A.",
        "JBSS3 - JBS S/A",
        "BRKM5 - BRASKEM S.A.",
        "MOVI3 - MOVIDA",
        "BRFS3 - BRF S.A.",
    ]

    for t in ativos_b3:
        consolidado, tipo = mapear_ticker_b3(t)
        print(f"{t.split(' - ')[0]:<10} → {consolidado:<10} | {tipo}")
