"""Durchstich gegen den echten Server: starten, anfragen, abhaken, widerrufen."""

import json
import threading
from datetime import date
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

import pytest

from elevage import archiv
from elevage.anmeldung import hashe_passwort
from elevage.models import Benutzer, Herde, Rolle, Tierart
from elevage.server import starte

EINSTALL = date(2026, 3, 2)
STICHTAG = "2026-03-20"
PASSWORT = "stallwaechter2026"


def _benutzer(conn, anmeldename: str, rolle: Rolle, tenant: str = "hof") -> None:
    archiv.lege_benutzer_an(
        conn,
        Benutzer(
            tenant_id=tenant,
            benutzer_id=anmeldename,
            name=f"Person {anmeldename}",
            rolle=rolle,
            angelegt_am=date(2026, 1, 1),
        ),
        hashe_passwort(PASSWORT),
    )


@pytest.fixture()
def dienst(tmp_path: Path):
    db = tmp_path / "srv.db"
    with archiv.oeffne(db) as conn:
        for tenant in ("hof", "fremder"):
            archiv.speichere_herde(
                conn,
                Herde(
                    tenant_id=tenant,
                    herde_id="H1",
                    name="Stall Nord" if tenant == "hof" else "Fremder Stall",
                    tierart=Tierart.LEGEHENNE,
                    einstalldatum=EINSTALL,
                    tierzahl=1000,
                ),
            )
        _benutzer(conn, "leitung", Rolle.LEITUNG)
        _benutzer(conn, "stall", Rolle.STALL)
        _benutzer(conn, "leser", Rolle.LESER)
        _benutzer(conn, "nachbar", Rolle.LEITUNG, tenant="fremder")
    server = starte(port=0, db=db)
    faden = threading.Thread(target=server.serve_forever, daemon=True)
    faden.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


