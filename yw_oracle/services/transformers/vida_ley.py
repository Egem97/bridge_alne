from .obreros import ObrerosTransformer
from ..mappings.activities import ACTIVITY_NORMALIZATIONS_VIDA_LEY


class VidaLeyTransformer(ObrerosTransformer):
    """Vida Ley is nearly identical to Obreros. Only activity normalizations differ if needed."""
    ACTIVITY_NORMALIZATIONS = ACTIVITY_NORMALIZATIONS_VIDA_LEY
