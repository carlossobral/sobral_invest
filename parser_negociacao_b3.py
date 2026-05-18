#!/usr/bin/env python3
"""
SOBRAL INVEST — Parser de Importacao B3 (Aba "Negociacao")
=============================================================
Processa arquivo Excel da aba NEGOCIACAO exportado do Canal do Investidor B3.

REGRAS:
- Opções: APENAS negociacoes (compra/venda no mercado)
- Exercicio de opcao: IGNORAR (é operacao de acoes no strike)
- Fracionario: remover sufixo F
- Corretoras: ignorar
- Renda fixa / Futuros: ignorar
"""

import re
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# ============================================================
# 1. ESTRUTURAS DE DADOS
# ============================================================

class TipoOperacao(Enum):
    COMPRA = "COMPRA"
    VENDA = "VENDA"
    COMPRA_OPCAO = "COMPRA_OPCAO"
    VENDA_OPCAO = "VENDA_OPCAO"
    COMPRA_FRACIONARIO = "COMPRA_FRACIONARIO"
    VENDA_FRACIONARIO = "VENDA_FRACIONARIO"
    IGNORAR = "IGNORAR"

class ClasseAtivo(Enum):
    ACAO = "ACAO"
    FII = "FII"
    FIAGRO = "FIAGRO"
    ETF = "ETF"
    BDR = "BDR"
    OPCAO = "OPCAO"
    RENDA_FIXA = "RENDA_FIXA"
    FUTURO = "FUTURO"
    DESCONHECIDO = "DESCONHECIDO"

@dataclass
class Operacao:
    """Operacao individual parseada do arquivo B3."""
    data: datetime
    tipo_operacao: TipoOperacao
    ticker_original: str
    ticker_consolidado: str
    classe: ClasseAtivo
    quantidade: float
    preco_unitario: float
    valor_total: float
    mercado: str = ""

    # Para opcoes
    tipo_opcao: Optional[str] = None  # CALL/PUT
    strike: Optional[float] = None
    vencimento: Optional[datetime] = None

    def __post_init__(self):
        # Normalizar quantidade (negativa para vendas)
        if self.tipo_operacao in [TipoOperacao.VENDA, TipoOperacao.VENDA_OPCAO, TipoOperacao.VENDA_FRACIONARIO]:
            self.quantidade = -abs(self.quantidade)

@dataclass
class PosicaoConsolidada:
    """Posicao consolidada de um ativo na carteira."""
    ticker: str
    classe: ClasseAtivo
    quantidade_total: float = 0
    custo_total: float = 0
    preco_medio: float = 0
    operacoes: List[Operacao] = field(default_factory=list)

    def adicionar_operacao(self, op: Operacao):
        self.operacoes.append(op)

        if op.tipo_operacao in [TipoOperacao.COMPRA, TipoOperacao.COMPRA_FRACIONARIO]:
            # Compra acao: aumenta posicao e custo
            novo_custo = self.custo_total + abs(op.valor_total)
            nova_qtd = self.quantidade_total + abs(op.quantidade)
            if nova_qtd > 0:
                self.preco_medio = novo_custo / nova_qtd
            self.custo_total = novo_custo
            self.quantidade_total = nova_qtd

        elif op.tipo_operacao in [TipoOperacao.VENDA, TipoOperacao.VENDA_FRACIONARIO]:
            # Venda acao: reduz posicao
            qtd_vendida = abs(op.quantidade)
            self.quantidade_total -= qtd_vendida
            if self.quantidade_total > 0:
                self.custo_total = self.quantidade_total * self.preco_medio
            else:
                self.custo_total = 0
                self.preco_medio = 0

        elif op.tipo_operacao in [TipoOperacao.COMPRA_OPCAO, TipoOperacao.VENDA_OPCAO]:
            # Opcoes: NAO consolidam na carteira de acoes
            # Sao derivativos - podemos logar separadamente
            pass


# ============================================================
# 2. MAPEAMENTO DE OPCOES (importar do mapeador_opcoes_b3)
# ============================================================

