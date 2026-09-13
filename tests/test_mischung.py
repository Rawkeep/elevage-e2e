"""Drei Wege mit einem Rezept, das nicht aufgeht — und die Spalten der Blätter."""

import pytest

from elevage.mischung import abweichung, baue_mischauftrag, vermerk_text
from elevage.models import Ausgleichsart
from elevage.rezepte import REZEPT_DEMARRAGE, REZEPT_PONTE, REZEPT_POULETTE

VERBATIM = Ausgleichsart.VERBATIM

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
def test_verbatim_trifft_die_spalten_der_blaetter(rezept, menge, erwartet):
    """Verbatim ist und bleibt das, was auf dem Zettel steht."""
    auftrag = baue_mischauftrag(rezept, menge, art=VERBATIM)
    assert [z.kg for z in auftrag.zeilen] == pytest.approx(erwartet)
    assert auftrag.freigegeben is True


def test_verbatim_sagt_was_wirklich_in_den_mischer_geht():
    auftrag = baue_mischauftrag(REZEPT_PONTE, 1000, art=VERBATIM)
    assert auftrag.ist_einwaage_kg == 1067.0
    assert any("1067.00 kg in den Mischer" in i for i in auftrag.issues)


def test_ausgleich_nimmt_den_ueberhang_aus_dem_energietraeger():
    """Mais trägt den Fehler, nicht Methionin und nicht der Muschelkalk."""
    auftrag = baue_mischauftrag(REZEPT_PONTE, 1000)
    nach_artikel = {z.artikel_id: z.kg for z in auftrag.zeilen}
    assert auftrag.ausgleich is Ausgleichsart.AUSGLEICH
    assert auftrag.ausgleich_posten == "MAIS"
    assert nach_artikel["MAIS"] == 433.0  # 50,0 - 6,7 = 43,3 je 100 kg
    assert nach_artikel["COQUILLE"] == 80.0  # unverändert
    assert nach_artikel["METHIONINE"] == 1.0  # unverändert
    assert auftrag.ist_einwaage_kg == 1000.0
    assert auftrag.freigegeben is True


def test_ausgleich_ist_die_vorgabe_und_meldet_sich():
    auftrag = baue_mischauftrag(REZEPT_PONTE, 1000)
    assert any("summiert auf 106.70" in i for i in auftrag.issues)
    assert any("Ausgeglichen über MAIS" in i for i in auftrag.issues)
    assert any("Prüfvermerk" in i for i in auftrag.issues)


def test_anteilig_trifft_die_menge_aendert_aber_jeden_anteil():
    auftrag = baue_mischauftrag(REZEPT_PONTE, 1000, art=Ausgleichsart.ANTEILIG)
    nach_artikel = {z.artikel_id: z.kg for z in auftrag.zeilen}
    assert auftrag.ist_einwaage_kg == pytest.approx(1000.0, abs=0.05)
    assert nach_artikel["COQUILLE"] < 80.0  # auch der Kalk sinkt
    assert any("auch Wirkstoffe und Kalk" in i for i in auftrag.issues)


def test_kleine_abweichung_wird_genauso_ausgeglichen():
    auftrag = baue_mischauftrag(REZEPT_DEMARRAGE, 100)
    mais = next(z.kg for z in auftrag.zeilen if z.artikel_id == "MAIS")
    assert mais == pytest.approx(59.4)  # 60,5 - 1,1
    assert auftrag.ist_einwaage_kg == 100.0


def test_zu_grosser_ueberhang_haelt_den_auftrag_an():
    """15 kg je 100 kg ist keine Abschreibfehler mehr, sondern eine andere Rezeptur."""
    kaputt = REZEPT_PONTE.model_copy(
        update={
            "posten": [
                p.model_copy(update={"kg_je_100": p.kg_je_100 + 20})
                if p.artikel_id == "SON_CUBE"
                else p
                for p in REZEPT_PONTE.posten
            ]
        }
    )
    auftrag = baue_mischauftrag(kaputt, 1000)
    assert auftrag.freigegeben is False
    assert any("GESPERRT" in i for i in auftrag.issues)


def test_ueberhang_groesser_als_der_ausgleichsposten_wird_nicht_verbogen():
    # Überhang +5,0 kg (unter der Sperrgrenze), aber Mais trägt nur 2,0 kg
    neue_mengen = {"MAIS": 2.0, "SON_CUBE": 65.3}
    schmal = REZEPT_PONTE.model_copy(
        update={
            "posten": [
                p.model_copy(update={"kg_je_100": neue_mengen[p.artikel_id]})
                if p.artikel_id in neue_mengen
                else p
                for p in REZEPT_PONTE.posten
            ]
        }
    )
    assert schmal.summe_je_100 == 105.0
    auftrag = baue_mischauftrag(schmal, 1000)
    assert auftrag.freigegeben is False
    assert any("größer als der Ausgleichsposten" in i for i in auftrag.issues)


def test_sauberes_rezept_braucht_keinen_ausgleich():
    sauber = REZEPT_PONTE.model_copy(
        update={
            "posten": [
                p.model_copy(update={"kg_je_100": 43.3}) if p.artikel_id == "MAIS" else p
                for p in REZEPT_PONTE.posten
            ]
        }
    )
    auftrag = baue_mischauftrag(sauber, 1000)
    assert auftrag.issues == []
    assert auftrag.ausgleich is Ausgleichsart.VERBATIM
    assert auftrag.ist_einwaage_kg == 1000.0


def test_posten_mit_null_kg_faellt_aus_der_waageliste():
    ohne = REZEPT_PONTE.model_copy(
        update={
            "posten": [
                p.model_copy(update={"kg_je_100": 0.0}) if p.artikel_id == "LECENAN" else p
                for p in REZEPT_PONTE.posten
            ]
        }
    )
    auftrag = baue_mischauftrag(ohne, 1000, art=Ausgleichsart.VERBATIM)
    assert "LECENAN" not in {z.artikel_id for z in auftrag.zeilen}


def test_vermerktext_nennt_zahl_quelle_und_auftrag():
    text = vermerk_text(REZEPT_PONTE, "MAIS", 50.0, 43.3)
    assert "+6.70" in text and "50.00 → 43.30" in text
    assert "Betriebsblatt" in text and "Bitte am Original prüfen" in text
    assert abweichung(REZEPT_PONTE) == 6.7


def test_menge_null_ist_ein_fehler():
    with pytest.raises(ValueError):
        baue_mischauftrag(REZEPT_PONTE, 0)
