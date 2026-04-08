import streamlit as st
import pandas as pd
import glob
import os
from io import BytesIO
from utils import NetSuiteClient
client = NetSuiteClient()
st.title("proceco transform asientos")
upload = st.file_uploader("Sube el archivo", type="xlsx")

name_file ="oracle_prod.xlsx" # 
                    #################################################################### SUBSIDIARIAS
def table_subsidiary():
    subsidiary = pd.read_excel(name_file,sheet_name="Subsidiary")
    subsidiary_dict = (
            subsidiary
            .set_index('name_subsidiary')['id_subsidiary']
            .to_dict()
    )
    return subsidiary_dict

                    #################################################################### ALMACENES

def add_codigo_location(df,subsidiary_dict):
    almacen = pd.read_excel(name_file,sheet_name="Almacen")
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
    sub_name = df["SUBSIDIARIA"].unique()[0]                                           
    empresa_id = subsidiary_dict[sub_name]                    
    if empresa_id not in location_map:
        raise ValueError(f"No hay ubicaciones configuradas para la empresa ID {empresa_id}")
    loc_data = location_map[empresa_id]               
    if sub_name == "EXCELLENCE FRUIT SAC":
        df["id_location"] = df["UBICACIÓN"].map(loc_data['locations'])
    else:
        df["id_location"] = loc_data["default"]
    return df


                    ######################################################################### CENTROS DE COSTOS
def add_codigo_ceco(df,subsidiary_dict):

    ceco = pd.read_excel("CECOS.xlsx")
    ceco_map = {}
    for _, row in ceco.iterrows():
        sub_id = row['id_subsidiary']
        ceco_id = row['id_ceco']
        ceco_name = row['name_ceco']     
        if sub_id not in ceco_map:
            ceco_map[sub_id] = {}
        ceco_map[sub_id][ceco_name] = ceco_id
    print("here cecops")
    
    sub_name = df["SUBSIDIARIA"].unique()[0]            
    empresa_id = subsidiary_dict[sub_name]
    ceco_data = ceco_map.get(empresa_id, {})

    def match_ceco(row):
        val = row.get("CLASE GENERAL")
        if pd.isna(val):
            return None
        val_str = str(val)

        # Caso especial para EXCELLENCE FRUIT SAC (ID=5) usando UBICACIÓN
        if empresa_id == 5:
            ubicacion = row.get("UBICACIÓN")
            if pd.notna(ubicacion):
                for name, cid in ceco_data.items():
                    if val_str in str(name) and str(ubicacion) in str(name):
                        return cid

        # Caso especial para QBERRIES SAC (ID=3)
        if empresa_id == 3:
            ubicacion = row.get("UBICACIÓN")
            clase_term = val_str
            
            # Ajuste de mapeo según requerimiento
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
                        # Verificar que el nombre termina con alguno de los sufijos esperados
                        # para evitar que "QBERRIES I" coincida con "QBERRIES II" o "QBERRIES III"
                        if any(name_str.endswith(sufijo) for sufijo in etapa_sufijos):
                            return cid

        for name, cid in ceco_data.items():
            name_str = str(name)
            if val_str in name_str:
                if val_str == "GERENCIA" and "GERENCIA AGRICOLA" in name_str:
                    continue
                return cid
        return None

    df["id_ceco"] = df.apply(match_ceco, axis=1)
    ceco = ceco[["id_ceco","name_ceco"]]
    st.dataframe(ceco)
    st.dataframe(df)
    df = pd.merge(df,ceco,on="id_ceco",how="left")
    return df

                    ######################################################################### AREA
                                    
def add_codigo_area(df,subsidiary_dict):
    area = pd.read_excel(name_file,sheet_name="Area")
    area_map = {}
    for _, row in area.iterrows():
        sub_id = row['id_subsidiary']
        area_id = row['id_area']
        area_name = row['name_area']     
        if sub_id not in area_map:
            area_map[sub_id] = {}
        area_map[sub_id][area_name] = area_id

    sub_name = df["SUBSIDIARIA"].unique()[0]    
    empresa_id = subsidiary_dict[sub_name]
    area_data = area_map[empresa_id]
    
    def get_area_id(row):
        tipo = row.get("TIPO_PRESUPUESTO")
        # Usamos Partida Presupuestaria_y si existe, sino Partida Presupuestaria
        partida = row.get("code_act") if "code_act" in row else row.get("code_act")
        
        target_keyword = None
        
        if tipo == 'O':
            if partida == "O0012":
                target_keyword = "COSECHA"
            elif partida == "O0014" or partida == "O0015" or  partida == "O0017":
                target_keyword = "OPERACIONES"
            else:
                target_keyword = "MANTENCION"
        elif tipo == 'C':
            # Si es C y tiene la partida específica (o en general para C) asignamos INVERSION
            if partida == "O0012-00101-MO COSECHA":
                 target_keyword = "INVERSION"
            else:
                 target_keyword = "INVERSION" # Asumimos inversión por defecto para tipo C
        
        if target_keyword:
            # Caso especial para EXCELLENCE FRUIT SAC (ID=5) usando UBICACIÓN
            if empresa_id == 5:
                ubicacion = row.get("UBICACIÓN")
                if pd.notna(ubicacion):
                    for name, aid in area_data.items():
                        if target_keyword in name and str(ubicacion) in name:
                            return aid

            # Caso especial para QBERRIES SAC (ID=3) usando UBICACIÓN
            if empresa_id == 3:
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
                            # Usar endswith para evitar que "ETAPA I" coincida con "ETAPA II" o "ETAPA III"
                            if target_keyword in name and name.endswith(search_term):
                                return aid

            # Buscar en el diccionario la clave que contenga la palabra clave
            for name, aid in area_data.items():
                if target_keyword in name:
                    return aid
        
        # Fallback si no encuentra coincidencia o lógica
        return None

    df["id_area"] = df.apply(get_area_id, axis=1)
    
    # Rellenar con mapeo original de CLASE si quedan nulos (opcional, depende de la lógica deseada, pero seguro tener un fallback)
    mask_null = df["id_area"].isna()
    if mask_null.any():
        df.loc[mask_null, "id_area"] = df.loc[mask_null, "CLASE"].map(area_data)
    area = area[["id_area","name_area"]]
    df = pd.merge(df,area,on="id_area",how="left")    
    return df                    
                    #########################################################################JOIN MACRO-PARTIDA-ACTIVIDAD

