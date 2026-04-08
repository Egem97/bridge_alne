from dataclasses import dataclass, asdict
import pandas as pd


@dataclass
class ValidationError:
    level: str       # 'error' | 'warning'
    category: str    # 'structure', 'data_type', 'mapping', 'balance'
    message: str
    details: dict

    def to_dict(self):
        return asdict(self)


REQUIRED_COLUMNS_SHARED = [
    "FECHA",
    "SUBSIDIARIA",
    "UBICACIÓN",
    "NOTA",
    "NOTA LINEA",
    "DEBITO",
    "CREDITO",
    "NUMERO y NOMBRE DE CUENTA CONTABLE",
    "Actividad del Proyecto",
    "Macro Partida",
    "Partida Presupuestaria",
    "CLASE",
]

REQUIRED_COLUMNS_EXTRA = {
    "empleados": ["DEPARTAMENTO"],
    "obreros": ["DEPARTAMENTO"],
    "vida_ley": ["DEPARTAMENTO"],
}


class ExcelValidator:

    def validate_all(self, df, planilla_type):
        errors = []
        errors.extend(self.validate_structure(df, planilla_type))
        if any(e.level == 'error' for e in errors):
            return errors
        errors.extend(self.validate_data_types(df))
        return errors

    def validate_post_transform(self, df):
        errors = []
        errors.extend(self.validate_mappings(df))
        errors.extend(self.validate_balance(df))
        return errors

    def validate_structure(self, df, planilla_type):
        errors = []
        required = REQUIRED_COLUMNS_SHARED + REQUIRED_COLUMNS_EXTRA.get(planilla_type, [])

        missing = [col for col in required if col not in df.columns]
        if missing:
            errors.append(ValidationError(
                level='error',
                category='structure',
                message=f'Columnas requeridas faltantes: {", ".join(missing)}',
                details={'missing_columns': missing}
            ))

        if df.empty:
            errors.append(ValidationError(
                level='error',
                category='structure',
                message='El archivo no contiene datos',
                details={}
            ))

        return errors

    def validate_data_types(self, df):
        errors = []

        # Validate DEBITO/CREDITO are numeric
        for col in ["DEBITO", "CREDITO"]:
            if col in df.columns:
                non_numeric = df[~pd.to_numeric(df[col], errors='coerce').notna() & df[col].notna()]
                if not non_numeric.empty:
                    bad_rows = non_numeric.index.tolist()[:10]
                    errors.append(ValidationError(
                        level='error',
                        category='data_type',
                        message=f'Valores no numéricos en columna {col}',
                        details={'column': col, 'rows': bad_rows}
                    ))

        # Validate FECHA is parseable
        if "FECHA" in df.columns:
            try:
                pd.to_datetime(df["FECHA"])
            except Exception:
                errors.append(ValidationError(
                    level='error',
                    category='data_type',
                    message='La columna FECHA contiene valores que no son fechas válidas',
                    details={'column': 'FECHA'}
                ))

        # Validate SUBSIDIARIA not empty
        if "SUBSIDIARIA" in df.columns:
            empty_subs = df[df["SUBSIDIARIA"].isna() | (df["SUBSIDIARIA"] == "")]
            if not empty_subs.empty:
                errors.append(ValidationError(
                    level='error',
                    category='data_type',
                    message='Filas con SUBSIDIARIA vacía',
                    details={'rows': empty_subs.index.tolist()[:10]}
                ))

        return errors

    def validate_mappings(self, df):
        errors = []

        mapping_checks = [
            ("id_cuenta", "Cuenta Contable"),
            ("id_location", "Ubicación"),
        ]

        for col, label in mapping_checks:
            if col in df.columns:
                null_rows = df[df[col].isna()]
                if not null_rows.empty:
                    row_indices = null_rows.index.tolist()[:15]
                    errors.append(ValidationError(
                        level='warning',
                        category='mapping',
                        message=f'{label} no mapeada en {len(null_rows)} fila(s)',
                        details={'column': col, 'rows': row_indices, 'count': len(null_rows)}
                    ))

        optional_mapping_checks = [
            ("id_ceco", "Centro de Costo"),
            ("id_area", "Área/Clase"),
            ("id_actividad", "Actividad del Proyecto"),
        ]

        for col, label in optional_mapping_checks:
            if col in df.columns:
                null_rows = df[df[col].isna()]
                if not null_rows.empty:
                    row_indices = null_rows.index.tolist()[:15]
                    errors.append(ValidationError(
                        level='warning',
                        category='mapping',
                        message=f'{label} no mapeada en {len(null_rows)} fila(s)',
                        details={'column': col, 'rows': row_indices, 'count': len(null_rows)}
                    ))

        return errors

    def validate_balance(self, df):
        errors = []

        if "DEBITO" in df.columns and "CREDITO" in df.columns:
            total_debit = round(df["DEBITO"].sum(), 2)
            total_credit = round(df["CREDITO"].sum(), 2)
            diff = round(abs(total_debit - total_credit), 2)

            if diff > 1.00:
                errors.append(ValidationError(
                    level='error',
                    category='balance',
                    message=f'Desbalance significativo: Débito={total_debit}, Crédito={total_credit}, Diferencia={diff}',
                    details={
                        'total_debit': total_debit,
                        'total_credit': total_credit,
                        'difference': diff
                    }
                ))
            elif diff > 0.00:
                errors.append(ValidationError(
                    level='warning',
                    category='balance',
                    message=f'Diferencia menor por redondeo: {diff} (se ajustará automáticamente)',
                    details={
                        'total_debit': total_debit,
                        'total_credit': total_credit,
                        'difference': diff
                    }
                ))

        return errors
