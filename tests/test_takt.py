"""Das Tagesbild: ein Stichtag, eine Herde, das ganze Bild."""

from datetime import date, timedelta

from elevage.models import Ampel, Herde, Quittung, Tierart
from elevage.takt import mischauftrag_fuer, naechster_schritt, rechne

EINSTALL = date(2026, 3, 2)


def herde(tierart=Tierart.LEGEHENNE, **kw) -> Herde:
    daten = dict(
        tenant_id="betrieb-1",
        herde_id="H1",
        name="Stall 1",
        tierart=tierart,
        einstalldatum=EINSTALL,
        tierzahl=1000,
    )
    daten.update(kw)
    return Herde(**daten)


def test_der_stichtag_kommt_herein_und_bestimmt_alles():
    """Zweimal derselbe Stichtag ⇒ zweimal dasselbe Bild. Keine Uhr im Kern."""
    a = rechne(herde(), date(2026, 4, 1))
    b = rechne(herde(), date(2026, 4, 1))
    assert a == b


def test_alter_und_phase_passen_zusammen():
    bild = rechne(herde(), EINSTALL + timedelta(days=6))  # Tag 7, Woche 1
    assert bild.alter_tage == 7
    assert bild.alter_wochen == 1
    assert bild.phase is not None and bild.phase.key == "DEMARRAGE_0_8"

    spaet = rechne(herde(), EINSTALL + timedelta(days=200))  # Woche 29
    assert spaet.phase is not None and spaet.phase.key == "PONTE_AB_21"


def test_ueberfaelliges_faerbt_das_ganze_bild_rot():
    bild = rechne(herde(), EINSTALL + timedelta(days=30))
    assert bild.ueberfaellig
    assert bild.ampel is Ampel.ROT


def test_alles_quittiert_ist_gruen():
    h = herde()
    stichtag = EINSTALL + timedelta(days=30)
    roh = rechne(h, stichtag)
    quittungen = [
        Quittung(
            tenant_id=h.tenant_id,
            herde_id=h.herde_id,
            schritt_key=t.schritt_key,
            quittung_id=f"q-{t.schritt_key}",
            erledigt_am=t.faellig_von,
        )
        for t in roh.ueberfaellig + roh.heute
    ]
    bild = rechne(h, stichtag, quittungen)
    assert not bild.ueberfaellig
    assert bild.ampel is Ampel.GRUEN
    assert len(bild.erledigt) == len(quittungen)


def test_bestellen_meldet_sich_vor_dem_termin():
    """Impfstoff muss da sein, bevor der Tag kommt."""
    h = herde()
    # Gumboro 1 liegt auf Tag 7, Vorlauf 3 Tage ⇒ an Tag 5 auf der Liste
    bild = rechne(h, EINSTALL + timedelta(days=4))
    keys = {t.schritt_key for t in bild.bestellen}
    assert "PONDEUSE_J7_GUMBORO_1" in keys


def test_naechster_schritt_setzt_ueberfaellig_nach_vorn():
    bild = rechne(herde(), EINSTALL + timedelta(days=30))
    n = naechster_schritt(bild)
    assert n is not None and n.ampel is Ampel.ROT


def test_masthuhn_bekommt_keinen_mischauftrag_und_sagt_warum():
    bild = rechne(herde(Tierart.MASTHUHN), EINSTALL + timedelta(days=10))
    assert bild.phase is None
    assert mischauftrag_fuer(bild, 500) is None
    assert any("kein Futterblatt" in i.text for i in bild.issues)


def test_widersprueche_der_blaetter_erreichen_das_tagesbild():
    """Ein Befund, der im Programm steckt, darf nicht im Modul versanden."""
    bild = rechne(herde(), EINSTALL + timedelta(days=10))
    text = " ".join(i.text for i in bild.issues)
    assert "GUMBORO" in text  # doppelte Zählung J12/J17
    assert "Tag 57-60" in text  # Zeile steht in Woche 7, datiert auf 57-60
    assert "Richtwerten" in text  # die Prognose sagt, worauf sie steht


def test_mischauftrag_der_laufenden_phase_gleicht_den_ueberhang_aus():
    bild = rechne(herde(), EINSTALL + timedelta(days=200))  # Ponte
    auftrag = mischauftrag_fuer(bild, 1000)
    assert auftrag is not None
    assert auftrag.freigegeben is True
    assert auftrag.ist_einwaage_kg == 1000.0
    assert auftrag.ausgleich_posten == "MAIS"


def test_verbatim_bleibt_verfuegbar_und_ehrlich():
    from elevage.models import Ausgleichsart

    bild = rechne(herde(), EINSTALL + timedelta(days=200))
    auftrag = mischauftrag_fuer(bild, 1000, art=Ausgleichsart.VERBATIM)
    assert auftrag is not None and auftrag.ist_einwaage_kg == 1067.0
