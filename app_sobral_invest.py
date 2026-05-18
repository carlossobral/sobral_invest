import streamlit as st
import pandas as pd
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Sobral Invest",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS custom - tema terminal escuro
st.markdown("""
<style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3 { color: #58a6ff !important; font-family: 'Courier New', monospace; }
    .stDataFrame { background-color: #161b22; border: 1px solid #30363d; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 10px; }
    .stMetric label { color: #8b949e !important; }
    .stMetric div { color: #c9d1d9 !important; font-family: 'Courier New', monospace; font-size: 1.5rem; font-weight: bold; }
    .stButton>button { background-color: #238636; color: white; border: 1px solid #2ea043; font-family: 'Courier New', monospace; }
    .stButton>button:hover { background-color: #2ea043; }
    .stFileUploader { background-color: #161b22; border: 2px dashed #30363d; border-radius: 6px; padding: 20px; }
    div[data-testid="stMarkdownContainer"] { font-family: 'Courier New', monospace; }
    .info-box { background-color: #1f6feb20; border: 1px solid #58a6ff; border-radius: 6px; padding: 15px; margin: 10px 0; }
    .success-box { background-color: #23863620; border: 1px solid #2ea043; border-radius: 6px; padding: 15px; margin: 10px 0; }
    .warning-box { background-color: #d2992220; border: 1px solid #d29922; border-radius: 6px; padding: 15px; margin: 10px 0; }
    .error-box { background-color: #da363320; border: 1px solid #f85149; border-radius: 6px; padding: 15px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONEXÃO COM BANCO DE DADOS
# ============================================================

@st.cache_resource
def get_db_engine():
    """Cria engine de conexão com PostgreSQL (Supabase)."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        st.error("DATABASE_URL não configurada. Configure no Render Dashboard.")
        return None
    return create_engine(db_url)

def test_connection():
    """Testa conexão com o banco."""
    try:
        engine = get_db_engine()
        if not engine:
            return False
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            return True
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return False

# ============================================================
# IMPORTAR PARSER (copiar código do parser aqui para evitar import)
# ============================================================

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

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
    data: datetime
    tipo_operacao: TipoOperacao
    ticker_original: str
    ticker_consolidado: str
    classe: ClasseAtivo
    quantidade: float
    preco_unitario: float
    valor_total: float
    mercado: str = ""
    tipo_opcao: Optional[str] = None
    strike: Optional[float] = None
    vencimento: Optional[datetime] = None

    def __post_init__(self):
        if self.tipo_operacao in [TipoOperacao.VENDA, TipoOperacao.VENDA_OPCAO, TipoOperacao.VENDA_FRACIONARIO]:
            self.quantidade = -abs(self.quantidade)

@dataclass
class PosicaoConsolidada:
    ticker: str
    classe: ClasseAtivo
    quantidade_total: float = 0
    custo_total: float = 0
    preco_medio: float = 0
    operacoes: List[Operacao] = field(default_factory=list)

    def adicionar_operacao(self, op: Operacao):
        self.operacoes.append(op)
        if op.tipo_operacao in [TipoOperacao.COMPRA, TipoOperacao.COMPRA_FRACIONARIO]:
            novo_custo = self.custo_total + abs(op.valor_total)
            nova_qtd = self.quantidade_total + abs(op.quantidade)
            if nova_qtd > 0:
                self.preco_medio = novo_custo / nova_qtd
            self.custo_total = novo_custo
            self.quantidade_total = nova_qtd
        elif op.tipo_operacao in [TipoOperacao.VENDA, TipoOperacao.VENDA_FRACIONARIO]:
            qtd_vendida = abs(op.quantidade)
            self.quantidade_total -= qtd_vendida
            if self.quantidade_total > 0:
                self.custo_total = self.quantidade_total * self.preco_medio
            else:
                self.custo_total = 0
                self.preco_medio = 0

# Mapeamento de opções
SERIES_MENSAIS = {
    'A': ('Janeiro', 'CALL'), 'B': ('Fevereiro', 'CALL'), 'C': ('Marco', 'CALL'),
    'D': ('Abril', 'CALL'), 'E': ('Maio', 'CALL'), 'F': ('Junho', 'CALL'),
    'G': ('Julho', 'CALL'), 'H': ('Agosto', 'CALL'), 'I': ('Setembro', 'CALL'),
    'J': ('Outubro', 'CALL'), 'K': ('Novembro', 'CALL'), 'L': ('Dezembro', 'CALL'),
    'M': ('Janeiro', 'PUT'), 'N': ('Fevereiro', 'PUT'), 'O': ('Marco', 'PUT'),
    'P': ('Abril', 'PUT'), 'Q': ('Maio', 'PUT'), 'R': ('Junho', 'PUT'),
    'S': ('Julho', 'PUT'), 'T': ('Agosto', 'PUT'), 'U': ('Setembro', 'PUT'),
    'V': ('Outubro', 'PUT'), 'W': ('Novembro', 'PUT'), 'X': ('Dezembro', 'PUT'),
}

def is_opcao(ticker: str) -> bool:
    t = ticker.strip().upper()
    if t.endswith('E'): t = t[:-1]
    return bool(re.match(r'^[A-Z]{4}[A-Z]\d{2,3}$', t) or re.match(r'^[A-Z]{4}[A-Z]\d+W\d$', t))

def parse_opcao(ticker: str) -> dict:
    t = ticker.strip().upper()
    exercicio_europeu = t.endswith('E')
    if exercicio_europeu: t = t[:-1]
    semanal = 'W' in t
    if semanal:
        match = re.match(r'^([A-Z]{4})([A-Z])(\d+)(W)(\d)$', t)
        if not match: return None
        ativo_cod, serie, strike_str, _, semana_str = match.groups()
    else:
        match = re.match(r'^([A-Z]{4})([A-Z])(\d{2,3})$', t)
        if not match: return None
        ativo_cod, serie, strike_str = match.groups()
    info_serie = SERIES_MENSAIS.get(serie)
    if not info_serie: return None
    mes_vencimento, tipo = info_serie
    try:
        strike = float(strike_str)
        if len(strike_str) == 3: strike = strike / 10
    except: strike = None
    return {'ativo_cod': ativo_cod, 'tipo': tipo, 'mes_vencimento': mes_vencimento, 'strike': strike, 'semanal': semanal, 'exercicio_europeu': exercicio_europeu}

def get_ativo_base(ticker: str) -> Optional[str]:
    info = parse_opcao(ticker)
    if not info: return None
    MAPEAMENTO_BASE = {
        'PETR': 'PETR4', 'VALE': 'VALE3', 'ITUB': 'ITUB4', 'BBDC': 'BBDC4',
        'BBAS': 'BBAS3', 'WEGE': 'WEGE3', 'MGLU': 'MGLU3', 'GGBR': 'GGBR4',
        'USIM': 'USIM5', 'CSNA': 'CSNA3', 'KLBN': 'KLBN4', 'SUZB': 'SUZB3',
        'RAIL': 'RAIL3', 'SBSP': 'SBSP3', 'EQTL': 'EQTL3', 'CPLE': 'CPLE3',
        'CMIG': 'CMIG4', 'TAEE': 'TAEE11', 'TRPL': 'TRPL4', 'ENBR': 'ENBR3',
        'EGIE': 'EGIE3', 'CPFE': 'CPFE3', 'AESB': 'AESB3', 'NEOE': 'NEOE3',
        'ELET': 'ELET3', 'ENEV': 'ENEV3', 'RAIZ': 'RAIZ4', 'PRIO': 'PRIO3',
        'RECV': 'RECV3', 'VBBR': 'VBBR3', 'BRAV': 'BRAV3', 'RRRP': 'RRRP3',
        'CSAN': 'CSAN3', 'UGPA': 'UGPA3', 'VIVT': 'VIVT3', 'TIMS': 'TIMS3',
        'OIBR': 'OIBR3', 'TOTS': 'TOTS3', 'LREN': 'LREN3', 'AMER': 'AMER3',
        'CEAB': 'CEAB3', 'GUAR': 'GUAR3', 'ALPA': 'ALPA4', 'PTNT': 'PTNT4',
        'TFCO': 'TFCO4', 'CAML': 'CAML3', 'MDIA': 'MDIA3', 'SMTO': 'SMTO3',
        'SLCE': 'SLCE3', 'SOJA': 'SOJA3', 'AGXY': 'AGXY3', 'JALL': 'JALL3',
        'BEEF': 'BEEF3', 'JBSS': 'JBSS3', 'BRFS': 'BRFS3', 'MRFG': 'MRFG3',
        'POMO': 'POMO4', 'RAPT': 'RAPT4', 'TUPY': 'TUPY3', 'LEVE': 'LEVE3',
        'MYPK': 'MYPK3', 'EMBR': 'EMBR3', 'AZUL': 'AZUL3', 'GOLL': 'GOLL4',
        'CVCB': 'CVCB3', 'RENT': 'RENT3', 'VAMO': 'VAMO3', 'MOVI': 'MOVI3',
        'ARML': 'ARML3', 'SYNE': 'SYNE3', 'ESPA': 'ESPA3', 'FLRY': 'FLRY3',
        'PARD': 'PARD3', 'RADL': 'RADL3', 'HYPE': 'HYPE3', 'PNVL': 'PNVL3',
        'PGMN': 'PGMN3', 'BLAU': 'BLAU3', 'BIOM': 'BIOM3', 'WIZS': 'WIZS3',
        'LWSA': 'LWSA3', 'IFCM': 'IFCM3', 'CASH': 'CASH3', 'DOTZ': 'DOTZ3',
        'BOAS': 'BOAS3', 'DTCY': 'DTCY3', 'VIVR': 'VIVR3', 'HBOR': 'HBOR3',
        'CYRE': 'CYRE3', 'DIRR': 'DIRR3', 'EZTC': 'EZTC3', 'JHSF': 'JHSF3',
        'LAVV': 'LAVV3', 'MTRE': 'MTRE3', 'TEND': 'TEND3', 'TRIS': 'TRIS3',
        'ALUP': 'ALUP11', 'AURE': 'AURE3', 'CEBR': 'CEBR3', 'CLSC': 'CLSC4',
        'CMIN': 'CMIN3', 'COCE': 'COCE3', 'CSMG': 'CSMG3', 'ENGI': 'ENGI11',
        'EQPA': 'EQPA3', 'LIGT': 'LIGT3', 'RNEW': 'RNEW4', 'SAPR': 'SAPR4',
        'SRNA': 'SRNA3', 'BAZA': 'BAZA3', 'BMIN': 'BMIN4', 'BMEB': 'BMEB4',
        'BRSR': 'BRSR6', 'BBSE': 'BBSE3', 'BPAC': 'BPAC11', 'BRBI': 'BRBI11',
        'BSLI': 'BSLI4', 'ITSA': 'ITSA4', 'PSSA': 'PSSA3', 'SANB': 'SANB11',
        'WEST': 'WEST3', 'AMAR': 'AMAR3', 'BEES': 'BEES4', 'BGIP': 'BGIP4',
        'BPAR': 'BPAR3', 'BRGE': 'BRGE11', 'CEEB': 'CEEB3', 'CRPG': 'CRPG5',
        'CSAB': 'CSAB4', 'CTKA': 'CTKA4', 'CTNM': 'CTNM4', 'CTSA': 'CTSA4',
        'DEXP': 'DEXP3', 'DOHL': 'DOHL4', 'EALT': 'EALT4', 'ECOR': 'ECOR3',
        'ENAT': 'ENAT3', 'ENJU': 'ENJU3', 'EPAR': 'EPAR3', 'EUCA': 'EUCA3',
        'EVEN': 'EVEN3', 'FESA': 'FESA4', 'FICT': 'FICT3', 'FRAS': 'FRAS3',
        'GFSA': 'GFSA3', 'GPAR': 'GPAR3', 'GPIV': 'GPIV33', 'GRND': 'GRND3',
        'HAGA': 'HAGA4', 'HOOT': 'HOOT4', 'IGBR': 'IGBR3', 'IGTI': 'IGTI11',
        'INEP': 'INEP3', 'IRBR': 'IRBR3', 'JBDU': 'JBDU4', 'JFEN': 'JFEN3',
        'JOPA': 'JOPA4', 'JSLG': 'JSLG3', 'KEPL': 'KEPL3', 'LAND': 'LAND3',
        'LOGG': 'LOGG3', 'LOGN': 'LOGN3', 'LPSB': 'LPSB3', 'LUPA': 'LUPA3',
        'LUXM': 'LUXM4', 'LVTC': 'LVTC3', 'MATD': 'MATD3', 'MILS': 'MILS3',
        'MLAS': 'MLAS3', 'MNPR': 'MNPR3', 'MOUR': 'MOUR3', 'MRSA': 'MRSA3B',
        'MRVE': 'MRVE3', 'MTSA': 'MTSA4', 'MWET': 'MWET4', 'NORD': 'NORD3',
        'NRTQ': 'NRTQ3', 'NTCO': 'NTCO3', 'ODPV': 'ODPV3', 'OPCT': 'OPCT3',
        'ORVR': 'ORVR3', 'PATI': 'PATI4', 'PEAB': 'PEAB4', 'PETZ': 'PETZ3',
        'PFRM': 'PFRM3', 'PINE': 'PINE4', 'PLAS': 'PLAS3', 'PMAM': 'PMAM3',
        'QUAL': 'QUAL3', 'RANI': 'RANI3', 'RDNI': 'RDNI3', 'RDOR': 'RDOR3',
        'REDE': 'REDE3', 'ROMI': 'ROMI3', 'RPAD': 'RPAD3', 'RPMG': 'RPMG3',
        'RSID': 'RSID3', 'RSUL': 'RSUL4', 'SCAR': 'SCAR3', 'SEQL': 'SEQL3',
        'SHOW': 'SHOW3', 'SHUL': 'SHUL4', 'SOND': 'SOND5', 'SQIA': 'SQIA3',
        'STBP': 'STBP3', 'SULA': 'SULA11', 'TGMA': 'TGMA3', 'TIMP': 'TIMP3',
        'TPIS': 'TPIS3', 'UCAS': 'UCAS3', 'UNIP': 'UNIP6', 'VSTE': 'VSTE3',
        'VULC': 'VULC3', 'VVAR': 'VVAR3', 'WDCN': 'WDCN3', 'WHRL': 'WHRL4',
        'WIZC': 'WIZC3', 'YDUQ': 'YDUQ3',
        'BOVA': 'BOVA11', 'BOVV': 'BOVV11', 'SMAL': 'SMAL11',
        'HASH': 'HASH11', 'NASD': 'NASD11', 'TECK': 'TECK11',
        'AAPL': 'AAPL34', 'MSFT': 'MSFT34', 'AMZO': 'AMZO34',
        'GOGL': 'GOGL34', 'TSLA': 'TSLA34', 'META': 'META34',
    }
    return MAPEAMENTO_BASE.get(info['ativo_cod'])

def classificar_negociacao(row: pd.Series) -> Tuple[TipoOperacao, ClasseAtivo, str]:
    mercado = str(row.get('Mercado', '')).strip()
    tipo_mov = str(row.get('Tipo de Movimentacao', '')).strip().upper()
    ticker = str(row.get('Codigo de Negociacao', '')).strip().upper()

    if 'Exercicio' in mercado:
        return TipoOperacao.IGNORAR, ClasseAtivo.ACAO, ticker
    if 'Futuro' in mercado:
        return TipoOperacao.IGNORAR, ClasseAtivo.FUTURO, ticker

    ticker_limpo = ticker.replace('F', '')

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

    classe = classificar_ativo(ticker_limpo)

    if 'Fracionario' in mercado:
        if tipo_mov == 'COMPRA':
            return TipoOperacao.COMPRA_FRACIONARIO, classe, ticker_limpo
        else:
            return TipoOperacao.VENDA_FRACIONARIO, classe, ticker_limpo
    else:
        if tipo_mov == 'COMPRA':
            return TipoOperacao.COMPRA, classe, ticker_limpo
        else:
            return TipoOperacao.VENDA, classe, ticker_limpo

def classificar_ativo(ticker: str) -> ClasseAtivo:
    t = ticker.upper()
    if any(x in t for x in ['AGRO', 'CRA', 'CRI']) and t.endswith('11'):
        return ClasseAtivo.FIAGRO
    etfs = ['BOVA11', 'BOVV11', 'SMAL11', 'HASH11', 'NASD11', 'TECK11', 
            'ECOO11', 'FIND11', 'MATB11', 'ISUS11', 'GOVE11', 'FIXA11',
            'XINA11', 'EMEG11', 'EURP11', 'ASIA11', 'MILL11']
    if t in etfs:
        return ClasseAtivo.ETF
    if t.endswith('34') or t.endswith('33') or t.endswith('35'):
        return ClasseAtivo.BDR
    if t.endswith('11'):
        return ClasseAtivo.FII
    if t.endswith('3') or t.endswith('4') or t.endswith('5') or t.endswith('6'):
        return ClasseAtivo.ACAO
    return ClasseAtivo.DESCONHECIDO

class ParserNegociacaoB3:
    def __init__(self, caminho_arquivo: str):
        self.caminho = caminho_arquivo
        self.df: Optional[pd.DataFrame] = None
        self.operacoes: List[Operacao] = []
        self.posicoes_acoes: Dict[str, PosicaoConsolidada] = {}
        self.operacoes_opcoes: List[Operacao] = []
        self.ignorados: List[Dict] = []

    def carregar(self) -> 'ParserNegociacaoB3':
        xls = pd.ExcelFile(self.caminho)
        aba_neg = None
        for aba in xls.sheet_names:
            if 'negoci' in aba.lower():
                aba_neg = aba
                break
        if not aba_neg:
            aba_neg = xls.sheet_names[0]
        self.df = pd.read_excel(self.caminho, sheet_name=aba_neg)
        self.df = self.df[self.df['Data do Negocio'] != 'Data do Negocio']
        return self

    def parse(self) -> 'ParserNegociacaoB3':
        for idx, row in self.df.iterrows():
            try:
                tipo_op, classe, ticker_consolidado = classificar_negociacao(row)
                if tipo_op == TipoOperacao.IGNORAR:
                    self.ignorados.append({'linha': idx, 'motivo': 'Exercicio/Futuro', 'ticker': row.get('Codigo de Negociacao', ''), 'mercado': row.get('Mercado', '')})
                    continue

                data_str = str(row.get('Data do Negocio', ''))
                try:
                    data = pd.to_datetime(data_str, dayfirst=True)
                except:
                    data = datetime.now()

                vencimento = None
                prazo = str(row.get('Prazo/Vencimento', '')).strip()
                if prazo and prazo != '-':
                    try:
                        vencimento = pd.to_datetime(prazo, dayfirst=True)
                    except:
                        pass

                quantidade = float(row.get('Quantidade', 0))
                preco = float(row.get('Preco', 0))
                valor = float(row.get('Valor', 0))
                ticker_original = str(row.get('Codigo de Negociacao', '')).strip().upper()

                operacao = Operacao(
                    data=data, tipo_operacao=tipo_op, ticker_original=ticker_original,
                    ticker_consolidado=ticker_consolidado, classe=classe,
                    quantidade=quantidade, preco_unitario=preco, valor_total=valor,
                    mercado=str(row.get('Mercado', ''))
                )

                if classe == ClasseAtivo.OPCAO:
                    info_op = parse_opcao(ticker_original)
                    if info_op:
                        operacao.tipo_opcao = info_op['tipo']
                        operacao.strike = info_op['strike']
                        operacao.vencimento = vencimento
                    self.operacoes_opcoes.append(operacao)
                else:
                    self.operacoes.append(operacao)
                    if ticker_consolidado not in self.posicoes_acoes:
                        self.posicoes_acoes[ticker_consolidado] = PosicaoConsolidada(ticker=ticker_consolidado, classe=classe)
                    self.posicoes_acoes[ticker_consolidado].adicionar_operacao(operacao)
            except Exception as e:
                continue
        return self

    def get_resumo_acoes(self) -> pd.DataFrame:
        dados = []
        for ticker, pos in self.posicoes_acoes.items():
            dados.append({'Ticker': ticker, 'Classe': pos.classe.value, 'Quantidade': pos.quantidade_total,
                         'Preco Medio': round(pos.preco_medio, 4), 'Custo Total': round(pos.custo_total, 2), 'Operacoes': len(pos.operacoes)})
        df = pd.DataFrame(dados)
        if not df.empty:
            df = df.sort_values('Custo Total', ascending=False)
        return df

    def get_operacoes_opcoes_df(self) -> pd.DataFrame:
        dados = []
        for op in self.operacoes_opcoes:
            dados.append({'Data': op.data, 'Tipo': op.tipo_operacao.value, 'Ticker Original': op.ticker_original,
                         'Ativo Base': op.ticker_consolidado, 'Tipo Opcao': op.tipo_opcao, 'Strike': op.strike,
                         'Vencimento': op.vencimento, 'Quantidade': op.quantidade, 'Preco': op.preco_unitario,
                         'Valor Total': op.valor_total, 'Mercado': op.mercado})
        return pd.DataFrame(dados)

    def get_operacoes_acoes_df(self) -> pd.DataFrame:
        dados = []
        for op in self.operacoes:
            dados.append({'Data': op.data, 'Tipo': op.tipo_operacao.value, 'Ticker': op.ticker_consolidado,
                         'Classe': op.classe.value, 'Quantidade': op.quantidade, 'Preco': op.preco_unitario,
                         'Valor Total': op.valor_total, 'Mercado': op.mercado})
        return pd.DataFrame(dados)

    def exportar_para_sql(self) -> Tuple[List[Dict], List[Dict]]:
        acoes = []
        for op in self.operacoes:
            acoes.append({'data_aquisicao': op.data.date(), 'ticker': op.ticker_consolidado,
                         'quantidade': abs(op.quantidade), 'preco_medio': op.preco_unitario,
                         'custo_total': abs(op.valor_total), 'tipo_operacao': 'COMPRA' if 'COMPRA' in op.tipo_operacao.value else 'VENDA',
                         'origem': 'B3_NEGOCIACAO'})
        opcoes = []
        for op in self.operacoes_opcoes:
            opcoes.append({'data': op.data.date(), 'ticker_original': op.ticker_original, 'ativo_base': op.ticker_consolidado,
                          'tipo_opcao': op.tipo_opcao, 'strike': op.strike, 'vencimento': op.vencimento.date() if op.vencimento else None,
                          'quantidade': abs(op.quantidade), 'preco': op.preco_unitario, 'valor_total': abs(op.valor_total),
                          'tipo_operacao': 'COMPRA' if 'COMPRA' in op.tipo_operacao.value else 'VENDA', 'origem': 'B3_NEGOCIACAO'})
        return acoes, opcoes

# ============================================================
# FUNÇÕES DO BANCO
# ============================================================

def salvar_carteira_no_banco(parser: ParserNegociacaoB3, usuario_id: int = 1):
    """Salva posições consolidadas no banco de dados."""
    engine = get_db_engine()
    if not engine:
        return False

    try:
        with engine.begin() as conn:
            # Verificar se usuário existe
            result = conn.execute(text("SELECT id FROM usuarios WHERE id = :uid"), {'uid': usuario_id})
            if not result.fetchone():
                # Criar usuário padrão
                conn.execute(text("""
                    INSERT INTO usuarios (email, nome) 
                    VALUES ('default@sobral.invest', 'Carlos Sobral')
                    ON CONFLICT DO NOTHING
                """))

            # Verificar se carteira existe
            result = conn.execute(text("SELECT id FROM carteiras WHERE usuario_id = :uid AND is_principal = TRUE"), {'uid': usuario_id})
            carteira = result.fetchone()

            if not carteira:
                # Criar carteira principal
                result = conn.execute(text("""
                    INSERT INTO carteiras (usuario_id, nome, is_principal)
                    VALUES (:uid, 'Carteira Principal', TRUE)
                    RETURNING id
                """), {'uid': usuario_id})
                carteira_id = result.fetchone()[0]
            else:
                carteira_id = carteira[0]

            # Inserir operações
            acoes, _ = parser.exportar_para_sql()
            for op in acoes:
                # Buscar empresa_id pelo ticker
                result = conn.execute(text("SELECT id FROM empresas WHERE nome_bovespa = :ticker"), {'ticker': op['ticker']})
                empresa = result.fetchone()

                if empresa:
                    empresa_id = empresa[0]
                    conn.execute(text("""
                        INSERT INTO carteira_ativos 
                        (carteira_id, empresa_id, data_aquisicao, quantidade, preco_medio, custo_total, tipo_operacao, corretora, origem)
                        VALUES (:carteira_id, :empresa_id, :data, :qtd, :preco, :custo, :tipo, 'B3', 'B3_IMPORT')
                    """), {
                        'carteira_id': carteira_id,
                        'empresa_id': empresa_id,
                        'data': op['data_aquisicao'],
                        'qtd': op['quantidade'],
                        'preco': op['preco_medio'],
                        'custo': op['custo_total'],
                        'tipo': op['tipo_operacao']
                    })

            return True
    except Exception as e:
        st.error(f"Erro ao salvar no banco: {e}")
        return False

def get_carteira_do_banco(usuario_id: int = 1):
    """Recupera carteira do banco."""
    engine = get_db_engine()
    if not engine:
        return pd.DataFrame()

    try:
        query = text("""
            SELECT e.nome_bovespa as ticker, e.razao_social, 
                   SUM(ca.quantidade) as quantidade_total,
                   SUM(ca.custo_total) / NULLIF(SUM(ca.quantidade), 0) as preco_medio,
                   SUM(ca.custo_total) as custo_total
            FROM carteira_ativos ca
            JOIN carteiras c ON ca.carteira_id = c.id
            JOIN empresas e ON ca.empresa_id = e.id
            WHERE c.usuario_id = :uid AND ca.ativo = TRUE
            GROUP BY e.nome_bovespa, e.razao_social
            ORDER BY custo_total DESC
        """)

        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={'uid': usuario_id})
            return df
    except Exception as e:
        st.error(f"Erro ao carregar carteira: {e}")
        return pd.DataFrame()

