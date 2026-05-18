#!/usr/bin/env python3
"""
SOBRAL INVEST — Parser de Importação B3 (Canal do Investidor)
===============================================================
Processa arquivo Excel de movimentação exportado do site da B3
e converte para operações de carteira.

Regras:
- Considerar Credito/Debito para direção da operação
- Ignorar: CDBs, Futuros, Corretoras
- Mapear opções para ativo-base
- Consolidar posição por ativo
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
    PROVENTO = "PROVENTO"
    EVENTO_CORP = "EVENTO_CORP"
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
    """Operação individual parseada do arquivo B3."""
    data: datetime
    tipo_operacao: TipoOperacao
    ticker_original: str
    ticker_consolidado: str
    classe: ClasseAtivo
    quantidade: float
    preco_unitario: float
    valor_total: float

    # Campos opcionais
    corretora: str = ""
    is_daytrade: bool = False

    # Para opções
    tipo_opcao: Optional[str] = None  # CALL/PUT
    strike: Optional[float] = None
    vencimento: Optional[str] = None

    def __post_init__(self):
        # Normalizar quantidade (negativa para vendas)
        if self.tipo_operacao in [TipoOperacao.VENDA, TipoOperacao.VENDA_OPCAO]:
            self.quantidade = -abs(self.quantidade)

@dataclass
class PosicaoConsolidada:
    """Posição consolidada de um ativo na carteira."""
    ticker: str
    classe: ClasseAtivo
    quantidade_total: float = 0
    custo_total: float = 0
    preco_medio: float = 0

    # Histórico
    operacoes: List[Operacao] = field(default_factory=list)

    def adicionar_operacao(self, op: Operacao):
        self.operacoes.append(op)

        if op.tipo_operacao in [TipoOperacao.COMPRA, TipoOperacao.COMPRA_OPCAO]:
            # Compra: aumenta posição e custo
            novo_custo = self.custo_total + op.valor_total
            nova_qtd = self.quantidade_total + op.quantidade
            if nova_qtd > 0:
                self.preco_medio = novo_custo / nova_qtd
            self.custo_total = novo_custo
            self.quantidade_total = nova_qtd

        elif op.tipo_operacao in [TipoOperacao.VENDA, TipoOperacao.VENDA_OPCAO]:
            # Venda: reduz posição (preço médio não muda)
            self.quantidade_total += op.quantidade  # quantidade já é negativa
            # Custo proporcional
            if self.quantidade_total > 0:
                self.custo_total = self.quantidade_total * self.preco_medio
            else:
                self.custo_total = 0
                self.preco_medio = 0


# ============================================================
# 2. REGRAS DE CLASSIFICAÇÃO
# ============================================================

def classificar_movimentacao(row: pd.Series) -> Tuple[TipoOperacao, ClasseAtivo]:
    """
    Classifica uma linha do arquivo B3.

    Returns:
        (TipoOperacao, ClasseAtivo)
    """
    movimentacao = str(row.get('Movimentacao', '')).strip()
    produto = str(row.get('Produto', '')).strip()
    entrada_saida = str(row.get('Entrada/Saida', '')).strip().upper()

    # 1. IGNORAR RENDA FIXA
    if 'CDB' in produto.upper():
        return TipoOperacao.IGNORAR, ClasseAtivo.RENDA_FIXA

    # 2. IGNORAR FUTUROS
    if 'Futuro' in movimentacao or 'WIN' in produto.upper() or 'WDO' in produto.upper():
        return TipoOperacao.IGNORAR, ClasseAtivo.FUTURO

    # 3. EXTRAIR TICKER
    ticker = extrair_ticker(produto)

    # 4. VERIFICAR SE É OPÇÃO
    if 'Opção' in movimentacao:
        # Mapear opção para ativo-base
        from mapeador_opcoes_b3 import mapear_ticker_b3, MapeadorOpcoes
        consolidado, tipo_str = mapear_ticker_b3(produto)

        if 'Compra' in movimentacao:
            return TipoOperacao.COMPRA_OPCAO, ClasseAtivo.OPCAO
        else:
            return TipoOperacao.VENDA_OPCAO, ClasseAtivo.OPCAO

    # 5. AÇÕES / FIIs / ETFs / BDRs
    classe = classificar_ativo(ticker, produto)

    # 6. DETERMINAR DIREÇÃO (Compra/Venda)
    if 'Transferência - Liquidação' in movimentacao:
        if entrada_saida == 'CREDITO':
            return TipoOperacao.VENDA, classe  # Recebeu = vendeu
        else:  # DEBITO
            return TipoOperacao.COMPRA, classe  # Pagou = comprou

    elif 'Compra' in movimentacao:
        return TipoOperacao.COMPRA, classe
    elif 'Venda' in movimentacao:
        return TipoOperacao.VENDA, classe

    # 7. PROVENTOS (futuro)
    if any(p in movimentacao for p in ['Dividendo', 'JCP', 'Bonificacao']):
        return TipoOperacao.PROVENTO, classe

    return TipoOperacao.IGNORAR, ClasseAtivo.DESCONHECIDO


def extrair_ticker(produto: str) -> str:
    """Extrai o ticker do campo Produto."""
    # Formato: "TICKER - Nome da Empresa"
    if ' - ' in produto:
        return produto.split(' - ')[0].strip().upper()
    return produto.strip().upper()


def classificar_ativo(ticker: str, produto: str) -> ClasseAtivo:
    """Classifica o ativo pela classe."""
    ticker = ticker.upper()
    produto_upper = produto.upper()

    # FIAGRO
    if 'FIAGRO' in produto_upper or 'AGRO' in produto_upper or 'CRA' in produto_upper:
        return ClasseAtivo.FIAGRO

    # FII
    if ticker.endswith('11') and 'FII' in produto_upper:
        return ClasseAtivo.FII

    # ETF
    etfs = ['BOVA11', 'BOVV11', 'SMAL11', 'HASH11', 'NASD11', 'TECK11', 
            'ECOO11', 'FIND11', 'MATB11', 'ISUS11', 'GOVE11', 'FIXA11',
            'XINA11', 'EMEG11', 'EURP11', 'ASIA11', 'MILL11']
    if ticker in etfs:
        return ClasseAtivo.ETF

    # BDR
    if ticker.endswith('34') or ticker.endswith('33') or ticker.endswith('35'):
        return ClasseAtivo.BDR

    # AÇÃO (padrão)
    if ticker.endswith('3') or ticker.endswith('4') or ticker.endswith('5') or ticker.endswith('6'):
        return ClasseAtivo.ACAO

    # FII genérico (termina em 11)
    if ticker.endswith('11'):
        return ClasseAtivo.FII

    return ClasseAtivo.DESCONHECIDO


# ============================================================
# 3. PARSER PRINCIPAL
# ============================================================

class ParserB3:
    """Parser completo do arquivo de movimentação B3."""

    def __init__(self, caminho_arquivo: str):
        self.caminho = caminho_arquivo
        self.df: Optional[pd.DataFrame] = None
        self.operacoes: List[Operacao] = []
        self.posicoes: Dict[str, PosicaoConsolidada] = {}
        self.ignorados: List[Dict] = []

    def carregar(self) -> 'ParserB3':
        """Carrega o arquivo Excel da B3."""
        print(f"Carregando: {self.caminho}")

        # Ler todas as abas
        xls = pd.ExcelFile(self.caminho)

        # Procurar aba de Movimentação
        aba_mov = None
        for aba in xls.sheet_names:
            if 'moviment' in aba.lower():
                aba_mov = aba
                break

        if not aba_mov:
            aba_mov = xls.sheet_names[0]  # Primeira aba como fallback

        self.df = pd.read_excel(self.caminho, sheet_name=aba_mov)

        # Remover linhas de cabeçalho duplicadas
        self.df = self.df[self.df['Entrada/Saida'] != 'Entrada/Saida']

        print(f"Total de registros: {len(self.df)}")
        return self

    def parse(self) -> 'ParserB3':
        """Parse todas as operações."""
        if self.df is None:
            raise ValueError("Arquivo não carregado. Execute .carregar() primeiro.")

        for idx, row in self.df.iterrows():
            try:
                tipo_op, classe = classificar_movimentacao(row)

                if tipo_op == TipoOperacao.IGNORAR:
                    self.ignorados.append({
                        'linha': idx,
                        'motivo': 'Ignorado por regra',
                        'produto': row.get('Produto', ''),
                        'movimentacao': row.get('Movimentacao', '')
                    })
                    continue

                # Parse data
                data_str = str(row.get('Data', ''))
                try:
                    data = pd.to_datetime(data_str, dayfirst=True)
                except:
                    data = datetime.now()

                # Parse valores
                quantidade = float(row.get('Quantidade', 0))
                preco = float(row.get('Preco unitario', 0))
                valor = float(row.get('Valor da Operacao', 0))

                # Ticker consolidado
                from mapeador_opcoes_b3 import mapear_ticker_b3
                ticker_consolidado, _ = mapear_ticker_b3(str(row.get('Produto', '')))
                ticker_original = extrair_ticker(str(row.get('Produto', '')))

                # Criar operação
                operacao = Operacao(
                    data=data,
                    tipo_operacao=tipo_op,
                    ticker_original=ticker_original,
                    ticker_consolidado=ticker_consolidado,
                    classe=classe,
                    quantidade=quantidade,
                    preco_unitario=preco,
                    valor_total=valor,
                    corretora=str(row.get('Instituicao', ''))
                )

                self.operacoes.append(operacao)

                # Consolidar posição
                if ticker_consolidado not in self.posicoes:
                    self.posicoes[ticker_consolidado] = PosicaoConsolidada(
                        ticker=ticker_consolidado,
                        classe=classe
                    )

                self.posicoes[ticker_consolidado].adicionar_operacao(operacao)

            except Exception as e:
                print(f"Erro na linha {idx}: {e}")
                continue

        print(f"Operações parseadas: {len(self.operacoes)}")
        print(f"Posições consolidadas: {len(self.posicoes)}")
        print(f"Registros ignorados: {len(self.ignorados)}")

        return self

    def get_resumo(self) -> pd.DataFrame:
        """Retorna DataFrame com posições consolidadas."""
        dados = []
        for ticker, pos in self.posicoes.items():
            dados.append({
                'Ticker': ticker,
                'Classe': pos.classe.value,
                'Quantidade': pos.quantidade_total,
                'Preço Médio': round(pos.preco_medio, 4),
                'Custo Total': round(pos.custo_total, 2),
                'Operações': len(pos.operacoes)
            })

        return pd.DataFrame(dados).sort_values('Custo Total', ascending=False)

    def get_operacoes_df(self) -> pd.DataFrame:
        """Retorna DataFrame com todas as operações."""
        dados = []
        for op in self.operacoes:
            dados.append({
                'Data': op.data,
                'Tipo': op.tipo_operacao.value,
                'Ticker Original': op.ticker_original,
                'Ticker Consolidado': op.ticker_consolidado,
                'Classe': op.classe.value,
                'Quantidade': op.quantidade,
                'Preço Unitário': op.preco_unitario,
                'Valor Total': op.valor_total,
                'Corretora': op.corretora
            })

        return pd.DataFrame(dados)

    def exportar_para_sql(self) -> List[Dict]:
        """Retorna operações formatadas para inserção no banco."""
        registros = []
        for op in self.operacoes:
            registros.append({
                'data_aquisicao': op.data.date(),
                'ticker': op.ticker_consolidado,
                'quantidade': abs(op.quantidade),
                'preco_medio': op.preco_unitario,
                'custo_total': abs(op.valor_total),
                'tipo_operacao': 'COMPRA' if op.tipo_operacao in [TipoOperacao.COMPRA, TipoOperacao.COMPRA_OPCAO] else 'VENDA',
                'corretora': op.corretora,
                'origem': 'B3_IMPORT'
            })
        return registros


# ============================================================
# 4. EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    # Exemplo de uso
    parser = ParserB3("movimentacao-2026-05-16-16-26-54.xlsx")
    parser.carregar().parse()

    # Mostrar resumo
    print("\n" + "="*70)
    print("POSIÇÕES CONSOLIDADAS")
    print("="*70)
    print(parser.get_resumo().to_string(index=False))

    # Mostrar operações
    print("\n" + "="*70)
    print("ÚLTIMAS 10 OPERAÇÕES")
    print("="*70)
    print(parser.get_operacoes_df().tail(10).to_string(index=False))
