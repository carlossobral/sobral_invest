#!/usr/bin/env python3
"""
SOBRAL INVEST — Pipeline ETL CVM
================================
Baixa demonstrações financeiras do portal dados.cvm.gov.br,
processa e insere no PostgreSQL.

Autor: Carlos Sobral
Data: 2026-05-18
"""

import os
import re
import zipfile
import io
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import pandas as pd
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

# ============================================================
# CONFIGURAÇÕES
# ============================================================

# URL base do portal de dados abertos CVM
CVM_BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA"

# Diretórios
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "cvm"
LOG_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Banco de dados (substitua com suas credenciais)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://user:password@localhost:5432/sobral_invest"
)

# Anos a baixar (últimos 5 anos + atual)
ANOS_DFP = list(range(2021, 2026))  # DFP anual
ANOS_ITR = list(range(2021, 2026))  # ITR trimestral

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"etl_cvm_{date.today()}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# MAPEAMENTO DE CONTAS CONTÁBEIS (DRE/BP/DFC)
# ============================================================

# Códigos de conta contábil da CVM para cálculo de indicadores
CONTAS_MAPEAMENTO = {
    # DRE — Receita
    "receita_liquida": [
        "3.01",        # Receita de Venda de Bens e/ou Serviços
        "3.01.01",     # Receita de Venda de Bens
        "3.01.02",     # Receita de Prestação de Serviços
    ],

    # DRE — Custos
    "custo_bens_servicos": [
        "3.02",        # Custo dos Bens e/ou Serviços Vendidos
    ],

    # DRE — Despesas Operacionais
    "despesas_administrativas": [
        "3.04",        # Despesas Administrativas
        "3.04.01",     # Despesas Gerais e Administrativas
    ],
    "despesas_vendas": [
        "3.03",        # Despesas Comerciais / de Venda
    ],

    # DRE — Resultados
    "ebitda": [
        "3.05",        # EBITDA (algumas empresas reportam)
    ],
    "ebit": [
        "3.05",        # Resultado antes do Resultado Financeiro
        "3.06",        # Resultado Financeiro (para subtrair)
    ],
    "lucro_liquido": [
        "3.11",        # Lucro/Prejuízo Consolidado do Período
        "3.11.01",     # Lucro/Prejuízo do Período
        "3.09",        # Lucro/Prejuízo antes dos Tributos (fallback)
    ],
    "lucro_liquido_controladora": [
        "3.11.01",     # Atribuído à Controladora
    ],

    # BP — Ativo
    "ativo_total": [
        "1",           # Ativo Total
        "1.01",        # Ativo Circulante (soma)
    ],
    "ativo_circulante": [
        "1.01",        # Ativo Circulante
    ],
    "caixa_equivalentes": [
        "1.01.01",     # Caixa e Equivalentes de Caixa
    ],
    "contas_receber": [
        "1.01.03",     # Contas a Receber
    ],
    "estoques": [
        "1.01.04",     # Estoques
    ],

    # BP — Passivo
    "passivo_total": [
        "2",           # Passivo Total
    ],
    "passivo_circulante": [
        "2.01",        # Passivo Circulante
    ],
    "divida_curto_prazo": [
        "2.01.04",     # Empréstimos e Financiamentos (CP)
    ],
    "divida_longo_prazo": [
        "2.02.01",     # Empréstimos e Financiamentos (LP)
    ],
    "divida_total": [
        "2.01.04",     # CP
        "2.02.01",     # LP
    ],

    # BP — Patrimônio Líquido
    "patrimonio_liquido": [
        "2.03",        # Patrimônio Líquido
    ],
    "capital_social": [
        "2.03.01",     # Capital Social
    ],
    "reservas_lucros": [
        "2.03.03",     # Reservas de Lucros
    ],
    "lucros_acumulados": [
        "2.03.05",     # Lucros/Prejuízos Acumulados
    ],

    # DFC — Fluxo de Caixa
    "fluxo_caixa_operacional": [
        "6.01",        # Caixa Líquido de Atividades Operacionais
    ],
    "fluxo_caixa_investimento": [
        "6.02",        # Caixa Líquido de Atividades de Investimento
    ],
    "fluxo_caixa_financiamento": [
        "6.03",        # Caixa Líquido de Atividades de Financiamento
    ],

    # DFC — Dividendos pagos
    "dividendos_pagos": [
        "6.01.01.09",  # Dividendos e JCP Pagos
        "7.08",        # Dividendos/Juros Pagos (DFC método indireto)
    ],

    # Número de ações
    "numero_acoes": [
        "9.01",        # Ações Ordinárias
        "9.02",        # Ações Preferenciais
    ],
}


