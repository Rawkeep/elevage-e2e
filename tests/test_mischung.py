"""Golden-File-Test gegen die 500er- und 1000er-Spalten der Blätter."""

import pytest

from elevage.mischung import baue_mischauftrag
from elevage.rezepte import REZEPT_DEMARRAGE, REZEPT_PONTE, REZEPT_POULETTE

# Die mittlere und rechte Spalte, wie sie auf dem Blatt stehen.
SPALTE_500_PONTE = [250, 70, 25, 95, 30, 40, 0.5, 0.5, 1.5, 21]
SPALTE_1000_PONTE = [500, 140, 50, 190, 60, 80, 1, 1, 3, 42]
SPALTE_500_DEMARRAGE = [302.5, 50, 60, 50, 25, 10, 2.5, 2.5, 1, 1, 1]
SPALTE_1000_POULETTE = [465, 40, 75, 50, 310, 25, 30, 5, 5, 2, 2, 2]


@pytest.mark.parametrize(
    "rezept,menge,erwartet",
    [
        (REZEPT_PONTE, 500, SPALTE_500_PONTE),
        (REZEPT_PONTE, 1000, SPALTE_1000_PONTE),
        (REZEPT_DEMARRAGE, 500, SPALTE_500_DEMARRAGE),
        (REZEPT_POULETTE, 1000, SPALTE_1000_POULETTE),
    ],
)
def test_hochrechnung_trifft_die_spalten_der_blaetter(rezept, menge, erwartet):
    auftrag = baue_mischauftrag(rezept, menge)
    assert [z.kg for z in auftrag.zeilen] == pytest.approx(erwartet)


def test_ponte_wird_gesperrt_und_meldet_die_echte_einwaage():
    auftrag = baue_mischauftrag(REZEPT_PONTE, 1000)
    assert auftrag.freigegeben is False
    assert auftrag.ist_einwaage_kg == 1067.0
    assert any("GESPERRT" in i for i in auftrag.issues)


def test_kleine_abweichung_laeuft_durch_wird_aber_gemeldet():
    auftrag = baue_mischauftrag(REZEPT_DEMARRAGE, 100)
    assert auftrag.freigegeben is True
    assert auftrag.ist_einwaage_kg == 101.1
    assert any("101.10 kg je 100 kg" in i for i in auftrag.issues)


def test_normieren_trifft_die_zielmenge_und_sagt_es():
    auftrag = baue_mischauftrag(REZEPT_PONTE, 1000, normieren=True)
    assert auftrag.freigegeben is True
    assert auftrag.ist_einwaage_kg == pytest.approx(1000.0, abs=0.05)
    assert any("normiert" in i for i in auftrag.issues)


def test_menge_null_ist_ein_fehler():
    with pytest.raises(ValueError):
        baue_mischauftrag(REZEPT_PONTE, 0)
