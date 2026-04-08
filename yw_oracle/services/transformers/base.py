import pandas as pd

from ..master_data import MasterDataLoader
from ..mappings.subsidiaries import (
    SUBSIDIARY_NAME_MAP,
    UBICACION_REPLACEMENTS,
    CODE_CORRECTIONS,
)
from ..mappings.sheets_loader import get_class_abbreviation_map


class BasePlanillaTransformer:
    ACTIVITY_NORMALIZATIONS = {}
    ACCOUNT_FALLBACKS = {}

    def __init__(self):
        self.master = MasterDataLoader
        self.subsidiary_dict = self.master.get_subsidiary_dict()
        self.empresa_id = None

    def transform(self, df):
        df = self.filter_id_externo(df)
        df = self.normalize_subsidiaries(df)
        self.empresa_id = self.subsidiary_dict[df["SUBSIDIARIA"].iloc[0]]
        df = self.normalize_text(df)
        df = self.normalize_activities(df)
        df = self.normalize_codes(df)
        df = self.add_derived_columns(df)
        df = self.transform_accounts(df)
        df = self.merge_actividad_ids(df)
        df = self.add_location(df)
        df = self.add_ceco(df)
        df = self.add_area(df)
        df = self.format_dates(df)
        df = self.build_nota(df)
        df = self.clean_amounts(df)
        return df

    def filter_id_externo(self, df):
        if "ID EXTERNO" in df.columns:
            df = df[df["ID EXTERNO"].notna()].reset_index(drop=True)
        return df

    def normalize_subsidiaries(self, df):
        df["SUBSIDIARIA"] = df["SUBSIDIARIA"].replace(SUBSIDIARY_NAME_MAP)
        return df

    def normalize_text(self, df):
        df["Actividad del Proyecto"] = (
            df["Actividad del Proyecto"]
            .str.normalize('NFKD')
            .str.encode('ascii', errors='ignore')
            .str.decode('utf-8')
        )
        df["Actividad del Proyecto"] = df["Actividad del Proyecto"].str.strip()
        if "CLASE" in df.columns:
            df["CLASE"] = (
                df["CLASE"]
                .str.normalize('NFKD')
                .str.encode('ascii', errors='ignore')
                .str.decode('utf-8')
            )
        df["NUMERO y NOMBRE DE CUENTA CONTABLE"] = df["NUMERO y NOMBRE DE CUENTA CONTABLE"].astype(str)
        return df

    def normalize_activities(self, df):
        if self.ACTIVITY_NORMALIZATIONS:
            df["Actividad del Proyecto"] = df["Actividad del Proyecto"].replace(
                self.ACTIVITY_NORMALIZATIONS
            )
        return df

    def normalize_codes(self, df):
        for old, new in CODE_CORRECTIONS.items():
            for col in ["Macro Partida", "Partida Presupuestaria", "Actividad del Proyecto"]:
                if col in df.columns:
                    df[col] = df[col].str.replace(old, new, regex=False)

        for col in ["Macro Partida", "Partida Presupuestaria", "Actividad del Proyecto"]:
            if col in df.columns:
                df[col] = df[col].str.upper()
        return df

    def add_derived_columns(self, df):
        return df

    def transform_accounts(self, df):
        raise NotImplementedError("Subclasses must implement transform_accounts")

    def merge_actividad_ids(self, df):
        mpa = self.master.get_actividad_table()
        df = df.merge(mpa, on=["Actividad del Proyecto"], how="left")
        df["id_actividad"] = df["id_actividad"].astype("Int64")
        df["id_partida"] = df["id_partida"].astype("Int64")
        df["id_macro_partida"] = df["id_macro_partida"].astype("Int64")
        return df

    def add_location(self, df):
        location_map = self.master.get_location_map()
        sub_name = df["SUBSIDIARIA"].iloc[0]

        if self.empresa_id not in location_map:
            raise ValueError(f"No hay ubicaciones configuradas para la empresa ID {self.empresa_id}")

        loc_data = location_map[self.empresa_id]

        df["UBICACIÓN"] = df["UBICACIÓN"].replace(UBICACION_REPLACEMENTS)

        if sub_name == "EXCELLENCE FRUIT SAC":
            df["id_location"] = df["UBICACIÓN"].map(loc_data['locations'])
        else:
            df["id_location"] = loc_data["default"]
        return df

    def add_ceco(self, df):
        raise NotImplementedError("Subclasses must implement add_ceco")

    def add_area(self, df):
        raise NotImplementedError("Subclasses must implement add_area")

    def format_dates(self, df):
        df["FECHA"] = pd.to_datetime(df["FECHA"]).dt.strftime("%d/%m/%Y")
        return df

    def build_nota(self, df):
        df["NOTA"] = df["SUBSIDIARIA"] + " - " + df["NOTA"]
        return df

    def clean_amounts(self, df):
        df["DEBITO"] = df["DEBITO"].fillna(0).round(2)
        df["CREDITO"] = df["CREDITO"].fillna(0).round(2)
        return df
