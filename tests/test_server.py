"""Durchstich gegen den echten Server: starten, anfragen, abhaken, widerrufen."""

import json
import threading
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from elevage import archiv
from elevage.models import Herde, Tierart
from elevage.server import starte

EINSTALL = date(2026, 3, 2)
STICHTAG = "2026-03-20"


@pytest.fixture()
def dienst(tmp_path: Path):
    db = tmp_path / "srv.db"
    with archiv.oeffne(db) as conn:
        archiv.speichere_herde(
            conn,
            Herde(
                tenant_id="hof",
                herde_id="H1",
                name="Stall Nord",
                tierart=Tierart.LEGEHENNE,
                einstalldatum=EINSTALL,
                tierzahl=1000,
            ),
        )
    server = starte(port=0, db=db)
    faden = threading.Thread(target=server.serve_forever, daemon=True)
    faden.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def hole(url: str) -> dict:
    with urlopen(url, timeout=10) as antwort:
        return json.loads(antwort.read())


def sende(url: str, daten: dict) -> dict:
    anfrage = Request(
        url,
        data=json.dumps(daten).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(anfrage, timeout=10) as antwort:
        return json.loads(antwort.read())


def test_startseite_ist_die_seite(dienst):
    with urlopen(dienst, timeout=10) as antwort:
        text = antwort.read().decode()
        assert antwort.headers["Content-Type"].startswith("text/html")
        assert antwort.headers["Content-Security-Policy"]
        assert antwort.headers["X-Content-Type-Options"] == "nosniff"
    assert "<title>Taktgeber</title>" in text


def test_herden_kommen_in_camelcase(dienst):
    daten = hole(f"{dienst}/api/herden?betrieb=hof")
    assert daten["herden"][0]["herdeId"] == "H1"
    assert daten["herden"][0]["einstalldatum"] == "2026-03-02"


def test_fremder_betrieb_sieht_nichts(dienst):
    assert hole(f"{dienst}/api/herden?betrieb=fremder")["herden"] == []


def test_tagesbild_liefert_das_ganze_bild(dienst):
    bild = hole(f"{dienst}/api/tagesbild?betrieb=hof&herde=H1&stichtag={STICHTAG}&vorrat=300")
    assert bild["alterTage"] == 19
    assert bild["ampel"] == "ROT"
    assert bild["futter"]["bedarfJeTagKg"] > 0
    assert bild["ueberfaellig"][0]["schrittKey"]
    assert bild["issues"]


def test_abhaken_und_wieder_widerrufen(dienst):
    schritt = "PONDEUSE_J7_GUMBORO_1"
    antwort = sende(
        f"{dienst}/api/quittung",
        {"betrieb": "hof", "herde": "H1", "schritt": schritt, "am": "2026-03-08"},
    )
    assert antwort["neu"] is True
    bild = hole(f"{dienst}/api/tagesbild?betrieb=hof&herde=H1&stichtag={STICHTAG}")
    assert any(t["schrittKey"] == schritt for t in bild["erledigt"])

    sende(
        f"{dienst}/api/quittung/widerrufen",
        {"betrieb": "hof", "quittungId": antwort["quittungId"]},
    )
    zurueck = hole(f"{dienst}/api/tagesbild?betrieb=hof&herde=H1&stichtag={STICHTAG}")
    assert any(t["schrittKey"] == schritt for t in zurueck["ueberfaellig"])


def test_vorfall_setzt_das_schema_in_den_plan(dienst):
    sende(
        f"{dienst}/api/vorfall",
        {"betrieb": "hof", "herde": "H1", "art": "GUMBORO", "am": "2026-03-19"},
    )
    bild = hole(f"{dienst}/api/tagesbild?betrieb=hof&herde=H1&stichtag={STICHTAG}")
    assert any("Gumboro-Schema" in t["titel"] for t in bild["heute"])
    assert bild["vorfaelle"][0]["art"] == "GUMBORO"


def test_mischung_rechnen_und_buchen(dienst):
    antwort = sende(
        f"{dienst}/api/mischung",
        {"betrieb": "hof", "herde": "H1", "kg": 500, "am": STICHTAG, "buchen": True},
    )
    assert antwort["auftrag"]["istEinwaageKg"] == 505.5
    assert antwort["gebucht"] is True
    kurve = hole(f"{dienst}/api/verzehr?betrieb=hof&herde=H1")
    assert kurve["kurve"]["punkte"]


def test_gesperrte_mischung_wird_abgelehnt_statt_gebucht(dienst):
    """Ponte summiert auf 106,7 kg — buchen muss scheitern."""
    with pytest.raises(HTTPError) as fehler:
        sende(
            f"{dienst}/api/mischung",
            {"betrieb": "hof", "herde": "H1", "kg": 1000, "am": "2026-09-01", "buchen": True},
        )
    assert fehler.value.code == 409


def test_unbekannte_herde_und_pfad_melden_sich_sauber(dienst):
    with pytest.raises(HTTPError) as fehler:
        hole(f"{dienst}/api/tagesbild?betrieb=hof&herde=XX&stichtag={STICHTAG}")
    assert fehler.value.code == 404
    with pytest.raises(HTTPError) as anderer:
        hole(f"{dienst}/api/gibtsnicht")
    assert anderer.value.code == 404


def test_kaputtes_datum_ist_ein_400(dienst):
    with pytest.raises(HTTPError) as fehler:
        hole(f"{dienst}/api/tagesbild?betrieb=hof&herde=H1&stichtag=gestern")
    assert fehler.value.code == 400