SERIES_MENSAIS = {
    'A': ('Janeiro', 'CALL'), 'B': ('Fevereiro', 'CALL'),
    'C': ('Marco', 'CALL'), 'D': ('Abril', 'CALL'),
    'E': ('Maio', 'CALL'), 'F': ('Junho', 'CALL'),
    'G': ('Julho', 'CALL'), 'H': ('Agosto', 'CALL'),
    'I': ('Setembro', 'CALL'), 'J': ('Outubro', 'CALL'),
    'K': ('Novembro', 'CALL'), 'L': ('Dezembro', 'CALL'),
    'M': ('Janeiro', 'PUT'), 'N': ('Fevereiro', 'PUT'),
    'O': ('Marco', 'PUT'), 'P': ('Abril', 'PUT'),
    'Q': ('Maio', 'PUT'), 'R': ('Junho', 'PUT'),
    'S': ('Julho', 'PUT'), 'T': ('Agosto', 'PUT'),
    'U': ('Setembro', 'PUT'), 'V': ('Outubro', 'PUT'),
    'W': ('Novembro', 'PUT'), 'X': ('Dezembro', 'PUT'),
}

def is_opcao(ticker: str) -> bool:
    """Verifica se o ticker eh uma opcao."""
    t = ticker.strip().upper()
    if t.endswith('E'):  # Exercicio europeu
        t = t[:-1]
    return bool(
        re.match(r'^[A-Z]{4}[A-Z]\d{2,3}$', t) or
        re.match(r'^[A-Z]{4}[A-Z]\d+W\d$', t)
    )

def parse_opcao(ticker: str) -> dict:
    """Parse um ticker de opcao."""
    t = ticker.strip().upper()
    exercicio_europeu = t.endswith('E')
    if exercicio_europeu:
        t = t[:-1]

    semanal = 'W' in t

    if semanal:
        match = re.match(r'^([A-Z]{4})([A-Z])(\d+)(W)(\d)$', t)
        if not match:
            return None
        ativo_cod, serie, strike_str, _, semana_str = match.groups()
    else:
        match = re.match(r'^([A-Z]{4})([A-Z])(\d{2,3})$', t)
        if not match:
            return None
        ativo_cod, serie, strike_str = match.groups()

    info_serie = SERIES_MENSAIS.get(serie)
    if not info_serie:
        return None

    mes_vencimento, tipo = info_serie

    try:
        strike = float(strike_str)
        if len(strike_str) == 3:
            strike = strike / 10
    except:
        strike = None

    return {
        'ativo_cod': ativo_cod,
        'tipo': tipo,
        'mes_vencimento': mes_vencimento,
        'strike': strike,
        'semanal': semanal,
        'exercicio_europeu': exercicio_europeu
    }

