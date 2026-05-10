import pandas as pd

from brapi_client import buscar_acoes
from valuation import (
    calcular_graham,
    calcular_graham_br,
    calcular_bazin,
    calcular_lynch,
    calcular_agf
)
from checklist import checklist_buy_hold
from export_excel import salvar_excel

# Lista de ativos (mantida completa)
ativos = [
    "AALR3","ABCB4","ABEV3","AERI3","AGRO3","AGXY3","ALLD3","ALOS3","ALPA4","ALPK3",
    "ALUP11","ALUP4","AMAR3","AMBP3","AMER3","AMOB3","ANIM3","ARML3","ASAI3","ATED3",
    "AURA33","AURE3","AZEV4","AZTE3","AZZA3","B3SA3","BAZA3","BBAS3","BBDC3","BBDC4",
    "BBSE3","BEEF3","BEES4","BGIP4","BHIA3","BIOM3","BLAU3","BMEB4","BMGB4","BMOB3",
    "BPAC11","BRAP3","BRAP4","BRAV3","BRBI11","BRKM3","BRKM5","BRSR6","BRST3","BSLI4",
    "CAMB3","CAML3","CASH3","CBAV3","CEAB3","CGRA4","CLSC4","CMIG3","CMIG4","CMIN3",
    "COCE5","COGN3","CPFE3","CPLE3","CSAN3","CSED3","CSMG3","CSNA3","CURY3","CVCB3",
    "CXSE3","CYRE3","DASA3","DESK3","DEXP3","DEXP4","DIRR3","DMVF3","DOTZ3","DXCO3",
    "EALT4","ECOR3","EGIE3","EMAE4","ENEV3","ENGI11","ENGI3","ENJU3","EQPA3","EQTL3",
    "ESPA3","EUCA3","EUCA4","EVEN3","EZTC3","FESA4","FHER3","FICT3","FIQE3","FLRY3",
    "FRAS3","G2DI33","GFSA3","GGBR3","GGBR4","GGPS3","GMAT3","GOAU3","GOAU4","GRND3",
    "HAPV3","HBOR3","HBRE3","HBSA3","HYPE3","IFCM3","IGTI11","IGTI3","INTB3","IRBR3",
    "ISAE4","ITSA4","ITUB4","JALL3","JHSF3","JSLG3","KEPL3","KLBN11","KLBN4","LAND3",
    "LAVV3","LEVE3","LIGT3","LJQQ3","LOGG3","LOGN3","LPSB3","LREN3","LUPA3","LWSA3",
    "MATD3","MBRF3","MDIA3","MDNE3","MEAL3","MELK3","MGLU3","MILS3","MLAS3","MOTV3",
    "MOVI3","MRVE3","MTRE3","MULT3","MYPK3","NATU3","NEOE3","NGRD3","ODPV3","OFSA3",
    "OIBR3","ONCO3","OPCT3","ORVR3","PCAR3","PDGR3","PDTC3","PETR3","PETR4","PFRM3",
    "PGMN3","PINE4","PLPL3","PMAM3","PNVL3","POMO3","POMO4","POSI3","PRIO3","PRNR3",
    "PSSA3","PTBL3","PTNT4","QUAL3","RADL3","RAIL3","RAIZ4","RANI3","RAPT3","RAPT4",
    "RCSL4","RDOR3","RECV3","RENT3","ROMI3","SANB11","SAPR11","SAPR4","SBFG3","SBSP3",
    "SCAR3","SEER3","SEQL3","SHOW3","SHUL4","SIMH3","SLCE3","SMFT3","SMTO3","SOJA3",
    "SUZB3","SYNE3","TAEE11","TAEE4","TCSA3","TECN3","TEND3","TFCO4","TGMA3","TIMS3",
    "TOTS3","TPIS3","TRAD3","TRIS3","TTEN3","TUPY3","UCAS3","UGPA3","UNIP6","USIM3",
    "USIM5","VALE3","VAMO3","VBBR3","VITT3","VIVA3","VIVR3","VIVT3","VLID3","VSTE3",
    "VTRU3","VULC3","VVEO3","WEGE3","WEST3","WIZC3","YDUQ3","SAUD3"
]

print("Buscando dados...")
dados = buscar_acoes(ativos)

dados_finais = []

for data in dados:
    try:
        ticker = data.get("Ticker", "N/A")
        print(f"Processando {ticker}")

        # Dados base com tratamento de None
        lpa = data.get("LPA") or 0
        vpa = data.get("PVP") or 0
        dividendos = data.get("DY") or 0
        pl = data.get("PL") or 0
        crescimento = data.get("Lucro_CAGR") or 0

        # Valuation com proteção contra erros
        graham = calcular_graham(lpa, vpa) or 0
        graham_br = calcular_graham_br(
            graham,
            data.get("ROE") or 0,
            data.get("Divida_PL") or 0,
            data.get("Margem_Liquida") or 0,
            data.get("Receita_CAGR") or 0
        ) or 0
        bazin = calcular_bazin(dividendos) or 0
        lynch = calcular_lynch(pl, crescimento) or 0
        agf = calcular_agf(dividendos, crescimento) or 0

        # Checklist
        checklist, score = checklist_buy_hold(data)

        # Linha final
        linha = {
            "Ticker": ticker,
            "Cotacao": data.get("Cotacao") or 0,
            "DY": dividendos,
            "PL": pl,
            "PVP": vpa,
            "EV_EBITDA": data.get("EV_EBITDA") or 0,
            "ROE": data.get("ROE") or 0,
            "ROA": data.get("ROA") or 0,
            "Margem_Liquida": data.get("Margem_Liquida") or 0,
            "Margem_EBIT": data.get("Margem_EBIT") or 0,
            "Margem_Bruta": data.get("Margem_Bruta") or 0,
            "Divida_PL": data.get("Divida_PL") or 0,
            "Receita_CAGR": data.get("Receita_CAGR") or 0,
            "Lucro_CAGR": crescimento,
            "Liquidez_Corrente": data.get("Liquidez_Corrente") or 0,
            "Graham": graham,
            "Graham_BR": graham_br,
            "Bazin": bazin,
            "Lynch_PEG": lynch,
            "AGF": agf,
            "Score_BH": score
        }

        dados_finais.append(linha)

    except Exception as e:
        print(f"Erro no ativo {ticker}: {e}")

# DataFrame final
df = pd.DataFrame(dados_finais)

# Exportação
salvar_excel(df)

print("✅ Excel gerado com sucesso!")
print(df.head())
