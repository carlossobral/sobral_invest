
-- ============================================================
-- 1. TABELAS DE CONFIGURAÇÃO / LOOKUP
-- ============================================================

CREATE TABLE IF NOT EXISTS setores_economicos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subsetores (
    id SERIAL PRIMARY KEY,
    setor_id INTEGER REFERENCES setores_economicos(id),
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS segmentos (
    id SERIAL PRIMARY KEY,
    subsetor_id INTEGER REFERENCES subsetores(id),
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 2. TABELA DE EMPRESAS / ATIVOS
-- ============================================================

CREATE TABLE IF NOT EXISTS empresas (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(18) UNIQUE NOT NULL,
    cd_cvm VARCHAR(10) UNIQUE NOT NULL,
    razao_social VARCHAR(200) NOT NULL,
    nome_fantasia VARCHAR(200),
    nome_bovespa VARCHAR(20),           -- Ex: PETR4, VALE3
    setor_id INTEGER REFERENCES setores_economicos(id),
    subsetor_id INTEGER REFERENCES subsetores(id),
    segmento_id INTEGER REFERENCES segmentos(id),

    -- Dados cadastrais
    situacao VARCHAR(20),               -- ATIVO, CANCELADO, etc
    data_registro DATE,                  -- Data de listagem na B3
    data_cancelamento DATE,
    tipo_mercado VARCHAR(50),           -- Novo Mercado, Nível 1, etc

    -- Flags
    is_fii BOOLEAN DEFAULT FALSE,
    is_etf BOOLEAN DEFAULT FALSE,
    is_bdr BOOLEAN DEFAULT FALSE,
    is_fiagro BOOLEAN DEFAULT FALSE,

    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_empresas_nome_bovespa ON empresas(nome_bovespa);
CREATE INDEX idx_empresas_cnpj ON empresas(cnpj);
CREATE INDEX idx_empresas_cd_cvm ON empresas(cd_cvm);

-- ============================================================
-- 3. TABELAS DE DEMONSTRATIVOS FINANCEIROS (BRUTOS CVM)
-- ============================================================

CREATE TABLE IF NOT EXISTS demonstracoes_financeiras (
    id BIGSERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id),

    -- Identificação do documento
    tipo_documento VARCHAR(10) NOT NULL,    -- DFP, ITR, IAN
    ano INTEGER NOT NULL,
    trimestre INTEGER,                      -- 1,2,3,4 (null para DFP anual)

    -- Período
    dt_referencia DATE NOT NULL,
    dt_ini_exercicio DATE,
    dt_fim_exercicio DATE,

    -- Conta contábil
    cd_conta VARCHAR(30) NOT NULL,
    ds_conta VARCHAR(300) NOT NULL,
    vl_conta NUMERIC(20,2) NOT NULL,

    -- Metadados CVM
    grupo_dfp VARCHAR(20),                  -- DF Consolidado, DF Individual
    moeda VARCHAR(10) DEFAULT 'REAL',
    escala_moeda VARCHAR(20) DEFAULT 'MIL',  -- MIL, UNIDADE
    ordem_exercicio VARCHAR(20),            -- ÚLTIMO, PENÚLTIMO
    versao INTEGER DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(empresa_id, tipo_documento, ano, trimestre, cd_conta, ordem_exercicio, versao)
);

CREATE INDEX idx_df_empresa ON demonstracoes_financeiras(empresa_id);
CREATE INDEX idx_df_tipo_ano ON demonstracoes_financeiras(tipo_documento, ano);
CREATE INDEX idx_df_conta ON demonstracoes_financeiras(cd_conta);
CREATE INDEX idx_df_referencia ON demonstracoes_financeiras(dt_referencia);

-- ============================================================
-- 4. TABELA DE COTAÇÕES
-- ============================================================

CREATE TABLE IF NOT EXISTS cotacoes (
    id BIGSERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id),

    data DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,

    preco_abertura NUMERIC(12,4),
    preco_maximo NUMERIC(12,4),
    preco_minimo NUMERIC(12,4),
    preco_fechamento NUMERIC(12,4),
    preco_ajustado NUMERIC(12,4),
    volume NUMERIC(20,0),

    -- Campos calculados
    variacao_dia NUMERIC(8,4),
    media_30d NUMERIC(12,4),
    media_200d NUMERIC(12,4),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(empresa_id, data)
);

CREATE INDEX idx_cotacoes_empresa_data ON cotacoes(empresa_id, data);
CREATE INDEX idx_cotacoes_ticker ON cotacoes(ticker);
CREATE INDEX idx_cotacoes_data ON cotacoes(data);

-- ============================================================
-- 5. TABELA DE INDICADORES FUNDAMENTALISTAS
-- ============================================================

CREATE TABLE IF NOT EXISTS indicadores (
    id BIGSERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id),

    -- Período de referência
    data_calculo DATE NOT NULL,
    tipo_periodo VARCHAR(10) NOT NULL,      -- TTM (últimos 12m), ANUAL, TRIMESTRAL
    ano_referencia INTEGER,
    trimestre_referencia INTEGER,

    -- ========== INDICADORES DE VALUATION ==========
    dy NUMERIC(8,4),                        -- Dividend Yield
    pl NUMERIC(8,4),                        -- P/L
    peg_ratio NUMERIC(8,4),                 -- PEG Ratio
    pvp NUMERIC(8,4),                       -- P/VP
    ev_ebitda NUMERIC(8,4),                 -- EV/EBITDA
    ev_ebit NUMERIC(8,4),                   -- EV/EBIT
    p_ebitda NUMERIC(8,4),                  -- P/EBITDA
    p_ebit NUMERIC(8,4),                    -- P/EBIT
    vpa NUMERIC(12,4),                      -- Valor Patrimonial por Ação
    p_ativo NUMERIC(8,4),                   -- P/Ativo
    lpa NUMERIC(12,4),                      -- Lucro por Ação
    psr NUMERIC(8,4),                       -- P/SR (Price/Sales Ratio)
    p_cap_giro NUMERIC(8,4),                -- P/Capital de Giro
    p_ativo_circ_liq NUMERIC(8,4),          -- P/Ativo Circulante Líquido

    -- ========== INDICADORES DE ENDIVIDAMENTO ==========
    div_liq_pl NUMERIC(8,4),                -- Dív. Líquida / PL
    div_liq_ebitda NUMERIC(8,4),            -- Dív. Líquida / EBITDA
    div_liq_ebit NUMERIC(8,4),              -- Dív. Líquida / EBIT
    pl_ativos NUMERIC(8,4),                 -- PL / Ativos
    passivos_ativos NUMERIC(8,4),           -- Passivos / Ativos
    liq_corrente NUMERIC(8,4),              -- Liquidez Corrente

    -- ========== INDICADORES DE EFICIÊNCIA ==========
    margem_bruta NUMERIC(8,4),              -- M. Bruta
    margem_ebitda NUMERIC(8,4),             -- M. EBITDA
    margem_ebit NUMERIC(8,4),               -- M. EBIT
    margem_liquida NUMERIC(8,4),            -- M. Líquida

    -- ========== INDICADORES DE RENTABILIDADE ==========
    roe NUMERIC(8,4),                       -- ROE
    roa NUMERIC(8,4),                       -- ROA
    roic NUMERIC(8,4),                      -- ROIC
    giro_ativos NUMERIC(8,4),               -- Giro dos Ativos

    -- ========== INDICADORES DE CRESCIMENTO ==========
    cagr_receitas_5a NUMERIC(8,4),          -- CAGR Receitas 5 anos
    cagr_lucros_5a NUMERIC(8,4),            -- CAGR Lucros 5 anos
    cagr_receitas_3a NUMERIC(8,4),          -- CAGR Receitas 3 anos
    cagr_lucros_3a NUMERIC(8,4),            -- CAGR Lucros 3 anos

    -- ========== INDICADORES DE DIVIDENDOS ==========
    payout NUMERIC(8,4),                    -- Payout
    dividendos_12m NUMERIC(20,2),           -- Total dividendos últimos 12m
    dy_media_5a NUMERIC(8,4),               -- DY médio 5 anos
    dy_media_7a NUMERIC(8,4),               -- DY médio 7 anos
    consistencia_dy NUMERIC(8,4),           -- % anos com DY > 0

    -- ========== DADOS BRUTOS (para cálculos) ==========
    receita_liquida_ttm NUMERIC(20,2),
    lucro_liquido_ttm NUMERIC(20,2),
    ebitda_ttm NUMERIC(20,2),
    ebit_ttm NUMERIC(20,2),
    patrimonio_liquido NUMERIC(20,2),
    ativo_total NUMERIC(20,2),
    divida_liquida NUMERIC(20,2),
    caixa_equivalentes NUMERIC(20,2),
    numero_acoes NUMERIC(20,0),
    valor_mercado NUMERIC(20,2),
    enterprise_value NUMERIC(20,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(empresa_id, data_calculo, tipo_periodo)
);

CREATE INDEX idx_indicadores_empresa ON indicadores(empresa_id);
CREATE INDEX idx_indicadores_data ON indicadores(data_calculo);
CREATE INDEX idx_indicadores_dy ON indicadores(dy);
CREATE INDEX idx_indicadores_pl ON indicadores(pl);
CREATE INDEX idx_indicadores_roe ON indicadores(roe);

-- ============================================================
-- 6. TABELA DE PREÇO TETO / VALOR JUSTO
-- ============================================================

CREATE TABLE IF NOT EXISTS precos_alvo (
    id BIGSERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id),

    data_calculo DATE NOT NULL,
    preco_atual NUMERIC(12,4) NOT NULL,

    -- Métodos de valuation
    preco_teto_graham NUMERIC(12,4),
    preco_teto_graham_br NUMERIC(12,4),
    preco_teto_lynch NUMERIC(12,4),
    preco_teto_bazin NUMERIC(12,4),         -- Taxa 7%
    preco_teto_agf NUMERIC(12,4),           -- Método AGF projetivo

    -- Valor justo consolidado (média ponderada ou mediana)
    valor_justo_consolidado NUMERIC(12,4),

    -- Margens de segurança
    ms_graham NUMERIC(8,4),                 -- (Teto - Atual) / Teto
    ms_graham_br NUMERIC(8,4),
    ms_lynch NUMERIC(8,4),
    ms_bazin NUMERIC(8,4),
    ms_agf NUMERIC(8,4),
    ms_consolidada NUMERIC(8,4),

    -- Parâmetros utilizados
    lpa_utilizado NUMERIC(12,4),
    vpa_utilizado NUMERIC(12,4),
    dy_medio_utilizado NUMERIC(8,4),
    cagr_lucros_utilizado NUMERIC(8,4),
    taxa_selic_utilizado NUMERIC(8,4),
    taxa_bazin_utilizado NUMERIC(8,4) DEFAULT 7.0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(empresa_id, data_calculo)
);