def table_actividad():
    mpa = pd.read_excel(name_file,sheet_name="Macro PP Actividad")
    mpa = mpa.drop(columns=["links"])
    mpa = mpa.rename(columns={
        "actividad":"Actividad del Proyecto",
        "macropartida":"Macro Partida",
        "partida_presupuestaria":"Partida Presupuestaria",
        "id_partida_pre":"id_partida",
        "id_macropartida":"id_macro_partida"
    })
    mpa["Actividad del Proyecto"] = mpa["Actividad del Proyecto"].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    
    return mpa





def transform_asiento(df):
    mpa = table_actividad()
    df["FECHA"] = pd.to_datetime(df["FECHA"]).dt.strftime("%d/%m/%Y")
    df["CLASE"] = df["CLASE"].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    df = df.rename(columns={
        "ID CUENTA CONTABLE (ID Interno de Netsuite)":"CUENTA_CONTABLE",
    })
    df["NUMERO y NOMBRE DE CUENTA CONTABLE"] = df["NUMERO y NOMBRE DE CUENTA CONTABLE"].replace({
        "4116200010 - VACACIONES POR PAGAR":"41111002",
        "41112002 - SALARIOS POR PAGAR":"41111002",
        ######### CUENTAS DE PROVISION Y VIDA LEY
        '90215202':'90215201',
        '94215202':'90215201'
        
    })

    def change_account_afp(id_cuenta_yawi, cuenta_contable_yawi):
        if id_cuenta_yawi == "3322" and cuenta_contable_yawi == "41710001":
            return "41720001 - AFP - HABITAT | PROVISION."
        elif id_cuenta_yawi == "3328" and cuenta_contable_yawi == "41710001":
            return "41740001 - AFP - PROFUTURO | PROVISION."
        elif id_cuenta_yawi == "3331" and cuenta_contable_yawi == "41710001":
            return "41750001 - AFP - PRIMA | PROVISION."
        elif id_cuenta_yawi == "3319" and cuenta_contable_yawi == "41710001":
            return "41710001 - AFP - INTEGRA | PROVISION."
        else:
            return cuenta_contable_yawi

    def change_account_for_cod_actividad(act_cod, cuenta_contable_yawi):
        
        if act_cod == "O0014" and cuenta_contable_yawi[:2] == "90":
            return "94"+cuenta_contable_yawi[2:]
        else:
            return cuenta_contable_yawi
        
    
    df["NUMERO y NOMBRE DE CUENTA CONTABLE"] = df.apply(lambda x: change_account_afp(str(x["CUENTA_CONTABLE"]), str(x["NUMERO y NOMBRE DE CUENTA CONTABLE"])), axis=1)
    df["NUMERO y NOMBRE DE CUENTA CONTABLE"] = df.apply(lambda x: change_account_for_cod_actividad(str(x["code_act"]), str(x["NUMERO y NOMBRE DE CUENTA CONTABLE"])), axis=1)
    df["NATURALEZA Y DESTINO DEBITO"] = df["NUMERO y NOMBRE DE CUENTA CONTABLE"].str[:8]
    
    accounts = pd.read_parquet("account_id_map.parquet")
    
    accounts["NATURALEZA Y DESTINO DEBITO"] = accounts["NATURALEZA Y DESTINO DEBITO"].astype(str)
    accounts = accounts[[
                            "NATURALEZA Y DESTINO DEBITO",
                            "externalid",
                            "name_cuenta_origen",
                            "id_cuenta",
                            "isinactive"
    ]]
    st.dataframe(accounts)
    #print(accounts)
    #print(accounts.info())
    df = df.merge(accounts, on="NATURALEZA Y DESTINO DEBITO", how="left")
    
    


    df["id_cuenta"] = df["id_cuenta"].fillna(df["NATURALEZA Y DESTINO DEBITO"])
    #
    df["id_cuenta"] = df["id_cuenta"].replace({
                            "14121101":647,
                            "40310005":3241,
                            "40320001":3248,
                            "41112002":3324,
                            "41710001":3404,
                            "46991101":4405,
                            "16291003":781,
                            "40173001":3208,
                            #"4116200010":3319,
                            "41111002":3319,
                            "41720001":3407,
                            "41750001":3416,
                            "41740001":3413,
                            "41151102":3356,
                            "18221001":1502,
                            "41152102":3363,
                            "18221001":1502,
                            "41111001":3318,
                            "40310001":3237,
                
                            
                          
                        })
    
    df["id_cuenta"] = df["id_cuenta"].astype(str)
    df["id_cuenta"] = df["id_cuenta"].str.replace(".0", "", regex=False)
    df["id_cuenta"] = df["id_cuenta"].str.replace("-", "0", regex=False)
    st.dataframe(df)
    df["id_cuenta"] = df["id_cuenta"].astype(int)
    
    try:
        df = df.rename(columns={
            "CENTRO DE COSTOS":"DEPARTAMENTO"
        })
    except:
        pass

    df = df.drop(columns=["Unnamed: 0","Proyecto","Etapa"])

    codes_mp = {
                            "O014":"O0014",
                            "C001":"C0001",
                            "O006":"O0006",
                            "O004":"O0004",
                            "O005":"O0005",
                            "O009":"O0009",
                            "O012":"O0012",
                        }
    for viejo, nuevo in codes_mp.items():
        df["Macro Partida"] = df["Macro Partida"].str.replace(viejo, nuevo, regex=False)
        df["Partida Presupuestaria"] = df["Partida Presupuestaria"].str.replace(viejo, nuevo, regex=False)
        df["Actividad del Proyecto"] = df["Actividad del Proyecto"].str.replace(viejo, nuevo, regex=False)

    df["Macro Partida"] = df["Macro Partida"].str.upper() 
    df["Partida Presupuestaria"] = df["Partida Presupuestaria"].str.upper() 
    df["Actividad del Proyecto"] = df["Actividad del Proyecto"].str.upper() 
          
                        #df["Actividad del Proyecto"] = df["Actividad del Proyecto"].replace("O0009-00078-10078-MECANICO", "O0009-00078-10078-MECÁNICO", regex=False)
    df["SUBSIDIARIA"] = df["SUBSIDIARIA"].replace({
                            "AGROBUSINESS INTERNATIONAL PERU SAC":"AGROBUSINESS INTERNATIONAL PERU SAC",
                            "ALZA PERU GROUP SAC":"ALZA PERU GROUP SAC",
                            "ALZA PERU PACKING S.A.C.":"ALZA PERU PACKING SAC",
                            "APG":"APG",
                            "BERRIES":"BERRIES",
                            "BIG BERRIES S.A.C.":"BIG BERRIES SAC",
                            "CANYON BERRIES S.A.C.":"CANYON BERRIES SAC",
                            "EXCELLENCE FRUIT S.A.C.":"EXCELLENCE FRUIT SAC",
                            "EXCELLENCE FRUIT S.A.C":"EXCELLENCE FRUIT SAC",
                            "GAP BERRIES S.A.C":"GAP BERRIES SAC",
                            "GOLDEN BERRIES S.A.C.":"GOLDEN BERRIES SAC",
                            "INMOBILIARIA SAN JUAN SA":"INMOBILIARIA SAN JUAN SA",
                            "INVERSIONES QUELEN PERU SAC":"INVERSIONES QUELEN PERU SAC",
                            "QBERRIES S.A.C":"QBERRIES SAC",#################
                            "TARA FARM S.A.C.":"TARA FARM SAC",
                            "TECNOLOGIAS ORGANICAS TAKAMATSU SAC":"TECNOLOGIAS ORGANICAS TAKAMATSU SAC",
                            "360 SMART AGRO SAC":"360 SMART AGRO SAC",
                            "GAP BERRIES S.A.C.":"GAP BERRIES SAC",
                        })
    df = df.merge(mpa, on=["Actividad del Proyecto"], how="left")#,"Macro Partida","Partida Presupuestaria"
    df["id_actividad"] = df["id_actividad"].astype("Int64")
    df["id_partida"] = df["id_partida"].astype("Int64")
    df["id_macro_partida"] = df["id_macro_partida"].astype("Int64")
    df["id_macro_partida"] = df["id_macro_partida"].astype("Int64")
    df["UBICACIÓN"] = df["UBICACIÓN"].replace({
                            "SAN JOSE":"SAN JOSE I"
                        })
    #str(df["SUBSIDIARIA"][0]) + " - " +    
    df["NOTA"] = df["SUBSIDIARIA"]+ " - " + df["NOTA"]  
    return df


