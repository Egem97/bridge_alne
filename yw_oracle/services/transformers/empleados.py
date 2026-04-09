import pandas as pd

from .base import BasePlanillaTransformer
from ..mappings.sheets_loader import (
    get_activity_normalizations_empleados,
    get_account_fallbacks_empleados,
    get_class_abbreviation_map,
)


class EmpleadosTransformer(BasePlanillaTransformer):
    @property
    def ACTIVITY_NORMALIZATIONS(self):
        return get_activity_normalizations_empleados()

    @property
    def ACCOUNT_FALLBACKS(self):
        return get_account_fallbacks_empleados()

    def transform_accounts(self, df):
        accounts = self.master.get_accounts_excel()
        df["CUENTA CONTABLE"] = df["NUMERO y NOMBRE DE CUENTA CONTABLE"].str[:8]
        df = df.merge(accounts, on="CUENTA CONTABLE", how="left")

        df["id_cuenta"] = df["id_cuenta"].fillna(df["CUENTA CONTABLE"])
        df["id_cuenta"] = df["id_cuenta"].replace(self.ACCOUNT_FALLBACKS)
        df["id_cuenta"] = df["id_cuenta"].astype(str)
        df["id_cuenta"] = df["id_cuenta"].str.replace(".0", "", regex=False)
        df["id_cuenta"] = df["id_cuenta"].str.replace("-", "0", regex=False)
        df["id_cuenta"] = df["id_cuenta"].astype(int)
        return df

    def add_ceco(self, df):
        ceco_map = self.master.get_ceco_codificacion_map()
        ceco_data = ceco_map.get(self.empresa_id, {})
        df["id_ceco"] = df["DEPARTAMENTO"].map(ceco_data)
        return df

    def add_area(self, df):
        area_map = self.master.get_area_map()
        area_data = area_map.get(self.empresa_id, {})

        # Extract CLASS from DEPARTAMENTO
        df["CLASS"] = df["DEPARTAMENTO"].str.split("-").str[1]
        df["CLASS"] = df["CLASS"].replace(get_class_abbreviation_map())
        df.loc[df["CLASE"] == "GESTION HUMANA", "CLASE"] = df["CLASS"]

        df["id_area"] = df["CLASE"].map(area_data)
        return df
