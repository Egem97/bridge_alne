# APP ALZA - Bridge Nómina ↔️ Oracle NetSuite

## Descripción General

**APP ALZA** es una aplicación web Django que actúa como puente entre el sistema de nómina (planillas en Excel) y Oracle NetSuite. Su función principal es:

1. Cargar archivos Excel generados por el equipo de nómina
2. Transformar/validar los datos según las reglas de negocio
3. Mapear los datos al formato que NetSuite espera
4. Enviar asientos contables (Journal Entries) a NetSuite mediante su API RESTlet

## Estado del Proyecto

- **Status**: En desarrollo (próximo a producción)
- **Usuarios**: Equipo de nómina, administrativos
- **Dependencias críticas**: Django 5.2.8, Pandas, NumPy, Oracle NetSuite API
- **Problemas conocidos**: None

## Arquitectura

```
APP ALZA/
├── yw_oracle/                    # App principal de transformaciones
│   ├── views.py                  # Endpoint: upload_excel_view (en desarrollo)
│   ├── models.py                 # Models vacío (necesita expandirse)
│   ├── urls.py                   # Rutas
│   └── utils.py                  # NetSuiteClient
├── add_functions/                # Ejemplos Streamlit (referencia)
│   ├── planillas_empleados.py    # Transformación de empleados (asientos)
│   ├── planillas_obreros.py      # Transformación de obreros
│   └── planillas_vida_ley.py     # Transformación de vida ley
├── dashboard/                    # App de autenticación y roles
│   ├── models.py                 # Modelos de usuario/roles
│   └── decorators.py             # @role_required('Nómina')
├── alza_tools/                   # Configuración general Django
│   └── urls.py                   # Incluye rutas de yw_oracle
└── requirements.txt              # Dependencias (NumPy, Pandas, etc)
```

## Flujo de Datos

### 1️⃣ Carga y Procesamiento del Excel

**Endpoint**: `POST /oracle/upload/` (upload_excel_view)

```
Usuario sube Excel
    ↓
Lectura con skiprows=2 (salta primeras 2 filas)
    ↓
Transformación en memoria (sin guardar BD aún)
    ↓
Mapeos aplicados:
    - SUBSIDIARIA → id_subsidiary (empresa en NetSuite)
    - UBICACIÓN → id_location (almacén)
    - DEPARTAMENTO → id_ceco (centro de costo)
    - CLASE → id_area (área)
    - Actividad del Proyecto → id_actividad, id_partida, id_macro_partida
    - CUENTA CONTABLE → id_cuenta (account en NetSuite)
    ↓
Construcción de payload NetSuite (line items + metadata)
    ↓
Retorna vista previa (preview) al usuario
```

### 2️⃣ Validación y Revisión

El usuario revisa los datos en la interfaz:
- Puede cancelar o confirmar
- Modal muestra errores si hay

### 3️⃣ Envío a NetSuite

**Endpoint**: `POST /oracle/upload/` con `action: 'confirm_upload'`

```
Payload JSON confirmado
    ↓
Envía a NetSuite Restlet
    ↓
Respuesta de NetSuite
    ↓
Guardar registro en BD (historial)
    ↓
Retorna resultado al usuario
```

## Tipos de Planillas (3 casos)

### Caso 1: Asientos Contables (Empleados)
- **Archivo**: `planillas_empleados.py`
- **Tipo de datos**: Asientos contables (journalentry) con débitos/créditos
- **Campos principales**: 
  - FECHA, SUBSIDIARIA, DEPARTAMENTO, CLASE
  - NÚMERO CUENTA CONTABLE, DEBITO, CREDITO, NOTA
  - Actividad del Proyecto, Macro Partida, Partida Presupuestaria
- **Mapeos específicos**: 
  - Cuentas AFP especiales (códigos 3322, 3328, 3331, 3319)
  - Ajuste por código de actividad (O0014 → prefijo 94)

### Caso 2: Asientos Contables (Obreros)
- **Archivo**: `planillas_obreros.py`
- **Tipo de datos**: Similar a empleados, probablemente con variaciones en cuentas/áreas
- **Status**: Pendiente revisar estructura exacta