##df = pd.read_excel(r"C:\Users\EdwardoGiampiereEnri\Desktop\ASIENTOS_30012026\PRIMERA PRUEBA FEBRERO09\BIG_Asiento Oracle Validar-Haberes-02ENE2026.xlsx",skiprows=2)             
#df = pd.read_parquet("df_concatenado.parquet")
df = pd.read_excel(upload,skiprows=2)
df["index"] = df.index

st.write(df.shape)
st.dataframe(df)
df["NUMERO y NOMBRE DE CUENTA CONTABLE"] = df["NUMERO y NOMBRE DE CUENTA CONTABLE"].astype(str)

subsidiary_dict = table_subsidiary()


df["Actividad del Proyecto"] = df["Actividad del Proyecto"].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
df["Actividad del Proyecto"] = df["Actividad del Proyecto"].str.strip()
df["Actividad del Proyecto"] = df["Actividad del Proyecto"].replace({
                        "O0008-00042-10042-RASTRILLADO DE  CAMPO":"O0008-00042-10042-RASTRILLADO DE CAMPO",
                        "O0106-30028-11066-ABASTECEDOR DE CLAMSHELL":"O0106-30028-11066-ABASTECEDOR DE CLAMSHELLS",
                        "O0106-30028-11055-OPERADOR DE MONTACARGA - DESPACHO":"O0106-30028-11055-OPERADOR DE MONTACARGA-DESPACHO",
                        "O0106-30028-11069-OPERADOR DE MAQUINA LLENADORA":"O0106-30028-11069-OPERADOR DE LLENADORA PONNYS",
                        "O0005-00018-10018-SUPEVISOR DE FITOSANIDAD":"O0005-00018-10018-SUPERVISOR DE FITOSANIDAD",
                        "O0012-00101-10110-SUPERVISOR DE CALIDAD":"O0101-30003-11001-SUPERVISOR DE CALIDAD",
                        "C0006-00007-90006-MANO DE OBRA PLANTACION":"C0006-10086-90006-MANO DE OBRA PLANTACION",
                        "C0003-00013-90004-JORNALEROS RIEGO":"C0003-10032-90004-JORNALEROS RIEGO",
                        "C0006-00008-90007-MO VIVERO":"C0006-10087-90007-MO VIVERO",
                        "C0006-00005-90005-ESTIBA":"C0006-10084-90005-ESTIBA",
                        "O0012-00101-10109-ETIQUETADOR": "O0106-30028-11028-ETIQUETADOR",
                        "C0006-10086-90006-MANO DE OBRA PLANTACIÓN":"C0006-10086-90006-MANO DE OBRA PLANTACIÓN",
                        "C0001-00006-90000-MANO OBRA ARMADO CAMELLONES":"C0001-10005-90000-MANO OBRA ARMADO CAMELLONES",
                        "C0006-00012-90010-DISTRIBUCION DE MACETAS Y FIBRA":"C0006-10091-90010-DISTRIBUCION DE MACETAS Y FIBRA",
                        "C0006-00016-90013-PUESTA DE ALAMBRE":"C0006-10095-90013-PUESTA DE ALAMBRE",
                        "O0012-00101-10081-ACOPIO":"O0012-00101-10084-ESTIBA ACOPIO",
                        #####################

                        "C0003-00012-90003-COLOCACION DE ESTACAS":"C0003-10031-90003-COLOCACION DE ESTACAS",
                        "00013-10013--APOYO DE ALMACEN":"O0004-00013-10013-APOYO DE ALMACEN",
                        "00116-10098--REMUNERACIONES ADM + OTROS GASTOS":"O0014-00116-10098-PLANILLERO",
                        "C0002-00005-90002-HIDRATACION DE FIBRA MO":"C0002-10018-90002-HIDRATACION DE FIBRA MO",
                        "C0006-00013-90011-ALINEAMIENTO DE MACETAS":"C0006-10092-90011-ALINEAMIENTO DE MACETAS",
                        "C006-00008-90007-MO VIVERO":"C0006-10092-90011-ALINEAMIENTO DE MACETAS",
                        "O0006-00033-10033-AUXILAR DE RIEGO":"O0006-00033-10033-AUXILIAR DE RIEGO",

                        #"O0005-00018-10018-SUPEVISOR DE FITOSANIDAD"
                        ##QBERRIES
                        "C00006-00005-90005-ESTIBA":"C0006-10084-90005-ESTIBA",
                        "C00006-00007-90006-MANO DE OBRA PLANTACION":"C0006-10086-90006-MANO DE OBRA PLANTACION",
                        "C00001-00006-90000-MANO OBRA ARMADO CAMELLONES":"C0001-10005-90000-MANO OBRA ARMADO CAMELLONES",
                        "O00005-00017-10017-EVALUADOR FITOSANITARIO":"O0005-00017-10017-EVALUADOR FITOSANITARIO",
                        "O0004-00012-10012-APOYO DE ALMACEN":"O0004-00013-10013-APOYO DE ALMACEN",


                        "01-O0012-00101-ESTIBA KIA":"O0012-00101-10085-ESTIBA KIA",
                        "01-O0012-00101-COSECHA":"O0012-00101-10083-COSECHA",
                        "01-O0009-00065-RIEGO DE CAMINOS":"O0012-00101-10083-COSECHA",
                        '01-O0003-00010-COORDINADOR DE RIEGO':'O0003-00010-10005-COORDINADOR DE RIEGO',
                        '01-O0003-00010-COORDINADOR DE SANIDAD':'O0003-00010-10004-COORDINADOR DE SANIDAD',
                        '01-O0004-00011-SUPERVISOR DE ALMACÉN':'O0004-00011-10009-SUPERVISOR DE ALMACÉN',
                        '01-O0004-00012-AUXILIAR DE ALMACÉN':'O0004-00012-10012-AUXILIAR DE ALMACÉN',
                        '01-O0005-00014-APLICACION CON MOCHILA-SANIDAD':'O0005-00014-10014-APLICACION CON MOCHILA-SANIDAD',
                        '01-O0005-00015-APLICACION CON TRACTOR-SANIDAD':'O0005-00015-10015-APLICACION CON TRACTOR-SANIDAD',
                        '01-O0005-00017-EVALUADOR FITOSANITARIO':'O0005-00017-10017-EVALUADOR FITOSANITARIO',
                        '01-O0005-00018-SUPERVISOR DE FITOSANIDAD':'O0005-00018-10018-SUPERVISOR DE FITOSANIDAD',
                        '01-O0005-00021-PRE MEZCLA':'O0005-00021-10021-PRE MEZCLA',
                        '01-O0006-00022-SUPERVISOR DE RIEGO':'O0006-00022-10022-SUPERVISOR DE RIEGO',
                        '01-O0006-00023-OPERADOR DE FILTRADO':'O0006-00023-10023-OPERADOR DE FILTRADO',
                        '01-O0006-00024-REGADORES':'O0006-00024-10024-REGADORES',
                        '01-O0006-00028-CAPTADOR DE AGUA':'O0006-00028-10028-CAPTADOR DE AGUA',
                        '01-O0006-00032-APOYO DE RIEGO':'O0006-00032-10032-APOYO DE RIEGO',
                        '01-O0008-00036-PODA':'O0008-00036-10036-PODA',
                        '01-O0008-00037-SUPERVISOR DE GRUPO PODA':'O0008-00037-10037-SUPERVISOR DE GRUPO PODA',
                        '01-O0008-00038-LIMPIEZA DE PODA':'O0008-00038-10038-LIMPIEZA DE PODA',
                        '01-O0008-00041-ELIMINACIÓN DE RESTOS VEGETALES':'O0008-00041-10041-ELIMINACION DE RESTOS VEGETALES',
                        '01-O0008-00042-RASTRILLADO DE CAMPO':'O0008-00042-10042-RASTRILLADO DE CAMPO',
                        '01-O0008-00043-APLICACIÓN CON MOCHILA - PODA': 'O0008-00043-10043-APLICACIÓN CON MOCHILA - PODA',
                        '01-O0009-00044-DESHIERBO':'O0009-00044-10044-DESHIERBO',
                        '01-O0009-00055-MANTENIMIENTO DE CAMPO':'O0009-00055-10055-MANTENIMIENTO DE CAMPO',
                        '01-O0009-00058-LIMPIEZA DE AMBIENTES':'O0009-00058-10058-LIMPIEZA DE AMBIENTES',
                        '01-O0009-00065-RIEGO DE CAMINOS':'O0009-00065-10065-RIEGO DE CAMINOS',
                        '01-O0009-00066-AUXILIAR DE CAMPO':'O0009-00066-10066-AUXILIAR DE CAMPO',
                        '01-O0009-00067-ASISTENTE DE PRODUCCION':'O0009-00067-10067-ASISTENTE DE PRODUCCION',
                        '01-O0009-00073-MANTENIMIENTO DE HERRAMIENTAS':'O0009-00073-10073-MANTENIMIENTO DE HERRAMIENTAS',
                        '01-O0009-00078-MECÁNICO':'O0009-00078-10078-MECÁNICO',
                        '01-O0009-00079-SUPERVISOR GENERAL':'O0009-00079-10079-SUPERVISOR GENERAL',
                        '01-O0012-00101-CALIDAD':'O0012-00101-10082-CALIDAD',
                        '01-O0012-00101-COSECHA':'O0012-00101-10083-COSECHA',
                        '01-O0012-00101-ESTIBA KIA':'O0012-00101-10085-ESTIBA KIA',
                        '01-O0012-00101-EVALUADOR DE PESOS Y CALIBRES':'O0012-00101-10086-EVALUADOR DE PESOS Y CALIBRES',
                        '01-O0012-00101-JABERO':'O0012-00101-10087-JABERO',
                        '01-O0012-00101-LAVADO DE JABAS':'O0012-00101-10088-LAVADO DE JABAS',
                        '01-O0012-00101-SCANER': 'O0012-00101-10094-SCANER',
                        '01-O0012-00101-SUPERVISOR DE ACOPIO':'O0012-00101-10081-SUPERVISOR DE ACOPIO',
                        '01-O0012-00101-SUPERVISOR DE COSECHA':'O0012-00101-10095-SUPERVISOR DE COSECHA',
                        'COSECHA-O0012-00101-SUPERVISOR DE COSECHA':'O0012-00101-10095-SUPERVISOR DE COSECHA',
                        '01-O0014-00116-ASISTENTE DE BIENESTAR SOCIAL':'O0014-00116-10099-ASISTENTE DE BIENESTAR SOCIAL',
                        '01-O0014-00116-AUXILIAR DE SALUD':'O0014-00116-10099-ASISTENTE DE BIENESTAR SOCIAL',
                        '01-O0014-00116-PLANILLERO':'O0014-00116-10098-PLANILLERO',
                        'ADMPERS-O0014-00116-PLANILLERO':'O0014-00116-10098-PLANILLERO',
                        'ADMPERS-O014-00116-ASISTENTE DE BIENESTAR SOCIAL':'O0014-00116-10099-ASISTENTE DE BIENESTAR SOCIAL',
                        '---AREA DE MANTENIMIENTO':'C0004-10066-70045-AREA DE MANTENIMIENTO',
                        'BIENEST-O0014-00116-ASISTENTE DE BIENESTAR SOCIAL':'O0014-00116-10099-ASISTENTE DE BIENESTAR SOCIAL',
                        'COSECHA-O0012-00101-CALIDAD':'O0012-00101-10082-CALIDAD',
                        'COSECHA-O0012-00101-COSECHA':'O0012-00101-10083-COSECHA',
                        'COSECHA-O0012-00101-ESTIBA ACOPIO':'O0012-00101-10084-ESTIBA ACOPIO',
                        'COSECHA-O0012-00101-ESTIBA KIA':'O0012-00101-10085-ESTIBA KIA',
                        'COSECHA-O0012-00101-EVALUADOR DE PESOS Y CALIBRES':'O0012-00101-10086-EVALUADOR DE PESOS Y CALIBRES',
                        'COSECHA-O0012-00101-JABERO':'O0012-00101-10087-JABERO',
                        'COSECHA-O0012-00101-LAVADO DE JABAS':'O0012-00101-10088-LAVADO DE JABAS',
                        'COSECHA-O0012-00101-LAVADO DE JARRAS':'O0012-00101-10089-LAVADO DE JARRAS',
                        'COSECHA-O0012-00101-SCANER':'O0012-00101-10094-SCANER',
                        'COSECHA-O0012-00101-SUPERVISOR DE ACOPIO':'O0012-00101-10081-SUPERVISOR DE ACOPIO',
                        'GHSSOMA-O0014-00116-AUXILIAR DE SALUD':'O0014-00116-10100-AUXILIAR DE SALUD',
                        '---HIDROLLENADO':'C0004-10048-70025-HIDROLLENADO',
                        'LOGISTI-O0004-00011-SUPERVISOR DE ALMACEN':'O0004-00011-10011-SUPERVISOR DE ALMACEN',
                        'LOGISTI-O0004-00012-AUXILIAR DE ALMACEN':'O0004-00012-10012-AUXILIAR DE ALMACEN',
                        'MANTENC-C0003-00012-COLOCACION DE ESTACAS':'C0003-10031-90003-COLOCACION DE ESTACAS',
                        'MANTENC-O0003-00010-COORDINADOR DE RIEGO':'O0003-00010-10005-COORDINADOR DE RIEGO',
                        'MANTENC-O0003-00010-COORDINADOR DE SANIDAD':'O0003-00010-10004-COORDINADOR DE SANIDAD',
                        'MANTENC-O0005-00014-APLICACION CON MOCHILA-SANIDAD':'O0005-00014-10014-APLICACION CON MOCHILA-SANIDAD',
                        'MANTENC-O0005-00015-APLICACION CON TRACTOR-SANIDAD':'O0005-00015-10015-APLICACION CON TRACTOR-SANIDAD',
                        'MANTENC-O0005-00017-EVALUADOR FITOSANITARIO':'O0005-00017-10017-EVALUADOR FITOSANITARIO',
                        'MANTENC-O0005-00018-SUPERVISOR DE FITOSANIDAD':'O0005-00018-10018-SUPERVISOR DE FITOSANIDAD',
                        'MANTENC-O0005-00021-PRE MEZCLA':'O0005-00021-10021-PRE MEZCLA',
                        'MANTENC-O0006-00022-SUPERVISOR DE RIEGO':'O0006-00022-10022-SUPERVISOR DE RIEGO',
                        'MANTENC-O0006-00023-OPERADOR DE FILTRADO':'O0006-00023-10023-OPERADOR DE FILTRADO',
                        'MANTENC-O0006-00024-REGADORES':'O0006-00024-10024-REGADORES',
                        'MANTENC-O0006-00025-TECNICO DE MANTENIMIENTO':'O0006-00025-10025-TECNICO DE MANTENIMIENTO',
                        'MANTENC-O0006-00032-APOYO DE RIEGO':'O0006-00032-10032-APOYO DE RIEGO',
                        'MANTENC-O0006-00033-AUXILIAR DE RIEGO':'O0006-00033-10033-AUXILIAR DE RIEGO',
                        '01-O0004-00011-SUPERVISOR DE ALMACEN':'O0004-00011-10011-SUPERVISOR DE ALMACEN',
                        '01-O0004-00012-AUXILIAR DE ALMACEN':'O0004-00012-10012-AUXILIAR DE ALMACEN',
                        '01-O0008-00041-ELIMINACION DE RESTOS VEGETALES':'O0008-00041-10041-ELIMINACION DE RESTOS VEGETALES',
                        '01-O0008-00043-APLICACION CON MOCHILA - PODA':'O0008-00043-10043-APLICACION CON MOCHILA - PODA',
                        '01-O0009-00078-MECANICO':'O0009-00078-10078-MECANICO',
                        '01-O0012-00101-ESTIBA ACOPIO':'O0012-00101-10084-ESTIBA ACOPIO',
                        '01-O0012-00101-LAVADO DE JARRAS':'O0012-00101-10089-LAVADO DE JARRAS',
                        'MANTENC-O0008-00036-PODA':'O0008-00036-10036-PODA',
                        'MANTENC-O0008-00037-SUPERVISOR DE GRUPO PODA':'O0008-00037-10037-SUPERVISOR DE GRUPO PODA',
                        'MANTENC-O0009-00058-':'O0009-00058-10058-LIMPIEZA DE AMBIENTES',

                        ##
                        'O0014-00116-10109-GERENTE GENERAL':'O0107-30037-11041-GERENTE GENERAL',
                        'C0001-00011-90001-LIMPIEZA DE TERRENO MO':'C0001-10010-90001-LIMPIEZA DE TERRENO MO',
                        '00012-10012--AUXILIAR DE ALMACEN':'O0004-00012-10012-AUXILIAR DE ALMACEN',
                        'C0006-C0006-10091-90010':'C0006-10091-90010-DISTRIBUCIÓN DE MACETAS Y FIBRA',
                        'C0006-C0006-10084-90005':'C0006-10084-90005-ESTIBA',
                        'C0002-C0002-10018-90002':'C0002-10018-90002-HIDRATACIÓN DE FIBRA MO',
                        'C0003-C0003-10032-90004':'C0003-10032-90004-JORNALEROS RIEGO',
                        'C0006-C0006-10086-90006':'C0006-10086-90006-MANO DE OBRA PLANTACIÓN',
                        'C0001-C0001-10005-90000':'C0001-10005-90000-MANO OBRA ARMADO CAMELLONES',
                         '00101-10083--COSECHA':'O0012-00101-10083-COSECHA'               
                        



                    })
