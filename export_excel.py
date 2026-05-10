import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.drawing.image import Image

def aplicar_estilo(sheet):
    # Cabeçalhos
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2F4F4F")  # Azul petróleo
        cell.alignment = Alignment(horizontal="center")

    # Linhas alternadas
    for i, row in enumerate(sheet.iter_rows(min_row=2), start=2):
        fill_color = "F7F7F7" if i % 2 == 0 else "FFFFFF"
        for cell in row:
            cell.fill = PatternFill("solid", fgColor=fill_color)

    # Congelar primeira linha
    sheet.freeze_panes = "A2"

    # Ajustar largura das colunas
    for col in sheet.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        sheet.column_dimensions[col_letter].width = max_length + 2

def inserir_logo(sheet, ticker, logo_path, row):
    """Insere brasão/logo da empresa ao lado do ticker"""
    try:
        img = Image(logo_path)
        img.width, img.height = 20, 20
        sheet.add_image(img, f"A{row}")
    except Exception as e:
        print(f"Não foi possível inserir logo para {ticker}: {e}")

def salvar_excel(df):
    wb = Workbook()
    ws = wb.active
    ws.title = "Ativos"

    # Inserir DataFrame
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    # Aplicar estilo
    aplicar_estilo(ws)

    # Exemplo: inserir logo manualmente (se tiver arquivos locais)
    # inserir_logo(ws, "ABEV3", "logos/ABEV3.png", 2)

    # Outras abas (Valuation, Checklist, Rankings, Radar)
    ws_val = wb.create_sheet("Valuation")
    ws_chk = wb.create_sheet("Checklist")
    ws_rank = wb.create_sheet("Rankings")
    ws_radar = wb.create_sheet("Radar")

    # Apenas cabeçalhos estilizados por enquanto
    for sheet in [ws_val, ws_chk, ws_rank, ws_radar]:
        sheet.append(["Exemplo"])
        aplicar_estilo(sheet)

    # Salvar arquivo
    wb.save("ativos.xlsx")
    print("✅ Excel estilizado gerado com sucesso!")
