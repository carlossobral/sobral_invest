import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class ParserNegociacaoB3:
    """
    Parser para arquivo de Negociacao do Canal do Investidor B3.
    Detecta automaticamente as colunas do arquivo.
    """

    # Mapeamento flexível de colunas (várias possibilidades)
    MAPEAMENTO_COLUNAS = {
        'data': ['Data do Negocio', 'Data do Negócio', 'Data', 'DATA', 'Data Negócio', 'Data Negocio'],
        'tipo_movimentacao': ['Tipo de Movimentacao', 'Tipo de Movimentação', 'Tipo Movimentacao', 'Tipo Movimentação', 'TIPO', 'Movimentação', 'Movimentacao'],
        'mercado': ['Mercado', 'MERCADO', 'Tipo Mercado'],
        'prazo_vencimento': ['Prazo/Vencimento', 'Prazo Vencimento', 'Vencimento', 'PRAZO'],
        'instituicao': ['Instituicao', 'Instituição', 'INSTITUICAO', 'Corretora'],
        'codigo_negociacao': ['Codigo de Negociacao', 'Código de Negociação', 'Codigo Negociacao', 'Código Negociação', 'Ticker', 'Ativo', 'ATIVO', 'Código'],
        'quantidade': ['Quantidade', 'QUANTIDADE', 'Qtd', 'QTD'],
        'preco': ['Preco', 'Preço', 'PRECO', 'Preco Unitario', 'Preço Unitário', 'Preço Unitario', 'PREÇO'],
        'valor': ['Valor', 'VALOR', 'Valor da Operacao', 'Valor da Operação', 'Valor Operacao', 'Valor Operação'],
        'entrada_saida': ['Entrada/Saída', 'Entrada/Saida', 'ENTRADA/SAIDA', 'Credito/Debito', 'Crédito/Débito', 'Entrada Saida'],
    }

    def __init__(self, caminho_arquivo: str):
        self.caminho = caminho_arquivo
        self.df: Optional[pd.DataFrame] = None
        self.operacoes: List[Dict] = []
        self.operacoes_opcoes: List[Dict] = []
        self.ignorados: List[Dict] = []
        self.colunas_detectadas: Dict[str, str] = {}

    def _detectar_colunas(self, df: pd.DataFrame) -> Dict[str, str]:
        """Detecta automaticamente quais colunas correspondem aos campos esperados."""
        colunas_arquivo = list(df.columns)
        colunas_detectadas = {}

        for campo, possiveis_nomes in self.MAPEAMENTO_COLUNAS.items():
            for nome in possiveis_nomes:
                # Verificar correspondência exata
                if nome in colunas_arquivo:
                    colunas_detectadas[campo] = nome
                    break
                # Verificar correspondência case-insensitive
                for col in colunas_arquivo:
                    if nome.lower() == col.lower():
                        colunas_detectadas[campo] = col
                        break
                if campo in colunas_detectadas:
                    break

        return colunas_detectadas

    def carregar(self) -> 'ParserNegociacaoB3':
        """Carrega o arquivo Excel e detecta colunas."""
        try:
            # Tentar ler o arquivo
            df = pd.read_excel(self.caminho)

            # Remover linhas de cabeçalho duplicado (se houver)
            df = df.dropna(how='all')

            # Detectar colunas
            self.colunas_detectadas = self._detectar_colunas(df)

            # Verificar colunas obrigatórias
            colunas_obrigatorias = ['data', 'tipo_movimentacao', 'codigo_negociacao', 'quantidade']
            faltantes = [c for c in colunas_obrigatorias if c not in self.colunas_detectadas]

            if faltantes:
                # Tentar usar primeira linha como header
                df = pd.read_excel(self.caminho, header=1)
                df = df.dropna(how='all')
                self.colunas_detectadas = self._detectar_colunas(df)
                faltantes = [c for c in colunas_obrigatorias if c not in self.colunas_detectadas]

                if faltantes:
                    raise ValueError(f"Colunas obrigatórias não encontradas: {faltantes}. Colunas disponíveis: {list(df.columns)}")

            self.df = df

        except Exception as e:
            raise Exception(f"Erro ao carregar arquivo: {e}")

        return self

    def _get_valor(self, row, campo: str):
        """Obtém valor de uma coluna de forma segura."""
        col = self.colunas_detectadas.get(campo)
        if col and col in row.index:
            return row[col]
        return None

    def _limpar_ticker(self, ticker: str) -> str:
        """Limpa e normaliza o ticker."""
        if pd.isna(ticker):
            return ""
        ticker = str(ticker).strip().upper()
        # Remover sufixo F (fracionário)
        if ticker.endswith('F'):
            ticker = ticker[:-1]
        return ticker

    def _classificar_mercado(self, mercado: str) -> str:
        """Classifica o tipo de mercado."""
        if pd.isna(mercado):
            return "DESCONHECIDO"

        mercado = str(mercado).upper().strip()

        if any(x in mercado for x in ['VISTA', 'FRACIONARIO', 'FRACIONÁRIO']):
            return "ACAO"
        elif any(x in mercado for x in ['OPCAO COMPRA', 'OPÇÃO COMPRA', 'CALL']):
            return "OPCAO_CALL"
        elif any(x in mercado for x in ['OPCAO VENDA', 'OPÇÃO VENDA', 'PUT']):
            return "OPCAO_PUT"
        elif any(x in mercado for x in ['EXERCICIO', 'EXERCÍCIO']):
            return "EXERCICIO"
        elif any(x in mercado for x in ['FUTURO', 'TERMO']):
            return "FUTURO"
        elif any(x in mercado for x in ['CDB', 'DEBENTURE', 'RENDA FIXA']):
            return "RENDA_FIXA"
        else:
            return "OUTRO"

    def _determinar_direcao(self, row) -> str:
        """Determina se é compra ou venda."""
        # Tentar pelo tipo de movimentação
        tipo = str(self._get_valor(row, 'tipo_movimentacao') or '').upper()

        if 'COMPRA' in tipo:
            return 'COMPRA'
        elif 'VENDA' in tipo:
            return 'VENDA'

        # Tentar por entrada/saída (crédito/débito)
        entrada_saida = self._get_valor(row, 'entrada_saida')
        if entrada_saida:
            es = str(entrada_saida).upper()
            if any(x in es for x in ['DEBITO', 'DÉBITO', 'DEBIT']):
                return 'COMPRA'
            elif any(x in es for x in ['CREDITO', 'CRÉDITO', 'CREDIT']):
                return 'VENDA'

        # Tentar pelo valor (positivo/negativo)
        valor = self._get_valor(row, 'valor')
        if valor and pd.notna(valor):
            try:
                v = float(str(valor).replace('.', '').replace(',', '.').replace('R$', '').strip())
                if v < 0:
                    return 'COMPRA'
                elif v > 0:
                    return 'VENDA'
            except:
                pass

        return 'DESCONHECIDO'

    def parse(self) -> 'ParserNegociacaoB3':
        """Processa todas as linhas do arquivo."""
        if self.df is None:
            raise ValueError("Arquivo não carregado. Execute carregar() primeiro.")

        for idx, row in self.df.iterrows():
            try:
                # Pular linhas de cabeçalho ou totais
                ticker = self._limpar_ticker(self._get_valor(row, 'codigo_negociacao') or '')
                if not ticker or any(x in ticker for x in ['TOTAL', 'SALDO', 'DATA']):
                    continue

                # Classificar mercado
                mercado_raw = self._get_valor(row, 'mercado') or ''
                tipo_mercado = self._classificar_mercado(mercado_raw)

                # Determinar direção
                direcao = self._determinar_direcao(row)

                # Obter quantidade
                qtd = self._get_valor(row, 'quantidade')
                if qtd is not None:
                    try:
                        qtd = int(float(str(qtd).replace('.', '').replace(',', '.').strip()))
                    except:
                        qtd = 0
                else:
                    qtd = 0

                # Obter preço
                preco = self._get_valor(row, 'preco')
                if preco is not None:
                    try:
                        preco = float(str(preco).replace('.', '').replace(',', '.').replace('R$', '').strip())
                    except:
                        preco = 0
                else:
                    preco = 0

                # Obter valor
                valor = self._get_valor(row, 'valor')
                if valor is not None:
                    try:
                        valor = float(str(valor).replace('.', '').replace(',', '.').replace('R$', '').strip())
                    except:
                        valor = preco * qtd if preco and qtd else 0
                else:
                    valor = preco * qtd if preco and qtd else 0

                # Obter data
                data = self._get_valor(row, 'data')
                if data and pd.notna(data):
                    try:
                        if isinstance(data, str):
                            data = pd.to_datetime(data, dayfirst=True)
                        else:
                            data = pd.to_datetime(data)
                    except:
                        data = None

                operacao = {
                    'data': data,
                    'ticker': ticker,
                    'tipo_mercado': tipo_mercado,
                    'mercado_raw': str(mercado_raw),
                    'direcao': direcao,
                    'quantidade': qtd,
                    'preco': preco,
                    'valor': abs(valor),
                    'instituicao': str(self._get_valor(row, 'instituicao') or ''),
                }

                # Classificar operação
                if tipo_mercado in ['ACAO']:
                    self.operacoes.append(operacao)
                elif tipo_mercado in ['OPCAO_CALL', 'OPCAO_PUT']:
                    self.operacoes_opcoes.append(operacao)
                elif tipo_mercado in ['EXERCICIO', 'FUTURO', 'RENDA_FIXA']:
                    self.ignorados.append({**operacao, 'motivo': f'Tipo ignorado: {tipo_mercado}'})
                else:
                    # Tentar identificar se é ação por padrão do ticker
                    if len(ticker) >= 5 and ticker[-1].isdigit() and not any(x in ticker for x in ['11', '12', '13']):
                        self.operacoes.append(operacao)
                    else:
                        self.ignorados.append({**operacao, 'motivo': f'Mercado não identificado: {tipo_mercado}'})

            except Exception as e:
                self.ignorados.append({
                    'linha': idx,
                    'motivo': f'Erro no parse: {str(e)}',
                    'dados': str(row.to_dict())
                })

        return self

    def get_resumo_acoes(self) -> pd.DataFrame:
        """Retorna DataFrame com posições consolidadas de ações."""
        if not self.operacoes:
            return pd.DataFrame()

        df_ops = pd.DataFrame(self.operacoes)

        # Agrupar por ticker
        resumo = []
        for ticker in df_ops['ticker'].unique():
            ops_ticker = df_ops[df_ops['ticker'] == ticker]

            compras = ops_ticker[ops_ticker['direcao'] == 'COMPRA']
            vendas = ops_ticker[ops_ticker['direcao'] == 'VENDA']

            qtd_compras = compras['quantidade'].sum()
            qtd_vendas = vendas['quantidade'].sum()

            saldo = qtd_compras - qtd_vendas

            if saldo > 0:
                # Preço médio das compras
                custo_total = (compras['quantidade'] * compras['preco']).sum()
                preco_medio = custo_total / qtd_compras if qtd_compras > 0 else 0

                resumo.append({
                    'Ticker': ticker,
                    'Quantidade': saldo,
                    'Preço Médio': round(preco_medio, 4),
                    'Custo Total': round(custo_total, 2),
                    'Classe': 'ACAO',
                    'Total Compras': qtd_compras,
                    'Total Vendas': qtd_vendas,
                })

        return pd.DataFrame(resumo)

    def get_operacoes_opcoes_df(self) -> pd.DataFrame:
        """Retorna DataFrame com operações de opções."""
        if not self.operacoes_opcoes:
            return pd.DataFrame()

        df = pd.DataFrame(self.operacoes_opcoes)

        # Mapear para ativo base (simplificado)
        def mapear_ativo_base(ticker):
            if len(ticker) >= 6:
                return ticker[:4] + ticker[-1]  # Ex: GGBRE203 -> GGBR4
            return ticker

        df['Ativo Base'] = df['ticker'].apply(mapear_ativo_base)
        df['Tipo'] = df['tipo_mercado'].apply(lambda x: 'CALL' if 'CALL' in x else 'PUT')

        return df[['data', 'ticker', 'Ativo Base', 'Tipo', 'direcao', 'quantidade', 'preco', 'valor']]


# Funções auxiliares para compatibilidade
def classificar_negociacao(row):
    """Função standalone para classificar uma negociação."""
    parser = ParserNegociacaoB3('')
    return parser._classificar_mercado(row.get('Mercado', ''))

def classificar_ativo(ticker: str) -> str:
    """Classifica o tipo de ativo pelo ticker."""
    ticker = str(ticker).upper().strip()

    if ticker.endswith('11') and not ticker.endswith('B11'):
        return 'FII'
    elif ticker.endswith('11') and ticker.endswith('B11'):
        return 'FIAGRO'
    elif ticker.endswith('33'):
        return 'BDR'
    elif ticker.endswith('34') or ticker.endswith('35'):
        return 'BDR'
    elif ticker.endswith('39'):
        return 'ETF'
    elif len(ticker) >= 5 and ticker[-1].isdigit():
        return 'ACAO'
    else:
        return 'OUTRO'