def get_ativo_base(ticker: str) -> Optional[str]:
    """Retorna o ativo-base para uma opcao."""
    info = parse_opcao(ticker)
    if not info:
        return None

    # Mapeamento basico (expandir conforme necessario)
    MAPEAMENTO_BASE = {
        'PETR': 'PETR4', 'VALE': 'VALE3', 'ITUB': 'ITUB4',
        'BBDC': 'BBDC4', 'BBAS': 'BBAS3', 'WEGE': 'WEGE3',
        'MGLU': 'MGLU3', 'GGBR': 'GGBR4', 'USIM': 'USIM5',
        'CSNA': 'CSNA3', 'KLBN': 'KLBN4', 'SUZB': 'SUZB3',
        'RAIL': 'RAIL3', 'SBSP': 'SBSP3', 'EQTL': 'EQTL3',
        'CPLE': 'CPLE3', 'CMIG': 'CMIG4', 'TAEE': 'TAEE11',
        'TRPL': 'TRPL4', 'ENBR': 'ENBR3', 'EGIE': 'EGIE3',
        'CPFE': 'CPFE3', 'AESB': 'AESB3', 'NEOE': 'NEOE3',
        'ELET': 'ELET3', 'ENEV': 'ENEV3', 'RAIZ': 'RAIZ4',
        'PRIO': 'PRIO3', 'RECV': 'RECV3', 'VBBR': 'VBBR3',
        'BRAV': 'BRAV3', 'RRRP': 'RRRP3', 'CSAN': 'CSAN3',
        'UGPA': 'UGPA3', 'VIVT': 'VIVT3', 'TIMS': 'TIMS3',
        'OIBR': 'OIBR3', 'TOTS': 'TOTS3', 'LREN': 'LREN3',
        'AMER': 'AMER3', 'CEAB': 'CEAB3', 'GUAR': 'GUAR3',
        'ALPA': 'ALPA4', 'PTNT': 'PTNT4', 'TFCO': 'TFCO4',
        'CAML': 'CAML3', 'MDIA': 'MDIA3', 'SMTO': 'SMTO3',
        'SLCE': 'SLCE3', 'SOJA': 'SOJA3', 'AGXY': 'AGXY3',
        'JALL': 'JALL3', 'BEEF': 'BEEF3', 'JBSS': 'JBSS3',
        'BRFS': 'BRFS3', 'MRFG': 'MRFG3', 'POMO': 'POMO4',
        'RAPT': 'RAPT4', 'TUPY': 'TUPY3', 'LEVE': 'LEVE3',
        'MYPK': 'MYPK3', 'EMBR': 'EMBR3', 'AZUL': 'AZUL3',
        'GOLL': 'GOLL4', 'CVCB': 'CVCB3', 'RENT': 'RENT3',
        'VAMO': 'VAMO3', 'MOVI': 'MOVI3', 'ARML': 'ARML3',
        'SYNE': 'SYNE3', 'ESPA': 'ESPA3', 'FLRY': 'FLRY3',
        'PARD': 'PARD3', 'RADL': 'RADL3', 'HYPE': 'HYPE3',
        'PNVL': 'PNVL3', 'PGMN': 'PGMN3', 'BLAU': 'BLAU3',
        'BIOM': 'BIOM3', 'WIZS': 'WIZS3', 'LWSA': 'LWSA3',
        'IFCM': 'IFCM3', 'CASH': 'CASH3', 'DOTZ': 'DOTZ3',
        'BOAS': 'BOAS3', 'DTCY': 'DTCY3', 'VIVR': 'VIVR3',
        'HBOR': 'HBOR3', 'CYRE': 'CYRE3', 'DIRR': 'DIRR3',
        'EZTC': 'EZTC3', 'JHSF': 'JHSF3', 'LAVV': 'LAVV3',
        'MTRE': 'MTRE3', 'TEND': 'TEND3', 'TRIS': 'TRIS3',
        'ALUP': 'ALUP11', 'AURE': 'AURE3', 'CEBR': 'CEBR3',
        'CLSC': 'CLSC4', 'CMIN': 'CMIN3', 'COCE': 'COCE3',
        'CSMG': 'CSMG3', 'ENGI': 'ENGI11', 'EQPA': 'EQPA3',
        'LIGT': 'LIGT3', 'RNEW': 'RNEW4', 'SAPR': 'SAPR4',
        'SRNA': 'SRNA3', 'BAZA': 'BAZA3', 'BMIN': 'BMIN4',
        'BMEB': 'BMEB4', 'BRSR': 'BRSR6', 'BBSE': 'BBSE3',
        'BPAC': 'BPAC11', 'BRBI': 'BRBI11', 'BSLI': 'BSLI4',
        'ITSA': 'ITSA4', 'PSSA': 'PSSA3', 'SANB': 'SANB11',
        'WEST': 'WEST3', 'AMAR': 'AMAR3', 'BEES': 'BEES4',
        'BGIP': 'BGIP4', 'BPAR': 'BPAR3', 'BRGE': 'BRGE11',
        'CEEB': 'CEEB3', 'CRPG': 'CRPG5', 'CSAB': 'CSAB4',
        'CTKA': 'CTKA4', 'CTNM': 'CTNM4', 'CTSA': 'CTSA4',
        'DEXP': 'DEXP3', 'DOHL': 'DOHL4', 'EALT': 'EALT4',
        'ECOR': 'ECOR3', 'ENAT': 'ENAT3', 'ENJU': 'ENJU3',
        'EPAR': 'EPAR3', 'EUCA': 'EUCA3', 'EVEN': 'EVEN3',
        'FESA': 'FESA4', 'FICT': 'FICT3', 'FRAS': 'FRAS3',
        'GFSA': 'GFSA3', 'GPAR': 'GPAR3', 'GPIV': 'GPIV33',
        'GRND': 'GRND3', 'HAGA': 'HAGA4', 'HOOT': 'HOOT4',
        'IGBR': 'IGBR3', 'IGTI': 'IGTI11', 'INEP': 'INEP3',
        'IRBR': 'IRBR3', 'JBDU': 'JBDU4', 'JFEN': 'JFEN3',
        'JOPA': 'JOPA4', 'JSLG': 'JSLG3', 'KEPL': 'KEPL3',
        'LAND': 'LAND3', 'LOGG': 'LOGG3', 'LOGN': 'LOGN3',
        'LPSB': 'LPSB3', 'LUPA': 'LUPA3', 'LUXM': 'LUXM4',
        'LVTC': 'LVTC3', 'MATD': 'MATD3', 'MILS': 'MILS3',
        'MLAS': 'MLAS3', 'MNPR': 'MNPR3', 'MOUR': 'MOUR3',
        'MRSA': 'MRSA3B', 'MRVE': 'MRVE3', 'MTSA': 'MTSA4',
        'MWET': 'MWET4', 'NORD': 'NORD3', 'NRTQ': 'NRTQ3',
        'NTCO': 'NTCO3', 'ODPV': 'ODPV3', 'OPCT': 'OPCT3',
        'ORVR': 'ORVR3', 'PATI': 'PATI4', 'PEAB': 'PEAB4',
        'PETZ': 'PETZ3', 'PFRM': 'PFRM3', 'PINE': 'PINE4',
        'PLAS': 'PLAS3', 'PMAM': 'PMAM3', 'QUAL': 'QUAL3',
        'RANI': 'RANI3', 'RDNI': 'RDNI3', 'RDOR': 'RDOR3',
        'REDE': 'REDE3', 'ROMI': 'ROMI3', 'RPAD': 'RPAD3',
        'RPMG': 'RPMG3', 'RSID': 'RSID3', 'RSUL': 'RSUL4',
        'SCAR': 'SCAR3', 'SEQL': 'SEQL3', 'SHOW': 'SHOW3',
        'SHUL': 'SHUL4', 'SOND': 'SOND5', 'SQIA': 'SQIA3',
        'STBP': 'STBP3', 'SULA': 'SULA11', 'TGMA': 'TGMA3',
        'TIMP': 'TIMP3', 'TPIS': 'TPIS3', 'UCAS': 'UCAS3',
        'UNIP': 'UNIP6', 'VSTE': 'VSTE3', 'VULC': 'VULC3',
        'VVAR': 'VVAR3', 'WDCN': 'WDCN3', 'WHRL': 'WHRL4',
        'WIZC': 'WIZC3', 'YDUQ': 'YDUQ3',
        # ETFs
        'BOVA': 'BOVA11', 'BOVV': 'BOVV11', 'SMAL': 'SMAL11',
        'HASH': 'HASH11', 'NASD': 'NASD11', 'TECK': 'TECK11',
        # BDRs
        'AAPL': 'AAPL34', 'MSFT': 'MSFT34', 'AMZO': 'AMZO34',
        'GOGL': 'GOGL34', 'TSLA': 'TSLA34', 'META': 'META34',
    }

    return MAPEAMENTO_BASE.get(info['ativo_cod'])


