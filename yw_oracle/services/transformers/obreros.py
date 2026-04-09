import pandas as pd

from .base import BasePlanillaTransformer
from ..mappings.accounts import AFP_ACCOUNT_RULES
from ..mappings.sheets_loader import (
    get_activity_normalizations_obreros,
    get_account_replacements_obreros,
    get_account_fallbacks_obreros,
    get_class_abbreviation_map,
    get_swap_class,
    get_act_class_packing,
)


class ObrerosTransformer(BasePlanillaTransformer):
    @property
    def ACTIVITY_NORMALIZATIONS(self):
        return get_activity_normalizations_obreros()

    @property
    def ACCOUNT_FALLBACKS(self):
        return get_account_fallbacks_obreros()

    def add_derived_columns(self, df):
        df["code_act"] = df["Actividad del Proyecto"].str[:5]
        df["TIPO_PRESUPUESTO"] = df["Actividad del Proyecto"].str[:1]

        # Rename if column exists
        if "ID CUENTA CONTABLE (ID Interno de Netsuite)" in df.columns:
            df = df.rename(columns={
                "ID CUENTA CONTABLE (ID Interno de Netsuite)": "CUENTA_CONTABLE",
            })

        if "CENTRO DE COSTOS" in df.columns:
            df = df.rename(columns={"CENTRO DE COSTOS": "DEPARTAMENTO"})

        # Build CLASE GENERAL for complex CECO/area matching
        df["CLASS"] = df["DEPARTAMENTO"].str.split("-").str[1]
        df["CLASS"] = df["CLASS"].replace(get_class_abbreviation_map())
        df.loc[df["CLASE"] == "GESTION HUMANA", "CLASE"] = df["CLASS"]
        df["CLASE GENERAL"] = df["CLASE"].fillna("-") + " - " + df["CLASS"].fillna("-")
        df["CLASE GENERAL"] = df["CLASE GENERAL"].replace(get_swap_class())

        return df

    def transform_accounts(self, df):
        # Apply account text replacements
        df["NUMERO y NOMBRE DE CUENTA CONTABLE"] = (
            df["NUMERO y NOMBRE DE CUENTA CONTABLE"].replace(get_account_replacements_obreros())
        )

        # AFP account rules
        if "CUENTA_CONTABLE" in df.columns:
            def change_account_afp(row):
                id_cuenta = str(row.get("CUENTA_CONTABLE", ""))
                cuenta = str(row["NUMERO y NOMBRE DE CUENTA CONTABLE"])
                key = (id_cuenta, cuenta[:8] if len(cuenta) >= 8 else cuenta)
                return AFP_ACCOUNT_RULES.get(key, cuenta)

            df["NUMERO y NOMBRE DE CUENTA CONTABLE"] = df.apply(change_account_afp, axis=1)

        # Code actividad rule: O0014 + prefix 90 → prefix 94
        if "code_act" in df.columns:
            def change_for_cod_actividad(row):
                act_cod = str(row.get("code_act", ""))
                cuenta = str(row["NUMERO y NOMBRE DE CUENTA CONTABLE"])
                if act_cod == "O0014" and cuenta[:2] == "90":
                    return "94" + cuenta[2:]
                return cuenta

            df["NUMERO y NOMBRE DE CUENTA CONTABLE"] = df.apply(change_for_cod_actividad, axis=1)

        # Extract 8-char account code and merge with parquet
        df["NATURALEZA Y DESTINO DEBITO"] = df["NUMERO y NOMBRE DE CUENTA CONTABLE"].str[:8]
        accounts = self.master.get_accounts_parquet()
        df = df.merge(accounts, on="NATURALEZA Y DESTINO DEBITO", how="left")

        # Apply fallbacks
        df["id_cuenta"] = df["id_cuenta"].fillna(df["NATURALEZA Y DESTINO DEBITO"])
        df["id_cuenta"] = df["id_cuenta"].replace(self.ACCOUNT_FALLBACKS)
        df["id_cuenta"] = df["id_cuenta"].astype(str)
        df["id_cuenta"] = df["id_cuenta"].str.replace(".0", "", regex=False)
        df["id_cuenta"] = df["id_cuenta"].str.replace("-", "0", regex=False)
        df["id_cuenta"] = df["id_cuenta"].astype(int)

        return df

    def add_ceco(self, df):
        ceco_map = self.master.get_ceco_map()
        ceco_data = ceco_map.get(self.empresa_id, {})

        def match_ceco(row):
            val = row.get("CLASE GENERAL")
            if pd.isna(val):
                return None
            val_str = str(val)

            # EXCELLENCE FRUIT SAC (ID=5)
            if self.empresa_id == 5:
                ubicacion = row.get("UBICACIÓN")
                if pd.notna(ubicacion):
                    for name, cid in ceco_data.items():
                        if val_str in str(name) and str(ubicacion) in str(name):
                            return cid

            # QBERRIES SAC (ID=3)
            if self.empresa_id == 3:
                ubicacion = row.get("UBICACIÓN")
                clase_term = val_str
                if "MANTENCION" in clase_term:
                    clase_term = "PRODUCCION"
                elif "COSECHA" in clase_term:
                    clase_term = "PRODUCCION"

                etapa_sufijos = None
                if pd.notna(ubicacion):
                    ubi_str = str(ubicacion).strip()
                    if ubi_str == "LICAPA":
                        etapa_sufijos = [" QBERRIES ETAPA I", " QBERRIES I"]
                    elif ubi_str == "LICAPA II":
                        etapa_sufijos = [" QBERRIES ETAPA II", " QBERRIES II"]
                    elif ubi_str == "LICAPA III":
                        etapa_sufijos = [" QBERRIES ETAPA III", " QBERRIES III"]

                if etapa_sufijos:
                    for name, cid in ceco_data.items():
                        name_str = str(name)
                        if clase_term in name_str:
                            if any(name_str.endswith(sufijo) for sufijo in etapa_sufijos):
                                return cid

            # General matching
            for name, cid in ceco_data.items():
                name_str = str(name)
                if val_str in name_str:
                    if val_str == "GERENCIA" and "GERENCIA AGRICOLA" in name_str:
                        continue
                    return cid
            return None

        df["id_ceco"] = df.apply(match_ceco, axis=1)
        return df

    def add_area(self, df):
        area_map = self.master.get_area_map()
        area_data = area_map.get(self.empresa_id, {})

        # Special case: ALZA PERU PACKING SAC (empresa_id == 10)
        if self.empresa_id == 10:
            area_df = self.master.get_area_dataframe()
            area_df = area_df[area_df["id_subsidiary"] == self.empresa_id]
            area_df = area_df[["id_area", "name_area"]]
            df["name_area"] = df["Actividad del Proyecto"].replace(get_act_class_packing())
            df = df.merge(area_df, on="name_area", how="left")
            return df

        def get_area_id(row):
            tipo = row.get("TIPO_PRESUPUESTO")
            partida = row.get("code_act")

            target_keyword = None
            if tipo == 'O':
                if partida == "O0012":
                    target_keyword = "COSECHA"
                elif partida in ("O0014", "O0015", "O0017"):
                    target_keyword = "OPERACIONES"
                else:
                    target_keyword = "MANTENCION"
            elif tipo == 'C':
                target_keyword = "INVERSION"

            if target_keyword:
                # EXCELLENCE FRUIT SAC (ID=5)
                if self.empresa_id == 5:
                    ubicacion = row.get("UBICACIÓN")
                    if pd.notna(ubicacion):
                        for name, aid in area_data.items():
                            if target_keyword in name and str(ubicacion) in name:
                                return aid

                # QBERRIES SAC (ID=3)
                if self.empresa_id == 3:
                    ubicacion = row.get("UBICACIÓN")
                    if pd.notna(ubicacion):
                        ubi_str = str(ubicacion).strip()
                        search_term = None
                        if ubi_str == "LICAPA":
                            search_term = "QBERRIES ETAPA I"
                        elif ubi_str == "LICAPA II":
                            search_term = "QBERRIES ETAPA II"
                        elif ubi_str == "LICAPA III":
                            search_term = "QBERRIES ETAPA III"
                        if search_term:
                            for name, aid in area_data.items():
                                if target_keyword in name and name.endswith(search_term):
                                    return aid

                for name, aid in area_data.items():
                    if target_keyword in name:
                        return aid
            return None

        df["id_area"] = df.apply(get_area_id, axis=1)

        # Fallback: map CLASE directly
        mask_null = df["id_area"].isna()
        if mask_null.any():
            df.loc[mask_null, "id_area"] = df.loc[mask_null, "CLASE"].map(area_data)

        return df
