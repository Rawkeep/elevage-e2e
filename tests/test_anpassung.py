"""Rezeptmengen sind anpassbar — das Blatt bleibt trotzdem stehen."""

from datetime import date

from elevage.anpassung import geaendert, wirksames_rezept
from elevage.einstellung import (
    VORGABE_DOSIS,
    ausgleichsart,
    dosis_schluessel,
    notfall_dosis,
)
from elevage.models import Ausgleichsart, Herkunft, Rezeptanpassung, Tierart
from elevage.rezepte import REZEPT_PONTE

HEUTE = date(2026, 9, 13)


def anpassung(artikel_id: str, kg: float, **kw) -> Rezeptanpassung:
    return Rezeptanpassung(
        tenant_id="hof",
        rezept_key="PONTE_AB_21",
        artikel_id=artikel_id,
        kg_je_100=kg,
        geaendert_am=HEUTE,
        **kw,
    )


def test_das_blatt_wird_nie_ueberschrieben():
    wirksam = wirksames_rezept(REZEPT_PONTE, [anpassung("MAIS", 43.3)])
    assert wirksam.summe_je_100 == 100.0
    assert REZEPT_PONTE.summe_je_100 == 106.7  # unberührt


def test_der_blattwert_bleibt_neben_dem_betriebswert_stehen():
    wirksam = wirksames_rezept(REZEPT_PONTE, [anpassung("MAIS", 43.3, grund="geprüft")])
    mais = next(p for p in wirksam.posten if p.artikel_id == "MAIS")
    assert mais.herkunft is Herkunft.BETRIEB
    assert mais.blatt_kg_je_100 == 50.0
    assert mais.kg_je_100 == 43.3
    assert [p.artikel_id for p in geaendert(wirksam)] == ["MAIS"]


def test_unberuehrte_posten_behalten_ihre_herkunft():
    wirksam = wirksames_rezept(REZEPT_PONTE, [anpassung("MAIS", 43.3)])
    kalk = next(p for p in wirksam.posten if p.artikel_id == "COQUILLE")
    assert kalk.herkunft is Herkunft.BLATT
    assert kalk.blatt_kg_je_100 is None


def test_null_kg_heisst_der_posten_entfaellt():
    wirksam = wirksames_rezept(REZEPT_PONTE, [anpassung("LECENAN", 0.0)])
    lecenan = next(p for p in wirksam.posten if p.artikel_id == "LECENAN")
    assert lecenan.kg_je_100 == 0.0
    assert wirksam.summe_je_100 == 102.5


def test_der_betrieb_darf_einen_rohstoff_ergaenzen():
    wirksam = wirksames_rezept(REZEPT_PONTE, [anpassung("SEL", 0.3)])
    salz = next(p for p in wirksam.posten if p.artikel_id == "SEL")
    assert salz.herkunft is Herkunft.BETRIEB
    assert salz.blatt_kg_je_100 is None  # das Blatt kennt ihn nicht
    assert salz.name == "Salz"


def test_anpassungen_anderer_rezepte_greifen_nicht():
    fremd = anpassung("MAIS", 1.0).model_copy(update={"rezept_key": "DEMARRAGE_0_8"})
    wirksam = wirksames_rezept(REZEPT_PONTE, [fremd])
    assert wirksam.summe_je_100 == 106.7


def test_schreibweise_des_blattes_trifft_die_stammnummer():
    """AFABIND ist ALFABIND — sonst legt die Anpassung einen zweiten Posten an."""
    wirksam = wirksames_rezept(REZEPT_PONTE, [anpassung("AFABIND", 0.5)])
    binder = [p for p in wirksam.posten if p.artikel_id == "ALFABIND"]
    assert len(binder) == 1 and binder[0].kg_je_100 == 0.5


def test_notfall_dosis_faellt_auf_das_blatt_zurueck():
    dosis, vom_betrieb = notfall_dosis({}, Tierart.LEGEHENNE)
    assert dosis == VORGABE_DOSIS[Tierart.LEGEHENNE] and vom_betrieb is False


def test_gesetzte_notfall_dosis_gewinnt_und_sagt_es():
    werte = {dosis_schluessel(Tierart.LEGEHENNE): "0,75 g/l"}
    dosis, vom_betrieb = notfall_dosis(werte, Tierart.LEGEHENNE)
    assert dosis == "0,75 g/l" and vom_betrieb is True
    # die andere Linie bleibt beim Blattwert
    assert notfall_dosis(werte, Tierart.MASTHUHN) == (VORGABE_DOSIS[Tierart.MASTHUHN], False)


def test_ausgleichsart_hat_eine_vorgabe_und_faellt_nicht_um():
    assert ausgleichsart({}) is Ausgleichsart.AUSGLEICH
    assert ausgleichsart({"mischung.ausgleich": "VERBATIM"}) is Ausgleichsart.VERBATIM
    assert ausgleichsart({"mischung.ausgleich": "quatsch"}) is Ausgleichsart.AUSGLEICH