# ============================================================
# 3. CLASSIFICACAO
# ============================================================

def classificar_negociacao(row: pd.Series) -> Tuple[TipoOperacao, ClasseAtivo, str]:
    """
    Classifica uma linha da aba NEGOCIACAO.

    Returns:
        (TipoOperacao, ClasseAtivo, ticker_consolidado)
    """
    mercado = str(row.get('Mercado', '')).strip()
    tipo_mov = str(row.get('Tipo de Movimentacao', '')).strip().upper()
    ticker = str(row.get('Codigo de Negociacao', '')).strip().upper()

    # 1. IGNORAR EXERCICIO DE OPCAO
    # Exercicio = operacao de acoes (ativo-base), NAO de opcoes
    if 'Exercicio' in mercado:
        return TipoOperacao.IGNORAR, ClasseAtivo.ACAO, ticker

    # 2. IGNORAR FUTUROS
    if 'Futuro' in mercado:
        return TipoOperacao.IGNORAR, ClasseAtivo.FUTURO, ticker

    # 3. REMOVER SUFIXO F (fracionario)
    ticker_limpo = ticker.replace('F', '')

    # 4. VERIFICAR SE EH OPCAO (negociacao)
    if 'Opcao de Compra' in mercado:
        ativo_base = get_ativo_base(ticker_limpo)
        if tipo_mov == 'COMPRA':
            return TipoOperacao.COMPRA_OPCAO, ClasseAtivo.OPCAO, ativo_base or ticker_limpo
        else:
            return TipoOperacao.VENDA_OPCAO, ClasseAtivo.OPCAO, ativo_base or ticker_limpo

    if 'Opcao de Venda' in mercado:
        ativo_base = get_ativo_base(ticker_limpo)
        if tipo_mov == 'COMPRA':
            return TipoOperacao.COMPRA_OPCAO, ClasseAtivo.OPCAO, ativo_base or ticker_limpo
        else:
            return TipoOperacao.VENDA_OPCAO, ClasseAtivo.OPCAO, ativo_base or ticker_limpo

    # 5. ACOES / FIIs / ETFs / BDRs (Mercado a Vista / Fracionario)
    classe = classificar_ativo(ticker_limpo)

    if 'Fracionario' in mercado:
        if tipo_mov == 'COMPRA':
            return TipoOperacao.COMPRA_FRACIONARIO, classe, ticker_limpo
        else:
            return TipoOperacao.VENDA_FRACIONARIO, classe, ticker_limpo
    else:
        # Mercado a Vista
        if tipo_mov == 'COMPRA':
            return TipoOperacao.COMPRA, classe, ticker_limpo
        else:
            return TipoOperacao.VENDA, classe, ticker_limpo


