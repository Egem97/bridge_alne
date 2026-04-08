import pandas as pd
from decimal import Decimal


def build_line(row):
    line_item = {
        "account": row["id_cuenta"],
        "debit": row["DEBITO"],
        "credit": row["CREDITO"],
        "memo": row["NOTA LINEA"],
        "location": row["id_location"],
    }
    if not pd.isna(row.get("id_actividad")):
        line_item["cseg_actividad"] = int(row["id_actividad"])
    if not pd.isna(row.get("id_partida")):
        line_item["cseg_partida_presup"] = int(row["id_partida"])
    if not pd.isna(row.get("id_macro_partida")):
        line_item["cseg_macropartida"] = int(row["id_macro_partida"])
    if not pd.isna(row.get("id_ceco")):
        line_item["department"] = int(row["id_ceco"])
    if not pd.isna(row.get("id_area")):
        line_item["class"] = int(row["id_area"])
    return line_item


def adjust_rounding(lines, target_debit, target_credit):
    current_debit = round(sum(l["debit"] for l in lines), 2)
    current_credit = round(sum(l["credit"] for l in lines), 2)

    diff_debit = round(target_debit - current_debit, 2)
    if diff_debit != 0:
        debit_indices = [i for i, l in enumerate(lines) if l["debit"] > 0]
        if debit_indices:
            last_debit_idx = debit_indices[-1]
            lines[last_debit_idx]["debit"] = round(lines[last_debit_idx]["debit"] + diff_debit, 2)

    diff_credit = round(target_credit - current_credit, 2)
    if diff_credit != 0:
        credit_indices = [i for i, l in enumerate(lines) if l["credit"] > 0]
        if credit_indices:
            last_credit_idx = credit_indices[-1]
            lines[last_credit_idx]["credit"] = round(lines[last_credit_idx]["credit"] + diff_credit, 2)

    return lines


def build_journal_entry(df, empresa_id):
    fecha_ = str(df["FECHA"].iloc[0])
    try:
        nota_ = str(df["NOTA"].iloc[0])
    except (KeyError, IndexError):
        nota_ = ""

    d_vals = [Decimal(str(round(v, 2))) for v in df["DEBITO"]]
    c_vals = [Decimal(str(round(v, 2))) for v in df["CREDITO"]]
    target_debit = float(sum(d_vals))
    target_credit = float(sum(c_vals))

    lines = [build_line(row) for _, row in df.iterrows()]
    lines = adjust_rounding(lines, target_debit, target_credit)

    payload = [
        {
            "action": "create",
            "recordType": "journalentry",
            "subsidiary": empresa_id,
            "trandate": {"text": fecha_},
            "currency": 1,
            "exchangerate": 1.0,
            "memo": nota_,
            "line": lines
        }
    ]
    return payload


def clean_nans(value):
    if isinstance(value, list):
        return [clean_nans(x) for x in value]
    if isinstance(value, dict):
        return {k: clean_nans(v) for k, v in value.items()}
    if pd.isna(value):
        return None
    return value


# Canonical key order for NetSuite journal entry lines
_LINE_KEY_ORDER = [
    "account", "debit", "credit", "memo", "location",
    "cseg_actividad", "cseg_partida_presup", "cseg_macropartida",
    "department", "class",
]

# Canonical key order for NetSuite journal entry header
_ENTRY_KEY_ORDER = [
    "action", "recordType", "subsidiary", "trandate",
    "currency", "exchangerate", "memo", "line",
]


def reorder_payload(payload):
    """
    Rebuild payload with canonical key ordering.
    Needed because PostgreSQL JSONB does not preserve insertion order.
    """
    result = []
    for entry in payload:
        ordered_lines = []
        for line in entry.get("line", []):
            ordered_line = {k: line[k] for k in _LINE_KEY_ORDER if k in line}
            # include any extra keys not in the canonical list
            for k in line:
                if k not in ordered_line:
                    ordered_line[k] = line[k]
            ordered_lines.append(ordered_line)

        ordered_entry = {k: entry[k] for k in _ENTRY_KEY_ORDER if k in entry}
        ordered_entry["line"] = ordered_lines
        # include any extra header keys not in the canonical list
        for k in entry:
            if k not in ordered_entry:
                ordered_entry[k] = entry[k]
        result.append(ordered_entry)
    return result
