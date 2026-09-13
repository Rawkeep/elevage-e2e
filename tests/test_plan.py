"""Zeitrechnung, Ampel und Quittungen — der Kern des Taktgebers."""

from datetime import date

from elevage.models import Ampel, Herde, Quittung, Tierart
from elevage.plan import alter_in_tagen, alter_in_wochen, baue_termine, datum_von_tag

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


def test_j1_ist_der_einstalltag():
    h = herde()
    assert datum_von_tag(h, 1) == EINSTALL
    assert datum_von_tag(h, 0) == date(2026, 3, 1)  # Vorbereitung am Vortag
    assert datum_von_tag(h, 13) == date(2026, 3, 14)
    assert alter_in_tagen(h, EINSTALL) == 1


def test_wochenrechnung_bricht_an_tag_7_um():
    assert alter_in_wochen(1) == 1
    assert alter_in_wochen(7) == 1
    assert alter_in_wochen(8) == 2
    assert alter_in_wochen(141) == 21  # Beginn der Legeperiode


def test_ampel_kennt_vier_zustaende():
    h = herde()
    schritt = "PONDEUSE_J7_GUMBORO_1"  # Tag 7 = 8. März
    vorher = {t.schritt_key: t for t in baue_termine(h, date(2026, 3, 5))}
    dran = {t.schritt_key: t for t in baue_termine(h, date(2026, 3, 8))}
    danach = {t.schritt_key: t for t in baue_termine(h, date(2026, 3, 20))}
    assert vorher[schritt].ampel is Ampel.GRUEN
    assert dran[schritt].ampel is Ampel.GELB
    assert danach[schritt].ampel is Ampel.ROT


def test_erledigt_schlaegt_alles():
    h = herde()
    q = Quittung(
        tenant_id="betrieb-1",
        herde_id="H1",
        schritt_key="PONDEUSE_J7_GUMBORO_1",
        quittung_id="q-1",
        erledigt_am=date(2026, 3, 8),
        lot="LOT-4711",
    )
    t = {x.schritt_key: x for x in baue_termine(h, date(2026, 4, 1), [q])}
    assert t["PONDEUSE_J7_GUMBORO_1"].ampel is Ampel.ERLEDIGT
    assert t["PONDEUSE_J7_GUMBORO_1"].lot == "LOT-4711"


def test_doppelt_gesendete_quittung_aendert_nichts():
    """Offline-Sync darf dasselbe Ereignis beliebig oft nachreichen."""
    h = herde()
    basis = dict(
        tenant_id="betrieb-1",
        herde_id="H1",
        schritt_key="PONDEUSE_J7_GUMBORO_1",
        erledigt_am=date(2026, 3, 8),
    )
    einmal = baue_termine(h, date(2026, 4, 1), [Quittung(quittung_id="q-1", **basis)])
    zweimal = baue_termine(
        h,
        date(2026, 4, 1),
        [Quittung(quittung_id="q-1", **basis), Quittung(quittung_id="q-2", **basis)],
    )
    assert len(einmal) == len(zweimal)
    assert einmal == zweimal


def test_fremder_mandant_quittiert_nicht_mit():
    """Mandantentrennung greift auch im Kern, nicht erst in der Query."""
    h = herde()
    fremd = Quittung(
        tenant_id="betrieb-2",
        herde_id="H1",
        schritt_key="PONDEUSE_J7_GUMBORO_1",
        quittung_id="q-x",
        erledigt_am=date(2026, 3, 8),
    )
    t = {x.schritt_key: x for x in baue_termine(h, date(2026, 4, 1), [fremd])}
    assert t["PONDEUSE_J7_GUMBORO_1"].ampel is Ampel.ROT


def test_bedingte_schritte_haengen_an_einem_feld_der_herde():
    ohne = {t.schritt_key for t in baue_termine(herde(Tierart.MASTHUHN), EINSTALL)}
    assert "CHAIR_J18_GUMBORO_3" not in ohne
    assert "CHAIR_J30_ND_SPAET" not in ohne

    mit = {
        t.schritt_key
        for t in baue_termine(
            herde(Tierart.MASTHUHN, hoher_virusdruck=True, spaete_schlachtung=True),
            EINSTALL,
        )
    }
    assert "CHAIR_J18_GUMBORO_3" in mit
    assert "CHAIR_J40_ANTIKOKZIDIUM_SPAET" in mit


def test_legeperiode_wird_erst_im_horizont_entfaltet():
    h = herde()
    jung = {t.schritt_key for t in baue_termine(h, EINSTALL)}
    assert not any(k.startswith("PONTE_") for k in jung)

    alt = {t.schritt_key for t in baue_termine(h, EINSTALL.replace(month=9))}
    assert "PONTE_ND_1" in alt
    assert "PONTE_IB_IBIRD_1" in alt


def test_beide_linien_laufen_unabhaengig():
    mast = {t.schritt_key for t in baue_termine(herde(Tierart.MASTHUHN), EINSTALL)}
    lege = {t.schritt_key for t in baue_termine(herde(), EINSTALL)}
    assert mast and lege and not (mast & lege)