print(df["Actividad del Proyecto"].unique())
"""
"""
df["code_act"] = df["Actividad del Proyecto"].str[:5]
df["TIPO_PRESUPUESTO"] = df["Actividad del Proyecto"].str[:1]
st.write("primero shape1")
st.write(df.shape)
df = transform_asiento(df)
st.write("segundo shape")
st.write(df.shape)
                                            
df = add_codigo_location(df,subsidiary_dict)              


df["CLASS"] = df["DEPARTAMENTO"].str.split("-").str[1]
df["CLASS"] = df["CLASS"].replace({
                        "ADMPERS":"ADMINISTRACION DE PERSONAL",
                        "GHSSOMA":"SSOMA",
                        "BIENEST":"BIENESTAR SOCIAL",
                        "COSECHA":"COSECHA",
                        "MANTENC":"MANTENCION",
})
df.loc[df["CLASE"] == "GESTION HUMANA", "CLASE"] = df["CLASS"]
                    




df["CLASE GENERAL"] = df["CLASE"].fillna("-") + " - " + df["CLASS"].fillna("-")
swap_class = {
    'ADMINISTRACION DE PERSONAL - ADMINISTRACION DE PERSONAL':"ADMINISTRACION DE PERSONAL",
    'SSOMA - SSOMA':"SSOMA",
    'BIENESTAR SOCIAL - BIENESTAR SOCIAL':"BIENESTAR SOCIAL",
    'PRODUCCION - MANTENCION':"PRODUCCION",
    'PRODUCCION - COSECHA':"PRODUCCION",
    'RIEGO - MANTENCION':"RIEGO",
    'SANIDAD - MANTENCION':"SANIDAD",
    'PRODUCCION - LOGISTI':"ALMACEN",
    'PRODUCCION - ADMINISTRACION DE PERSONAL':"ADMINISTRACION DE PERSONAL",
    'RIEGO - ADMINISTRACION DE PERSONAL':"ADMINISTRACION DE PERSONAL",
    'RIEGO - COSECHA':"RIEGO",
    'SANIDAD - ADMINISTRACION DE PERSONAL':"ADMINISTRACION DE PERSONAL",
    'CALIDAD - GERPROD':"PRODUCCION",
    'CALIDAD - -':"PRODUCCION",
    '- - -':"-",
    'PRODUCCION - GERPROD':"PRODUCCION",
    'MANTENIMIENTO - GERPROD':"PRODUCCION",
    'MANTENIMIENTO - -':"PRODUCCION",
    'PRODUCCION - 04.40OZ':"GERENCIA PRODUCCION PACKING",
    'PRODUCCION - -':"PRODUCCION",
    'PRODUCCION - GRANEL.':"GERENCIA PRODUCCION PACKING",
    'PRODUCCION - 06.00OZ':"GERENCIA PRODUCCION PACKING",
    'PRODUCCION - 08.18OZ':"GERENCIA PRODUCCION PACKING",
    'PRODUCCION - 12.18OZ':"GERENCIA PRODUCCION PACKING",
    'PRODUCCION - P. ALTA':"GERENCIA PRODUCCION PACKING",
    'PRODUCCION - P.PLANA':"GERENCIA PRODUCCION PACKING",
    'MANTENCION QBERRIES ETAPA I - MANTENCION':"",
    'COSECHA - COSECHA':"COSECHA",
    'PRODUCCION - BIENESTAR SOCIAL':"",
    'SANIDAD - COSECHA':"PRODUCCION",
    'PRODUCCION - SSOMA':"SSOMA",
    'PRODUCCION - GERENCI':"PRODUCCION",
    'ALMACEN - LOGISTI':"ALMACEN",
    '- - MANTENCION':"MANTENCION",
    '- - COSECHA':'COSECHA',
    '- - OPERACIONES':'OPERACIONES',
    'MANTENCION - MANTENCION': 'MANTENCION',
    '- - LOGISTI':"ALMACEN",
    'PRODUCCION - 01':"PRODUCCION",
    '- - ADMINISTRACION DE PERSONAL':"ADMINISTRACION DE PERSONAL",
    'RIEGO - -':'RIEGO',
    'CALIDAD - 06.00OZ':'PRODUCCION',
    'CALIDAD - GRANEL.':'PRODUCCION',
    'CALIDAD - 04.40OZ':'PRODUCCION',
    'MANTENIMIENTO - 04.40OZ':'PRODUCCION',
    'ADMNISTRACION - -':'ADMINISTRACION DE PERSONAL',
    'ADMINISTRATIVO - -': 'ADMINISTRACION DE PERSONAL',
    'ADMINISTRACION DE PERSONAL - -':'ADMINISTRACION DE PERSONAL',
    'MANTENCION - -':'PRODUCCION',

    'COSECHA - -':'PRODUCCION',
    'LOGISTICA - -':'ALMACEN',
    'SSOMA - -':'SSOMA',
    'ADMINISTRACION DE PERSONAL SAN PEDRO - -':'ADMINISTRACION DE PERSONAL',
    'BIENESTAR - -':'BIENESTAR SOCIAL',
    'SSOMA SAN PEDRO - -':'SSOMA',
    'SANIDAD - -':'SANIDAD',
    'PRODUCCION - PRODUCC':'PRODUCCION',
    'GERENCIA - GERENCI':'GERENCIA',
    'GERENCIA GENERAL - GERENCI':'GERENCIA',
    'CALIDAD - CALIDAD':'PRODUCCION',
    'MANTENIMIENTO - MANTTO.':'PRODUCCION',
    'PRODUCCION - CALIDAD':'PRODUCCION',
    'GERENCIA DE PRODUCCION - GERPROD':'PRODUCCION',
    'PRODUCCION - MANTTO.':'PRODUCCION',

    'ALMACEN - ALMACEN':'ALMACEN',
    'PRODUCCION - ALMACEN':'ALMACEN',
    'PRODUCCION - RIEGO':'RIEGO',
    'PRODUCCION - SANIDAD':'SANIDAD',
    'SANIDAD - TRANSPO':'TRANSPORTE',
    'SANIDAD - SANIDAD':'SANIDAD',
    'SANIDAD - PRODUCC':'SANIDAD',
    'RIEGO - RIEGO':'RIEGO',
    'RIEGO - SANIDAD':'SANIDAD',
    '- - ALMACEN':'ALMACEN',
    'PRODUCC - PRODUCC':'PRODUCCION',
    'RIEGO - PRODUCC': 'RIEGO',
    'ADMINIS - ADMINIS':'ADMINISTRACION DE PERSONAL',
    'SANIDAD - RIEGO':'RIEGO',
    'GERENCIA  - GERENCI':'GERENCIA',   
    }
