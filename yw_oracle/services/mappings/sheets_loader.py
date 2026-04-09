"""
Google Sheets → mapping dicts loader with 3-minute TTL cache.

Sheets layout (each sheet has two columns: CLAVE ORIGINAL | CLAVE NORMALIZADA, with a header row):
    ACT OBREROS                    → ACTIVITY_NORMALIZATIONS_OBREROS
    ACT EMPLEADOS                  → ACTIVITY_NORMALIZATIONS_EMPLEADOS
    CLASE SWAP                     → SWAP_CLASS
    CLASE SWAP PACKING             → ACT_CLASS_PACKING
    ABREVIACION CLASE              → CLASS_ABBREVIATION_MAP
    ACCOUNT_REPLACEMENTS_OBREROS   → ACCOUNT_REPLACEMENTS_OBREROS
    ACCOUNT_FALLBACKS_OBREROS      → ACCOUNT_FALLBACKS_OBREROS (numeric values)
    ACCOUNT_FALLBACKS_EMPLEADOS    → ACCOUNT_FALLBACKS_EMPLEADOS (numeric values)

Falls back to the static .py dicts if Sheets is unreachable.
"""

import os
import time
import logging
import threading

import gspread
from google.oauth2.service_account import Credentials

from .activities import (
    ACTIVITY_NORMALIZATIONS_OBREROS   as _STATIC_ACT_OBREROS,
    ACTIVITY_NORMALIZATIONS_EMPLEADOS  as _STATIC_ACT_EMPLEADOS,
)
from .swap_class import (
    SWAP_CLASS        as _STATIC_SWAP_CLASS,
    ACT_CLASS_PACKING as _STATIC_ACT_CLASS_PACKING,
)
from .subsidiaries import CLASS_ABBREVIATION_MAP as _STATIC_CLASS_ABBREV
from .accounts import (
    ACCOUNT_REPLACEMENTS_OBREROS as _STATIC_ACCOUNT_REPLACEMENTS_OBREROS,
    ACCOUNT_FALLBACKS_OBREROS as _STATIC_ACCOUNT_FALLBACKS_OBREROS,
    ACCOUNT_FALLBACKS_EMPLEADOS as _STATIC_ACCOUNT_FALLBACKS_EMPLEADOS,
)

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

SPREADSHEET_ID  = "1HmDT65jqoZag90aozZrbjpm8gnXRBDEwPVMvpimo-40"
TTL_SECONDS     = 180   # 3 minutes

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Resolved at import time — file lives at the project root
_CREDENTIALS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "nifty-might-269005-cd303aaaa33f.json",
)

# Sheet name → dict name
_SHEET_MAP = {
    "ACT OBREROS":        "ACTIVITY_NORMALIZATIONS_OBREROS",
    "ACT EMPLEADOS":      "ACTIVITY_NORMALIZATIONS_EMPLEADOS",
    "CLASE SWAP":         "SWAP_CLASS",
    "CLASE SWAP PACKING": "ACT_CLASS_PACKING",
    "ABREVIACION CLASE":  "CLASS_ABBREVIATION_MAP",
    "ACCOUNT_REPLACEMENTS_OBREROS": "ACCOUNT_REPLACEMENTS_OBREROS",
    "ACCOUNT_FALLBACKS_OBREROS": "ACCOUNT_FALLBACKS_OBREROS",
    "ACCOUNT_FALLBACKS_EMPLEADOS": "ACCOUNT_FALLBACKS_EMPLEADOS",
}

# ── Internal cache state ───────────────────────────────────────────────────────

_cache: dict = {}
_cache_ts: float = 0.0
_lock = threading.Lock()


def _sheet_to_dict(worksheet) -> dict:
    """Convert a two-column worksheet (header row + data) into a Python dict."""
    rows = worksheet.get_all_values()
    if len(rows) < 2:
        return {}
    return {
        str(row[0]).strip(): str(row[1]).strip()
        for row in rows[1:]          # skip header
        if len(row) >= 2 and row[0]  # skip empty keys
    }


def _sheet_to_dict_numeric(worksheet) -> dict:
    """Convert a two-column worksheet to dict, trying to convert values to int/float, fallback to str."""
    rows = worksheet.get_all_values()
    if len(rows) < 2:
        return {}

    result = {}
    for row in rows[1:]:  # skip header
        if len(row) >= 2 and row[0]:  # skip empty keys
            key = str(row[0]).strip()
            val = str(row[1]).strip()

            # Try to convert value to int or float
            try:
                if "." in val:
                    result[key] = float(val)
                else:
                    result[key] = int(val)
            except ValueError:
                # Keep as string if conversion fails
                result[key] = val

    return result


