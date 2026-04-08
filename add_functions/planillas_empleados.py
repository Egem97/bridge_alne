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
    #mpa["Actividad del Proyecto"] = mpa["Actividad del Proyecto"].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    mpa["Actividad del Proyecto COMPLETO"] = mpa["Actividad del Proyecto"]
    mpa["Actividad del Proyecto"] = mpa["Actividad del Proyecto"].str.strip()
    mpa["Actividad del Proyecto"] = mpa["Actividad del Proyecto"].str[:17]
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
        
    
    #df["NUMERO y NOMBRE DE CUENTA CONTABLE"] = df.apply(lambda x: change_account_afp(str(x["CUENTA_CONTABLE"]), str(x["NUMERO y NOMBRE DE CUENTA CONTABLE"])), axis=1)
    #df["NUMERO y NOMBRE DE CUENTA CONTABLE"] = df.apply(lambda x: change_account_for_cod_actividad(str(x["code_act"]), str(x["NUMERO y NOMBRE DE CUENTA CONTABLE"])), axis=1)
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
                            "GAP BERRIES S.A.C":"GAP BERRIES SAC",
                            "GOLDEN BERRIES S.A.C.":"GOLDEN BERRIES SAC",
                            "INMOBILIARIA SAN JUAN SA":"INMOBILIARIA SAN JUAN SA",
                            "INVERSIONES QUELEN PERU SAC":"INVERSIONES QUELEN PERU SAC",
                            "QBERRIES S.A.C":"QBERRIES SAC",#################
                            "TARA FARM S.A.C.":"TARA FARM SAC",
                            "TECNOLOGIAS ORGANICAS TAKAMATSU SAC":"TECNOLOGIAS ORGANICAS TAKAMATSU SAC",
                            "360 SMART AGRO SAC":"360 SMART AGRO SAC",
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
df["SUBSIDIARIA"] = df["SUBSIDIARIA"].replace({
                            "AGROBUSINESS INTERNATIONAL PERU SAC":"AGROBUSINESS INTERNATIONAL PERU SAC",
                            "ALZA PERU GROUP SAC":"ALZA PERU GROUP SAC",
                            "ALZA PERU PACKING S.A.C.":"ALZA PERU PACKING SAC",
                            "APG":"APG",
                            "BERRIES":"BERRIES",
                            "BIG BERRIES S.A.C.":"BIG BERRIES SAC",
                            "CANYON BERRIES S.A.C.":"CANYON BERRIES SAC",
                            "EXCELLENCE FRUIT S.A.C.":"EXCELLENCE FRUIT SAC",
                            "GAP BERRIES S.A.C":"GAP BERRIES SAC",
                            "GOLDEN BERRIES S.A.C.":"GOLDEN BERRIES SAC",
                            "INMOBILIARIA SAN JUAN SA":"INMOBILIARIA SAN JUAN SA",
                            "INVERSIONES QUELEN PERU SAC":"INVERSIONES QUELEN PERU SAC",
                            "QBERRIES S.A.C":"QBERRIES SAC",#################
                            "TARA FARM S.A.C.":"TARA FARM SAC",
                            "TECNOLOGIAS ORGANICAS TAKAMATSU SAC":"TECNOLOGIAS ORGANICAS TAKAMATSU SAC",
                            "360 SMART AGRO SAC":"360 SMART AGRO SAC",
                        })
df["NUMERO y NOMBRE DE CUENTA CONTABLE"] = df["NUMERO y NOMBRE DE CUENTA CONTABLE"].astype(str)
df["Actividad del Proyecto"] = df["Actividad del Proyecto"].str.strip()
df["CUENTA CONTABLE"] = df["NUMERO y NOMBRE DE CUENTA CONTABLE"].str[:8]
#NUMERO y NOMBRE DE CUENTA CONTABLE
subsidiary_dict = table_subsidiary()
empresa_id = subsidiary_dict[df["SUBSIDIARIA"][0]]
mpa = table_actividad()
st.write(empresa_id)
#df["code_act"] = df["Actividad del Proyecto"].str[:16]
st.write(df.shape)
st.dataframe(df)




st.dataframe(mpa)
#JOIN ACTIVIDAD
df = df.merge(mpa, on=["Actividad del Proyecto"], how="left")
#JOIN ID CUENTA
accounts = pd.read_excel("accounts.xlsx",dtype={"externalid":str})
accounts = accounts.rename(columns={
    "externalid":"CUENTA CONTABLE",
    "id":"id_cuenta"
})
accounts = accounts[["CUENTA CONTABLE","id_cuenta","custrecord_gd_auxiliar","isinactive"]]
accounts["CUENTA CONTABLE"] = accounts["CUENTA CONTABLE"].astype(str)
#st.subheader("q")
#st.dataframe(accounts)


df = df.merge(accounts, on=["CUENTA CONTABLE"], how="left")
### LOCATION
df = add_codigo_location(df,subsidiary_dict)      

### DEPARTAMENTO
ceco = pd.read_excel("CECOS.xlsx")
ceco = ceco[ceco["id_subsidiary"] == empresa_id]
ceco = ceco[["id_ceco","name_ceco"]]
ceco = ceco.rename(columns={
    "name_ceco":"DEPARTAMENTO"
})


df = df.merge(ceco, on=["DEPARTAMENTO"], how="left")

###CLASE

area_df = pd.read_excel(name_file,sheet_name="Area")
area_df = area_df[area_df["id_subsidiary"] == empresa_id]
area_df = area_df[["id_area","name_area"]]
area_df = area_df.rename(columns={
    "name_area":"CLASE"
})

st.write("CLASE")
st.dataframe(area_df)
df = df.merge(area_df, on=["CLASE"], how="left")


st.write(df.shape)
st.dataframe(df)


##
df["DEBITO"] = df["DEBITO"].fillna(0).round(2)
df["CREDITO"] = df["CREDITO"].fillna(0).round(2)
#df["DEBITO"] = round(df["DEBITO"],3)
#df["CREDITO"] = round(df["CREDITO"],3)


df["FECHA"] = pd.to_datetime(df["FECHA"]).dt.strftime("%d/%m/%Y")
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
        "debit": row["DEBITO"],
        "credit": row["CREDITO"],
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
###############################################################################
from decimal import Decimal

d_vals = [Decimal(str(round(v, 2))) for v in df["DEBITO"]]
c_vals = [Decimal(str(round(v, 2))) for v in df["CREDITO"]]
target_debit  = float(sum(d_vals))  # 30825.28
target_credit = float(sum(c_vals))  # 30825.29210.74     
diff = round(target_credit - target_debit, 2)  # +0.01
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
lines = adjust_rounding(lines, target_debit, target_credit) # aplicar ajuste antes de enviar

data_journalentry = [
                    {
                        "action": "create",
                        "recordType": "journalentry",
                        "subsidiary": empresa_id,
                        "trandate":{"text":fecha_},
                        "currency":1,
                        "exchangerate":1.0,
                        "memo":nota_,
                        "line": lines
                    }
                ]
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