"""
'-'
"""
df["CLASE GENERAL"] = df["CLASE GENERAL"].replace(swap_class)
empresa_id = subsidiary_dict[df["SUBSIDIARIA"][0]]

if empresa_id == 10:
    act_class = {
        "O0101-30003-11004-OPERARIO DE SANEAMIENTO": "OPERACIONES PACKING",
        "O0102-30004-11008-AUXILIAR DE TRAZABILIDAD": "OPERACIONES PACKING",
        "O0102-30004-11009-AUXILIAR DE PRODUCCION": "OPERACIONES PACKING",
        "O0102-30004-11011-AUXILIAR DE LINEA": "OPERACIONES PACKING",
        "O0102-30007-11015-OPERARIO DE ALMACEN": "ALMACENAMIENTO DE MP",
        "O0103-30008-11018-AUXILIAR DE MANTENIMIENTO": "OPERACIONES PACKING",
        "O0103-30008-11051-OPERARIO DE INFRAESTRUCTURA": "OPERACIONES PACKING",
        "O0106-30028-11022-ABASTECEDOR DE MATERIALES": "LINEA DE EMPAQUE",
        "O0106-30028-11024-CONTROLADOR DE MP": "RECEPCION",
        "O0106-30028-11025-CONTROLADOR DE PT": "DESPACHO",
        "O0106-30028-11026-DESPACHO": "DESPACHO",
        "O0106-30028-11027-ENZUNCHADOR": "DESPACHO",
        "O0106-30028-11028-ETIQUETADOR": "DESPACHO",
        "O0106-30028-11030-OPERADOR DE MAQUINARIA": "OPERACIONES PACKING",
        "O0106-30028-11031-RECEPCIONADOR DE MP": "RECEPCION",
        "O0106-30028-11033-REEMPACADOR- WALMART": "ALMACENAMIENTO DE PT",
        "O0106-30028-11034-SELECCION MANUAL - WALMART": "LINEA DE EMPAQUE",
        "O0106-30028-11035-TUNELERO MP": "RECEPCION",
        "O0106-30028-11036-TUNELERO PT": "DESPACHO",
        "O0106-30028-11037-ABASTECEDOR": "LINEA DE EMPAQUE",
        "O0106-30028-11038-ENCAJADOR": "DESPACHO",
        "O0106-30028-11039-PALETIZADOR": "DESPACHO",
        "O0106-30028-11040-PESADOR": "LINEA DE EMPAQUE",
        "O0106-30028-11052-SELLADOR": "LINEA DE EMPAQUE",
        "O0106-30028-11053-DIGITADOR DE RECEPCION": "RECEPCION",
        "O0106-30028-11054-DIGITADOR DE DESPACHO": "DESPACHO",
        "O0106-30028-11055-OPERADOR DE MONTACARGA-DESPACHO": "DESPACHO",
        "O0106-30028-11066-ABASTECEDOR DE CLAMSHELLS": "LINEA DE EMPAQUE",
        "O0106-30028-11067-DIGITADOR DE PRODUCCION": "LINEA DE EMPAQUE",
        "O0106-30028-11068-OPERADOR DE MAQUINA ETIQUETADORA": "LINEA DE EMPAQUE",
        "O0106-30028-11069-OPERADOR DE LLENADORA PONNYS": "LINEA DE EMPAQUE",
        "O0110-30053-11060-TAREADOR": "OPERACIONES PACKING",
        "O0106-30028-11023-CONTROL DE ABASTECIMIENTO MP":"RECEPCION"
    }
    area_df = pd.read_excel(name_file,sheet_name="Area")
    area_df = area_df[area_df["id_subsidiary"] == empresa_id]
    area_df = area_df[["id_area","name_area"]]
    df["name_area"] = df["Actividad del Proyecto"].replace(act_class)
    df = df.merge(area_df,on="name_area",how="left")
    
