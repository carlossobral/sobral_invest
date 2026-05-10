import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import os

from usebolsai_client import buscar_acoes_usebolsai
from indicadores import calcular_indicadores
from checklist import checklist_buy_hold
from valuation import calcular_graham, calcular_graham_br, calcular_bazin, calcular_lynch, calcular_agf

# ─── Configuração ────────────────────────────────
st.set_page_config(
    page_title="Sobral Invest",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Helpers ───────────────────────────────────────────────────────────────

def formatar_percentual(valor):
    try:
        valor = float(valor)
    except Exception:
        return "N/A"
    if abs(valor) <= 1:
        return f"{valor:.2%}"
    return f"{valor:.2f}%"


def gerar_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ativos")
        writer.save()
    return output.getvalue()


def criar_estilo_tema(tema: str):
    if tema == "Claro":
        return """
            <style>
                body, .main { background-color: #f9f9f9; color: #000000; }
                h1, h2, h3, h4, h5 { color: #003366; }
                .stDataFrame { background-color: #ffffff; color: #000000; }
            </style>
        """
    return """
            <style>
                body, .main { background-color: #121212; color: #ffffff; }
                h1, h2, h3, h4, h5 { color: #66ccff; }
                .stDataFrame { background-color: #1e1e1e; color: #ffffff; }
            </style>
        """


def montar_agenda_dividendos(df: pd.DataFrame) -> pd.DataFrame:
    agenda = []
    hoje = pd.to_datetime("today").normalize()
    for _, row in df.head(5).iterrows():
        ticker = row.get("Ticker", "N/A")
        dy = float(row.get("DY") or 0)
        preco = float(row.get("Cotacao") or 0)
        if preco <= 0 or dy <= 0:
            continue
        valor = preco * dy / 4
        agenda.append({
            "Ticker": ticker,
            "Data Ex": (hoje + pd.Timedelta(days=7)).strftime("%Y-%m-%d"),
            "Pagamento Estimado": (hoje + pd.Timedelta(days=30)).strftime("%Y-%m-%d"),
            "Valor por ação (estimado)": f"R$ {valor:.2f}",
            "Dividend Yield": formatar_percentual(dy)
        })
    return pd.DataFrame(agenda)


# ─── Sidebar ──────────────────────────────────────────────────────────────
st.sidebar.title("Configurações")
tema = st.sidebar.radio("Tema visual", ["Claro", "Escuro"], index=0)
st.sidebar.markdown(criar_estilo_tema(tema), unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### Funcionalidades sugeridas")
st.sidebar.markdown(
    "- Comparar ações lado a lado\n"
    "- Rankings por DY, ROE, PL e Score\n"
    "- Calendário de dividendos e eventos\n"
    "- Exportar relatórios para Excel\n"
    "- Definições rápidas de indicadores e interpretações\n"
)
st.sidebar.markdown("---")
st.sidebar.markdown("### Observações")
st.sidebar.info(
    "Os indicadores são calculados a partir de dados do UsebolsaI e yfinance. "
    "Valores podem variar conforme disponibilidade de dados." 
)


# ─── Cabeçalho ───────────────────────────────────────────────────────────────
st.markdown("# 📊 Sobral Invest")
st.markdown(
    "Plataforma simples para análise fundamentalista da B3 com métricas, ranking e valuation. "
    "Digite os tickers, compare resultados e exporte relatórios em Excel."
)

with st.expander("Como aperfeiçoar a página inicial", expanded=True):
    st.markdown(
        "- Adicionar um comparador de até 5 ações.\n"
        "- Exibir cards de destaque com melhor Score, maior DY, melhor ROE e menor PL.\n"
        "- Incluir um calendário de dividendos real e notícias recentes.\n"
        "- Mostrar explicações rápidas dos indicadores e dos modelos de valuation.\n"
        "- Permitir a exportação de relatórios de ativos para Excel."
    )

st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### O que você pode fazer aqui")
    st.markdown(
        "- Buscar tickers da B3 e visualizar métricas fundacionais.\n"
        "- Comparar ações lado a lado e identificar as melhores oportunidades.\n"
        "- Visualizar rankings de DY, ROE e Score Buy & Hold.\n"
        "- Exportar a análise em Excel para consultas offline."
    )
with col2:
    st.markdown("### Diferenciais")
    st.markdown(
        "- Interface leve e direta.\n"
        "- Uso de dados do UsebolsaI e yfinance.\n"
        "- Métricas e valuation prontos para comparar.\n"
        "- Ideal para quem busca análise fundamentalista rápida."
    )

# ─── Carrega dados do Excel ───────────────────────────────────────────────
@st.cache_data
def carregar_dados_excel():
    if os.path.exists("ativos.xlsx"):
        try:
            return pd.read_excel("ativos.xlsx", sheet_name="Ativos")
        except Exception as e:
            st.warning(f"Erro ao carregar ativos.xlsx: {e}")
            return None
    return None

# ─── Busca de tickers (opcional para análise customizada) ───────────────────────────────────────────────────────
with st.form("ticker_form"):
    tickers_input = st.text_area("(Opcional) Digite os tickers separados por vírgula para análise customizada", "PETR4,VALE3,ITSA4")
    submitted = st.form_submit_button("Buscar dados customizados")

# Tenta carregar dados do Excel primeiro
df = None
if not submitted:
    df = carregar_dados_excel()
    if df is not None:
        st.session_state["dados_ativos"] = df
else:
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    if not tickers:
        st.warning("Informe pelo menos um ticker válido.")
    else:
        with st.spinner("Buscando dados e calculando indicadores..."):
            resultados, _ = buscar_acoes_usebolsai(tickers)

            dados = []
            for r in resultados:
                ind = calcular_indicadores(r)
                _, score = checklist_buy_hold(ind)
                graham = calcular_graham(ind["LPA"], ind["VPA"])
                graham_br = calcular_graham_br(
                    graham,
                    ind["ROE"],
                    ind["Divida_PL"],
                    ind["Margem_Liquida"],
                    ind["Receita_CAGR"]
                )
                bazin = calcular_bazin(ind["DY"])
                lynch = calcular_lynch(ind["PL"], ind["Lucro_CAGR"])
                agf = calcular_agf(ind["DY"], ind["Lucro_CAGR"])

                dados.append({
                    "Ticker": r.get("Ticker", "N/A"),
                    **ind,
                    "Score_BH": score,
                    "Graham": graham,
                    "Graham_BR": graham_br,
                    "Bazin": bazin,
                    "Lynch_PEG": lynch,
                    "AGF": agf
                })

            st.session_state["dados_ativos"] = pd.DataFrame(dados)

df = st.session_state.get("dados_ativos")

if df is None or df.empty:
    st.info("📊 Carregando dados do arquivo gerado por app.py... Se vazio, execute `app.py` para atualizar os indicadores de todos os ativos da B3.")
else:
    df = df.fillna(0)
    df["DY_formatado"] = df["DY"].apply(formatar_percentual)

    with st.container():
        st.subheader("📌 Destaques rápidos")
        melhor_score = df.sort_values("Score_BH", ascending=False).iloc[0]
        maior_dy = df.sort_values("DY", ascending=False).iloc[0]
        melhor_roe = df.sort_values("ROE", ascending=False).iloc[0]
        menor_pl = df[df["PL"] > 0].sort_values("PL", ascending=True).iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Melhor Score BH", melhor_score["Ticker"], f"{melhor_score['Score_BH']} pts")
        c2.metric("Maior Dividend Yield", maior_dy["Ticker"], formatar_percentual(maior_dy["DY"]))
        c3.metric("Melhor ROE", melhor_roe["Ticker"], formatar_percentual(melhor_roe["ROE"]))
        c4.metric("Menor PL (vivo)", menor_pl["Ticker"], f"{menor_pl['PL']:.2f}")

    with st.container():
        st.subheader("🔎 Análise rápida de indicadores")
        cols = ["Ticker", "PL", "PVP", "ROE", "DY", "Margem_Liquida", "Divida_PL", "Liquidez_Corrente", "Score_BH"]
        st.dataframe(df[cols], use_container_width=True)

    with st.expander("O que significam estes indicadores?", expanded=False):
        st.markdown(
            "**PL:** preço sobre lucro. Valores menores podem indicar desconto.\n"
            "**P/VPA:** preço sobre valor patrimonial. Abaixo de 1 pode sugerir bom desconto.\n"
            "**ROE:** retorno sobre patrimônio. Quanto maior, melhor geralmente.\n"
            "**DY:** dividend yield. Mostra o retorno de dividendos pago pela ação.\n"
            "**Dívida/PL:** baixo indica menor alavancagem.\n"
            "**Liquidez Corrente:** saúde financeira de curto prazo. Acima de 1 é melhor."
        )

    with st.container():
        st.subheader("📈 Rank e comparações")
        st.markdown("Compare os tickers buscados por métricas e visualize os melhores do grupo.")
        ranking_dy = df.sort_values("DY", ascending=False).head(10)
        st.bar_chart(ranking_dy.set_index("Ticker")["DY"])

        tab1, tab2 = st.tabs(["Ranking Score", "Radar de Indicadores"])
        with tab1:
            st.dataframe(df.sort_values("Score_BH", ascending=False).head(20), use_container_width=True)

        with tab2:
            radar_ind = px.line_polar(df.head(10), r="ROE", theta="Ticker", line_close=True)
            st.plotly_chart(radar_ind, use_container_width=True)

    with st.container():
        st.subheader("📊 Comparar ações")
        comparacao_selecionadas = st.multiselect(
            "Selecione até 5 ações para comparar:",
            options=df["Ticker"].tolist(),
            default=df["Ticker"].tolist()[: min(5, len(df))],
            help="Selecione as ações que você deseja ver lado a lado."
        )
        indicador = st.selectbox(
            "Indicador para gráfico comparativo",
            options=["DY", "ROE", "PL", "PVP", "Score_BH", "Liquidez_Corrente", "Divida_PL"],
            index=0,
            help="Escolha o indicador que será exibido no gráfico de barras."
        )

        if comparacao_selecionadas:
            comparacao_df = df[df["Ticker"].isin(comparacao_selecionadas)].copy()
            comparacao_cols = [
                "Ticker", "Cotacao", "PL", "PVP", "ROE", "DY", "Margem_Liquida",
                "Divida_PL", "Liquidez_Corrente", "Score_BH", "Graham", "Graham_BR"
            ]
            st.dataframe(comparacao_df[comparacao_cols].set_index("Ticker"), use_container_width=True)

            if indicador in comparacao_df.columns:
                comparacao_plot = px.bar(
                    comparacao_df,
                    x="Ticker",
                    y=indicador,
                    text=indicador,
                    title=f"Comparação por {indicador}",
                    labels={indicador: indicador}
                )
                comparacao_plot.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                st.plotly_chart(comparacao_plot, use_container_width=True)

            if len(comparacao_df) > 1:
                radar_metrics = [m for m in ["PL", "PVP", "ROE", "DY", "Score_BH"] if m in comparacao_df.columns]
                radar_df = comparacao_df.melt(
                    id_vars=["Ticker"],
                    value_vars=radar_metrics,
                    var_name="Indicador",
                    value_name="Valor"
                )
                if not radar_df.empty:
                    radar_chart = px.line_polar(
                        radar_df,
                        r="Valor",
                        theta="Indicador",
                        color="Ticker",
                        line_close=True,
                        title="Radar de indicadores por ação"
                    )
                    radar_chart.update_traces(fill="toself")
                    st.plotly_chart(radar_chart, use_container_width=True)

            if len(comparacao_df) > 1:
                st.markdown("### Gráficos múltiplos por métrica")
                col_a, col_b = st.columns(2)
                metricas = ["DY", "ROE", "PL", "PVP"]
                for i, metrica in enumerate(metricas):
                    if metrica in comparacao_df.columns:
                        with (col_a if i % 2 == 0 else col_b):
                            grafico = px.bar(
                                comparacao_df,
                                x="Ticker",
                                y=metrica,
                                text=metrica,
                                title=f"{metrica} por ação"
                            )
                            grafico.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                            st.plotly_chart(grafico, use_container_width=True)
        else:
            st.info("Selecione pelo menos uma ação para habilitar a comparação.")

    with st.container():
        st.subheader("📅 Agenda de dividendos")
        agenda_div = montar_agenda_dividendos(df)
        if agenda_div.empty:
            st.info("Não há dados suficientes para estimar o calendário de dividendos.")
        else:
            st.dataframe(agenda_div, use_container_width=True)

    with st.container():
        st.subheader("💰 Modelos de valuation")
        st.dataframe(df[["Ticker", "Graham", "Graham_BR", "Bazin", "Lynch_PEG", "AGF"]], use_container_width=True)

    with st.expander("Sugestões de melhorias futuras", expanded=False):
        st.markdown(
            "- Comparador de até 5 ações com gráficos lado a lado.\n"
            "- Filtro de ações por setor, liquidez e score.\n"
            "- Agenda de dividendos dinâmica com dados reais.\n"
            "- Relatórios de carteira e simulações de alocação.\n"
            "- Assistente de IA para explicar cada ativo e responder perguntas."
        )

    excel_data = gerar_excel_bytes(df)
    st.download_button(
        label="📥 Baixar relatório em Excel",
        data=excel_data,
        file_name="sobral_invest.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
