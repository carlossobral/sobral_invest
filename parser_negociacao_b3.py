import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class ParserNegociacaoB3:
    """
    Parser para arquivo de Negociacao do Canal do Investidor B3.
    Detecta automaticamente as colunas e converte valores numéricos corretamente.
    """

    # Mapeamento flexível de colunas
    MAPEAMENTO_COLUNAS = {
        'data': ['Data do Negocio', 'Data do Negócio', 'Data', 'DATA', 'Data Negócio', 'Data Negocio'],
        'tipo_movimentacao': ['Tipo de Movimentacao', 'Tipo de Movimentação', 'Tipo Movimentacao', 'Tipo Movimentação', 'TIPO', 'Movimentação', 'Movimentacao'],
        'mercado': ['Mercado', 'MERCADO', 'Tipo Mercado'],
        'prazo_vencimento': ['Prazo/Vencimento', 'Prazo Vencimento', 'Vencimento', 'PRAZO'],
        'instituicao': ['Instituicao', 'Instituição', 'INSTITUICAO', 'Corretora'],
        'codigo_negociacao': ['Codigo de Negociacao', 'Código de Negociação', 'Codigo Negociacao', 'Código Negociação', 'Ticker', 'Ativo', 'ATIVO', 'Código', 'Código de Negociação'],
        'quantidade': ['Quantidade', 'QUANTIDADE', 'Qtd', 'QTD'],
        'preco': ['Preco', 'Preço', 'PRECO', 'Preco Unitario', 'Preço Unitário', 'Preço Unitario', 'PREÇO', 'Preço'],
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
                if nome in colunas_arquivo:
                    colunas_detectadas[campo] = nome
                    break
                for col in colunas_arquivo:
                    if nome.lower() == col.lower():
                        colunas_detectadas[campo] = col
                        break
                if campo in colunas_detectadas:
                    break

        return colunas_detectadas

    def _converter_numero(self, valor) -> float:
        """
        Converte valor numérico do formato brasileiro para float.
        Suporta: "25,30", "2.530,00", "R$ 1.234,56", "1234.56"
        """
        if pd.isna(valor):
            return 0.0

        if isinstance(valor, (int, float)):
            return float(valor)

        # Converter para string e limpar
        s = str(valor).strip()

        # Remover R$, espaços, etc.
        s = s.replace('R$', '').replace(' ', '').replace('%', '')

        # Detectar formato
        # Se tem vírgula e ponto: "2.530,00" → brasileiro
        # Se tem só vírgula: "25,30" → brasileiro
        # Se tem só ponto: "25.30" → americano
        # Se não tem nenhum: "2530" → inteiro

        if ',' in s and '.' in s:
            # Formato brasileiro com milhar: "2.530,00"
            s = s.replace('.', '')  # Remove separador de milhar
            s = s.replace(',', '.')  # Converte decimal
        elif ',' in s:
            # Pode ser "25,30" (brasileiro) ou "2530" (americano com vírgula de milhar)
            # Se vírgula está a 2-3 posições do final, é decimal brasileiro
            partes = s.split(',')
            if len(partes) == 2 and len(partes[1]) <= 2:
                # Decimal brasileiro: "25,30" → "25.30"
                s = s.replace(',', '.')
            else:
                # Milhar americano: "1,234" → "1234"
                s = s.replace(',', '')
        # Se só tem ponto, assume americano: "25.30" → mantém

        try:
            return float(s)
        except:
            return 0.0

    def _validar_preco(self, preco: float, valor: float, qtd: int) -> float:
        """
        Valida e corrige o preço unitário.
        Se preço * qtd não bate com valor, tenta corrigir.
        """
        if preco <= 0 or qtd <= 0 or valor <= 0:
            return preco

        # Calcular preço esperado
        preco_esperado = valor / qtd

        # Se o preço informado é muito diferente do esperado, usar o esperado
        if preco_esperado > 0:
            razao = preco / preco_esperado if preco_esperado > 0 else 0

            # Se razão está entre 0.5 e 2.0, o preço está razoável
            if 0.5 <= razao <= 2.0:
                return preco

            # Se preço é 100x maior (ex: 2530 ao invés de 25.30)
            if razao > 50:
                return preco / 100

            # Se preço é 100x menor
            if razao < 0.02:
                return preco * 100

        return preco

    def carregar(self) -> 'ParserNegociacaoB3':
        """Carrega o arquivo Excel e detecta colunas."""
        try:
            df = pd.read_excel(self.caminho)
            df = df.dropna(how='all')

            self.colunas_detectadas = self._detectar_colunas(df)

            colunas_obrigatorias = ['data', 'tipo_movimentacao', 'codigo_negociacao', 'quantidade']
            faltantes = [c for c in colunas_obrigatorias if c not in self.colunas_detectadas]

            if faltantes:
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
        tipo = str(self._get_valor(row, 'tipo_movimentacao') or '').upper()

        if 'COMPRA' in tipo:
            return 'COMPRA'
        elif 'VENDA' in tipo:
            return 'VENDA'

        entrada_saida = self._get_valor(row, 'entrada_saida')
        if entrada_saida:
            es = str(entrada_saida).upper()
            if any(x in es for x in ['DEBITO', 'DÉBITO', 'DEBIT']):
                return 'COMPRA'
            elif any(x in es for x in ['CREDITO', 'CRÉDITO', 'CREDIT']):
                return 'VENDA'

        valor = self._get_valor(row, 'valor')
        if valor and pd.notna(valor):
            try:
                v = self._converter_numero(valor)
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
                ticker = self._limpar_ticker(self._get_valor(row, 'codigo_negociacao') or '')
                if not ticker or any(x in ticker for x in ['TOTAL', 'SALDO', 'DATA']):
                    continue

                mercado_raw = self._get_valor(row, 'mercado') or ''
                tipo_mercado = self._classificar_mercado(mercado_raw)

                direcao = self._determinar_direcao(row)

                # Converter quantidade
                qtd_raw = self._get_valor(row, 'quantidade')
                qtd = int(self._converter_numero(qtd_raw))

                # Converter preço
                preco_raw = self._get_valor(row, 'preco')
                preco = self._converter_numero(preco_raw)

                # Converter valor
                valor_raw = self._get_valor(row, 'valor')
                valor = self._converter_numero(valor_raw)

                # Validar e corrigir preço
                preco = self._validar_preco(preco, abs(valor), qtd)

                # Recalcular valor se necessário
                if valor == 0 and preco > 0 and qtd > 0:
                    valor = preco * qtd

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

        resumo = []
        for ticker in df_ops['ticker'].unique():
            ops_ticker = df_ops[df_ops['ticker'] == ticker]

            compras = ops_ticker[ops_ticker['direcao'] == 'COMPRA']
            vendas = ops_ticker[ops_ticker['direcao'] == 'VENDA']

            qtd_compras = compras['quantidade'].sum()
            qtd_vendas = vendas['quantidade'].sum()

            saldo = qtd_compras - qtd_vendas

            if saldo > 0:
                # Preço médio ponderado das compras
                custo_total = (compras['quantidade'] * compras['preco']).sum()
                preco_medio = custo_total / qtd_compras if qtd_compras > 0 else 0

                resumo.append({
                    'Ticker': ticker,
                    'Quantidade': int(saldo),
                    'Preço Médio': round(preco_medio, 4),
                    'Custo Total': round(custo_total, 2),
                    'Classe': 'ACAO',
                    'Total Compras': int(qtd_compras),
                    'Total Vendas': int(qtd_vendas),
                })

        return pd.DataFrame(resumo)

    def get_operacoes_opcoes_df(self) -> pd.DataFrame:
        """Retorna DataFrame com operações de opções."""
        if not self.operacoes_opcoes:
            return pd.DataFrame()

        df = pd.DataFrame(self.operacoes_opcoes)

        def mapear_ativo_base(ticker):
            if len(ticker) >= 6:
                return ticker[:4] + ticker[-1]
            return ticker

        df['Ativo Base'] = df['ticker'].apply(mapear_ativo_base)
        df['Tipo'] = df['tipo_mercado'].apply(lambda x: 'CALL' if 'CALL' in x else 'PUT')

        return df[['data', 'ticker', 'Ativo Base', 'Tipo', 'direcao', 'quantidade', 'preco', 'valor']]


def classificar_negociacao(row):
    parser = ParserNegociacaoB3('')
    return parser._classificar_mercado(row.get('Mercado', ''))

def classificar_ativo(ticker: str) -> str:
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
