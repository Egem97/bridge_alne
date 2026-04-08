import os
import pandas as pd
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORACLE_FILE = os.path.join(BASE_DIR, "oracle_prod.xlsx")
CECOS_FILE = os.path.join(BASE_DIR, "CECOS.xlsx")
ACCOUNTS_PARQUET = os.path.join(BASE_DIR, "account_id_map.parquet")
ACCOUNTS_EXCEL = os.path.join(BASE_DIR, "accounts.xlsx")


class MasterDataLoader:

    @staticmethod
    @lru_cache(maxsize=1)
    def get_subsidiary_dict():
        subsidiary = pd.read_excel(ORACLE_FILE, sheet_name="Subsidiary")
        return (
            subsidiary
            .set_index('name_subsidiary')['id_subsidiary']
            .to_dict()
        )

    @staticmethod
    @lru_cache(maxsize=1)
    def get_location_map():
        almacen = pd.read_excel(ORACLE_FILE, sheet_name="Almacen")
        location_map = {}
        for _, row in almacen.iterrows():
            sub_id = row['id_subsidiary']
            loc_id = row['id_location']
            loc_name = row['name_location']
            if sub_id not in location_map:
                location_map[sub_id] = {
                    'default': loc_id,
                    'locations': {}
                }
            location_map[sub_id]['locations'][loc_name] = loc_id
        return location_map

    @staticmethod
    @lru_cache(maxsize=1)
    def get_ceco_map():
        ceco = pd.read_excel(CECOS_FILE)
        ceco_map = {}
        for _, row in ceco.iterrows():
            sub_id = row['id_subsidiary']
            ceco_id = row['id_ceco']
            ceco_name = row['name_ceco']
            if sub_id not in ceco_map:
                ceco_map[sub_id] = {}
            ceco_map[sub_id][ceco_name] = ceco_id
        return ceco_map

    @staticmethod
    @lru_cache(maxsize=1)
    def get_ceco_codificacion_map():
        ceco = pd.read_excel(CECOS_FILE)
        ceco_map = {}
        for _, row in ceco.iterrows():
            sub_id = row['id_subsidiary']
            ceco_id = row['id_ceco']
            ceco_code = row['CODIFICACION']
            if sub_id not in ceco_map:
                ceco_map[sub_id] = {}
            ceco_map[sub_id][ceco_code] = ceco_id
        return ceco_map

    @staticmethod
    @lru_cache(maxsize=1)
    def get_ceco_dataframe():
        return pd.read_excel(CECOS_FILE)

    @staticmethod
    @lru_cache(maxsize=1)
    def get_area_map():
        area = pd.read_excel(ORACLE_FILE, sheet_name="Area")
        area_map = {}
        for _, row in area.iterrows():
            sub_id = row['id_subsidiary']
            area_id = row['id_area']
            area_name = row['name_area']
            if sub_id not in area_map:
                area_map[sub_id] = {}
            area_map[sub_id][area_name] = area_id
        return area_map

    @staticmethod
    @lru_cache(maxsize=1)
    def get_area_dataframe():
        return pd.read_excel(ORACLE_FILE, sheet_name="Area")

    @staticmethod
    @lru_cache(maxsize=1)
    def get_actividad_table():
        mpa = pd.read_excel(ORACLE_FILE, sheet_name="Macro PP Actividad")
        mpa = mpa.drop(columns=["links"])
        mpa = mpa.rename(columns={
            "actividad": "Actividad del Proyecto",
            "macropartida": "Macro Partida",
            "partida_presupuestaria": "Partida Presupuestaria",
            "id_partida_pre": "id_partida",
            "id_macropartida": "id_macro_partida"
        })
        mpa["Actividad del Proyecto"] = (
            mpa["Actividad del Proyecto"]
            .str.normalize('NFKD')
            .str.encode('ascii', errors='ignore')
            .str.decode('utf-8')
        )
        mpa["Actividad del Proyecto"] = mpa["Actividad del Proyecto"].str.strip()
        return mpa

    @staticmethod
    @lru_cache(maxsize=1)
    def get_accounts_parquet():
        accounts = pd.read_parquet(ACCOUNTS_PARQUET)
        accounts["NATURALEZA Y DESTINO DEBITO"] = accounts["NATURALEZA Y DESTINO DEBITO"].astype(str)
        return accounts[
            ["NATURALEZA Y DESTINO DEBITO", "externalid", "name_cuenta_origen", "id_cuenta", "isinactive"]
        ]

    @staticmethod
    @lru_cache(maxsize=1)
    def get_accounts_excel():
        accounts = pd.read_excel(ACCOUNTS_EXCEL, dtype={"externalid": str})
        accounts = accounts.rename(columns={
            "externalid": "CUENTA CONTABLE",
            "id": "id_cuenta"
        })
        accounts["CUENTA CONTABLE"] = accounts["CUENTA CONTABLE"].astype(str)
        return accounts[["CUENTA CONTABLE", "id_cuenta", "custrecord_gd_auxiliar", "isinactive"]]

    @classmethod
    def clear_cache(cls):
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, 'cache_clear'):
                attr.cache_clear()