### Caso 3: Asientos Vida Ley
- **Archivo**: `planillas_vida_ley.py`
- **Tipo de datos**: Asientos para provisiones de vida ley
- **Cuentas especiales**: 90215202 → 90215201, 94215202 → 90215201
- **Status**: Pendiente revisar estructura exacta

## Transformaciones Principales

### A. Lectura del Excel
```python
df = pd.read_excel(uploaded_file, skiprows=2)
```

### B. Mapeo de Subsidiarias
- Lee desde `oracle_prod.xlsx` (sheet: "Subsidiary")
- Diccionario: `name_subsidiary` → `id_subsidiary`

### C. Mapeo de Ubicaciones
- Lee desde `oracle_prod.xlsx` (sheet: "Almacen")
- Lógica especial para EXCELLENCE FRUIT SAC (usa UBICACIÓN)
- Fallback: ubicación default por empresa

### D. Mapeo de Centros de Costo (CECOS)
- Lee desde `CECOS.xlsx`
- Lógica especial para QBERRIES SAC (ID=3):
  - Mapea LICAPA → ETAPA I, ETAPA II, ETAPA III
  - Reemplaza MANTENCION/COSECHA → PRODUCCION
  - Valida sufijos para evitar coincidencias incorrectas

### E. Mapeo de Áreas
- Lee desde `oracle_prod.xlsx` (sheet: "Area")
- Basado en TIPO_PRESUPUESTO (O/C) y Partida Presupuestaria
- Lógica especial para EXCELLENCE FRUIT SAC y QBERRIES SAC

### F. Mapeo de Cuentas Contables
- Lectura de `oracle_prod.xlsx` (sheet: "Macro PP Actividad")
- Merge por "Actividad del Proyecto" para obtener:
  - `id_actividad`, `id_partida`, `id_macro_partida`

### G. Mapeo de Cuentas de NetSuite
- Lectura desde archivo (Excel o Parquet)
- Mapeo de "NÚMERO CUENTA CONTABLE" → `id_cuenta`
- Diccionario hardcodeado de excepciones (casos especiales)

### H. Ajuste de Rounding
- Suma de débitos debe = suma de créditos (asiento balanceado)
- Algoritmo: ajusta última línea de débito/crédito para cumplir
- Importante: evita pérdida de precisión con `Decimal`

### I. Construcción de Payload NetSuite
```python
{
  "action": "create",
  "recordType": "journalentry",
  "subsidiary": empresa_id,
  "trandate": {"text": fecha},
  "currency": 1,
  "exchangerate": 1.0,
  "memo": nota,
  "line": [
    {
      "account": id_cuenta,
      "debit": monto_debito,
      "credit": monto_credito,
      "memo": nota_linea,
      "location": id_location,
      "cseg_actividad": id_actividad,
      "cseg_partida_presup": id_partida,
      "cseg_macropartida": id_macro_partida,
      "department": id_ceco,
      "class": id_area
    }
  ]
}
```

## Modelos Django (Pendientes)

El archivo `yw_oracle/models.py` está vacío. Se necesita crear:

### Modelo Sugerido: UploadHistory
```python
class UploadHistory(models.Model):
    ESTADO_CHOICES = [
        ('pending', 'Pendiente'),
        ('success', 'Exitoso'),
        ('error', 'Error'),
    ]
    
    user = ForeignKey(User, on_delete=models.CASCADE)
    file_name = CharField(max_length=255)
    upload_date = DateTimeField(auto_now_add=True)
    estado = CharField(choices=ESTADO_CHOICES, default='pending')
    row_count = IntegerField()
    netsuite_response = JSONField(null=True)
    error_message = TextField(null=True)
    processed_data = JSONField()  # Guardar los datos procesados
```

## Validaciones Necesarias

### 1. Validación de Estructura
- ✅ Columnas requeridas presentes
- ✅ Tipos de datos correctos
- ✅ Fecha en formato válido

### 2. Validación de Mapeos
- ✅ Subsidiaria existe en diccionario
- ✅ Ubicación existe para esa subsidiaria
- ✅ Centro de costo existe
- ✅ Cuenta contable mapea a NetSuite
- ✅ Actividad existe

