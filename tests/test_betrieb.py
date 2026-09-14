"""Die Naht: Archiv rein, Tagesbild raus — inklusive gelernter Kurve."""

from datetime import date
from pathlib import Path

import pytest

from elevage import archiv
from elevage.betrieb import tagesbild, verzehrkurve
from elevage.mischung import baue_mischauftrag
from elevage.models import Ereignis, EreignisArt, Herde, Quelle, Tierart
from elevage.rezepte import REZEPT_DEMARRAGE

EINSTALL = date(2026, 3, 2)


@pytest.fixture()
def conn(tmp_path: Path):
    with archiv.oeffne(tmp_path / "b.db") as c:
        archiv.speichere_herde(
            c,
            Herde(
                tenant_id="hof",
                herde_id="H1",
                name="Stall Nord",
                tierart=Tierart.LEGEHENNE,
                einstalldatum=EINSTALL,
                tierzahl=1000,
            ),
        )
        yield c


def mische(conn, am: date, kg: float) -> None:
    archiv.protokolliere_mischung(
        conn, "hof", f"M-{am}", "H1", am, baue_mischauftrag(REZEPT_DEMARRAGE, kg)
    )


def test_ohne_mischung_steht_die_kurve_ganz_auf_richtwerten(conn):
    kurve, issues = verzehrkurve(conn, "hof", "H1")
    assert all(p.quelle is Quelle.RICHTWERT for p in kurve.punkte)
    assert any("Noch keine protokollierte Mischung" in i.text for i in issues)


def test_die_kurve_lernt_aus_dem_eigenen_mischprotokoll(conn):
    mische(conn, date(2026, 3, 9), 140.0)
    mische(conn, date(2026, 3, 16), 200.0)
    mische(conn, date(2026, 3, 23), 260.0)
    kurve, _ = verzehrkurve(conn, "hof", "H1")
    gemessen = [p for p in kurve.punkte if p.quelle is Quelle.GEMESSEN]
    assert [p.woche for p in gemessen] == [2, 3]
    # Ausgeglichen: 140 kg Ziel sind auch 140 kg im Mischer
    assert gemessen[0].gramm_je_tier_tag == pytest.approx(20.0, abs=0.1)


def test_tagesbild_zieht_quittungen_vorfaelle_und_kurve_zusammen(conn):
    archiv.melde_ereignis(
        conn,
        Ereignis(
            tenant_id="hof",
            herde_id="H1",
            ereignis_id="V1",
            art=EreignisArt.GUMBORO,
            festgestellt_am=date(2026, 3, 16),
        ),
    )
    bild = tagesbild(conn, "hof", "H1", date(2026, 3, 17), vorrat_kg=300.0)
    assert len(bild.vorfaelle) == 1
    assert any("Gumboro-Schema" in t.titel for t in bild.heute)
    assert bild.futter is not None and bild.futter.reicht_bis is not None


def test_vorfall_des_anderen_mandanten_loest_nichts_aus(conn):
    archiv.melde_ereignis(
        conn,
        Ereignis(
            tenant_id="fremder",
            herde_id="H1",
            ereignis_id="V-fremd",
            art=EreignisArt.GUMBORO,
            festgestellt_am=date(2026, 3, 16),
        ),
    )
    bild = tagesbild(conn, "hof", "H1", date(2026, 3, 17))
    assert bild.vorfaelle == []
    assert not any("Gumboro-Schema" in t.titel for t in bild.heute)


def test_unbekannte_herde_wirft_statt_zu_raten(conn):
    with pytest.raises(KeyError):
        tagesbild(conn, "hof", "XX", date(2026, 3, 17))


def test_eine_handaenderung_am_rezept_hinterlaesst_eine_spur(conn):
    """Der Ausgleich tat es längst — die bewusste Änderung gehört erst recht
    gegengelesen."""
    from datetime import date as _date

    from elevage.betrieb import passe_rezept_an
    from elevage.models import Rezeptanpassung

    passe_rezept_an(
        conn,
        "hof",
        Rezeptanpassung(
            tenant_id="hof",
            rezept_key="PONTE_AB_21",
            artikel_id="MAIS",
            kg_je_100=43.3,
            grund="am Original geprüft",
            geaendert_am=_date(2026, 9, 13),
        ),
    )
    vermerke = archiv.vermerke_fuer(conn, "hof")
    assert any(v.vermerk_id.startswith("anpassung:") for v in vermerke)
    text = next(v.text for v in vermerke if v.vermerk_id.startswith("anpassung:"))
    assert "43.30" in text and "Blatt: 50.00" in text
    assert "am Original geprüft" in text