def _fetch_from_sheets() -> dict:
    """Open the spreadsheet and read all sheets. Returns a dict of dicts."""
    creds = Credentials.from_service_account_file(_CREDENTIALS_FILE, scopes=_SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    result = {}
    # Sheets that need numeric value conversion
    numeric_sheets = {
        "ACCOUNT_FALLBACKS_OBREROS",
        "ACCOUNT_FALLBACKS_EMPLEADOS",
    }

    for sheet_name, dict_name in _SHEET_MAP.items():
        try:
            ws = spreadsheet.worksheet(sheet_name)
            # Use numeric converter for account fallback sheets
            if dict_name in numeric_sheets:
                result[dict_name] = _sheet_to_dict_numeric(ws)
            else:
                result[dict_name] = _sheet_to_dict(ws)
        except Exception as e:
            logger.warning(f"[SheetsLoader] Could not read sheet '{sheet_name}': {e}")
            result[dict_name] = None   # signal to use static fallback

    return result


def _get_cache() -> dict:
    """Return cached data, refreshing if TTL has expired."""
    global _cache, _cache_ts

    now = time.monotonic()
    if _cache and (now - _cache_ts) < TTL_SECONDS:
        return _cache

    with _lock:
        # Double-check inside lock
        now = time.monotonic()
        if _cache and (now - _cache_ts) < TTL_SECONDS:
            return _cache

        try:
            fresh = _fetch_from_sheets()
            _cache = fresh
            _cache_ts = now
            logger.info("[SheetsLoader] Mappings refreshed from Google Sheets.")
        except Exception as e:
            logger.error(f"[SheetsLoader] Refresh failed, using previous cache or static fallback: {e}")
            # Keep stale cache if available; otherwise _cache stays empty

    return _cache


# ── Public accessors ───────────────────────────────────────────────────────────

def get_activity_normalizations_obreros() -> dict:
    data = _get_cache().get("ACTIVITY_NORMALIZATIONS_OBREROS")
    if data is None:
        return _STATIC_ACT_OBREROS
    return {**_STATIC_ACT_OBREROS, **data}   # Sheets overrides static


def get_activity_normalizations_empleados() -> dict:
    data = _get_cache().get("ACTIVITY_NORMALIZATIONS_EMPLEADOS")
    if data is None:
        return _STATIC_ACT_EMPLEADOS
    return {**_STATIC_ACT_EMPLEADOS, **data}


def get_swap_class() -> dict:
    data = _get_cache().get("SWAP_CLASS")
    if data is None:
        return _STATIC_SWAP_CLASS
    return {**_STATIC_SWAP_CLASS, **data}


def get_act_class_packing() -> dict:
    data = _get_cache().get("ACT_CLASS_PACKING")
    if data is None:
        return _STATIC_ACT_CLASS_PACKING
    return {**_STATIC_ACT_CLASS_PACKING, **data}


def get_class_abbreviation_map() -> dict:
    data = _get_cache().get("CLASS_ABBREVIATION_MAP")
    if data is None:
        return _STATIC_CLASS_ABBREV
    return {**_STATIC_CLASS_ABBREV, **data}


def get_account_replacements_obreros() -> dict:
    """Load ACCOUNT_REPLACEMENTS_OBREROS from Google Sheets with fallback to static."""
    data = _get_cache().get("ACCOUNT_REPLACEMENTS_OBREROS")
    if data is None:
        return _STATIC_ACCOUNT_REPLACEMENTS_OBREROS
    return {**_STATIC_ACCOUNT_REPLACEMENTS_OBREROS, **data}


def get_account_fallbacks_obreros() -> dict:
    """Load ACCOUNT_FALLBACKS_OBREROS from Google Sheets with fallback to static."""
    data = _get_cache().get("ACCOUNT_FALLBACKS_OBREROS")
    if data is None:
        return _STATIC_ACCOUNT_FALLBACKS_OBREROS
    return {**_STATIC_ACCOUNT_FALLBACKS_OBREROS, **data}


def get_account_fallbacks_empleados() -> dict:
    """Load ACCOUNT_FALLBACKS_EMPLEADOS from Google Sheets with fallback to static."""
    data = _get_cache().get("ACCOUNT_FALLBACKS_EMPLEADOS")
    if data is None:
        return _STATIC_ACCOUNT_FALLBACKS_EMPLEADOS
    return {**_STATIC_ACCOUNT_FALLBACKS_EMPLEADOS, **data}