else:
    df = add_codigo_area(df,subsidiary_dict)

print(df["CLASE GENERAL"].unique())
df = add_codigo_ceco(df,subsidiary_dict)
##
df["DEBITO"] = df["DEBITO"].fillna(0)
df["CREDITO"] = df["CREDITO"].fillna(0)

fecha_ = str(df["FECHA"][0])
nota_ = str(df["NOTA"][0])

df.to_excel("prueba_asiento.xlsx",index=False)
st.write("Proceso completado")
st.write(df.shape)
st.dataframe(df)

st.write(f"debito: {df['DEBITO'].sum()}")
st.write(f"credito: {df['CREDITO'].sum()}")

def build_line(row):
    line_item = {
        "account": row["id_cuenta"],
        "debit": round(float(row["DEBITO"]), 2),   # ← REDONDEAR A 2 DEC
        "credit": round(float(row["CREDITO"]), 2),  # ← REDONDEAR A 2 DEC
        "memo": row["NOTA LINEA"],
        "location": row["id_location"], # Use row value
    }
    if not pd.isna(row["id_actividad"]):
        line_item["cseg_actividad"] = int(row["id_actividad"])
    if not pd.isna(row["id_partida"]):
        line_item["cseg_partida_presup"] = int(row["id_partida"])
    if not pd.isna(row["id_macro_partida"]):
        line_item["cseg_macropartida"] = int(row["id_macro_partida"])
    if not pd.isna(row["id_ceco"]):
        line_item["department"] = int(row["id_ceco"])
    if not pd.isna(row["id_area"]):
        line_item["class"] = int(row["id_area"])
    
    return line_item
