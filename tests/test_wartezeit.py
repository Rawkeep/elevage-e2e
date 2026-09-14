"""Wartezeiten: unbekannt ist nicht null, und die Frist läuft ab der letzten Gabe."""

from datetime import date

from elevage.models import Erzeugnis, Herde, Praeparat, Quittung, Tierart
from elevage.plan import schritte_fuer
from elevage.wartezeit import (
    berechne_sperren,
    freigabe_ab,
    offene,
    praeparat_id,
)

EINSTALL = date(2026, 3, 2)


def herde(tierart: Tierart = Tierart.LEGEHENNE) -> Herde:
    return Herde(
        tenant_id="hof",
        herde_id="H1",
        name="Stall Nord",
        tierart=tierart,
        einstalldatum=EINSTALL,
        tierzahl=1000,
    )


def mittel(name: str, eier: int | None = None, fleisch: int | None = None) -> Praeparat:
    return Praeparat(
        tenant_id="hof",
        praeparat_id=praeparat_id(name),
        name=name,
        wartezeit_eier_tage=eier,
        wartezeit_fleisch_tage=fleisch,
        quelle="Beipackzettel",
    )


def quittung(schritt: str, am: date, praeparat: str | None = None) -> Quittung:
    return Quittung(
        tenant_id="hof",
        herde_id="H1",
        schritt_key=schritt,
        quittung_id=f"q-{schritt}",
        erledigt_am=am,
        praeparat=praeparat,
    )


def rechne(quittungen, praeparate, tierart=Tierart.LEGEHENNE, stichtag=date(2026, 3, 10)):
    h = herde(tierart)
    return berechne_sperren(h, stichtag, quittungen, schritte_fuer(h, stichtag), praeparate)


# PONDEUSE_J2_ANTIBIOTIKUM läuft Tag 2 bis 6 = 3. bis 7. März.
ANTIBIOTIKUM = "PONDEUSE_J2_ANTIBIOTIKUM"


def test_die_frist_laeuft_ab_der_letzten_gabe_nicht_ab_dem_abhaken():
    """Abgehakt am ersten Tag, gegeben bis zum fünften — es zählt der fünfte."""
    sperren, _ = rechne(
        [quittung(ANTIBIOTIKUM, date(2026, 3, 3), "COVIT")], [mittel("COVIT", eier=7)]
    )
    assert len(sperren) == 1
    assert sperren[0].letzte_gabe == date(2026, 3, 7)  # bis_tag 6 = 7. März
    assert sperren[0].freigabe_ab == date(2026, 3, 14)  # + 7 Tage
    assert sperren[0].erzeugnis is Erzeugnis.EIER


def test_unbekannte_wartezeit_ist_keine_freigabe():
    """Die härteste Regel: kein Eintrag heißt Befund, nicht null."""
    sperren, issues = rechne([quittung(ANTIBIOTIKUM, date(2026, 3, 3), "COVIT")], [mittel("COVIT")])
    assert sperren == []
    assert any("Unbekannt ist nicht null" in i.text for i in issues)


def test_ohne_angabe_des_mittels_wird_nicht_geraten():
    sperren, issues = rechne([quittung(ANTIBIOTIKUM, date(2026, 3, 3))], [])
    assert sperren == []
    assert any("ohne Angabe, welches Mittel" in i.text for i in issues)


def test_ein_unbekanntes_mittel_faellt_auf():
    sperren, issues = rechne(
        [quittung(ANTIBIOTIKUM, date(2026, 3, 3), "IRGENDWAS")], [mittel("COVIT", eier=7)]
    )
    assert sperren == []
    assert any("IRGENDWAS" in i.text for i in issues)


def test_laeuft_noch_haengt_am_stichtag():
    q = [quittung(ANTIBIOTIKUM, date(2026, 3, 3), "COVIT")]
    m = [mittel("COVIT", eier=7)]
    vorher, _ = rechne(q, m, stichtag=date(2026, 3, 13))
    genau, _ = rechne(q, m, stichtag=date(2026, 3, 14))
    assert vorher[0].laeuft_noch is True
    assert genau[0].laeuft_noch is False  # am Freigabetag darf wieder verkauft werden
    assert freigabe_ab(vorher) == date(2026, 3, 14)
    assert freigabe_ab(genau) is None


def test_masthuhn_fragt_nach_fleisch_nicht_nach_eiern():
    sperren, issues = rechne(
        [quittung("CHAIR_J2_ANTIBIOTIKUM", date(2026, 3, 3), "COVIT")],
        [mittel("COVIT", eier=7)],  # nur Eier hinterlegt
        tierart=Tierart.MASTHUHN,
    )
    assert sperren == []
    assert any("COVIT" in i.text for i in issues)

    mit_fleisch, _ = rechne(
        [quittung("CHAIR_J2_ANTIBIOTIKUM", date(2026, 3, 3), "COVIT")],
        [mittel("COVIT", eier=7, fleisch=5)],
        tierart=Tierart.MASTHUHN,
    )
    assert mit_fleisch[0].erzeugnis is Erzeugnis.FLEISCH
    assert mit_fleisch[0].wartezeit_tage == 5


def test_vitamine_und_hygiene_brauchen_keine_wartezeit():
    """Sonst erzeugt jeder Starttrunk einen Befund und niemand liest sie mehr."""
    sperren, issues = rechne([quittung("PONDEUSE_J1_START", date(2026, 3, 2))], [])
    assert sperren == [] and issues == []


def test_die_spaeteste_sperre_gewinnt():
    sperren, _ = rechne(
        [
            quittung(ANTIBIOTIKUM, date(2026, 3, 3), "COVIT"),
            quittung("PONDEUSE_J7_GUMBORO_1", date(2026, 3, 8), "CEVAC GUMBO L"),
        ],
        [mittel("COVIT", eier=7), mittel("CEVAC GUMBO L", eier=21)],
        stichtag=date(2026, 3, 20),
    )
    assert len(offene(sperren)) == 1
    assert freigabe_ab(sperren) == date(2026, 3, 29)  # 8. März + 21 Tage


def test_die_nummer_ignoriert_schreibweise_und_beiwerk():
    assert praeparat_id("CEVAC GUMBO L") == praeparat_id("cevac-gumbo l")
    sperren, _ = rechne(
        [quittung(ANTIBIOTIKUM, date(2026, 3, 3), "covit")], [mittel("COVIT", eier=7)]
    )
    assert len(sperren) == 1


def test_fremde_herde_erzeugt_keine_sperre():
    fremd = quittung(ANTIBIOTIKUM, date(2026, 3, 3), "COVIT").model_copy(update={"herde_id": "H2"})
    sperren, _ = rechne([fremd], [mittel("COVIT", eier=7)])
    assert sperren == []
