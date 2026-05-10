import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.drawing.image import Image

def aplicar_estilo(sheet):
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2F4F4F")
        cell.alignment = Alignment(horizontal="center")

    for i, row in enumerate(sheet.iter_rows(min_row=2), start=2):
        fill_color = "F7F7F7" if i % 2 == 0 else "FFFFFF"
        for cell in row:
            cell.fill = PatternFill("solid", fgColor=fill_color)

    sheet.freeze_panes = "A2"

    for col in sheet.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        sheet.column_dimensions[col_letter].width = min(max_length + 2, 40)

def salvar_excel(df):
    if df is None or df.empty:
        print("⚠️ DataFrame vazio — nenhum dado para exportar.")
        return

    # Arredondar colunas numéricas
    cols_numericas = df.select_dtypes(include="number").columns
    df[cols_numericas] = df[cols_numericas].round(2)

    wb = Workbook()

    # Aba principal
    ws = wb.active
    ws.title = "Ativos"
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)
    aplicar_estilo(ws)

    # Aba Valuation
    ws_val = wb.create_sheet("Valuation")
    colunas_val = ["Ticker", "Graham", "Graham_BR", "Bazin", "Lynch_PEG", "AGF", "Score_BH"]
    colunas_val = [c for c in colunas_val if c in df.columns]
    for r in dataframe_to_rows(df[colunas_val], index=False, header=True):
        ws_val.append(r)
    aplicar_estilo(ws_val)

    # Aba Checklist
    ws_chk = wb.create_sheet("Checklist")
    colunas_chk = ["Ticker", "ROE", "DY", "Divida_PL", "Liquidez_Corrente", "Score_BH"]
    colunas_chk = [c for c in colunas_chk if c in df.columns]
    for r in dataframe_to_rows(df[colunas_chk], index=False, header=True):
        ws_chk.append(r)
    aplicar_estilo(ws_chk)

    # Aba Rankings (top 20 por Score)
    ws_rank = wb.create_sheet("Rankings")
    df_rank = df.sort_values("Score_BH", ascending=False).head(20) if "Score_BH" in df.columns else df.head(20)
    for r in dataframe_to_rows(df_rank, index=False, header=True):
        ws_rank.append(r)
    aplicar_estilo(ws_rank)

    # Aba Radar
    ws_radar = wb.create_sheet("Radar")
    colunas_radar = ["Ticker", "ROE", "DY", "Margem_Liquida", "ROIC", "Liquidez_Corrente"]
    colunas_radar = [c for c in colunas_radar if c in df.columns]
    for r in dataframe_to_rows(df[colunas_radar], index=False, header=True):
        ws_radar.append(r)
    aplicar_estilo(ws_radar)

    wb.save("ativos.xlsx")
    print("✅ Excel estilizado gerado com sucesso!")