# ============================================================
# INTERFACE STREAMLIT
# ============================================================

st.title("📊 SOBRAL INVEST")
st.markdown("### `Plataforma de Analise Fundamentalista`")
st.markdown("---")

# Sidebar
st.sidebar.markdown("## `MENU`")
st.sidebar.markdown("---")

# Status do banco
if test_connection():
    st.sidebar.markdown("🟢 `Banco: Conectado`")
else:
    st.sidebar.markdown("🔴 `Banco: Desconectado`")
    st.sidebar.markdown("Configure DATABASE_URL no Render")

st.sidebar.markdown("---")

modo = st.sidebar.radio("Modo:", ["Importar B3", "Carteira", "Analise", "Sobre"], index=0)

# ============================================================
# ABA: IMPORTAR B3
# ============================================================

if modo == "Importar B3":
    st.markdown("## `Importacao Canal do Investidor B3`")
    st.markdown("""
    <div class="info-box">
    <b>Instrucoes:</b><br>
    1. Acesse o <b>Canal do Investidor B3</b><br>
    2. Exporte a aba <b>"Negociacao"</b> em Excel<br>
    3. Faca o upload aqui<br><br>
    <b>Regras:</b> Acoes, FIIs, FIAGROs, ETFs, BDRs | Opcoes (derivativos) | Ignora: Exercicio, Futuros, CDBs
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=['xlsx'])

    if uploaded_file is not None:
        temp_path = Path("temp_upload.xlsx")
        temp_path.write_bytes(uploaded_file.getvalue())

        try:
            with st.spinner("Processando..."):
                parser = ParserNegociacaoB3(str(temp_path))
                parser.carregar().parse()

            # Metricas
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Acoes", len(parser.operacoes))
            with col2: st.metric("Opcoes", len(parser.operacoes_opcoes))
            with col3: st.metric("Posicoes", len(parser.posicoes_acoes))
            with col4: st.metric("Ignorados", len(parser.ignorados))

            st.markdown("---")

            # Tabs
            tab1, tab2, tab3, tab4 = st.tabs(["📈 Posicoes", "📋 Operacoes", "🎯 Opcoes", "⚠️ Ignorados"])

            with tab1:
                st.markdown("## `Posicoes Consolidadas`")
                df_pos = parser.get_resumo_acoes()
                if not df_pos.empty:
                    st.dataframe(df_pos, use_container_width=True, height=400)

                    # Grafico
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        df_classe = df_pos.groupby('Classe')['Custo Total'].sum().reset_index()
                        st.bar_chart(df_classe.set_index('Classe'))
                    with col_p2:
                        df_top = df_pos.nlargest(10, 'Custo Total')[['Ticker', 'Custo Total']]
                        st.bar_chart(df_top.set_index('Ticker'))
                else:
                    st.warning("Nenhuma posicao encontrada.")

            with tab2:
                st.markdown("## `Operacoes de Acoes`")
                df_acoes = parser.get_operacoes_acoes_df()
                if not df_acoes.empty:
                    st.dataframe(df_acoes.sort_values('Data', ascending=False), use_container_width=True, height=500)
                    csv = df_acoes.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download CSV", csv, "operacoes_acoes.csv", "text/csv")
                else:
                    st.info("Nenhuma operacao de acoes.")

            with tab3:
                st.markdown("## `Operacoes de Opcoes (Derivativos)`")
                df_op = parser.get_operacoes_opcoes_df()
                if not df_op.empty:
                    st.dataframe(df_op.sort_values('Data', ascending=False), use_container_width=True, height=500)
                else:
                    st.info("Nenhuma operacao de opcoes.")

            with tab4:
                st.markdown("## `Ignorados`")
                if parser.ignorados:
                    st.dataframe(pd.DataFrame(parser.ignorados), use_container_width=True, height=400)
                else:
                    st.success("Nenhum registro ignorado!")

            # Salvar no banco
            st.markdown("---")
            if st.button("💾 Salvar no Banco de Dados", type="primary"):
                if test_connection():
                    with st.spinner("Salvando..."):
                        if salvar_carteira_no_banco(parser):
                            st.success("✅ Carteira salva com sucesso!")
                        else:
                            st.error("❌ Erro ao salvar. Verifique se as empresas estao cadastradas.")
                else:
                    st.error("❌ Banco nao conectado. Configure DATABASE_URL.")

            temp_path.unlink(missing_ok=True)

        except Exception as e:
            st.error(f"Erro: {e}")

# ============================================================
# ABA: CARTEIRA
# ============================================================

elif modo == "Carteira":
    st.markdown("## `Minha Carteira`")

    if test_connection():
        df_carteira = get_carteira_do_banco()
        if not df_carteira.empty:
            st.dataframe(df_carteira, use_container_width=True, height=500)
            st.metric("Total Investido", f"R$ {df_carteira['custo_total'].sum():,.2f}")
        else:
            st.info("Carteira vazia. Importe dados do B3 primeiro.")
    else:
        st.error("Banco nao conectado. Configure DATABASE_URL no Render Dashboard.")

# ============================================================
# ABA: ANALISE
# ============================================================

elif modo == "Analise":
    st.markdown("## `Analise Fundamentalista`")
    st.markdown("### `Em desenvolvimento...`")
    st.info("Proxima feature: Score CS + Precos Teto (Graham, Bazin, Lynch, AGF)")

# ============================================================
# ABA: SOBRE
# ============================================================

else:
    st.markdown("## `Sobre`")
    st.markdown("""
    <div class="info-box">
    <h3>Sobral Invest v0.1</h3>
    <p>Plataforma de analise fundamentalista e gerenciamento de carteira.</p>
    <p><b>Stack:</b> Python + Streamlit + PostgreSQL (Supabase)</p>
    <p><b>Fontes:</b> CVM Dados Abertos, B3 Canal do Investidor</p>
    </div>
    """, unsafe_allow_html=True)