class Sitzung:
    """Ein angemeldeter Browser: hält das Cookie über die ganze Runde."""

    def __init__(self, basis: str, anmeldename: str = "leitung") -> None:
        self.basis = basis
        self.oeffner = build_opener(HTTPCookieProcessor(CookieJar()))
        self.sende("/api/anmelden", {"benutzer": anmeldename, "passwort": PASSWORT})

    def hole(self, pfad: str) -> dict:
        with self.oeffner.open(self.basis + pfad, timeout=10) as antwort:
            return json.loads(antwort.read())

    def sende(self, pfad: str, daten: dict) -> dict:
        anfrage = Request(
            self.basis + pfad,
            data=json.dumps(daten).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.oeffner.open(anfrage, timeout=10) as antwort:
            return json.loads(antwort.read())

    def roh(self, pfad: str):
        return self.oeffner.open(self.basis + pfad, timeout=10)


@pytest.fixture()
def angemeldet(dienst):
    return Sitzung(dienst)


def test_startseite_ist_die_seite(angemeldet):
    with angemeldet.roh("/") as antwort:
        text = antwort.read().decode()
        assert antwort.headers["Content-Type"].startswith("text/html")
        assert antwort.headers["Content-Security-Policy"]
        assert antwort.headers["X-Content-Type-Options"] == "nosniff"
    assert "<title>Taktgeber</title>" in text


def test_herden_kommen_in_camelcase(angemeldet):
    daten = angemeldet.hole("/api/herden")
    assert daten["herden"][0]["herdeId"] == "H1"
    assert daten["herden"][0]["einstalldatum"] == "2026-03-02"


def test_der_betrieb_kommt_aus_der_sitzung_nicht_aus_der_anfrage(angemeldet):
    """Ein Parameter darf den Mandanten nicht mehr wechseln."""
    eigen = angemeldet.hole("/api/herden")["herden"]
    versucht = angemeldet.hole("/api/herden?betrieb=fremder")["herden"]
    assert eigen == versucht
    assert [h["name"] for h in eigen] == ["Stall Nord"]


def test_tagesbild_liefert_das_ganze_bild(angemeldet):
    bild = angemeldet.hole(f"/api/tagesbild?herde=H1&stichtag={STICHTAG}&vorrat=300")
    assert bild["alterTage"] == 19
    assert bild["ampel"] == "ROT"
    assert bild["futter"]["bedarfJeTagKg"] > 0
    assert bild["ueberfaellig"][0]["schrittKey"]
    assert bild["issues"]


def test_abhaken_und_wieder_widerrufen(angemeldet):
    schritt = "PONDEUSE_J7_GUMBORO_1"
    antwort = angemeldet.sende(
        "/api/quittung",
        {"herde": "H1", "schritt": schritt, "am": "2026-03-08"},
    )
    assert antwort["neu"] is True
    bild = angemeldet.hole(f"/api/tagesbild?herde=H1&stichtag={STICHTAG}")
    assert any(t["schrittKey"] == schritt for t in bild["erledigt"])

    angemeldet.sende(
        "/api/quittung/widerrufen",
        {"quittungId": antwort["quittungId"]},
    )
    zurueck = angemeldet.hole(f"/api/tagesbild?herde=H1&stichtag={STICHTAG}")
    assert any(t["schrittKey"] == schritt for t in zurueck["ueberfaellig"])


def test_vorfall_setzt_das_schema_in_den_plan(angemeldet):
    angemeldet.sende(
        "/api/vorfall",
        {"herde": "H1", "art": "GUMBORO", "am": "2026-03-19"},
    )
    bild = angemeldet.hole(f"/api/tagesbild?herde=H1&stichtag={STICHTAG}")
    assert any("Gumboro-Schema" in t["titel"] for t in bild["heute"])
    assert bild["vorfaelle"][0]["art"] == "GUMBORO"


def test_mischung_rechnen_und_buchen(angemeldet):
    antwort = angemeldet.sende(
        "/api/mischung",
        {"herde": "H1", "kg": 500, "am": STICHTAG, "buchen": True},
    )
    assert antwort["auftrag"]["istEinwaageKg"] == 500.0
    assert antwort["auftrag"]["ausgleich"] == "AUSGLEICH"
    assert antwort["gebucht"] is True
    kurve = angemeldet.hole("/api/verzehr?herde=H1")
    assert kurve["kurve"]["punkte"]


def test_verbatim_buchen_scheitert_weil_die_menge_nicht_stimmt(angemeldet):
    """Verbatim gibt 1067 statt 1000 kg — das darf nicht ins Protokoll."""
    antwort = angemeldet.sende(
        "/api/mischung",
        {"herde": "H1", "kg": 1000, "am": "2026-09-01", "art": "VERBATIM"},
    )
    assert antwort["auftrag"]["istEinwaageKg"] == 1067.0
    assert antwort["gebucht"] is False


def test_ausgleich_wird_als_pruefvermerk_hinterlegt(angemeldet):
    angemeldet.sende(
        "/api/mischung",
        {"herde": "H1", "kg": 1000, "am": "2026-09-01"},
    )
    bild = angemeldet.hole("/api/tagesbild?herde=H1&stichtag=2026-09-01")
    assert any("ausgleich:" in v["vermerkId"] for v in bild["vermerke"])


def test_unbekannte_herde_und_pfad_melden_sich_sauber(angemeldet):
    with pytest.raises(HTTPError) as fehler:
        angemeldet.hole(f"/api/tagesbild?herde=XX&stichtag={STICHTAG}")
    assert fehler.value.code == 404
    with pytest.raises(HTTPError) as anderer:
        angemeldet.hole("/api/gibtsnicht")
    assert anderer.value.code == 404


def test_kaputtes_datum_ist_ein_400(angemeldet):
    with pytest.raises(HTTPError) as fehler:
        angemeldet.hole("/api/tagesbild?herde=H1&stichtag=gestern")
    assert fehler.value.code == 400


# --- Anmeldung, Rollen, Mandantengrenze ---------------------------------


def test_ohne_anmeldung_gibt_es_keine_daten(dienst):
    for pfad in ("/api/herden", f"/api/tagesbild?herde=H1&stichtag={STICHTAG}", "/api/ich"):
        with pytest.raises(HTTPError) as fehler:
            urlopen(dienst + pfad, timeout=10)
        assert fehler.value.code == 401, pfad


def test_startseite_schickt_unangemeldete_zur_anmeldung(dienst):
    with urlopen(dienst + "/", timeout=10) as antwort:
        assert "Anmeldung" in antwort.read().decode()
        assert antwort.url.endswith("/anmelden")


def test_falsches_passwort_verraet_nicht_ob_das_konto_existiert(dienst):
    meldungen = set()
    for name, passwort in (("leitung", "falschfalsch"), ("gibtsnicht", PASSWORT)):
        with pytest.raises(HTTPError) as fehler:
            anfrage = Request(
                dienst + "/api/anmelden",
                data=json.dumps({"benutzer": name, "passwort": passwort}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urlopen(anfrage, timeout=10)
        assert fehler.value.code == 401
        meldungen.add(json.loads(fehler.value.read())["fehler"])
    assert len(meldungen) == 1


def test_zu_viele_fehlversuche_werden_gebremst(dienst):
    def versuch() -> int:
        anfrage = Request(
            dienst + "/api/anmelden",
            data=json.dumps({"benutzer": "stall", "passwort": "immerfalsch"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(anfrage, timeout=10)
        except HTTPError as fehler:
            return fehler.code
        return 200

    codes = [versuch() for _ in range(7)]
    assert codes[:5] == [401] * 5
    assert codes[-1] == 429


def test_das_cookie_ist_httponly_und_samesite_strict(dienst):
    anfrage = Request(
        dienst + "/api/anmelden",
        data=json.dumps({"benutzer": "leitung", "passwort": PASSWORT}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(anfrage, timeout=10) as antwort:
        keks = antwort.headers["Set-Cookie"]
    assert "HttpOnly" in keks and "SameSite=Strict" in keks


def test_abmelden_macht_die_sitzung_ungueltig(dienst):
    sitzung = Sitzung(dienst)
    assert sitzung.hole("/api/ich")["benutzerId"] == "leitung"
    sitzung.sende("/api/abmelden", {})
    with pytest.raises(HTTPError) as fehler:
        sitzung.hole("/api/ich")
    assert fehler.value.code == 401


def test_leser_darf_sehen_aber_nicht_abhaken(dienst):
    leser = Sitzung(dienst, "leser")
    assert leser.hole("/api/herden")["herden"]
    with pytest.raises(HTTPError) as fehler:
        leser.sende(
            "/api/quittung",
            {"herde": "H1", "schritt": "PONDEUSE_J7_GUMBORO_1", "am": "2026-03-08"},
        )
    assert fehler.value.code == 403


def test_nur_die_leitung_hakt_einen_pruefvermerk_ab(dienst):
    """Ein Vermerk abhaken heißt: am Original verglichen — das ist Leitung."""
    stall = Sitzung(dienst, "stall")
    stall.sende("/api/mischung", {"herde": "H1", "kg": 1000, "am": "2026-09-01"})
    bild = stall.hole("/api/tagesbild?herde=H1&stichtag=2026-09-01")
    nummer = bild["vermerke"][0]["vermerkId"]
    with pytest.raises(HTTPError) as fehler:
        stall.sende("/api/vermerk/abhaken", {"vermerkId": nummer, "am": "2026-09-01"})
    assert fehler.value.code == 403
    assert Sitzung(dienst, "leitung").sende(
        "/api/vermerk/abhaken", {"vermerkId": nummer, "am": "2026-09-01"}
    )["abgehakt"]


def test_der_nachbarbetrieb_sieht_seine_eigenen_herden(dienst):
    """Mandantentrennung hängt jetzt am Konto, nicht an einem Parameter."""
    nachbar = Sitzung(dienst, "nachbar")
    assert [h["name"] for h in nachbar.hole("/api/herden")["herden"]] == ["Fremder Stall"]
    eigen = Sitzung(dienst).hole("/api/herden")["herden"]
    assert [h["name"] for h in eigen] == ["Stall Nord"]


def test_quittung_traegt_den_namen_des_angemeldeten(dienst):
    sitzung = Sitzung(dienst, "stall")
    sitzung.sende(
        "/api/quittung",
        {"herde": "H1", "schritt": "PONDEUSE_J7_GUMBORO_1", "am": "2026-03-08"},
    )
    bild = sitzung.hole(f"/api/tagesbild?herde=H1&stichtag={STICHTAG}")
    assert any(t["schrittKey"] == "PONDEUSE_J7_GUMBORO_1" for t in bild["erledigt"])


def test_fremde_herkunft_wird_abgewiesen(dienst):
    sitzung = Sitzung(dienst)
    anfrage = Request(
        dienst + "/api/quittung",
        data=json.dumps({"herde": "H1", "schritt": "X", "am": "2026-03-08"}).encode(),
        headers={"Content-Type": "application/json", "Origin": "https://boeser-hof.example"},
        method="POST",
    )
    with pytest.raises(HTTPError) as fehler:
        sitzung.oeffner.open(anfrage, timeout=10)
    assert fehler.value.code == 403


def test_wartezeit_wird_beim_abhaken_mitgefuehrt(dienst):
    leitung = Sitzung(dienst, "leitung")
    leitung.sende(
        "/api/praeparat",
        {"name": "COVIT", "wartezeitEierTage": 7, "quelle": "Beipackzettel"},
    )
    assert leitung.hole("/api/praeparate")["praeparate"][0]["wartezeitEierTage"] == 7

    leitung.sende(
        "/api/quittung",
        {
            "herde": "H1",
            "schritt": "PONDEUSE_J2_ANTIBIOTIKUM",
            "am": "2026-03-03",
            "praeparat": "COVIT",
        },
    )
    bild = leitung.hole("/api/tagesbild?herde=H1&stichtag=2026-03-10")
    sperre = bild["sperren"][0]
    assert sperre["freigabeAb"] == "2026-03-14"
    assert sperre["laeuftNoch"] is True


def test_ohne_wartezeit_gibt_es_einen_befund_statt_einer_freigabe(dienst):
    stall = Sitzung(dienst, "stall")
    stall.sende(
        "/api/quittung",
        {
            "herde": "H1",
            "schritt": "PONDEUSE_J2_ANTIBIOTIKUM",
            "am": "2026-03-03",
            "praeparat": "COVIT",
        },
    )
    bild = stall.hole("/api/tagesbild?herde=H1&stichtag=2026-03-10")
    assert bild["sperren"] == []
    assert any("Unbekannt ist nicht null" in i for i in bild["issues"])


def test_nur_die_leitung_traegt_eine_wartezeit_ein(dienst):
    """Für eine Wartezeit geradezustehen ist keine Handgriff-Entscheidung."""
    with pytest.raises(HTTPError) as fehler:
        Sitzung(dienst, "stall").sende("/api/praeparat", {"name": "COVIT", "wartezeitEierTage": 7})
    assert fehler.value.code == 403


def test_ein_mittel_ohne_jede_zahl_wird_abgewiesen(dienst):
    with pytest.raises(HTTPError) as fehler:
        Sitzung(dienst, "leitung").sende("/api/praeparat", {"name": "COVIT"})
    assert fehler.value.code == 400


def test_abgang_senkt_den_bestand_und_hebt_den_verzehr(dienst):
    stall = Sitzung(dienst, "stall")
    vorher = stall.hole(f"/api/tagesbild?herde=H1&stichtag={STICHTAG}")
    assert vorher["bestand"]["tierzahl"] == 1000

    stall.sende(
        "/api/abgang",
        {"herde": "H1", "tiere": 200, "grund": "VERENDET", "am": "2026-03-05"},
    )
    nachher = stall.hole(f"/api/tagesbild?herde=H1&stichtag={STICHTAG}")
    assert nachher["bestand"]["tierzahl"] == 800
    assert nachher["bestand"]["verlusteProzent"] == 20.0
    assert nachher["futter"]["bedarfJeTagKg"] < vorher["futter"]["bedarfJeTagKg"]
    assert any("Verluste seit dem Einstallen" in i for i in nachher["issues"])


def test_derselbe_abgang_zweimal_gebucht_zaehlt_einmal(dienst):
    stall = Sitzung(dienst, "stall")
    daten = {"herde": "H1", "tiere": 20, "grund": "VERENDET", "am": "2026-03-05"}
    assert stall.sende("/api/abgang", daten)["neu"] is True
    assert stall.sende("/api/abgang", daten)["neu"] is False
    bild = stall.hole(f"/api/tagesbild?herde=H1&stichtag={STICHTAG}")
    assert bild["bestand"]["tierzahl"] == 980


def test_ein_leser_bucht_keine_abgaenge(dienst):
    with pytest.raises(HTTPError) as fehler:
        Sitzung(dienst, "leser").sende(
            "/api/abgang", {"herde": "H1", "tiere": 5, "am": "2026-03-05"}
        )
    assert fehler.value.code == 403


# --- Gesundheit, Passwort, Zeitzone -------------------------------------


def test_health_braucht_keine_anmeldung_und_verraet_nichts(dienst):
    """Ein Wächter hat kein Cookie — und soll keine Betriebszahlen sehen."""
    with urlopen(dienst + "/api/health", timeout=10) as antwort:
        stand = json.loads(antwort.read())
    assert stand["status"] == "ok"
    assert set(stand) == {"status", "version", "commit"}


def test_die_seite_zeigt_den_versionsstempel(angemeldet):
    with angemeldet.roh("/") as antwort:
        assert 'id="stempel"' in antwort.read().decode()


def test_passwort_aendern_verlangt_das_alte(dienst):
    sitzung = Sitzung(dienst, "stall")
    with pytest.raises(HTTPError) as fehler:
        sitzung.sende("/api/passwort", {"alt": "falschfalsch", "neu": "neuespasswort2026"})
    assert fehler.value.code == 401


def test_ein_zu_kurzes_passwort_wird_abgewiesen(dienst):
    with pytest.raises(HTTPError) as fehler:
        Sitzung(dienst, "stall").sende("/api/passwort", {"alt": PASSWORT, "neu": "kurz"})
    assert fehler.value.code == 400


def test_nach_dem_passwortwechsel_gilt_kein_altes_cookie(dienst):
    """Wer sein Passwort ändert, vermutet oft, dass es jemand kennt."""
    alte = Sitzung(dienst, "stall")
    zweite = Sitzung(dienst, "stall")
    alte.sende("/api/passwort", {"alt": PASSWORT, "neu": "einneuesgutes2026"})

    for sitzung in (alte, zweite):
        with pytest.raises(HTTPError) as fehler:
            sitzung.hole("/api/ich")
        assert fehler.value.code == 401

    neu = Sitzung.__new__(Sitzung)
    neu.basis = dienst
    neu.oeffner = build_opener(HTTPCookieProcessor(CookieJar()))
    neu.sende("/api/anmelden", {"benutzer": "stall", "passwort": "einneuesgutes2026"})
    assert neu.hole("/api/ich")["benutzerId"] == "stall"