# ============================================================
# CLASSES
# ============================================================

@dataclass
class EmpresaCVM:
    """Representa uma empresa do cadastro CVM."""
    cnpj: str
    cd_cvm: str
    razao_social: str
    nome_fantasia: Optional[str]
    nome_bovespa: Optional[str]
    situacao: str
    data_registro: Optional[date]
    setor: Optional[str]
    subsetor: Optional[str]
    segmento: Optional[str]


class CVMDataExtractor:
    """Extrai e processa dados do portal de dados abertos CVM."""

    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(db_url)
        self.session = sessionmaker(bind=self.engine)()
        self.logger = logging.getLogger(self.__class__.__name__)

    # --------------------------------------------------------
    # 1. DOWNLOAD DE DADOS
    # --------------------------------------------------------

    def download_cadastro_empresas(self) -> pd.DataFrame:
        """Baixa o cadastro atualizado de companhias abertas."""
        url = f"{CVM_BASE_URL}/CAD/DADOS/cad_cia_aberta.csv"
        self.logger.info(f"Baixando cadastro de empresas: {url}")

        try:
            df = pd.read_csv(url, sep=";", encoding="latin1", dtype=str)
            self.logger.info(f"Cadastro baixado: {len(df)} empresas")
            return df
        except Exception as e:
            self.logger.error(f"Erro ao baixar cadastro: {e}")
            raise

    def download_demonstracao(self, tipo: str, ano: int) -> Optional[pd.DataFrame]:
        """
        Baixa DFP ou ITR de um ano específico.

        Args:
            tipo: 'DFP' (anual) ou 'ITR' (trimestral)
            ano: Ano do documento
        """
        url = f"{CVM_BASE_URL}/DOC/{tipo}/DADOS/{tipo.lower()}_cia_aberta_{ano}.zip"
        self.logger.info(f"Baixando {tipo} {ano}: {url}")

        try:
            response = requests.get(url, timeout=120)
            response.raise_for_status()

            # Extrair ZIP em memória
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # Procurar arquivo CSV dentro do ZIP
                csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                if not csv_files:
                    self.logger.warning(f"Nenhum CSV encontrado em {tipo} {ano}")
                    return None

                # Ler o primeiro CSV (geralmente o consolidado)
                with z.open(csv_files[0]) as f:
                    df = pd.read_csv(f, sep=";", encoding="latin1", dtype=str, low_memory=False)
                    self.logger.info(f"{tipo} {ano} carregado: {len(df)} registros")
                    return df

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.logger.warning(f"Arquivo não encontrado: {tipo} {ano}")
                return None
            raise
        except Exception as e:
            self.logger.error(f"Erro ao baixar {tipo} {ano}: {e}")
            raise

    # --------------------------------------------------------
    # 2. PROCESSAMENTO DE DADOS
    # --------------------------------------------------------

    def processar_cadastro(self, df: pd.DataFrame) -> List[EmpresaCVM]:
        """Processa DataFrame de cadastro em objetos EmpresaCVM."""
        empresas = []

        for _, row in df.iterrows():
            # Limpar CNPJ
            cnpj = re.sub(r'[^0-9]', '', str(row.get('CNPJ_CIA', '')))
            if len(cnpj) != 14:
                continue

            # Data de registro
            data_reg = None
            if pd.notna(row.get('DT_REG')):
                try:
                    data_reg = pd.to_datetime(row['DT_REG'], dayfirst=True).date()
                except:
                    pass

            empresa = EmpresaCVM(
                cnpj=cnpj,
                cd_cvm=str(row.get('CD_CVM', '')),
                razao_social=str(row.get('DENOM_COMERC', '')) or str(row.get('DENOM_SOCIAL', '')),
                nome_fantasia=str(row.get('DENOM_COMERC', '')) if pd.notna(row.get('DENOM_COMERC')) else None,
                nome_bovespa=str(row.get('TICKER', '')) if pd.notna(row.get('TICKER')) else None,
                situacao=str(row.get('SIT', 'ATIVO')),
                data_registro=data_reg,
                setor=str(row.get('SETOR_ATIV', '')) if pd.notna(row.get('SETOR_ATIV')) else None,
                subsetor=str(row.get('SUBSETOR_ATIV', '')) if pd.notna(row.get('SUBSETOR_ATIV')) else None,
                segmento=str(row.get('SEGMENTO_ATIV', '')) if pd.notna(row.get('SEGMENTO_ATIV')) else None,
            )
            empresas.append(empresa)

        self.logger.info(f"Processadas {len(empresas)} empresas válidas")
        return empresas

    def extrair_valor_conta(
        self, 
        df: pd.DataFrame, 
        cd_cvm: str, 
        cd_conta: str,
        grupo_dfp: str = "DF Consolidado",
        ordem_exercicio: str = "ÚLTIMO"
    ) -> Optional[float]:
        """
        Extrai valor de uma conta contábil específica do DataFrame.

        Args:
            df: DataFrame com demonstrações
            cd_cvm: Código CVM da empresa
            cd_conta: Código da conta contábil
            grupo_dfp: DF Consolidado ou DF Individual
            ordem_exercicio: ÚLTIMO ou PENÚLTIMO
        """
        filtro = (
            (df['CD_CVM'] == cd_cvm) &
            (df['CD_CONTA'] == cd_conta) &
            (df['GRUPO_DFP'] == grupo_dfp) &
            (df['ORDEM_EXERC'] == ordem_exercicio)
        )

        resultado = df[filtro]
        if len(resultado) == 0:
            return None

        # Pegar o primeiro valor (deve ser único)
        valor_str = str(resultado.iloc[0]['VL_CONTA'])
        # Limpar formato brasileiro (1.234,56 -> 1234.56)
        valor_str = valor_str.replace('.', '').replace(',', '.')

        try:
            return float(valor_str)
        except ValueError:
            return None

    def calcular_indicadores_empresa(
        self,
        cd_cvm: str,
        df_dfp: pd.DataFrame,
        df_itr: Optional[pd.DataFrame] = None,
        df_dfp_anterior: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Calcula todos os indicadores fundamentalistas de uma empresa.

        Returns:
            Dict com todos os indicadores calculados
        """
        indicadores = {}

        # --- Dados do Balanço Patrimonial ---
        ativo_total = self.extrair_valor_conta(df_dfp, cd_cvm, "1")
        patrimonio_liquido = self.extrair_valor_conta(df_dfp, cd_cvm, "2.03")
        ativo_circulante = self.extrair_valor_conta(df_dfp, cd_cvm, "1.01")
        passivo_circulante = self.extrair_valor_conta(df_dfp, cd_cvm, "2.01")
        caixa = self.extrair_valor_conta(df_dfp, cd_cvm, "1.01.01")

        # Dívida (simplificada - pode precisar de múltiplas contas)
        divida_cp = self.extrair_valor_conta(df_dfp, cd_cvm, "2.01.04") or 0
        divida_lp = self.extrair_valor_conta(df_dfp, cd_cvm, "2.02.01") or 0
        divida_total = divida_cp + divida_lp
        divida_liquida = divida_total - (caixa or 0)

        # --- Dados da DRE ---
        receita_liq = self.extrair_valor_conta(df_dfp, cd_cvm, "3.01")
        custo = self.extrair_valor_conta(df_dfp, cd_cvm, "3.02") or 0
        desp_adm = self.extrair_valor_conta(df_dfp, cd_cvm, "3.04") or 0
        desp_vendas = self.extrair_valor_conta(df_dfp, cd_cvm, "3.03") or 0

        # EBIT (Resultado antes do Resultado Financeiro e Tributos)
        ebit = self.extrair_valor_conta(df_dfp, cd_cvm, "3.05")

        # Lucro Líquido
        lucro_liq = self.extrair_valor_conta(df_dfp, cd_cvm, "3.11")
        if lucro_liq is None:
            lucro_liq = self.extrair_valor_conta(df_dfp, cd_cvm, "3.09")  # Fallback

        # Número de ações (pode estar em BP ou nota explicativa)
        num_acoes = self.extrair_valor_conta(df_dfp, cd_cvm, "9.01")
        if num_acoes is None:
            num_acoes = self.extrair_valor_conta(df_dfp, cd_cvm, "9.02")

        # --- Cálculos ---
        if num_acoes and num_acoes > 0:
            indicadores['lpa'] = lucro_liq / num_acoes if lucro_liq else None
            indicadores['vpa'] = patrimonio_liquido / num_acoes if patrimonio_liquido else None
        else:
            indicadores['lpa'] = None
            indicadores['vpa'] = None

        # Margens
        if receita_liq and receita_liq != 0:
            indicadores['margem_bruta'] = (receita_liq - custo) / receita_liq * 100
            indicadores['margem_liquida'] = (lucro_liq / receita_liq * 100) if lucro_liq else None
            indicadores['margem_ebit'] = (ebit / receita_liq * 100) if ebit else None
        else:
            indicadores['margem_bruta'] = None
            indicadores['margem_liquida'] = None
            indicadores['margem_ebit'] = None

        # Rentabilidade
        if patrimonio_liquido and patrimonio_liquido != 0:
            indicadores['roe'] = (lucro_liq / patrimonio_liquido * 100) if lucro_liq else None
        else:
            indicadores['roe'] = None

        if ativo_total and ativo_total != 0:
            indicadores['roa'] = (lucro_liq / ativo_total * 100) if lucro_liq else None
            indicadores['giro_ativos'] = (receita_liq / ativo_total) if receita_liq else None
        else:
            indicadores['roa'] = None
            indicadores['giro_ativos'] = None

        # Endividamento
        if patrimonio_liquido and patrimonio_liquido != 0:
            indicadores['div_liq_pl'] = divida_liquida / patrimonio_liquido
        else:
            indicadores['div_liq_pl'] = None

        if ativo_total and ativo_total != 0:
            indicadores['pl_ativos'] = patrimonio_liquido / ativo_total if patrimonio_liquido else None
            indicadores['passivos_ativos'] = (divida_total + (passivo_circulante or 0)) / ativo_total
        else:
            indicadores['pl_ativos'] = None
            indicadores['passivos_ativos'] = None

        if passivo_circulante and passivo_circulante != 0:
            indicadores['liq_corrente'] = (ativo_circulante or 0) / passivo_circulante
        else:
            indicadores['liq_corrente'] = None

        # Valuation (precisa de cotação - será preenchido depois)
        indicadores['receita_liquida_ttm'] = receita_liq
        indicadores['lucro_liquido_ttm'] = lucro_liq
        indicadores['ebit_ttm'] = ebit
        indicadores['patrimonio_liquido'] = patrimonio_liquido
        indicadores['ativo_total'] = ativo_total
        indicadores['divida_liquida'] = divida_liquida
        indicadores['caixa_equivalentes'] = caixa
        indicadores['numero_acoes'] = num_acoes

        return indicadores

    # --------------------------------------------------------
    # 3. PERSISTÊNCIA NO BANCO
    # --------------------------------------------------------

    def salvar_empresas(self, empresas: List[EmpresaCVM]) -> None:
        """Insere ou atualiza empresas no banco."""
        with self.engine.begin() as conn:
            for emp in tqdm(empresas, desc="Salvando empresas"):
                query = text("""
                    INSERT INTO empresas (
                        cnpj, cd_cvm, razao_social, nome_fantasia, nome_bovespa,
                        situacao, data_registro, setor, subsetor, segmento
                    ) VALUES (
                        :cnpj, :cd_cvm, :razao_social, :nome_fantasia, :nome_bovespa,
                        :situacao, :data_registro, :setor, :subsetor, :segmento
                    )
                    ON CONFLICT (cnpj) DO UPDATE SET
                        cd_cvm = EXCLUDED.cd_cvm,
                        razao_social = EXCLUDED.razao_social,
                        nome_fantasia = EXCLUDED.nome_fantasia,
                        nome_bovespa = EXCLUDED.nome_bovespa,
                        situacao = EXCLUDED.situacao,
                        data_registro = EXCLUDED.data_registro,
                        setor = EXCLUDED.setor,
                        subsetor = EXCLUDED.subsetor,
                        segmento = EXCLUDED.segmento,
                        updated_at = CURRENT_TIMESTAMP
                """)
                conn.execute(query, {
                    'cnpj': emp.cnpj,
                    'cd_cvm': emp.cd_cvm,
                    'razao_social': emp.razao_social,
                    'nome_fantasia': emp.nome_fantasia,
                    'nome_bovespa': emp.nome_bovespa,
                    'situacao': emp.situacao,
                    'data_registro': emp.data_registro,
                    'setor': emp.setor,
                    'subsetor': emp.subsetor,
                    'segmento': emp.segmento,
                })

        self.logger.info(f"{len(empresas)} empresas salvas/atualizadas")

    def salvar_demonstracoes(self, df: pd.DataFrame, tipo: str, ano: int) -> int:
        """Salva demonstrações financeiras no banco."""
        registros = 0

        with self.engine.begin() as conn:
            # Buscar mapeamento cd_cvm -> empresa_id
            result = conn.execute(text("SELECT id, cd_cvm FROM empresas"))
            empresa_map = {row.cd_cvm: row.id for row in result}

            for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Salvando {tipo} {ano}"):
                cd_cvm = str(row.get('CD_CVM', ''))
                empresa_id = empresa_map.get(cd_cvm)

                if not empresa_id:
                    continue

                # Parse datas
                dt_refer = None
                if pd.notna(row.get('DT_REFER')):
                    try:
                        dt_refer = pd.to_datetime(row['DT_REFER'], dayfirst=True).date()
                    except:
                        dt_refer = date(ano, 12, 31)

                dt_ini = None
                if pd.notna(row.get('DT_INI_EXERC')):
                    try:
                        dt_ini = pd.to_datetime(row['DT_INI_EXERC'], dayfirst=True).date()
                    except:
                        pass

                dt_fim = None
                if pd.notna(row.get('DT_FIM_EXERC')):
                    try:
                        dt_fim = pd.to_datetime(row['DT_FIM_EXERC'], dayfirst=True).date()
                    except:
                        pass

                # Parse valor
                valor_str = str(row.get('VL_CONTA', '0'))
                valor_str = valor_str.replace('.', '').replace(',', '.')
                try:
                    valor = float(valor_str)
                except ValueError:
                    valor = 0

                # Determinar trimestre para ITR
                trimestre = None
                if tipo == 'ITR' and dt_fim:
                    mes = dt_fim.month
                    if mes in [3, 4]:
                        trimestre = 1
                    elif mes in [6, 7]:
                        trimestre = 2
                    elif mes in [9, 10]:
                        trimestre = 3
                    elif mes in [12, 1, 2]:
                        trimestre = 4

                query = text("""
                    INSERT INTO demonstracoes_financeiras (
                        empresa_id, tipo_documento, ano, trimestre,
                        dt_referencia, dt_ini_exercicio, dt_fim_exercicio,
                        cd_conta, ds_conta, vl_conta, grupo_dfp, moeda,
                        escala_moeda, ordem_exercicio, versao
                    ) VALUES (
                        :empresa_id, :tipo, :ano, :trimestre,
                        :dt_refer, :dt_ini, :dt_fim,
                        :cd_conta, :ds_conta, :vl_conta, :grupo_dfp, :moeda,
                        :escala, :ordem, :versao
                    )
                    ON CONFLICT (empresa_id, tipo_documento, ano, trimestre, cd_conta, ordem_exercicio, versao)
                    DO UPDATE SET
                        vl_conta = EXCLUDED.vl_conta,
                        ds_conta = EXCLUDED.ds_conta,
                        dt_referencia = EXCLUDED.dt_referencia,
                        dt_ini_exercicio = EXCLUDED.dt_ini_exercicio,
                        dt_fim_exercicio = EXCLUDED.dt_fim_exercicio
                """)

                conn.execute(query, {
                    'empresa_id': empresa_id,
                    'tipo': tipo,
                    'ano': ano,
                    'trimestre': trimestre,
                    'dt_refer': dt_refer,
                    'dt_ini': dt_ini,
                    'dt_fim': dt_fim,
                    'cd_conta': str(row.get('CD_CONTA', '')),
                    'ds_conta': str(row.get('DS_CONTA', '')),
                    'vl_conta': valor,
                    'grupo_dfp': str(row.get('GRUPO_DFP', 'DF Consolidado')),
                    'moeda': str(row.get('MOEDA', 'REAL')),
                    'escala': str(row.get('ESCALA_MOEDA', 'MIL')),
                    'ordem': str(row.get('ORDEM_EXERC', 'ÚLTIMO')),
                    'versao': int(row.get('VERSAO', 1)) if pd.notna(row.get('VERSAO')) else 1,
                })
                registros += 1

        self.logger.info(f"{registros} demonstrações salvas ({tipo} {ano})")
        return registros

    # --------------------------------------------------------
    # 4. PIPELINE COMPLETO
    # --------------------------------------------------------

    def executar_pipeline_completo(self):
        """Executa o pipeline ETL completo."""
        self.logger.info("=" * 60)
        self.logger.info("INICIANDO PIPELINE ETL CVM — SOBRAL INVEST")
        self.logger.info("=" * 60)

        # 1. Cadastro de empresas
        self.logger.info("
[1/4] BAIXANDO CADASTRO DE EMPRESAS...")
        df_cadastro = self.download_cadastro_empresas()
        empresas = self.processar_cadastro(df_cadastro)
        self.salvar_empresas(empresas)

        # 2. DFPs (Demonstrações Anuais)
        self.logger.info("
[2/4] BAIXANDO DFPs (DEMONSTRAÇÕES ANUAIS)...")
        for ano in ANOS_DFP:
            df_dfp = self.download_demonstracao("DFP", ano)
            if df_dfp is not None:
                self.salvar_demonstracoes(df_dfp, "DFP", ano)

        # 3. ITRs (Demonstrações Trimestrais)
        self.logger.info("
[3/4] BAIXANDO ITRs (DEMONSTRAÇÕES TRIMESTRAIS)...")
        for ano in ANOS_ITR:
            df_itr = self.download_demonstracao("ITR", ano)
            if df_itr is not None:
                self.salvar_demonstracoes(df_itr, "ITR", ano)

        # 4. Calcular indicadores (após ter todos os dados)
        self.logger.info("
[4/4] CALCULANDO INDICADORES...")
        self.calcular_indicadores_todas_empresas()

        self.logger.info("
" + "=" * 60)
        self.logger.info("PIPELINE ETL CONCLUÍDO COM SUCESSO!")
        self.logger.info("=" * 60)

    def calcular_indicadores_todas_empresas(self) -> None:
        """Calcula indicadores para todas as empresas ativas."""
        with self.engine.begin() as conn:
            result = conn.execute(text("""
                SELECT id, cd_cvm, nome_bovespa 
                FROM empresas 
                WHERE situacao = 'ATIVO'
            """))
            empresas = list(result)

        self.logger.info(f"Calculando indicadores para {len(empresas)} empresas...")

        for emp in tqdm(empresas, desc="Calculando indicadores"):
            try:
                # Buscar último DFP
                result = conn.execute(text("""
                    SELECT * FROM demonstracoes_financeiras
                    WHERE empresa_id = :emp_id AND tipo_documento = 'DFP'
                    ORDER BY dt_referencia DESC LIMIT 1
                """), {'emp_id': emp.id})

                # TODO: Implementar cálculo completo de indicadores
                # Inserir na tabela indicadores

            except Exception as e:
                self.logger.error(f"Erro ao calcular indicadores para {emp.nome_bovespa}: {e}")


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    extractor = CVMDataExtractor()
    extractor.executar_pipeline_completo()