def classificar_ativo(ticker: str) -> ClasseAtivo:
    """Classifica o ativo pela classe."""
    t = ticker.upper()

    # FIAGRO
    if any(x in t for x in ['AGRO', 'CRA', 'CRI']) and t.endswith('11'):
        return ClasseAtivo.FIAGRO

    # ETF
    etfs = ['BOVA11', 'BOVV11', 'SMAL11', 'HASH11', 'NASD11', 'TECK11', 
            'ECOO11', 'FIND11', 'MATB11', 'ISUS11', 'GOVE11', 'FIXA11',
            'XINA11', 'EMEG11', 'EURP11', 'ASIA11', 'MILL11']
    if t in etfs:
        return ClasseAtivo.ETF

    # BDR
    if t.endswith('34') or t.endswith('33') or t.endswith('35'):
        return ClasseAtivo.BDR

    # FII (termina em 11, mas nao eh ETF)
    if t.endswith('11'):
        return ClasseAtivo.FII

    # ACAO (padrao)
    if t.endswith('3') or t.endswith('4') or t.endswith('5') or t.endswith('6'):
        return ClasseAtivo.ACAO

    return ClasseAtivo.DESCONHECIDO


# ============================================================
# 4. PARSER PRINCIPAL
# ============================================================

class ParserNegociacaoB3:
    """Parser da aba NEGOCIACAO do arquivo B3."""

    def __init__(self, caminho_arquivo: str):
        self.caminho = caminho_arquivo
        self.df: Optional[pd.DataFrame] = None
        self.operacoes: List[Operacao] = []
        self.posicoes_acoes: Dict[str, PosicaoConsolidada] = {}
        self.operacoes_opcoes: List[Operacao] = []  # Log separado para opcoes
        self.ignorados: List[Dict] = []

    def carregar(self) -> 'ParserNegociacaoB3':
        """Carrega o arquivo Excel da B3 (aba NEGOCIACAO)."""
        print(f"Carregando: {self.caminho}")

        xls = pd.ExcelFile(self.caminho)

        # Procurar aba de Negociacao
        aba_neg = None
        for aba in xls.sheet_names:
            if 'negoci' in aba.lower():
                aba_neg = aba
                break

        if not aba_neg:
            aba_neg = xls.sheet_names[0]

        self.df = pd.read_excel(self.caminho, sheet_name=aba_neg)

        # Remover linhas de cabecalho duplicadas
        self.df = self.df[self.df['Data do Negocio'] != 'Data do Negocio']

        print(f"Total de registros: {len(self.df)}")
        return self

    def parse(self) -> 'ParserNegociacaoB3':
        """Parse todas as operacoes."""
        if self.df is None:
            raise ValueError("Arquivo nao carregado. Execute .carregar() primeiro.")

        for idx, row in self.df.iterrows():
            try:
                tipo_op, classe, ticker_consolidado = classificar_negociacao(row)

                if tipo_op == TipoOperacao.IGNORAR:
                    self.ignorados.append({
                        'linha': idx,
                        'motivo': 'Exercicio/Futuro/RendaFixa',
                        'ticker': row.get('Codigo de Negociacao', ''),
                        'mercado': row.get('Mercado', '')
                    })
                    continue

                # Parse data
                data_str = str(row.get('Data do Negocio', ''))
                try:
                    data = pd.to_datetime(data_str, dayfirst=True)
                except:
                    data = datetime.now()

                # Parse vencimento (para opcoes)
                vencimento = None
                prazo = str(row.get('Prazo/Vencimento', '')).strip()
                if prazo and prazo != '-':
                    try:
                        vencimento = pd.to_datetime(prazo, dayfirst=True)
                    except:
                        pass

                # Parse valores
                quantidade = float(row.get('Quantidade', 0))
                preco = float(row.get('Preco', 0))
                valor = float(row.get('Valor', 0))

                ticker_original = str(row.get('Codigo de Negociacao', '')).strip().upper()

                # Criar operacao
                operacao = Operacao(
                    data=data,
                    tipo_operacao=tipo_op,
                    ticker_original=ticker_original,
                    ticker_consolidado=ticker_consolidado,
                    classe=classe,
                    quantidade=quantidade,
                    preco_unitario=preco,
                    valor_total=valor,
                    mercado=str(row.get('Mercado', ''))
                )

                # Adicionar info de opcao se aplicavel
                if classe == ClasseAtivo.OPCAO:
                    info_op = parse_opcao(ticker_original)
                    if info_op:
                        operacao.tipo_opcao = info_op['tipo']
                        operacao.strike = info_op['strike']
                        operacao.vencimento = vencimento
                    self.operacoes_opcoes.append(operacao)
                else:
                    self.operacoes.append(operacao)

                    # Consolidar posicao de acao
                    if ticker_consolidado not in self.posicoes_acoes:
                        self.posicoes_acoes[ticker_consolidado] = PosicaoConsolidada(
                            ticker=ticker_consolidado,
                            classe=classe
                        )

                    self.posicoes_acoes[ticker_consolidado].adicionar_operacao(operacao)

            except Exception as e:
                print(f"Erro na linha {idx}: {e}")
                continue

        print(f"\n{'='*60}")
        print("RESUMO DO PARSE")
        print(f"{'='*60}")
        print(f"Operacoes de acoes: {len(self.operacoes)}")
        print(f"Operacoes de opcoes (derivativos): {len(self.operacoes_opcoes)}")
        print(f"Posicoes consolidadas: {len(self.posicoes_acoes)}")
        print(f"Registros ignorados: {len(self.ignorados)}")

        return self

    def get_resumo_acoes(self) -> pd.DataFrame:
        """Retorna DataFrame com posicoes consolidadas de acoes."""
        dados = []
        for ticker, pos in self.posicoes_acoes.items():
            dados.append({
                'Ticker': ticker,
                'Classe': pos.classe.value,
                'Quantidade': pos.quantidade_total,
                'Preco Medio': round(pos.preco_medio, 4),
                'Custo Total': round(pos.custo_total, 2),
                'Operacoes': len(pos.operacoes)
            })

        df = pd.DataFrame(dados)
        if not df.empty:
            df = df.sort_values('Custo Total', ascending=False)
        return df

    def get_operacoes_opcoes_df(self) -> pd.DataFrame:
        """Retorna DataFrame com operacoes de opcoes (derivativos)."""
        dados = []
        for op in self.operacoes_opcoes:
            dados.append({
                'Data': op.data,
                'Tipo': op.tipo_operacao.value,
                'Ticker Original': op.ticker_original,
                'Ativo Base': op.ticker_consolidado,
                'Tipo Opcao': op.tipo_opcao,
                'Strike': op.strike,
                'Vencimento': op.vencimento,
                'Quantidade': op.quantidade,
                'Preco': op.preco_unitario,
                'Valor Total': op.valor_total,
                'Mercado': op.mercado
            })

        return pd.DataFrame(dados)

    def get_operacoes_acoes_df(self) -> pd.DataFrame:
        """Retorna DataFrame com operacoes de acoes."""
        dados = []
        for op in self.operacoes:
            dados.append({
                'Data': op.data,
                'Tipo': op.tipo_operacao.value,
                'Ticker': op.ticker_consolidado,
                'Classe': op.classe.value,
                'Quantidade': op.quantidade,
                'Preco': op.preco_unitario,
                'Valor Total': op.valor_total,
                'Mercado': op.mercado
            })

        return pd.DataFrame(dados)

    def exportar_para_sql(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Retorna operacoes formatadas para insercao no banco.

        Returns:
            (operacoes_acoes, operacoes_opcoes)
        """
        acoes = []
        for op in self.operacoes:
            acoes.append({
                'data_aquisicao': op.data.date(),
                'ticker': op.ticker_consolidado,
                'quantidade': abs(op.quantidade),
                'preco_medio': op.preco_unitario,
                'custo_total': abs(op.valor_total),
                'tipo_operacao': 'COMPRA' if 'COMPRA' in op.tipo_operacao.value else 'VENDA',
                'origem': 'B3_NEGOCIACAO'
            })

        opcoes = []
        for op in self.operacoes_opcoes:
            opcoes.append({
                'data': op.data.date(),
                'ticker_original': op.ticker_original,
                'ativo_base': op.ticker_consolidado,
                'tipo_opcao': op.tipo_opcao,
                'strike': op.strike,
                'vencimento': op.vencimento.date() if op.vencimento else None,
                'quantidade': abs(op.quantidade),
                'preco': op.preco_unitario,
                'valor_total': abs(op.valor_total),
                'tipo_operacao': 'COMPRA' if 'COMPRA' in op.tipo_operacao.value else 'VENDA',
                'origem': 'B3_NEGOCIACAO'
            })

        return acoes, opcoes


# ============================================================
# 5. EXECUCAO
# ============================================================

if __name__ == "__main__":
    # Exemplo de uso
    parser = ParserNegociacaoB3("negociacao-2026-05-18-16-09-42.xlsx")
    parser.carregar().parse()

    print("\n" + "="*60)
    print("POSICOES CONSOLIDADAS (ACOES)")
    print("="*60)
    print(parser.get_resumo_acoes().to_string(index=False))

    print("\n" + "="*60)
    print("OPERACOES DE OPCOES (DERIVATIVOS)")
    print("="*60)
    df_opcoes = parser.get_operacoes_opcoes_df()
    if not df_opcoes.empty:
        print(df_opcoes.to_string(index=False))
    else:
        print("Nenhuma operacao de opcoes encontrada.")

    print("\n" + "="*60)
    print("IGNORADOS")
    print("="*60)
    for ign in parser.ignorados[:10]:
        print(f"  - {ign['ticker']}: {ign['motivo']} ({ign['mercado']})")