CREATE INDEX idx_precos_alvo_empresa ON precos_alvo(empresa_id);
CREATE INDEX idx_precos_alvo_data ON precos_alvo(data_calculo);

-- ============================================================
-- 7. TABELA DE SCORING BUY AND HOLD
-- ============================================================

CREATE TABLE IF NOT EXISTS scoring_bh (
    id BIGSERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id),

    data_calculo DATE NOT NULL,
    score_total INTEGER NOT NULL,           -- 0 a 100

    -- Critérios individuais (0 ou pontuação)
    score_mais_7_anos_bolsa INTEGER DEFAULT 0,      -- 10 pts
    score_nunca_prejuizo INTEGER DEFAULT 0,          -- 15 pts
    score_lucro_28_trimestres INTEGER DEFAULT 0,     -- 15 pts
    score_dy_7anos_7pct INTEGER DEFAULT 0,         -- 15 pts
    score_roe_12pct INTEGER DEFAULT 0,               -- 15 pts
    score_divida_menor_pl INTEGER DEFAULT 0,         -- 10 pts
    score_cresc_receita_7a INTEGER DEFAULT 0,        -- 10 pts
    score_cresc_lucro_7a INTEGER DEFAULT 0,          -- 10 pts
    score_liquidez_1m INTEGER DEFAULT 0,             -- 10 pts

    -- Flags booleanas
    passou_mais_7_anos BOOLEAN DEFAULT FALSE,
    passou_nunca_prejuizo BOOLEAN DEFAULT FALSE,
    passou_lucro_28t BOOLEAN DEFAULT FALSE,
    passou_dy_7a BOOLEAN DEFAULT FALSE,
    passou_roe_12 BOOLEAN DEFAULT FALSE,
    passou_divida_pl BOOLEAN DEFAULT FALSE,
    passou_cresc_rec BOOLEAN DEFAULT FALSE,
    passou_cresc_luc BOOLEAN DEFAULT FALSE,
    passou_liquidez BOOLEAN DEFAULT FALSE,

    -- Classificação
    classificacao VARCHAR(20),              -- EXCELENTE (>80), BOM (60-80), REGULAR (40-60), FRACO (<40)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(empresa_id, data_calculo)
);

