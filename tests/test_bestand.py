"""Der Bestand ändert sich — und die Verzehrkurve muss das merken."""

from datetime import date

import pytest

from elevage.bestand import mittlere_tierzahl, rechne_bestand, tierzahl_am
from elevage.models import Abgangsgrund, Bestandsbewegung, Herde, Tierart
from elevage.verzehr import aus_mischungen

EINSTALL = date(2026, 3, 2)


def herde(tierzahl: int = 1000) -> Herde:
    return Herde(
        tenant_id="hof",
        herde_id="H1",
        name="Stall Nord",
        tierart=Tierart.LEGEHENNE,
        einstalldatum=EINSTALL,
        tierzahl=tierzahl,
    )


def abgang(
    am: date, tiere: int, grund: Abgangsgrund = Abgangsgrund.VERENDET, nr: str = ""
) -> Bestandsbewegung:
    return Bestandsbewegung(
        tenant_id="hof",
        herde_id="H1",
        bewegung_id=nr or f"b-{am}-{grund.value}",
        am=am,
        abgang=tiere,
        grund=grund,
    )


def test_ohne_bewegung_gilt_die_einstallzahl_und_das_wird_gesagt():
    stand = rechne_bestand(herde(), date(2026, 4, 1), [])
    assert stand.tierzahl == 1000
    assert any("Keine Bestandsbewegung erfasst" in i.text for i in stand.issues)


def test_abgaenge_zaehlen_bis_zum_stichtag_und_nicht_weiter():
    bewegungen = [abgang(date(2026, 3, 10), 20), abgang(date(2026, 4, 10), 30)]
    assert tierzahl_am(herde(), date(2026, 3, 31), bewegungen) == 980
    assert tierzahl_am(herde(), date(2026, 4, 30), bewegungen) == 950


def test_verkauft_ist_kein_verlust():
    """Sonst sieht ein Verkauf aus wie ein Ausbruch."""
    stand = rechne_bestand(
        herde(),
        date(2026, 4, 1),
        [abgang(date(2026, 3, 10), 100, Abgangsgrund.VERKAUFT)],
    )
    assert stand.tierzahl == 900
    assert stand.verluste_prozent == 0.0


def test_verluste_ueber_der_schwelle_werden_gemeldet():
    stand = rechne_bestand(herde(), date(2026, 6, 1), [abgang(date(2026, 3, 10), 60)])
    assert stand.verluste_prozent == 6.0
    assert any("Verluste seit dem Einstallen" in i.text for i in stand.issues)


def test_eine_haeufung_ist_etwas_anderes_als_dieselbe_zahl_ueber_monate():
    frisch = rechne_bestand(herde(), date(2026, 3, 12), [abgang(date(2026, 3, 10), 25)])
    assert any("Häufung" in i.text for i in frisch.issues)

    verteilt = rechne_bestand(
        herde(),
        date(2026, 6, 1),
        [abgang(date(2026, 3, 10), 12, nr="a"), abgang(date(2026, 4, 10), 13, nr="b")],
    )
    assert not any("Häufung" in i.text for i in verteilt.issues)


def test_mehr_abgaenge_als_tiere_ist_ein_befund_keine_negative_zahl():
    stand = rechne_bestand(herde(100), date(2026, 4, 1), [abgang(date(2026, 3, 10), 150)])
    assert stand.tierzahl == 0
    assert any("stimmt eine Buchung nicht" in i.text for i in stand.issues)


def test_fremde_herde_und_fremder_mandant_zaehlen_nicht_mit():
    fremd = abgang(date(2026, 3, 10), 50).model_copy(update={"herde_id": "H2"})
    anderer = abgang(date(2026, 3, 10), 50).model_copy(update={"tenant_id": "fremder"})
    assert tierzahl_am(herde(), date(2026, 4, 1), [fremd, anderer]) == 1000


def test_die_verzehrkurve_rechnet_mit_dem_echten_bestand():
    """Der stille Fehler: dieselbe Futtermenge auf zu viele Tiere."""
    h = herde(1000)
    bewegungen = [abgang(date(2026, 3, 5), 200)]
    mischungen = [(date(2026, 3, 9), 140.0), (date(2026, 3, 16), 200.0)]

    ohne, _ = aus_mischungen(h.tierart, h.tierzahl, h.einstalldatum, mischungen)
    mit, _ = aus_mischungen(
        h.tierart,
        h.tierzahl,
        h.einstalldatum,
        mischungen,
        lambda von, bis: mittlere_tierzahl(h, von, bis, bewegungen),
    )
    assert ohne.punkte[0].gramm_je_tier_tag == 20.0  # 140 kg / 1000 Tiere / 7 Tage
    assert mit.punkte[0].gramm_je_tier_tag == 25.0  # dieselbe Menge auf 800 Tiere
    assert mit.punkte[0].gramm_je_tier_tag > ohne.punkte[0].gramm_je_tier_tag


def test_mittlere_tierzahl_nimmt_anfang_und_ende():
    h = herde(1000)
    bewegungen = [abgang(date(2026, 3, 10), 100)]
    assert mittlere_tierzahl(h, date(2026, 3, 5), date(2026, 3, 15), bewegungen) == 950.0


def test_ein_bestand_von_null_bricht_die_kurve_nicht():
    h = herde(100)
    kurve, issues = aus_mischungen(
        h.tierart,
        h.tierzahl,
        h.einstalldatum,
        [(date(2026, 3, 9), 140.0), (date(2026, 3, 16), 200.0)],
        lambda von, bis: 0.0,
    )
    assert kurve.punkte == []
    assert issues


@pytest.mark.parametrize("grund", list(Abgangsgrund))
def test_jeder_grund_laesst_sich_buchen(grund):
    stand = rechne_bestand(herde(), date(2026, 4, 1), [abgang(date(2026, 3, 10), 10, grund)])
    assert stand.tierzahl == 990