# Calcular targets ANTES de construir las líneas (desde el df original)
target_debit  = round(df["DEBITO"].sum(), 2)   # 210.74
target_credit = round(df["CREDITO"].sum(), 2)  # 210.74     
lines = [build_line(row) for _, row in df.iterrows()]   
def adjust_rounding(lines, target_debit, target_credit):
    # Suma actual ya redondeada por línea
    current_debit  = round(sum(l["debit"]  for l in lines), 2)  # 210.32
    current_credit = round(sum(l["credit"] for l in lines), 2)  # 210.32

    # Ajustar última línea de débito
    diff_debit = round(target_debit - current_debit, 2)
    if diff_debit != 0:
        last_debit_idx = max(i for i, l in enumerate(lines) if l["debit"] > 0)
        lines[last_debit_idx]["debit"] = round(lines[last_debit_idx]["debit"] + diff_debit, 2)

    # Ajustar última línea de crédito
    diff_credit = round(target_credit - current_credit, 2)
    if diff_credit != 0:
        last_credit_idx = max(i for i, l in enumerate(lines) if l["credit"] > 0)
        lines[last_credit_idx]["credit"] = round(lines[last_credit_idx]["credit"] + diff_credit, 2)

    return lines
# Construcción del journal entry
lines = adjust_rounding(lines, target_debit, target_credit) # aplicar ajuste antes de enviar

data_journalentry = [
                        {
                            "action": "create",
                            "recordType": "journalentry",
                            "subsidiary": empresa_id,
                            #"subsidiary": 999999,
                            "trandate":{"text":fecha_},
                            "currency":1,
                            "exchangerate":1.0,
                            "memo":nota_,
                            "line": lines
                        }
                    ]
# Debug: verificar que cuadra
total_d = round(sum(l["debit"]  for l in lines), 2)
total_c = round(sum(l["credit"] for l in lines), 2)
st.write(f"✅ Débito final:  {total_d}")
st.write(f"✅ Crédito final: {total_c}")
st.write(f"✅ Diferencia:    {round(total_d - total_c, 2)}")

st.write(data_journalentry)

# Botón de descarga
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='Asientos')
buffer.seek(0)

st.download_button(
    label="📥 Descargar Excel",
    data=buffer,
    file_name="asientos_procesados.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

if st.button("Enviar a NetSuite", type="primary"):
    try:
        with st.spinner("Enviando datos a NetSuite..."):
            response = client.restlet(data_journalentry)
        st.success("¡Datos enviados con éxito!")
        st.write("Respuesta del servidor:")
        st.json(response)
    except Exception as e:
        st.error(f"Error al enviar a NetSuite: {e}")