### 3. Validación de Integridad
- ✅ Débitos = créditos (balance)
- ✅ Montos positivos
- ✅ No hay valores nulos en campos críticos

## Consideraciones de Seguridad

**IMPORTANTE**: Actualmente no hay medidas de seguridad establecidas. Necesario:

1. **Autenticación**: @login_required + @role_required('Nómina')
2. **Validación de entrada**: Validar all Excel inputs
3. **Rate limiting**: Limitar cargas por usuario
4. **Auditoría**: Log all NetSuite submissions
5. **Datos sensibles**: Sueldos/DNI en Excel - proteger transporte y almacenamiento

## Archivos de Configuración Externos

Estos archivos se leen desde el directorio raíz y son críticos:

1. **oracle_prod.xlsx**: Mapeos maestros
   - Sheets: Subsidiary, Almacen, Area, Macro PP Actividad
   
2. **CECOS.xlsx**: Centros de costo
   - Columnas: id_subsidiary, id_ceco, name_ceco, CODIFICACION
   
3. **account_id_map.parquet** o **accounts.xlsx**: Cuentas de NetSuite

⚠️ **Nota**: Estos archivos deben versionarse en Git o tener un sistema de gestión

## NetSuite Integration

### Clase: NetSuiteClient
- Ubicación: `yw_oracle/utils.py`
- Método: `restlet(payload)`
- Autenticación: OAuth/Token (ver .env)

### Variables de entorno requeridas (.env)
```
NETSUITE_ACCOUNT_ID=xxxxx
NETSUITE_CLIENT_ID=xxxxx
NETSUITE_CLIENT_SECRET=xxxxx
NETSUITE_RESTLET_URL=xxxxx
```

## Desarrollo y Notas

### Puntos de Extension

1. **Nuevos tipos de planillas**: Crear nuevo archivo en `add_functions/` con lógica, luego integrar a views.py
2. **Nuevas validaciones**: Agregar métodos de validación en `validators.py` (crear)
3. **Nuevos mapeos**: Actualizar Excel maestro o agregar lógica especial en funciones de mapeo

### Decisiones de Arquitectura

- ✅ **Procesamiento en memoria**: No guarda estado intermedio, más rápido
- ✅ **Pandas para transformaciones**: Potente para operaciones tabulares
- ✅ **Preview antes de envío**: Permite validación manual
- ⏳ **BD para historial**: Necesario implementar (actualmente solo en memoria)

### Debugging

- Los archivos Streamlit (`add_functions/*.py`) tienen `st.dataframe()` para visualizar en cada paso
- La versión Django debe loguear equivalentes en JSON responses o archivos

## Próximos Pasos Recomendados

1. **Crear Models Django** → UploadHistory, ValidationLog
2. **Validación robusta** → validators.py con checks
3. **Refactor views.py** → Sacar lógica de transformación a módulo separado
4. **Completar planillas_obreros.py y planillas_vida_ley.py** → Entender mapeos
5. **UI review** → Modal de errores, preview legible, confirmación
6. **Testing** → Tests unitarios para cada transformación
7. **Security hardening** → Validación, autenticación, rate limiting

## Referencia Rápida de Funciones

| Función | Entrada | Salida | Ubicación |
|---------|---------|--------|-----------|
| `table_subsidiary()` | - | Dict name→id | views.py:65 |
| `add_codigo_location()` | df, subsidiary_dict | df con id_location | views.py:76 |
| `add_codigo_ceco()` | df, subsidiary_dict | df con id_ceco | views.py:105 |
| `add_codigo_area()` | df, subsidiary_dict | df con id_area | views.py:126 |
| `table_actividad()` | - | df actividades | views.py:143 |
| `build_line()` | row | dict line_item | views.py (en Streamlit) |
| `adjust_rounding()` | lines, debit, credit | lines ajustadas | views.py (en Streamlit) |

---

**Última actualización**: Abril 2026
**Tecnología**: Django 5.2.8, Pandas 2.2.0, NumPy 1.26.4
