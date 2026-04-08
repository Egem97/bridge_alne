from .obreros import ObrerosTransformer
from ..mappings.sheets_loader import get_activity_normalizations_obreros


class VidaLeyTransformer(ObrerosTransformer):
    """Vida Ley shares the same activity normalizations as Obreros."""

    @property
    def ACTIVITY_NORMALIZATIONS(self):
        return get_activity_normalizations_obreros()
