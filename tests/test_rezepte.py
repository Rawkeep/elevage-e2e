"""Die Rezepte sind Stammdaten — hier wird gegen die Blätter gegengerechnet."""

from elevage.models import Tierart
from elevage.rezepte import (
    ARTIKEL_ALIAS,
    REZEPT_DEMARRAGE,
    REZEPT_PONTE,
    REZEPT_POULETTE,
    rezept_fuer,
)


def test_summen_weichen_ab_wie_auf_dem_blatt():
    """Nicht 'reparieren': die Abweichung IST der Befund."""
    assert REZEPT_DEMARRAGE.summe_je_100 == 101.1
    assert REZEPT_POULETTE.summe_je_100 == 101.1
    assert REZEPT_PONTE.summe_je_100 == 106.7


def test_ein_rohstoff_eine_nummer():
    """Das Blatt schreibt ALFABIND und AFABIND — der Stamm kennt einen."""
    assert ARTIKEL_ALIAS["AFABIND"] == "ALFABIND"
    ids = {p.artikel_id for p in REZEPT_DEMARRAGE.posten}
    assert "AFABIND" not in ids and "ALFABIND" in ids


def test_phasenwechsel_an_den_richtigen_wochen():
    L = Tierart.LEGEHENNE
    assert rezept_fuer(L, 1).key == "DEMARRAGE_0_8"
    assert rezept_fuer(L, 8).key == "DEMARRAGE_0_8"
    assert rezept_fuer(L, 9).key == "POULETTE_8_21"
    assert rezept_fuer(L, 21).key == "POULETTE_8_21"
    assert rezept_fuer(L, 22).key == "PONTE_AB_21"
    assert rezept_fuer(L, 80).key == "PONTE_AB_21"


def test_masthuhn_hat_kein_futterblatt():
    """Ehrlich fehlend statt still geraten."""
    assert rezept_fuer(Tierart.MASTHUHN, 3) is None