CREATE INDEX idx_scoring_bh_empresa ON scoring_bh(empresa_id);
CREATE INDEX idx_scoring_bh_score ON scoring_bh(score_total);
CREATE INDEX idx_scoring_bh_class ON scoring_bh(classificacao);

-- ============================================================
-- 8. TABELAS DE CARTEIRA DO USUÁRIO
-- ============================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    email VARCHAR(200) UNIQUE NOT NULL,
    nome VARCHAR(200),

    -- Configurações pessoais
    taxa_bazin_personalizada NUMERIC(5,2) DEFAULT 7.0,
    prazo_longo_minimo INTEGER DEFAULT 7,   -- anos mínimo na bolsa
    dy_minimo_bh NUMERIC(5,2) DEFAULT 7.0,
    roe_minimo_bh NUMERIC(5,2) DEFAULT 12.0,
    liquidez_minima_bh NUMERIC(20,2) DEFAULT 1000000,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS carteiras (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    is_principal BOOLEAN DEFAULT FALSE,
    moeda_principal VARCHAR(10) DEFAULT 'BRL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS carteira_ativos (
    id BIGSERIAL PRIMARY KEY,
    carteira_id INTEGER REFERENCES carteiras(id),
    empresa_id INTEGER REFERENCES empresas(id),

    -- Dados da transação/aquisição
    data_aquisicao DATE NOT NULL,
    quantidade NUMERIC(20,8) NOT NULL,      -- Permite frações (FII)
    preco_medio NUMERIC(12,4) NOT NULL,
    custo_total NUMERIC(20,2) NOT NULL,

    -- Tipo de operação
    tipo_operacao VARCHAR(20) DEFAULT 'COMPRA',  -- COMPRA, BONIFICACAO, DESDOBRAMENTO
    corretora VARCHAR(100),
    nota_corretagem VARCHAR(50),

    -- Situação
    ativo BOOLEAN DEFAULT TRUE,
    data_venda DATE,
    preco_venda NUMERIC(12,4),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_carteira_ativos_carteira ON carteira_ativos(carteira_id);
CREATE INDEX idx_carteira_ativos_empresa ON carteira_ativos(empresa_id);

CREATE TABLE IF NOT EXISTS carteira_proventos (
    id BIGSERIAL PRIMARY KEY,
    carteira_id INTEGER REFERENCES carteiras(id),
    empresa_id INTEGER REFERENCES empresas(id),

    data_pagamento DATE NOT NULL,
    tipo_provento VARCHAR(20) NOT NULL,     -- DIVIDENDO, JCP, BONIFICACAO
    valor_por_acao NUMERIC(12,4) NOT NULL,
    quantidade_acoes NUMERIC(20,8) NOT NULL,
    valor_total NUMERIC(20,2) NOT NULL,

    -- IR / DARF
    ir_retido NUMERIC(12,4) DEFAULT 0,      -- Para JCP
    valor_liquido NUMERIC(20,2),

    -- Fonte
    data_com DATE,
    data_anuncio DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_proventos_carteira ON carteira_proventos(carteira_id);
CREATE INDEX idx_proventos_empresa ON carteira_proventos(empresa_id);
CREATE INDEX idx_proventos_data ON carteira_proventos(data_pagamento);

-- ============================================================
-- 9. TABELA DE AGENDA DE DIVIDENDOS
-- ============================================================

CREATE TABLE IF NOT EXISTS agenda_dividendos (
    id BIGSERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id),

    -- Datas
    data_anuncio DATE,
    data_com DATE NOT NULL,
    data_pagamento DATE NOT NULL,

    -- Valores
    tipo_provento VARCHAR(20) NOT NULL,     -- DIVIDENDO, JCP
    valor_por_acao NUMERIC(12,4) NOT NULL,
    valor_total_estimado NUMERIC(20,2),

    -- Status
    status VARCHAR(20) DEFAULT 'ANUNCIADO', -- ANUNCIADO, PAGO, CANCELADO

    -- Metadados
    fonte VARCHAR(50),                      -- CVM, B3, ESTIMATIVA
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agenda_empresa ON agenda_dividendos(empresa_id);
CREATE INDEX idx_agenda_data_com ON agenda_dividendos(data_com);
CREATE INDEX idx_agenda_data_pag ON agenda_dividendos(data_pagamento);

-- ============================================================
-- 10. TABELA DE NOTAS DE CORRETAGEM (Importação)
-- ============================================================

CREATE TABLE IF NOT EXISTS notas_corretagem (
    id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),

    -- Identificação
    numero_nota VARCHAR(50) NOT NULL,
    corretora VARCHAR(100) NOT NULL,
    data_pregao DATE NOT NULL,

    -- Valores
    valor_operacoes NUMERIC(20,2) NOT NULL,
    taxa_liquidacao NUMERIC(12,4),
    taxa_registro NUMERIC(12,4),
    taxa_termo_opcoes NUMERIC(12,4),
    taxa_ana NUMERIC(12,4),
    emolumentos NUMERIC(12,4),
    taxa_operacional NUMERIC(12,4),
    execucao NUMERIC(12,4),
    taxa_custodia NUMERIC(12,4),
    impostos NUMERIC(12,4),
    irrf_daytrade NUMERIC(12,4),
    outros NUMERIC(12,4),

    -- Totais
    taxa_corretagem_total NUMERIC(20,2),
    valor_liquido NUMERIC(20,2) NOT NULL,

    -- Fonte
    origem VARCHAR(20) DEFAULT 'MANUAL',    -- MANUAL, PDF, INVESTIDOR_B3
    arquivo_origem VARCHAR(500),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notas_corretagem_operacoes (
    id BIGSERIAL PRIMARY KEY,
    nota_id INTEGER REFERENCES notas_corretagem(id),
    empresa_id INTEGER REFERENCES empresas(id),

    tipo_operacao VARCHAR(10) NOT NULL,     -- COMPRA, VENDA
    quantidade NUMERIC(20,8) NOT NULL,
    preco NUMERIC(12,4) NOT NULL,
    valor_total NUMERIC(20,2) NOT NULL,
    day_trade BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 11. TABELA DE LOG DE PROCESSAMENTO
-- ============================================================

CREATE TABLE IF NOT EXISTS log_processamento (
    id BIGSERIAL PRIMARY KEY,
    tipo_processo VARCHAR(50) NOT NULL,   -- ETL_CVM, CALC_INDICADORES, ATUALIZA_COTACOES
    status VARCHAR(20) NOT NULL,            -- INICIADO, SUCESSO, ERRO
    mensagem TEXT,
    registros_processados INTEGER DEFAULT 0,
    tempo_execucao_segundos NUMERIC(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 12. VIEWS PARA CONSULTAS RÁPIDAS
-- ============================================================

-- View: Resumo de empresa com últimos indicadores
CREATE OR REPLACE VIEW v_empresa_resumo AS
SELECT 
    e.id AS empresa_id,
    e.nome_bovespa AS ticker,
    e.razao_social,
    e.situacao,
    e.data_registro,
    i.data_calculo,
    i.dy, i.pl, i.pvp, i.roe, i.margem_liquida,
    i.cagr_receitas_5a, i.cagr_lucros_5a,
    i.valor_mercado,
    s.score_total AS score_bh,
    s.classificacao AS classificacao_bh,
    p.preco_atual,
    p.preco_teto_graham,
    p.preco_teto_bazin,
    p.ms_consolidada
FROM empresas e
LEFT JOIN LATERAL (
    SELECT * FROM indicadores i2 
    WHERE i2.empresa_id = e.id 
    ORDER BY i2.data_calculo DESC 
    LIMIT 1
) i ON true
LEFT JOIN LATERAL (
    SELECT * FROM scoring_bh s2 
    WHERE s2.empresa_id = e.id 
    ORDER BY s2.data_calculo DESC 
    LIMIT 1
) s ON true
LEFT JOIN LATERAL (
    SELECT * FROM precos_alvo p2 
    WHERE p2.empresa_id = e.id 
    ORDER BY p2.data_calculo DESC 
    LIMIT 1
) p ON true
WHERE e.situacao = 'ATIVO';

-- View: Carteira consolidada do usuário
CREATE OR REPLACE VIEW v_carteira_consolidada AS
SELECT 
    ca.carteira_id,
    c.nome AS nome_carteira,
    u.nome AS nome_usuario,
    ca.empresa_id,
    e.nome_bovespa AS ticker,
    e.razao_social,
    SUM(ca.quantidade) AS quantidade_total,
    SUM(ca.custo_total) / NULLIF(SUM(ca.quantidade), 0) AS preco_medio,
    SUM(ca.custo_total) AS custo_total,
    cot.preco_fechamento AS preco_atual,
    SUM(ca.quantidade) * cot.preco_fechamento AS valor_atual,
    (SUM(ca.quantidade) * cot.preco_fechamento - SUM(ca.custo_total)) / NULLIF(SUM(ca.custo_total), 0) * 100 AS rentabilidade_pct
FROM carteira_ativos ca
JOIN carteiras c ON ca.carteira_id = c.id
JOIN usuarios u ON c.usuario_id = u.id
JOIN empresas e ON ca.empresa_id = e.id
LEFT JOIN LATERAL (
    SELECT preco_fechamento FROM cotacoes 
    WHERE empresa_id = ca.empresa_id 
    ORDER BY data DESC LIMIT 1
) cot ON true
WHERE ca.ativo = TRUE
GROUP BY ca.carteira_id, c.nome, u.nome, ca.empresa_id, e.nome_bovespa, e.razao_social, cot.preco_fechamento;

COMMIT;
