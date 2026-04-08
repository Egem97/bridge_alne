import io
import pandas as pd

from .transformers.empleados import EmpleadosTransformer
from .transformers.obreros import ObrerosTransformer
from .transformers.vida_ley import VidaLeyTransformer
from .validators import ExcelValidator
from .payload import build_journal_entry, clean_nans
from .master_data import MasterDataLoader

TRANSFORMER_REGISTRY = {
    'empleados': EmpleadosTransformer,
    'obreros': ObrerosTransformer,
    'vida_ley': VidaLeyTransformer,
}


def process_upload(file_content, planilla_type):
    if planilla_type not in TRANSFORMER_REGISTRY:
        return {
            "valid": False,
            "errors": [{
                "level": "error",
                "category": "structure",
                "message": f"Tipo de planilla no válido: {planilla_type}",
                "details": {"valid_types": list(TRANSFORMER_REGISTRY.keys())}
            }]
        }

    try:
        df = pd.read_excel(io.BytesIO(file_content), skiprows=2)
    except Exception as e:
        return {
            "valid": False,
            "errors": [{
                "level": "error",
                "category": "structure",
                "message": f"Error al leer el archivo Excel: {str(e)}",
                "details": {}
            }]
        }

    # Stage 1: Pre-transform validation
    validator = ExcelValidator()
    pre_errors = validator.validate_all(df, planilla_type)
    blocking_errors = [e for e in pre_errors if e.level == 'error']
    if blocking_errors:
        return {
            "valid": False,
            "errors": [e.to_dict() for e in pre_errors]
        }

    # Stage 2: Transform
    try:
        transformer_cls = TRANSFORMER_REGISTRY[planilla_type]
        transformer = transformer_cls()
        df = transformer.transform(df)
    except Exception as e:
        return {
            "valid": False,
            "errors": [{
                "level": "error",
                "category": "transform",
                "message": f"Error en la transformación: {str(e)}",
                "details": {}
            }]
        }

    # Stage 3: Post-transform validation
    post_errors = validator.validate_post_transform(df)
    blocking_post = [e for e in post_errors if e.level == 'error']
    if blocking_post:
        # Include transformed data so the user can download it and diagnose errors
        return clean_nans({
            "valid": False,
            "errors": [e.to_dict() for e in post_errors],
            "subsidiary_name": df["SUBSIDIARIA"].iloc[0] if not df.empty else None,
            "_transformed_data": df.to_dict(orient='records'),
            "_transformed_columns": list(df.columns),
        })

    # Stage 4: Build payload
    try:
        empresa_id = transformer.empresa_id
        payload = build_journal_entry(df, empresa_id)
    except Exception as e:
        return {
            "valid": False,
            "errors": [{
                "level": "error",
                "category": "payload",
                "message": f"Error al construir el payload: {str(e)}",
                "details": {}
            }]
        }

    # Build preview columns
    preview_columns = [
        "FECHA", "SUBSIDIARIA", "NOTA LINEA", "DEBITO", "CREDITO",
        "id_cuenta", "id_location", "id_ceco", "id_area",
        "id_actividad", "id_partida", "id_macro_partida",
    ]
    available_cols = [c for c in preview_columns if c in df.columns]
    dff = df[available_cols].copy()

    warnings = [e.to_dict() for e in post_errors if e.level == 'warning']

    subsidiary_name = df["SUBSIDIARIA"].iloc[0] if not df.empty else None

    summary = {
        "status": "preview",
        "valid": True,
        "warnings": warnings,
        "columns": list(dff.columns),
        "table_data": dff.to_dict(orient='records'),
        "netsuite_payload": payload,
        "row_count": len(df),
        "subsidiary_name": subsidiary_name,
        "total_debit": float(round(df["DEBITO"].sum(), 4)),
        "total_credit": float(round(df["CREDITO"].sum(), 4)),
        # Full transformed df stored for Excel download (not sent to client directly)
        "_transformed_data": df.to_dict(orient='records'),
        "_transformed_columns": list(df.columns),
    }

    return clean_nans(summary)
