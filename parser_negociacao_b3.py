import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class ParserNegociacaoB3:
    """
    Parser para arquivo de Negociacao do Canal do Investidor B3.
    Detecta automaticamente as colunas e converte valores numéricos corretamente.

    REGRAS:
    - Exercicio de opcao → Contabiliza como operacao de acoes (ativo-base)
    - Opcoes (compra/venda) → Derivativos, nao consolidam na carteira
    - Futuros/CDBs → Ignorados
    """

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
        self.operacoes: List[Dict] = []  # Acoes + exercicios de opcoes
        self.operacoes_opcoes: List[Dict] = []  # Derivativos (compra/venda de opcoes)
        self.ignorados: List[Dict] = []
        self.colunas_detectadas: Dict[str, str] = {}

    def _detectar_colunas(self, df: pd.DataFrame) -> Dict[str, str]:
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
        if pd.isna(valor):
            return 0.0

        if isinstance(valor, (int, float)):
            return float(valor)

        s = str(valor).strip()
        s = s.replace('R$', '').replace(' ', '').replace('%', '')

        if ',' in s and '.' in s:
            s = s.replace('.', '')
            s = s.replace(',', '.')
        elif ',' in s:
            partes = s.split(',')
            if len(partes) == 2 and len(partes[1]) <= 2:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')

        try:
            return float(s)
        except:
            return 0.0

    def _validar_preco(self, preco: float, valor: float, qtd: int) -> float:
        if preco <= 0 or qtd <= 0 or valor <= 0:
            return preco

        preco_esperado = valor / qtd

        if preco_esperado > 0:
            razao = preco / preco_esperado if preco_esperado > 0 else 0

            if 0.5 <= razao <= 2.0:
                return preco

            if razao > 50:
                return preco / 100

            if razao < 0.02:
                return preco * 100

        return preco

    def _mapear_exercicio_para_ativo_base(self, ticker: str) -> Tuple[str, str]:
        """
        Mapeia exercicio de opcao para ativo-base.
        Ex: BBASQ245E → BBAS3 (acao base)
        Retorna: (ativo_base, tipo_exercicio)
        """
        ticker = ticker.upper().strip()

        # Remover sufixo E (exercicio europeu) ou A (americano)
        if ticker.endswith('E') or ticker.endswith('A'):
            ticker_opcao = ticker[:-1]
        else:
            ticker_opcao = ticker

        # Regra de mapeamento B3:
        # Opcoes: [PREFIXO 4 letras][TIPO 1 letra][STRIKE 3-5 digitos]
        # Ativo base: [PREFIXO 4 letras][NUMERO 1 digito]

        if len(ticker_opcao) >= 6:
            prefixo = ticker_opcao[:4]
            # O último caractere antes do strike é o tipo (CALL/PUT)
            # O dígito do ativo base geralmente é o último número do ticker original
            # ou inferido pelo padrão

            # Tentar extrair digito do ativo base do ticker da opcao
            # Regra comum: opcao GGBRE203 → acao GGBR4
            # O digito é geralmente o último caractere do ticker original da acao

            # Para simplificar, usamos heurística:
            # Se ticker da opcao tem 6+ chars, o ativo base é prefixo + ultimo digito encontrado
            digitos = [c for c in ticker_opcao if c.isdigit()]
            if digitos:
                digito = digitos[-1]  # Ultimo digito
                return f"{prefixo}{digito}", "EXERCICIO"
            else:
                # Fallback: tentar com digito 3 (mais comum)
                return f"{prefixo}3", "EXERCICIO"

        return ticker, "EXERCICIO"

    def carregar(self) -> 'ParserNegociacaoB3':
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
        col = self.colunas_detectadas.get(campo)
        if col and col in row.index:
            return row[col]
        return None

    def _limpar_ticker(self, ticker: str) -> str:
        if pd.isna(ticker):
            return ""
        ticker = str(ticker).strip().upper()
        if ticker.endswith('F'):
            ticker = ticker[:-1]
        return ticker

    def _classificar_mercado(self, mercado: str) -> str:
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

                qtd_raw = self._get_valor(row, 'quantidade')
                qtd = int(self._converter_numero(qtd_raw))

                preco_raw = self._get_valor(row, 'preco')
                preco = self._converter_numero(preco_raw)

                valor_raw = self._get_valor(row, 'valor')
                valor = self._converter_numero(valor_raw)

                preco = self._validar_preco(preco, abs(valor), qtd)

                if valor == 0 and preco > 0 and qtd > 0:
                    valor = preco * qtd

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

                # ============================================================
                # REGRA PRINCIPAL: Exercicio de opcao → Contabiliza como ACAO
                # ============================================================
                if tipo_mercado == "EXERCICIO":
                    # Mapear para ativo base
                    ativo_base, _ = self._mapear_exercicio_para_ativo_base(ticker)

                    # Determinar direcao pelo tipo de exercicio
                    # Exercicio de PUT → VENDA de acoes (investidor vende acoes ao strike)
                    # Exercicio de CALL → COMPRA de acoes (investidor compra acoes ao strike)
                    # Usar o preco como strike

                    if 'PUT' in str(mercado_raw).upper() or 'VENDA' in str(mercado_raw).upper():
                        direcao_exercicio = 'VENDA'
                    elif 'CALL' in str(mercado_raw).upper() or 'COMPRA' in str(mercado_raw).upper():
                        direcao_exercicio = 'COMPRA'
                    else:
                        # Inferir pelo tipo de opcao no ticker ou usar direcao original
                        direcao_exercicio = direcao

                    operacao_acao = {
                        'data': data,
                        'ticker': ativo_base,
                        'tipo_mercado': 'ACAO',  # Contabiliza como acao!
                        'mercado_raw': f"EXERCICIO_OPCAO → {ativo_base}",
                        'direcao': direcao_exercicio,
                        'quantidade': qtd,
                        'preco': preco,  # Strike vira preco da acao
                        'valor': abs(valor),
                        'instituicao': str(self._get_valor(row, 'instituicao') or ''),
                        'origem': f"Exercicio de opcao: {ticker}",
                    }

                    self.operacoes.append(operacao_acao)

                elif tipo_mercado in ['ACAO']:
                    self.operacoes.append(operacao)

                elif tipo_mercado in ['OPCAO_CALL', 'OPCAO_PUT']:
                    # Derivativos - nao consolidam na carteira principal
                    self.operacoes_opcoes.append(operacao)

                elif tipo_mercado in ['FUTURO', 'RENDA_FIXA']:
                    self.ignorados.append({**operacao, 'motivo': f'Tipo ignorado: {tipo_mercado}'})

                else:
                    # Tentar identificar se é acao por padrao do ticker
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
                custo_total = (compras['quantidade'] * compras['preco']).sum()
                preco_medio = custo_total / qtd_compras if qtd_compras > 0 else 0

                # Verificar se veio de exercicio de opcao
                origens = ops_ticker['origem'].dropna().unique() if 'origem' in ops_ticker.columns else []
                tem_exercicio = len(origens) > 0

                resumo.append({
                    'Ticker': ticker,
                    'Quantidade': int(saldo),
                    'Preço Médio': round(preco_medio, 4),
                    'Custo Total': round(custo_total, 2),
                    'Classe': 'ACAO',
                    'Total Compras': int(qtd_compras),
                    'Total Vendas': int(qtd_vendas),
                    'Exercício Opção': '✅' if tem_exercicio else '—',
                    'Detalhes': '; '.join(origens) if tem_exercicio else '—',
                })

        return pd.DataFrame(resumo)

    def get_operacoes_opcoes_df(self) -> pd.DataFrame:
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
