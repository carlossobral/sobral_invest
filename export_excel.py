import pandas as pd


def salvar_excel(df):

    with pd.ExcelWriter(
        "ativos.xlsx",
        engine="openpyxl",
        mode="w"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Ativos",
            index=False
        )
